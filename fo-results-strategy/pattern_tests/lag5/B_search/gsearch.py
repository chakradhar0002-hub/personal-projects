"""
gsearch.py -- rule search engine for the lag > 5% group (extends ../../five_pct/A_rule_search/rulelib.py).

Conditions come from rulelib.build_conditions (cuts from the training rows passed in).  The searcher evaluates
  * every 1-condition and every 2-condition rule (exhaustive),
  * 3-condition rules by beam search (top `beam` pairs per objective x min-trades x side, each extended by every
    compatible third condition; triples de-duplicated exactly as in rulelib),
for three objectives:
  mean   pooled average P&L of the rule's training trades
  fpos   share of training quarters with picks whose average P&L > 0  (+ 0.5 x pooled average as a tie-break)
  worst  the worst training-quarter average P&L
Each with min trades m and picks in >= minq training quarters.  Long (P&L = +y) and short (P&L = -y).
"""
import os, sys
os.environ.setdefault('OPENBLAS_NUM_THREADS', '2')
import numpy as np, pandas as pd
sys.path.insert(0, os.environ.get('LAB_ROOT', 'lab') + '/five_pct/A_rule_search')
import rulelib as RL

HERE = os.path.dirname(os.path.abspath(__file__))
COST = 0.0017
OBJS = ('mean', 'fpos', 'worst')
NUM_FEATS = RL.NUM_FEATS
CAT_FEATS = RL.CAT_FEATS


def load_group(universe='fo', lag=-0.05):
    df = pd.read_csv(f'{RL.HERE}/features_all.csv')
    if universe == 'fo':
        df = df[df.in_fo]
    df = df[df.vs_nifty_1m < lag]
    return df.sort_values(['qn', 'results_date', 'symbol']).reset_index(drop=True)


def build_conditions(df, train_mask):
    return RL.build_conditions(df, train_mask, min_train=15, min_cat=20)


rule_str = RL.rule_str
rule_mask = RL.rule_mask


