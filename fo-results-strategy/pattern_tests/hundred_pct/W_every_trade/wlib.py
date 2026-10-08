"""
wlib.py -- engine for reading (W): rules whose trades are ALL winners.

Conditions are copied verbatim from five_pct/A_rule_search/rulelib.py (feature >= / <= cut, cuts = training-row
percentiles; category == value; missing value -> condition false).  A rule = AND of 1, 2 or 3 conditions,
traded long or short.  Win = P&L > thr (thr = 0 gross, 0.0017 after costs).

Search per call of Engine.run():
  level 1 and 2: exhaustive (all conditions, all compatible pairs);
  level 3: beam -- for every (m, side) the top B pairs by shrunk win rate (w+1)/(n+2) and the top B pairs by
  Wilson 95% lower bound (n >= m, picks in >= minq quarters) are each extended with every compatible third
  condition (exact de-duplication of triples, as in rulelib).  Same beam on real and null data.
For each side and m it returns: number of 100%-winner rules by level, the largest ones, and (when a test set is
given) the out-of-sample record of every in-sample 100% rule plus the top-k rules by shrunk win rate / Wilson LB.
"""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS', '2')
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.path.abspath(os.path.join(HERE, '..', '..'))
FEAT = SP + '/five_pct/A_rule_search/features_all.csv'
EVT = SP + '/sector_lab/data/events.csv'
CUT_PCTS = [5, 10, 15, 20, 30, 40, 50, 60, 70, 80, 85, 90, 95]
COST = 0.0017
Z = 1.96

NUM_FEATS = [
    'r1w', 'r1m', 'r3m', 'r6m', 'r1y', 'r3y', 'r5y', 'from_52w_high', 'from_52w_low', 'vs_ma50', 'vs_ma200',
    'vol60', 'volume_5d_vs_60d', 'sector_1w', 'vs_sector_1w', 'vs_nifty_1w', 'nifty_1w', 'sector_1m',
    'vs_sector_1m', 'vs_nifty_1m', 'nifty_1m', 'sector_3m', 'vs_sector_3m', 'vs_nifty_3m', 'nifty_3m',
    'india_vix', 'prev1_3d', 'prev2_sum', 'past_avg_3d', 'past_pct_up', 'prev1_next20', 'prev_pat_yoy',
    'prev_sales_yoy', 'profit_rising_4q', 'sales_rising_4q', 'prev_net_margin', 'pe', 'pb', 'roe',
    'debt_equity', 'pe_vs_peers', 'log_mcap', 'days_since_dividend', 'iv_t5', 'iv_vs_realised',
    'days_after_quarter_end', 'peers_reported_3d', 'peers_reported_n', 'season_so_far_3d',
    'sec_vs_nifty_1w', 'sec_vs_nifty_1m', 'sec_vs_nifty_3m', 'sec_rank_1m', 'sec_rank_3m', 'sec_vs_50dma',
    'sec_vs_200dma', 'sec_from_52w_high', 'sec_reported_3d',
    'd0', 'd1', 'd2', 'r2d', 'r3d', 'r10d', 'r20d', 'gap0', 'intra0', 'gap5', 'intra5', 'nifty_d0',
    'nifty_3d', 'exn_d0', 'exn_3d', 'exn_10d', 'sec_d0', 'sec_3d', 'exs_3d', 'dist_20h', 'dist_20l',
    'dist_60h', 'vol5_60', 'vol20_60', 'maxabs5', 'z5', 'z20', 'up10', 'streak', 'pre5', 'own_dm1', 'own_rd',
    'own_dp1', 'own_abs3d', 'pre5_vs_own', 'n_prior', 'cal_days',
]
CAT_FEATS = ['fin_type', 'sector_index', 'industry', 'fq']


def load(universe='fo'):
    df = pd.read_csv(FEAT)
    E = pd.read_csv(EVT, usecols=['symbol', 'qn', 'ret_dm1', 'ret_rd', 'ret_dp1'])
    df = df.merge(E, on=['symbol', 'qn'], how='left')
    assert df.ret_dm1.notna().all()
    if universe == 'fo':
        df = df[df.in_fo].reset_index(drop=True)
    df = df.sort_values(['qn', 'results_date', 'symbol']).reset_index(drop=True)
    assert np.allclose(df.ret_dm1 + df.ret_rd + df.ret_dp1, df.three_day)
    return df


def pieces(df):
    return np.c_[df.ret_dm1.values, df.ret_rd.values, df.ret_dp1.values].astype(float)


