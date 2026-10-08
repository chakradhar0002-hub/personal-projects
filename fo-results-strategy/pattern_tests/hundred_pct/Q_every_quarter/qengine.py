"""
qengine.py -- "every quarter positive" rule search engine (reading Q).

Rules = AND of 1, 2 or 3 conditions from rulelib.build_conditions (copied unchanged into this folder).
For every rule and every quarter we need (#trades, sum of P&L).  For all 1/2-condition rules this is done
with one matrix product per quarter (C x n_q) @ (n_q x C); for 3-condition rules with a beam of pairs
(B x n_q) @ (n_q x C).  Per rule we accumulate, over the quarters of a period:
    nq   quarters with picks              K   trades             S[v]  P&L sum
    mn[u] worst quarter average           nf[u] quarters with average <= 0     nfn[u] quarters with average <= 0.17%
for the P&L variants  L3 = long three_day, S3 = short three_day, LT = long take-profit, ST = short take-profit.
A rule "qualifies" (every quarter positive) for variant u if nf[u] == 0 (gross) or nfn[u] == 0 (after costs)
and it has picks in at least `req` quarters of the period.
"""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS', '2')
import numpy as np, pandas as pd
import rulelib as R

HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.path.abspath(os.path.join(HERE, '..', '..'))
COST = 0.0017
UVARS = ('L3', 'S3', 'LT', 'ST')          # P&L variants (rule direction x exit)
FAMS = {'3day': ('L3', 'S3'), 'tp': ('LT', 'ST')}
SIGN = {'L3': 1, 'S3': -1, 'LT': 1, 'ST': -1}
COV = {'strict': 1.0, 'hi': 16 / 22, 'lo': 10 / 22}


def load(universe='fo'):
    df = pd.read_csv(f'{HERE}/features_all.csv')
    if universe == 'fo':
        df = df[df.in_fo].reset_index(drop=True)
    e = pd.read_csv(f'{SP}/sector_lab/data/events.csv', usecols=['symbol', 'qn', 'ret_dm1', 'ret_rd', 'ret_dp1'])
    df = df.merge(e, on=['symbol', 'qn'], how='left', validate='1:1')
    df = df.sort_values(['qn', 'results_date', 'symbol']).reset_index(drop=True)
    assert np.abs(df.ret_dm1 + df.ret_rd + df.ret_dp1 - df.three_day).max() < 1e-9
    y3, tl, ts = outcomes(df.ret_dm1.values, df.ret_rd.values, df.ret_dp1.values)
    assert np.abs(tl - df.tp3.values).max() < 1e-9
    df = df.assign(tp3s=ts)
    return df


def outcomes(d1, d2, d3):
    y3 = d1 + d2 + d3
    a1, a2 = d1, d1 + d2
    tl = np.where(a1 > 0.03, a1, np.where(a2 > 0.03, a2, y3))
    ts = np.where(-a1 > 0.03, -a1, np.where(-a2 > 0.03, -a2, -y3))
    return y3, tl, ts


def real_Y(df):
    return {'L3': df.three_day.values.astype(float), 'LT': df.tp3.values.astype(float),
            'ST': df.tp3s.values.astype(float)}


