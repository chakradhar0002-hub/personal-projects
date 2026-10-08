"""
rulelib.py -- shared code for the exhaustive 1/2/3-condition rule search.

A condition is  feature >= cut  or  feature <= cut  (cuts = percentiles 5,10,15,20,30,...,80,85,90,95
of the TRAINING rows only), or  category == value  (fin_type, sector_index, industry, fiscal quarter).
A missing feature value makes the condition false.
A rule is an AND of 1, 2 or 3 conditions, traded long (P&L = +three_day) or short (P&L = -three_day).
Selection objective: pooled average P&L of the rule's trades in the training quarters, subject to a
minimum number of trades m (10/20/30) and picks in at least `minq` distinct training quarters.
3-condition rules: beam search -- the top `beam` 2-condition rules for every (m, long/short) are each
extended with every compatible third condition.
"""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS', '2')
import numpy as np, pandas as pd

HERE = os.environ.get('LAB_ROOT', 'lab') + '/five_pct/A_rule_search'
CUT_PCTS = [5, 10, 15, 20, 30, 40, 50, 60, 70, 80, 85, 90, 95]
COST = 0.0017

NUM_FEATS = [
    # features.csv (results time / after_close deliberately excluded)
    'r1w', 'r1m', 'r3m', 'r6m', 'r1y', 'r3y', 'r5y', 'from_52w_high', 'from_52w_low', 'vs_ma50', 'vs_ma200',
    'vol60', 'volume_5d_vs_60d', 'sector_1w', 'vs_sector_1w', 'vs_nifty_1w', 'nifty_1w', 'sector_1m',
    'vs_sector_1m', 'vs_nifty_1m', 'nifty_1m', 'sector_3m', 'vs_sector_3m', 'vs_nifty_3m', 'nifty_3m',
    'india_vix', 'prev1_3d', 'prev2_sum', 'past_avg_3d', 'past_pct_up', 'prev1_next20', 'prev_pat_yoy',
    'prev_sales_yoy', 'profit_rising_4q', 'sales_rising_4q', 'prev_net_margin', 'pe', 'pb', 'roe',
    'debt_equity', 'pe_vs_peers', 'log_mcap', 'days_since_dividend', 'iv_t5', 'iv_vs_realised',
    'days_after_quarter_end', 'peers_reported_3d', 'peers_reported_n', 'season_so_far_3d',
    # sector_features.csv extras
    'sec_vs_nifty_1w', 'sec_vs_nifty_1m', 'sec_vs_nifty_3m', 'sec_rank_1m', 'sec_rank_3m', 'sec_vs_50dma',
    'sec_vs_200dma', 'sec_from_52w_high', 'sec_reported_3d',
    # new cutoff-time features (01_build_features.py)
    'd0', 'd1', 'd2', 'r2d', 'r3d', 'r10d', 'r20d', 'gap0', 'intra0', 'gap5', 'intra5', 'nifty_d0',
    'nifty_3d', 'exn_d0', 'exn_3d', 'exn_10d', 'sec_d0', 'sec_3d', 'exs_3d', 'dist_20h', 'dist_20l',
    'dist_60h', 'vol5_60', 'vol20_60', 'maxabs5', 'z5', 'z20', 'up10', 'streak', 'pre5', 'own_dm1', 'own_rd',
    'own_dp1', 'own_abs3d', 'pre5_vs_own', 'n_prior', 'cal_days',
]
CAT_FEATS = ['fin_type', 'sector_index', 'industry', 'fq']


def load(universe='fo'):
    df = pd.read_csv(f'{HERE}/features_all.csv')
    if universe == 'fo':
        df = df[df.in_fo].reset_index(drop=True)
    df = df.sort_values(['qn', 'results_date', 'symbol']).reset_index(drop=True)
    return df


def build_conditions(df, train_mask, min_train=10, min_cat=30):
    """Return (Xbool C x N over ALL rows of df, list of condition descriptors, feat id, dir id)."""
    names, feat, dirn, masks = [], [], [], []
    for fi, f in enumerate(NUM_FEATS):
        x = df[f].values.astype(float)
        xt = x[train_mask]
        xt = xt[np.isfinite(xt)]
        if len(xt) < 50:
            continue
        cuts = np.unique(np.percentile(xt, CUT_PCTS))
        with np.errstate(invalid='ignore'):
            for c in cuts:
                names.append((f, '>=', float(c))); feat.append(fi); dirn.append(0); masks.append(x >= c)
                names.append((f, '<=', float(c))); feat.append(fi); dirn.append(1); masks.append(x <= c)
    for k, f in enumerate(CAT_FEATS):
        vals = df[f].astype(str).values
        vc = pd.Series(vals[train_mask]).value_counts()
        for v, cnt in vc.items():
            if cnt >= min_cat and v != 'nan':
                names.append((f, '==', v)); feat.append(1000 + k); dirn.append(2); masks.append(vals == v)
    M = np.array(masks)
    ntr = M[:, train_mask].sum(1)
    keep = (ntr >= min_train) & (ntr < train_mask.sum())
    seen, idx = set(), []
    for i in np.where(keep)[0]:
        key = np.packbits(M[i]).tobytes()
        if key in seen:
            continue
        seen.add(key); idx.append(i)
    idx = np.array(idx)
    feat = np.array(feat)[idx]; dirn = np.array(dirn)[idx]
    names = [names[i] for i in idx]
    M = M[idx]
    same = feat[:, None] == feat[None, :]
    bad = same & ((dirn[:, None] == dirn[None, :]) | (dirn[:, None] == 2))
    compat = ~bad
    np.fill_diagonal(compat, False)
    return M, names, compat