def outcomes(pc):
    """pc: N x 3 daily pieces (D-1, RD, D+1). Returns {'3day': (long, short), 'tp': (long, short)}."""
    a = pc[:, 0]; b = a + pc[:, 1]; t = b + pc[:, 2]
    tpl = np.where(a > 0.03, a, np.where(b > 0.03, b, t))
    tps = np.where(-a > 0.03, -a, np.where(-b > 0.03, -b, -t))
    return {'3day': (t, -t), 'tp': (tpl, tps)}


def null_pieces(pc, qn, kind, rng):
    if kind == 'shuffle':        # permute whole results (all 3 days together) within each quarter
        idx = np.arange(len(pc))
        for q in np.unique(qn):
            ix = np.where(qn == q)[0]
            idx[ix] = rng.permutation(ix)
        return pc[idx]
    if kind == 'signflip':       # keep each result's size of move around its quarter mean, random direction
        qm = pd.DataFrame(pc).groupby(qn).transform('mean').values
        s = rng.choice([-1.0, 1.0], len(pc))
        return qm + s[:, None] * (pc - qm)
    raise ValueError(kind)


def build_conditions(df, train_mask, min_train=10, min_cat=30):
    """verbatim copy of rulelib.build_conditions"""
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


def wilson(w, n, z=Z):
    w = np.asarray(w, float); n = np.maximum(np.asarray(n, float), 1e-9)
    p = w / n
    den = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * np.sqrt(np.maximum(p * (1 - p) / n + z * z / (4 * n * n), 0))
    return (c - r) / den


def shrunk(w, n):
    return (np.asarray(w, float) + 1) / (np.asarray(n, float) + 2)


def trade_record(pnl, qn, thr):
    """per-trade P&L (fraction) -> dict in PERCENT."""
    pnl = np.asarray(pnl, float)
    n = len(pnl)
    if n == 0:
        return {'trades': 0, 'wins': 0, 'win_rate': np.nan, 'avg': np.nan, 'worst': np.nan,
                'quarters': 0, 'quarters_pos': 0, 'all_win': False}
    _, qi = np.unique(np.asarray(qn), return_inverse=True)
    qa = np.bincount(qi, weights=pnl) / np.bincount(qi)
    w = int((pnl > thr).sum())
    return {'trades': n, 'wins': w, 'win_rate': 100.0 * w / n, 'avg': 100 * pnl.mean(),
            'worst': 100 * pnl.min(), 'quarters': int(len(qa)), 'quarters_pos': int((qa > thr).sum()),
            'all_win': bool(w == n)}


_WT = {}


def wilson_table(nmax):
    """T[n, w] = Wilson 95% lower bound (float32), integer n, w <= nmax."""
    if nmax not in _WT:
        n = np.arange(nmax + 1, dtype=float)[:, None]
        w = np.arange(nmax + 1, dtype=float)[None, :]
        with np.errstate(invalid='ignore', divide='ignore'):
            T = wilson(np.minimum(w, n), n).astype(np.float32)
        T[0, :] = 0
        _WT[nmax] = T
    return _WT[nmax]


def _top(score, k):
    flat = score.ravel()
    fin = np.isfinite(flat)
    k = min(k, int(fin.sum()))
    if k <= 0:
        return np.array([], int)
    idx = np.argpartition(-flat, k - 1)[:k]
    return idx[np.argsort(-flat[idx], kind='stable')]