class GSearcher:
    def __init__(self, Mtr, qid, compat, ms=(15, 30, 60), minq=6):
        X = Mtr.astype(np.float32)
        self.X = X
        self.C, self.N = X.shape
        self.compat = compat
        self.ms, self.minq = ms, minq
        upper = np.triu(compat, 1)
        self.n_pairs = int(upper.sum())
        qs = np.unique(qid)
        self.qidx = [np.where(qid == q)[0] for q in qs]
        self.Xq = [np.ascontiguousarray(X[:, ix]) for ix in self.qidx]
        self.K1 = X.sum(1)
        self.K1q = np.stack([Xq.sum(1) for Xq in self.Xq])
        self.Q1 = (self.K1q > 0).sum(0)
        K2 = X @ X.T
        K2q = [(Xq @ Xq.T) for Xq in self.Xq]
        Q2 = np.zeros((self.C, self.C), np.int16)
        for K in K2q:
            Q2 += K > 0.5
        keep = upper & (K2 >= min(ms)) & (Q2 >= minq)
        self.idx2 = np.flatnonzero(keep)
        self.K2 = K2.ravel()[self.idx2]
        self.Q2 = Q2.ravel()[self.idx2]
        self.K2q = np.stack([K.ravel()[self.idx2] for K in K2q])
        self.n_pairs_eligible = len(self.idx2)

    @staticmethod
    def _top_idx(score, k):
        k = min(k, int(np.isfinite(score).sum()))
        if k <= 0:
            return np.array([], int)
        idx = np.argpartition(-score, k - 1)[:k]
        return idx[np.argsort(-score[idx], kind='stable')]

    @staticmethod
    def _qstats(Sq, Kq):
        """Sq, Kq: (nq x n) per-quarter sums and counts -> pos_long, pos_short, worst_long, worst_short."""
        h = Kq > 0.5
        mq = Sq / np.maximum(Kq, 1)
        posl = (h & (mq > 0)).sum(0); poss = (h & (mq < 0)).sum(0)
        wl = np.where(h, mq, np.inf).min(0); ws = np.where(h, -mq, np.inf).min(0)
        return posl, poss, wl, ws

    @staticmethod
    def _obj(o, sgn, mean, st, nq):
        posl, poss, wl, ws = st
        if o == 'mean':
            return sgn * mean
        if o == 'fpos':
            return (posl if sgn > 0 else poss) / np.maximum(nq, 1) + 0.5 * sgn * mean
        return wl if sgn > 0 else ws

    def run(self, y, beam=300, ntop=30, objs=OBJS):
        X, C, ms, minq = self.X, self.C, self.ms, self.minq
        y = y.astype(np.float32)
        yq = [y[ix] for ix in self.qidx]
        # ---- level 1
        S1 = X @ y
        S1q = np.stack([Xq @ yy for Xq, yy in zip(self.Xq, yq)])
        mean1 = S1 / np.maximum(self.K1, 1)
        st1 = self._qstats(S1q, self.K1q)
        # ---- level 2 (eligible pairs only, flat)
        S2 = ((X * y) @ X.T).ravel()[self.idx2]
        S2q = np.stack([((Xq * yy) @ Xq.T).ravel()[self.idx2] for Xq, yy in zip(self.Xq, yq)])
        mean2 = S2 / self.K2
        st2 = self._qstats(S2q, self.K2q)
        del S2q
        ob2 = {}
        beam_flat = set()
        v2s = {m: (self.K2 >= m) & (self.Q2 >= minq) for m in ms}
        for o in objs:
            for sgn in (1, -1):
                ob = self._obj(o, sgn, mean2, st2, self.Q2).astype(np.float64)
                ob2[(o, sgn)] = ob
                for m in ms:
                    t = self._top_idx(np.where(v2s[m], ob, -np.inf), beam)
                    beam_flat.update(self.idx2[t].tolist())
        bf = np.array(sorted(beam_flat), dtype=np.int64)
        a, b = np.divmod(bf, C)
        inbeam = np.zeros((C, C), bool)
        inbeam.ravel()[bf] = True
        # ---- level 3 (beam pairs x third condition)
        P = X[a] * X[b]
        K3 = P @ X.T
        Kq3 = [P[:, ix] @ Xq.T for ix, Xq in zip(self.qidx, self.Xq)]
        Q3 = np.zeros(K3.shape, np.int16)
        for K in Kq3:
            Q3 += K > 0.5
        A_ = a[:, None]; B_ = b[:, None]; c_ = np.arange(C)[None, :]
        lo1 = np.minimum(A_, c_); hi1 = np.maximum(A_, c_)
        lo2 = np.minimum(B_, c_); hi2 = np.maximum(B_, c_)
        sm1 = (lo1 < A_) | ((lo1 == A_) & (hi1 < B_))
        sm2 = (lo2 < A_) | ((lo2 == A_) & (hi2 < B_))
        canon = ~(inbeam[lo1, hi1] & sm1) & ~(inbeam[lo2, hi2] & sm2)
        del lo1, hi1, lo2, hi2, sm1, sm2
        valid3 = canon & self.compat[a] & self.compat[b] & (K3 >= min(ms)) & (Q3 >= minq)
        n_triples_all = int((canon & self.compat[a] & self.compat[b]).sum())
        idx3 = np.flatnonzero(valid3)
        K3f = K3.ravel()[idx3]; Q3f = Q3.ravel()[idx3]
        S3f = ((P * y) @ X.T).ravel()[idx3]
        S3q = np.stack([((P[:, ix] * yy) @ Xq.T).ravel()[idx3] for ix, Xq, yy in zip(self.qidx, self.Xq, yq)])
        K3q = np.stack([K.ravel()[idx3] for K in Kq3])
        del Kq3
        mean3 = S3f / K3f
        st3 = self._qstats(S3q, K3q)
        del S3q, K3q
        out = {'n_conditions': C, 'n_pairs': self.n_pairs, 'n_beam_pairs': len(bf), 'n_triples': n_triples_all}
        for m in ms:
            v1 = (self.K1 >= m) & (self.Q1 >= minq)
            v3 = (K3f >= m)
            for o in objs:
                for sgn in (1, -1):
                    cands = []
                    o1 = np.where(v1, self._obj(o, sgn, mean1, st1, self.Q1), -np.inf)
                    pl1, ps1 = st1[0], st1[1]
                    for i in self._top_idx(o1, ntop):
                        cands.append((float(o1[i]), float(sgn * mean1[i]), int(self.K1[i]), 1, (int(i),), sgn,
                                      int(self.Q1[i]), int(pl1[i] if sgn > 0 else ps1[i])))
                    o2 = np.where(v2s[m], ob2[(o, sgn)], -np.inf)
                    for t in self._top_idx(o2, ntop):
                        i, j = divmod(int(self.idx2[t]), C)
                        cands.append((float(o2[t]), float(sgn * mean2[t]), int(self.K2[t]), 2, (i, j), sgn,
                                      int(self.Q2[t]), int(st2[0][t] if sgn > 0 else st2[1][t])))
                    o3 = np.where(v3, self._obj(o, sgn, mean3, st3, Q3f), -np.inf)
                    for t in self._top_idx(o3, ntop):
                        r_, j = divmod(int(idx3[t]), C)
                        cands.append((float(o3[t]), float(sgn * mean3[t]), int(K3f[t]), 3,
                                      tuple(sorted((int(a[r_]), int(b[r_]), j))), sgn,
                                      int(Q3f[t]), int(st3[0][t] if sgn > 0 else st3[1][t])))
                    cands.sort(key=lambda z: (-round(z[0], 9), -z[1], z[3]))
                    seen, top = set(), []
                    for c in cands:
                        if c[4] in seen:
                            continue
                        seen.add(c[4]); top.append(c)
                    out[(o, m, sgn)] = top[:ntop]
        return out


def best_either(res, o, m):
    """single best rule of either side for objective o and min trades m."""
    L, S = res[(o, m, 1)], res[(o, m, -1)]
    c = [x for x in (L[:1] + S[:1])]
    c.sort(key=lambda z: (-z[0], -z[1], z[3]))
    return c[0] if c else None


def signflip(y, qn, rng):
    qm = pd.Series(y).groupby(qn).transform('mean').values
    return qm + rng.choice([-1.0, 1.0], len(y)) * (y - qm)


def shuffle_within(y, qn, rng):
    return RL.shuffle_within(y, qn, rng)


def stats(pnl, qn, prefix=''):
    """pnl fraction -> percent stats incl. quarter counts."""
    pnl = np.asarray(pnl, float); qn = np.asarray(qn)
    n = len(pnl)
    if n == 0:
        return {prefix + 'trades': 0}
    qa = pd.Series(pnl).groupby(qn).mean()
    srt = np.sort(pnl)[::-1]
    return {prefix + 'trades': n, prefix + 'avg_pct': 100 * pnl.mean(), prefix + 'avg_net_pct': 100 * (pnl.mean() - COST),
            prefix + 'up_pct': 100 * (pnl > 0).mean(), prefix + 'median_pct': 100 * np.median(pnl),
            prefix + 'q_with': int(len(qa)), prefix + 'q_pos': int((qa > 0).sum()),
            prefix + 'worst_q_pct': 100 * qa.min(), prefix + 'without_best5_pct': 100 * srt[5:].mean() if n > 5 else np.nan}