def rule_str(names, conds, sign):
    parts = []
    for c in conds:
        f, op, v = names[c]
        parts.append(f'{f} {op} {v:.4g}' if op != '==' else f'{f} == {v}')
    return ('LONG: ' if sign > 0 else 'SHORT: ') + ' AND '.join(parts)


def rule_mask(M, conds):
    m = M[conds[0]].copy()
    for c in conds[1:]:
        m &= M[c]
    return m


class Searcher:
    """Pre-computes the y-independent parts (trade counts, quarter coverage) on training rows."""

    def __init__(self, Mtr, qid, compat, Mte=None):
        self.X = Mtr.astype(np.float32)
        self.C, self.N = self.X.shape
        self.compat = compat
        self.upper = np.triu(compat, 1)
        qs = np.unique(qid)
        self.qidx = [np.where(qid == q)[0] for q in qs]
        self.Xq = [np.ascontiguousarray(self.X[:, ix]) for ix in self.qidx]
        self.K1 = self.X.sum(1)
        self.Q1 = np.zeros(self.C, np.int16)
        for Xq in self.Xq:
            self.Q1 += Xq.sum(1) > 0
        self.K2 = self.X @ self.X.T
        self.Q2 = np.zeros((self.C, self.C), np.uint8)
        for Xq in self.Xq:
            self.Q2 += (Xq @ Xq.T) > 0.5
        self.Xte = None
        if Mte is not None:
            self.Xte = Mte.astype(np.float32)
            self.K1te = self.Xte.sum(1)
            self.K2te = self.Xte @ self.Xte.T
        self.n_pairs = int(self.upper.sum())

    def _top_idx(self, score, k):
        flat = score.ravel()
        k = min(k, int(np.isfinite(flat).sum()))
        if k <= 0:
            return np.array([], int)
        idx = np.argpartition(-flat, k - 1)[:k]
        return idx[np.argsort(-flat[idx])]

    def run(self, y, ms=(10, 20, 30), minq=4, beam=1000, n0=0.0, ntop=100, yte=None, collect_oos_gt5=False,
            count_eligible=False):
        X, C = self.X, self.C
        y = y.astype(np.float32)
        S1 = X @ y
        S2 = (X * y) @ X.T
        res = {'n_conditions': C, 'n_pairs': self.n_pairs}
        if yte is not None:
            yte = yte.astype(np.float32)
            S1te = self.Xte @ yte
            S2te = (self.Xte * yte) @ self.Xte.T
        with np.errstate(invalid='ignore', divide='ignore'):
            mean1 = S1 / self.K1
            mean2 = S2 / self.K2
            base2 = S2 / (self.K2 + n0)
        # ---- beam selection of pairs for the 3-condition extension
        inbeam = np.zeros((C, C), bool)
        v2s = {}
        for m in ms:
            v2 = self.upper & (self.K2 >= m) & (self.Q2 >= minq)
            v2s[m] = v2
            for sgn in (1, -1):
                obj = np.where(v2, sgn * base2, -np.inf)
                top = self._top_idx(obj, beam)
                inbeam.ravel()[top] = True
        a, b = np.nonzero(inbeam)          # a < b because only the upper triangle is eligible
        P = X[a] * X[b]
        S3 = (P * y) @ X.T
        K3 = P @ X.T
        Q3 = np.zeros(K3.shape, np.uint8)
        for ix, Xq in zip(self.qidx, self.Xq):
            Q3 += (P[:, ix] @ Xq.T) > 0.5
        # a triple {a,b,c} can be reached from up to 3 beam pairs; keep it only from the
        # lexicographically smallest of its sub-pairs that is in the beam (exact de-duplication)
        A_ = a[:, None]; B_ = b[:, None]; c_ = np.arange(C)[None, :]
        lo1 = np.minimum(A_, c_); hi1 = np.maximum(A_, c_)
        lo2 = np.minimum(B_, c_); hi2 = np.maximum(B_, c_)
        sm1 = (lo1 < A_) | ((lo1 == A_) & (hi1 < B_))
        sm2 = (lo2 < A_) | ((lo2 == A_) & (hi2 < B_))
        canon = ~(inbeam[lo1, hi1] & sm1) & ~(inbeam[lo2, hi2] & sm2)
        del lo1, hi1, lo2, hi2, sm1, sm2
        valid3 = canon & self.compat[a] & self.compat[b]
        if yte is not None:
            Pte = self.Xte[a] * self.Xte[b]
            S3te = (Pte * yte) @ self.Xte.T
            K3te = Pte @ self.Xte.T
        res['n_triples_evaluated'] = int(valid3.sum())
        res['n_beam_pairs'] = len(a)
        with np.errstate(invalid='ignore', divide='ignore'):
            mean3 = S3 / K3
            base3 = S3 / (K3 + n0)
        absm1, absm2, absm3 = np.abs(mean1), np.abs(mean2), np.abs(mean3)
        for m in ms:
            r = {}
            v1 = (self.K1 >= m) & (self.Q1 >= minq)
            v2 = v2s[m]
            v3 = valid3 & (K3 >= m) & (Q3 >= minq)
            cands = []  # (obj, mean, n, level, conds, sign)
            for sgn in (1, -1):
                for i in np.where(v1)[0]:
                    cands.append((sgn * S1[i] / (self.K1[i] + n0), sgn * mean1[i], int(self.K1[i]), 1, (int(i),), sgn))
                obj2 = np.where(v2, sgn * base2, -np.inf)
                for t in self._top_idx(obj2, 3 * ntop):
                    i, j = divmod(int(t), C)
                    cands.append((obj2[i, j], sgn * mean2[i, j], int(self.K2[i, j]), 2, (i, j), sgn))
                obj3 = np.where(v3, sgn * base3, -np.inf)
                for t in self._top_idx(obj3, 6 * ntop):
                    i, j = divmod(int(t), C)
                    cands.append((obj3[i, j], sgn * mean3[i, j], int(K3[i, j]), 3,
                                  tuple(sorted((int(a[i]), int(b[i]), j))), sgn))
            g1 = v1 & (absm1 > 0.05); g2 = v2 & (absm2 > 0.05); g3 = v3 & (absm3 > 0.05)
            r['count_gt5'] = {1: int(g1.sum()), 2: int(g2.sum()), 3: int(g3.sum())}
            r['count_gt5_long'] = {1: int((v1 & (mean1 > 0.05)).sum()), 2: int((v2 & (mean2 > 0.05)).sum()),
                                   3: int((v3 & (mean3 > 0.05)).sum())}
            if count_eligible:
                r['n_eligible'] = {1: int(v1.sum()) * 2, 2: int(v2.sum()) * 2, 3: int(v3.sum()) * 2}
            cands.sort(key=lambda z: -z[0])
            seen, top = set(), []
            for c in cands:
                k = (c[4], c[5])
                if k in seen:
                    continue
                seen.add(k); top.append(c)
            r['top'] = top[:ntop]
            r['best_by_level'] = {}
            for L in (1, 2, 3):
                tl = [c for c in top if c[3] == L]
                r['best_by_level'][L] = tl[0] if tl else None
            r['top_upto2'] = [c for c in top if c[3] <= 2][:ntop]
            r['top_upto1'] = [c for c in top if c[3] <= 1][:ntop]
            if yte is not None and collect_oos_gt5:
                oo = {1: (np.sign(mean1[g1]) * S1te[g1], self.K1te[g1]),
                      2: (np.sign(mean2[g2]) * S2te[g2], self.K2te[g2]),
                      3: (np.sign(mean3[g3]) * S3te[g3], K3te[g3])}
                r['oos_gt5'] = {L: summarize_oos(*oo[L]) for L in oo}
            res[m] = r
        return res