class Engine:
    def __init__(self, df, tr, te=None, minq=4, ms=(10, 15, 20, 30), B=500, ntop=100, chunk=1500):
        self.df, self.tr = df, tr
        self.te = te if (te is not None and te.any()) else None
        self.minq, self.ms, self.B, self.ntop, self.chunk = minq, tuple(ms), B, ntop, chunk
        self.qn = df.qn.values
        M, names, compat = build_conditions(df, tr)
        self.M, self.names, self.compat = M, names, compat
        self.C = C = len(names)
        X = M[:, tr].astype(np.float32)
        self.X = X
        qtr = self.qn[tr]
        self.qidx = [np.where(qtr == q)[0] for q in np.unique(qtr)]
        self.Xq = [np.ascontiguousarray(X[:, ix]) for ix in self.qidx]
        self.K1 = X.sum(1)
        self.Q1 = np.zeros(C, np.int16)
        for Xq in self.Xq:
            self.Q1 += Xq.sum(1) > 0
        self.K2 = X @ X.T
        self.Q2 = np.zeros((C, C), np.uint8)
        for Xq in self.Xq:
            self.Q2 += (Xq @ Xq.T) > 0.5
        self.upper = np.triu(compat, 1)
        self.n_pairs = int(self.upper.sum())
        if self.te is not None:
            self.Xte = M[:, self.te].astype(np.float32)
            self.K1te = self.Xte.sum(1)
            self.K2te = self.Xte @ self.Xte.T
        self.mmin = min(self.ms)
        self.WT = wilson_table(int(tr.sum()))

    # ------------------------------------------------------------------ main search
    def run(self, pnl_long, pnl_short, thr, keep_list=False):
        X, C, tr, te = self.X, self.C, self.tr, self.te
        ms, minq, B = self.ms, self.minq, self.B
        sides = {}
        for sgn, pnl in ((1, pnl_long), (-1, pnl_short)):
            ytr = pnl[tr]
            w = ytr > thr
            Xw = np.ascontiguousarray(X[:, w])
            d = {'pnl': pnl, 'w': w, 'Xw': Xw, 'W1': Xw.sum(1), 'W2': Xw @ Xw.T}
            if te is not None:
                yte = pnl[te].astype(np.float32)
                wte = yte > thr
                Xwte = np.ascontiguousarray(self.Xte[:, wte])
                d.update(yte=yte, wte=wte, Xwte=Xwte, W1te=Xwte.sum(1), S1te=self.Xte @ yte,
                         W2te=Xwte @ Xwte.T, S2te=(self.Xte * yte) @ self.Xte.T)
            sides[sgn] = d
        # ---- beam
        inbeam = np.zeros((C, C), bool)
        K2i = self.K2.astype(np.int32)
        elq = self.upper & (self.Q2 >= minq)
        for sgn, d in sides.items():
            W2i = d['W2'].astype(np.int32)
            sh = (d['W2'] + 1) / (self.K2 + 2)
            wl = self.WT[K2i, W2i]
            for m in ms:
                el = elq & (K2i >= m)
                inbeam.ravel()[_top(np.where(el, sh, -np.inf), B)] = True
                inbeam.ravel()[_top(np.where(el, wl, -np.inf), B)] = True
            del W2i, sh, wl
        a, b = np.nonzero(inbeam)
        # ---- collectors
        col = {sgn: {'h': [], 'pool': {m: {'shrunk': [], 'wilson': []} for m in ms},
                     'n_elig': {m: [0, 0, 0] for m in ms}} for sgn in sides}

        def collect(level, K, Q, valid, conds_of, d, colS, Wm, Kte=None, Wte=None, Ste=None):
            """K, Q, Wm, Kte... flat arrays; valid flat bool; conds_of(idx)->array (k x 3) of condition ids."""
            base = valid & (Q >= minq)
            h = base & (K >= self.mmin) & (Wm == K)
            hi = np.nonzero(h)[0]
            if len(hi):
                rec = {'level': np.full(len(hi), level, np.int8), 'conds': conds_of(hi), 'n': K[hi].astype(np.int32),
                       'q': Q[hi].astype(np.int16)}
                if Kte is not None:
                    rec.update(nte=Kte[hi].astype(np.int32), wte=Wte[hi].astype(np.int32), ste=Ste[hi].astype(np.float32))
                colS['h'].append(rec)
            for m in ms:
                el = base & (K >= m)
                ei = np.nonzero(el)[0]
                colS['n_elig'][m][level - 1] += len(ei)
                if not len(ei):
                    continue
                Ke, We = K[ei], Wm[ei]
                for crit in ('shrunk', 'wilson'):
                    sc = ((We + 1) / (Ke + 2) if crit == 'shrunk' else self.WT[Ke.astype(np.int32), We.astype(np.int32)]) - 1e-6 * level
                    t = _top(sc, 3 * self.ntop)
                    sel = ei[t]
                    colS['pool'][m][crit].append({'score': sc[t], 'level': np.full(len(t), level, np.int8),
                                                  'conds': conds_of(sel), 'n': K[sel], 'w': Wm[sel]})

        # level 1
        ar1 = np.arange(C)
        c1 = lambda ix: np.c_[ix, np.full(len(ix), -1), np.full(len(ix), -1)]
        for sgn, d in sides.items():
            kw = {}
            if te is not None:
                kw = dict(Kte=self.K1te, Wte=d['W1te'], Ste=d['S1te'])
            collect(1, self.K1, self.Q1, np.ones(C, bool), c1, d, col[sgn], d['W1'], **kw)
        # level 2
        c2 = lambda ix: np.c_[ix // C, ix % C, np.full(len(ix), -1)]
        for sgn, d in sides.items():
            kw = {}
            if te is not None:
                kw = dict(Kte=self.K2te.ravel(), Wte=d['W2te'].ravel(), Ste=d['S2te'].ravel())
            collect(2, self.K2.ravel(), self.Q2.ravel(), self.upper.ravel(), c2, d, col[sgn], d['W2'].ravel(), **kw)
        # level 3 (beam) in chunks
        n_trip = 0
        for s0 in range(0, len(a), self.chunk):
            aa, bb = a[s0:s0 + self.chunk], b[s0:s0 + self.chunk]
            k = len(aa)
            P = X[aa] * X[bb]
            K3 = np.zeros((k, C), np.float32)
            Q3 = np.zeros((k, C), np.uint8)
            for ix, Xq in zip(self.qidx, self.Xq):
                cnt = P[:, ix] @ Xq.T
                K3 += cnt
                Q3 += cnt > 0.5
            A_ = aa[:, None]; B_ = bb[:, None]; c_ = ar1[None, :]
            lo1 = np.minimum(A_, c_); hi1 = np.maximum(A_, c_)
            lo2 = np.minimum(B_, c_); hi2 = np.maximum(B_, c_)
            sm1 = (lo1 < A_) | ((lo1 == A_) & (hi1 < B_))
            sm2 = (lo2 < A_) | ((lo2 == A_) & (hi2 < B_))
            canon = ~(inbeam[lo1, hi1] & sm1) & ~(inbeam[lo2, hi2] & sm2)
            valid3 = canon & self.compat[aa] & self.compat[bb]
            del lo1, hi1, lo2, hi2, sm1, sm2, canon
            n_trip += int(valid3.sum())

            def c3(ix, aa=aa, bb=bb):
                r, c = ix // C, ix % C
                return np.sort(np.c_[aa[r], bb[r], c], axis=1)
            if te is not None:
                Pte = self.Xte[aa] * self.Xte[bb]
                K3te = Pte @ self.Xte.T
            for sgn, d in sides.items():
                W3 = P[:, d['w']] @ d['Xw'].T
                kw = {}
                if te is not None:
                    W3te = Pte[:, d['wte']] @ d['Xwte'].T
                    S3te = (Pte * d['yte']) @ self.Xte.T
                    kw = dict(Kte=K3te.ravel(), Wte=W3te.ravel(), Ste=S3te.ravel())
                collect(3, K3.ravel(), Q3.ravel(), valid3.ravel(), c3, d, col[sgn], W3.ravel(), **kw)
        counts = {'n_conditions': C, 'n_pairs': self.n_pairs, 'n_beam_pairs': int(len(a)), 'n_triples': n_trip,
                  'rules_evaluated_long_and_short': 2 * (C + self.n_pairs + n_trip)}
        return self._finish(col, sides, counts, thr, keep_list)

    # ------------------------------------------------------------------ summaries
    def _finish(self, col, sides, counts, thr, keep_list):
        out = {'counts': counts, 'sides': {}}
        for sgn, cs in col.items():
            d = sides[sgn]
            so = {}
            H = cs['h']
            if H:
                hl = np.concatenate([r['level'] for r in H]); hc = np.concatenate([r['conds'] for r in H])
                hn = np.concatenate([r['n'] for r in H]); hq = np.concatenate([r['q'] for r in H])
                if self.te is not None:
                    hnte = np.concatenate([r['nte'] for r in H]); hwte = np.concatenate([r['wte'] for r in H])
                    hste = np.concatenate([r['ste'] for r in H])
            else:
                hl = np.zeros(0, np.int8); hc = np.zeros((0, 3), int); hn = np.zeros(0, int); hq = np.zeros(0, int)
                hnte = hwte = np.zeros(0, int); hste = np.zeros(0, float)
            for m in self.ms:
                r = {}
                sel = hn >= m
                r['count100'] = {L: int(((hl == L) & sel).sum()) for L in (1, 2, 3)}
                r['count100']['all'] = int(sel.sum())
                r['n_eligible'] = {L: cs['n_elig'][m][L - 1] for L in (1, 2, 3)}
                r['largest100_n'] = int(hn[sel].max()) if sel.any() else 0
                r['largest100_level'] = int(hl[sel][np.argmax(hn[sel])]) if sel.any() else 0
                if self.te is not None:
                    s2 = sel & (hnte > 0)
                    r['oos_of_100'] = {
                        'n_rules': int(sel.sum()), 'n_with_oos_trades': int(s2.sum()),
                        'mean_rule_winrate': float(100 * (hwte[s2] / hnte[s2]).mean()) if s2.any() else None,
                        'pooled_winrate': float(100 * hwte[s2].sum() / hnte[s2].sum()) if s2.any() else None,
                        'frac_rules_oos_all_win': float((hwte[s2] == hnte[s2]).mean()) if s2.any() else None,
                        'frac_rules_oos_all_win_ge5': float((hwte[s2 & (hnte >= 5)] == hnte[s2 & (hnte >= 5)]).mean())
                        if (s2 & (hnte >= 5)).any() else None,
                        'n_rules_oos_ge5': int((s2 & (hnte >= 5)).sum()),
                        'mean_rule_avg': float(100 * (hste[s2] / hnte[s2]).mean()) if s2.any() else None,
                        'median_oos_trades': float(np.median(hnte[s2])) if s2.any() else None}
                    # the largest in-sample 100% rules (by n, ties fewer conditions) -> OOS
                    if sel.any():
                        order = np.lexsort((hl[sel], -hn[sel]))
                        idx = np.nonzero(sel)[0][order[:10]]
                        nt, wt = hnte[idx], hwte[idx]
                        r['largest10_oos'] = {'oos_trades': int(nt.sum()), 'oos_wins': int(wt.sum()),
                                              'pooled_winrate': float(100 * wt.sum() / nt.sum()) if nt.sum() else None}
                        r['largest1_oos'] = {'is_n': int(hn[idx[0]]), 'oos_trades': int(nt[0]), 'oos_wins': int(wt[0]),
                                             'oos_avg': float(100 * hste[idx[0]] / nt[0]) if nt[0] else None}
                # top-k by shrunk / wilson
                for crit in ('shrunk', 'wilson'):
                    r[crit] = self._toplist(cs['pool'][m][crit], d, sgn, thr)
                so[m] = r
            if keep_list:
                so['list100'] = {'level': hl, 'conds': hc, 'n': hn, 'q': hq}
                if self.te is not None:
                    so['list100'].update(nte=hnte, wte=hwte, ste=hste)
            out['sides'][sgn] = so
        return out

    def _toplist(self, pool, d, sgn, thr):
        if not pool:
            return {'rules': []}
        sc = np.concatenate([p['score'] for p in pool]); lv = np.concatenate([p['level'] for p in pool])
        cd = np.concatenate([p['conds'] for p in pool]); n = np.concatenate([p['n'] for p in pool])
        order = np.lexsort((-n, lv, -sc))
        seen, rules = set(), []
        pnl = d['pnl']
        for i in order:
            conds = [int(c) for c in cd[i] if c >= 0]
            mk = rule_mask(self.M, conds)
            key = np.packbits(mk).tobytes()
            if key in seen:
                continue
            seen.add(key)
            rec = {'conds': conds, 'sign': sgn, 'level': int(lv[i]), 'score': float(sc[i])}
            ist = trade_record(pnl[mk & self.tr], self.qn[mk & self.tr], thr)
            rec.update({'is_' + k: v for k, v in ist.items()})
            if self.te is not None:
                ost = trade_record(pnl[mk & self.te], self.qn[mk & self.te], thr)
                rec.update({'oos_' + k: v for k, v in ost.items()})
            rules.append(rec)
            if len(rules) >= self.ntop:
                break
        res = {'rules': rules}
        if self.te is not None:
            for k in (1, 10, 100):
                sub = [x for x in rules[:k] if x['oos_trades'] > 0]
                if sub:
                    res[f'top{k}'] = {'n_rules_with_oos': len(sub),
                                      'mean_rule_winrate': float(np.mean([x['oos_win_rate'] for x in sub])),
                                      'pooled_winrate': float(100 * sum(x['oos_wins'] for x in sub) / sum(x['oos_trades'] for x in sub)),
                                      'mean_rule_avg': float(np.mean([x['oos_avg'] for x in sub])),
                                      'frac_rules_oos_all_win': float(np.mean([x['oos_all_win'] for x in sub])),
                                      'oos_trades_total': int(sum(x['oos_trades'] for x in sub))}
                else:
                    res[f'top{k}'] = None
        return res