def null_Y(df, kind, rng):
    """kind 'shuffle': rows' outcomes permuted within quarter (all three columns together);
       kind 'signflip': each result's 3 daily returns flipped around that quarter's mean daily return
       (one random sign per result) -> keeps size of moves and quarter averages, removes direction."""
    qn = df.qn.values
    comps = np.c_[df.ret_dm1.values, df.ret_rd.values, df.ret_dp1.values]
    if kind == 'shuffle':
        perm = np.arange(len(df))
        for q in np.unique(qn):
            ix = np.where(qn == q)[0]
            perm[ix] = rng.permutation(ix)
        c = comps[perm]
    elif kind == 'signflip':
        qm = pd.DataFrame(comps).groupby(qn).transform('mean').values
        s = rng.choice([-1.0, 1.0], len(df))[:, None]
        c = qm + s * (comps - qm)
    elif kind == 'weekflip':
        # extra null (added after seeing that the two main nulls break the "stocks move together" structure):
        # ONE random sign per (season, ISO week of the cutoff date), shared by all results in that week ->
        # keeps sizes of moves, quarter averages AND the co-movement of stocks in the same week; kills direction.
        qm = pd.DataFrame(comps).groupby(qn).transform('mean').values
        wk = pd.to_datetime(df.cutoff).dt.isocalendar()
        g = pd.factorize(df.qn.astype(str) + '_' + wk.year.astype(str) + '_' + wk.week.astype(str))[0]
        s = rng.choice([-1.0, 1.0], g.max() + 1)[g][:, None]
        c = qm + s * (comps - qm)
    else:
        raise ValueError(kind)
    y3, tl, ts = outcomes(c[:, 0], c[:, 1], c[:, 2])
    return {'L3': y3, 'LT': tl, 'ST': ts}


class Acc:
    def __init__(self, shape):
        self.nq = np.zeros(shape, np.uint8)
        self.K = np.zeros(shape, np.int32)
        self.S = {v: np.zeros(shape, np.float32) for v in ('L3', 'LT', 'ST')}
        self.mn = {u: np.full(shape, np.inf, np.float32) for u in UVARS}
        self.nf = {u: np.zeros(shape, np.uint8) for u in UVARS}
        self.nfn = {u: np.zeros(shape, np.uint8) for u in UVARS}

    def update(self, Kq, Sq):
        has = Kq > 0.5
        self.nq += has
        self.K += Kq.astype(np.int32)
        inv = 1.0 / np.maximum(Kq, 1.0)
        tmp = np.empty_like(Kq)
        for v in ('L3', 'LT', 'ST'):
            self.S[v] += Sq[v]
            avg = Sq[v] * inv
            us = (('L3', 1.0), ('S3', -1.0)) if v == 'L3' else ((v, 1.0),)
            for u, sg in us:
                a = avg if sg > 0 else -avg
                np.copyto(tmp, a); tmp[~has] = np.inf
                np.minimum(self.mn[u], tmp, out=self.mn[u])
                self.nf[u] += has & (a <= 0)
                self.nfn[u] += has & (a <= COST)

    def sum_for(self, u):
        # P&L sum of variant u.  S['ST'] is already the short take-profit P&L, only S3 is the negated long sum.
        return -self.S['L3'] if u == 'S3' else self.S['L3' if u == 'L3' else u]


def scan(Ablocks, Xblocks, Yblocks, quarters, train_q, test_q):
    """Ablocks/Xblocks/Yblocks: dicts q -> (rows x n_q), (C x n_q), {v: y_q}.  Returns (acc_train, acc_test)."""
    shape = (Ablocks[quarters[0]].shape[0], Xblocks[quarters[0]].shape[0])
    tr = Acc(shape)
    te = Acc(shape) if test_q else None
    for q in quarters:
        if q not in train_q and q not in test_q:
            continue
        Aq, Xq = Ablocks[q], Xblocks[q]
        XqT = Xq.T
        Kq = Aq @ XqT
        Sq = {v: (Aq * Yblocks[q][v][None, :].astype(np.float32)) @ XqT for v in ('L3', 'LT', 'ST')}
        (tr if q in train_q else te).update(Kq, Sq)
    return tr, te