def summarize_oos(s, n):
    s = np.asarray(s, float); n = np.asarray(n, float)
    has = n > 0
    out = {'n_rules': int(len(n)), 'n_with_oos_trades': int(has.sum())}
    if has.sum():
        avg = s[has] / n[has]
        out.update(mean_of_rule_avgs=float(avg.mean()), median_rule_avg=float(np.median(avg)),
                   frac_gt0=float((avg > 0).mean()), frac_gt5=float((avg > 0.05).mean()),
                   pooled=float(s[has].sum() / n[has].sum()), median_oos_trades=float(np.median(n[has])))
    return out


def eval_rule(M, y, conds, sign):
    m = rule_mask(M, conds)
    v = sign * y[m]
    return v


def trade_stats(pnl, qn=None):
    """pnl: per-trade gross P&L (fraction). Returns dict in PERCENT units."""
    pnl = np.asarray(pnl, float)
    n = len(pnl)
    if n == 0:
        return {'trades': 0}
    out = {'trades': n, 'avg_gross': 100 * pnl.mean(), 'avg_net': 100 * (pnl.mean() - COST),
           'pct_win': 100 * (pnl > 0).mean(), 'median': 100 * np.median(pnl)}
    srt = np.sort(pnl)[::-1]
    tot = pnl.sum()
    out['top5_share_of_total'] = float(srt[:5].sum() / tot) if tot != 0 else np.nan
    out['avg_without_top5'] = 100 * srt[5:].mean() if n > 5 else np.nan
    if qn is not None:
        qa = pd.Series(pnl).groupby(np.asarray(qn)).mean()
        out['quarters_with_picks'] = int(len(qa))
        out['avg_of_quarter_avgs'] = 100 * qa.mean()
    return out


def shuffle_within(y, qn, rng):
    ys = y.copy()
    for q in np.unique(qn):
        ix = np.where(qn == q)[0]
        ys[ix] = y[rng.permutation(ix)]
    return ys