class Search:
    """Conditions + per-quarter blocks for one universe and one training period."""

    def __init__(self, df, train_q, test_q=(), beam=1000):
        self.df = df
        self.qn = df.qn.values
        self.train_q = sorted(train_q)
        self.test_q = sorted(test_q)
        self.quarters = self.train_q + self.test_q
        trmask = np.isin(self.qn, self.train_q)
        M, names, compat = R.build_conditions(df, trmask)
        self.M, self.names, self.compat = M, names, compat
        self.C = len(names)
        self.beam = beam
        self.ix = {q: np.where(self.qn == q)[0] for q in self.quarters}
        X = M.astype(np.float32)
        self.Xb = {q: np.ascontiguousarray(X[:, self.ix[q]]) for q in self.quarters}
        self.upper = np.triu(compat, 1)
        self.valid1 = np.eye(self.C, dtype=bool)
        self.ntr = len(self.train_q)
        self.req = {k: int(np.ceil(f * self.ntr - 1e-9)) for k, f in COV.items()}
        self.trrows = np.where(trmask)[0]
        rng = np.random.default_rng(99)
        self.w1 = rng.integers(0, 2 ** 20, len(df)).astype(np.float64)
        self.w2 = rng.integers(0, 2 ** 20, len(df)).astype(np.float64)
        # pair-level Kq is y independent -> cache products of the training+test blocks lazily
        self._pairK = None

    def Yb(self, Y):
        return {q: {v: Y[v][self.ix[q]] for v in ('L3', 'LT', 'ST')} for q in self.quarters}

    def run(self, Y):
        Yb = self.Yb(Y)
        tr2, te2 = scan(self.Xb, self.Xb, Yb, self.quarters, set(self.train_q), set(self.test_q))
        # ---- beam: per variant the pairs with fewest failing quarters (ties: more quarters, better worst quarter)
        elig = self.upper & (tr2.nq >= self.req['lo'])
        inbeam = np.zeros((self.C, self.C), bool)
        nqf = tr2.nq.astype(np.float64)
        for u in UVARS:
            key = tr2.nf[u].astype(np.float64) * 1e4 - nqf * 100 - np.clip(tr2.mn[u], -5, 5)
            key = np.where(elig, key, np.inf).ravel()
            k = min(self.beam, int(np.isfinite(key).sum()))
            if k > 0:
                top = np.argpartition(key, k - 1)[:k]
                inbeam.ravel()[top] = True
        a, b = np.nonzero(inbeam)
        A3 = {q: self.Xb[q][a] * self.Xb[q][b] for q in self.quarters}
        tr3, te3 = scan(A3, self.Xb, Yb, self.quarters, set(self.train_q), set(self.test_q))
        A_ = a[:, None]; B_ = b[:, None]; c_ = np.arange(self.C)[None, :]
        lo1 = np.minimum(A_, c_); hi1 = np.maximum(A_, c_)
        lo2 = np.minimum(B_, c_); hi2 = np.maximum(B_, c_)
        sm1 = (lo1 < A_) | ((lo1 == A_) & (hi1 < B_))
        sm2 = (lo2 < A_) | ((lo2 == A_) & (hi2 < B_))
        canon = ~(inbeam[lo1, hi1] & sm1) & ~(inbeam[lo2, hi2] & sm2)
        valid3 = canon & self.compat[a] & self.compat[b]
        del lo1, hi1, lo2, hi2, sm1, sm2, canon
        self.last = dict(tr2=tr2, te2=te2, tr3=tr3, te3=te3, a=a, b=b, valid3=valid3)
        return self.last

    # ------------------------------------------------------------------ extraction
    def qualifying(self, res, fam, cov, net, levels=(1, 2, 3)):
        """Return DataFrame of qualifying rules: level, r, c, u, train stats, test stats."""
        out = []
        for L in levels:
            if L == 3:
                tr, te, valid = res['tr3'], res['te3'], res['valid3']
            else:
                tr, te, valid = res['tr2'], res['te2'], (self.valid1 if L == 1 else self.upper)
            for u in FAMS[fam]:
                ok = valid & (tr.nq >= self.req[cov]) & ((tr.nfn[u] if net else tr.nf[u]) == 0)
                r, c = np.nonzero(ok)
                if len(r) == 0:
                    continue
                d = {'level': np.full(len(r), L, np.int8), 'r': r, 'c': c, 'u': u,
                     'nq': tr.nq[r, c], 'K': tr.K[r, c], 'S': tr.sum_for(u)[r, c], 'mn': tr.mn[u][r, c]}
                if te is not None:
                    d.update(te_nq=te.nq[r, c], te_K=te.K[r, c], te_S=te.sum_for(u)[r, c],
                             te_pos=te.nq[r, c].astype(int) - (te.nfn[u] if net else te.nf[u])[r, c],
                             te_mn=te.mn[u][r, c])
                out.append(pd.DataFrame(d))
        if not out:
            return pd.DataFrame()
        Q = pd.concat(out, ignore_index=True)
        return Q

    def conds_of(self, res, level, r, c):
        if level == 1:
            return (int(r),)
        if level == 2:
            return (int(r), int(c))
        return tuple(sorted((int(res['a'][r]), int(res['b'][r]), int(c))))

    def fingerprints(self, res, Q, rows=None):
        """exact pick-set fingerprint over the training rows (two random-integer weighted sums)."""
        rows = self.trrows if rows is None else rows
        Mt = self.M[:, rows]
        w1, w2 = self.w1[rows], self.w2[rows]
        f1 = np.empty(len(Q)); f2 = np.empty(len(Q))
        lv, rr, cc = Q.level.values, Q.r.values, Q.c.values
        a, b = res['a'], res['b']
        for L in (1, 2, 3):
            idx = np.where(lv == L)[0]
            for s in range(0, len(idx), 20000):
                ii = idx[s:s + 20000]
                r, c = rr[ii], cc[ii]
                if L == 1:
                    m = Mt[r]
                elif L == 2:
                    m = Mt[r] & Mt[c]
                else:
                    m = Mt[a[r]] & Mt[b[r]] & Mt[c]
                f1[ii] = m @ w1; f2[ii] = m @ w2
        return f1, f2

    def rule_mask(self, conds):
        return R.rule_mask(self.M, list(conds))

    def rule_str(self, conds, u):
        return R.rule_str(self.names, conds, SIGN[u]) + (' [TP exit]' if u in ('LT', 'ST') else '')


def rank_top(Q, k):
    """pre-registered choice: most quarters with picks, then best worst-quarter average, then most trades."""
    if len(Q) == 0:
        return Q
    o = np.lexsort((-Q.K.values, -Q.mn.values, -Q.nq.values.astype(int)))
    return Q.iloc[o[:k]]


def summarize(Q, n_test_q, net):
    """summary of a set of qualifying rules (in-sample and, if present, out-of-sample)."""
    d = {'n_rules': int(len(Q))}
    if len(Q) == 0:
        return d
    d['n_by_level'] = {int(L): int((Q.level == L).sum()) for L in (1, 2, 3)}
    d['n_long'] = int(Q.u.isin(['L3', 'LT']).sum())
    d['is_trades_median'] = float(np.median(Q.K)); d['is_trades_max'] = int(Q.K.max())
    d['is_nq_max'] = int(Q.nq.max())
    if 'te_nq' in Q and n_test_q:
        has = Q.te_nq > 0
        d['oos_frac_rules_with_picks'] = float(has.mean())
        H = Q[has]
        if len(H):
            frac = H.te_pos / H.te_nq
            d['oos_mean_frac_quarters_pos'] = float(frac.mean())
            d['oos_frac_rules_all_pos'] = float((H.te_pos == H.te_nq).mean())
            d['oos_mean_pos_of_all'] = float((Q.te_pos).mean())        # out of n_test_q, empty = failure
            d['oos_frac_rules_all8_pos'] = float((Q.te_pos == n_test_q).mean())
            d['oos_pooled_avg_pct'] = 100 * float(H.te_S.sum() / H.te_K.sum())
            d['oos_mean_rule_avg_pct'] = 100 * float((H.te_S / H.te_K).mean())
            d['oos_trades_median'] = float(np.median(H.te_K))
            # histogram: number of the n_test_q hold-out quarters that were positive (empty quarter = failure)
            d['oos_hist_pos_of_all'] = np.bincount(Q.te_pos.astype(int).clip(0, n_test_q), minlength=n_test_q + 1).tolist()
    return d
