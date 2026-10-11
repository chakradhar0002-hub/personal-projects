#!/usr/bin/env python3
"""Verifier - recompute the family's 36 tests from MY features and stress the candidates (B09, B13, A12, A22).

usage: python3 -P v3_tests.py <scratchpad> <features.csv> <out_dir> <tag>
features.csv: my_results_features.csv (my pipeline) or the family's results_features.csv (for comparison).
"""
import sys

import numpy as np
import pandas as pd

SP, FEAT, OUT, TAG = sys.argv[1:5]
rng = np.random.default_rng(99)
LOGF = open(f'{OUT}/v3_{TAG}.log', 'w')


def log(*a):
    s = ' '.join(map(str, a))
    print(s, flush=True)
    LOGF.write(s + '\n')


COST_A = 0.17
ses = pd.read_csv(f'{SP}/sector_lab/data/sessions.csv')
DAYS = ses.day.to_numpy()
T = len(DAYS)
ret = pd.read_csv(f'{SP}/sector_lab/data/returns.csv', index_col=0)
JX = {s: j for j, s in enumerate(ret.columns)}
PX = np.cumprod(1 + np.nan_to_num(ret.to_numpy(float)), axis=0)
NIFTY = pd.read_csv(f'{SP}/sector_lab/data/index_close.csv', index_col=0)['Nifty 50'].to_numpy(float)


def hedged(sym, a, H=20, cost=0.19):
    j = np.asarray([JX[s] for s in sym])
    a = np.asarray(a, int)
    b = a + H
    ok = b <= T - 1
    b = np.minimum(b, T - 1)
    v = ((PX[b, j] / PX[a, j] - 1) - (NIFTY[b] / NIFTY[a] - 1)) * 100 - cost
    return np.where(ok, v, np.nan)


X = pd.read_csv(FEAT)
O = pd.read_csv(f'{SP}/perf/features/outcomes.csv', usecols=['symbol', 'qn', 'three_day', 'vsN_net_H20', 'tradable_B'])
keep = [c for c in X.columns if c not in ('three_day', 'vsN_net_H20', 'tradable_B')]
D = X[keep].merge(O, on=['symbol', 'qn'], validate='1:1')
PC = ['cut_rsi14', 'i_react', 'i_cut', 'industry', 'XN', 'W']
P_ = pd.read_csv(f'{SP}/perf/features/panel.csv', usecols=['symbol', 'qn'] + PC)
D = D.drop(columns=[c for c in PC if c in D.columns]).merge(P_, on=['symbol', 'qn'], validate='1:1')
D['yr'] = pd.to_datetime(pd.Series(DAYS[D.i_react.to_numpy()])).dt.year.to_numpy()
D['W'] = D.W.astype(bool)
D['vsN_k1'] = hedged(D.symbol, D.i_react + 1)       # entry close k+1, exit close k+21
D['vsN_k2'] = hedged(D.symbol, D.i_react + 2)
assert len(D) == 3280

# lag rule, RSI>50 winners, habitual drifters, early F&O members
lag = pd.read_csv(__import__('os').environ.get('REPO_ROOT', '.') + '/results/lag10_volume/trades.csv')
D['LAG'] = [(s, q) in set(zip(lag.symbol, lag.qn)) for s, q in zip(D.symbol, D.qn)]
hb = pd.read_csv(f'{SP}/perf/B_post_results/trades.csv')
hb = hb[hb.test == 'S1_DRIFT4_Q5']
D['HABIT'] = [(s, q) in set(zip(hb.symbol, hb.qn)) for s, q in zip(D.symbol, D.qn)]
first_q = D.groupby('symbol').qn.min()
D['EARLY'] = D.symbol.map(first_q).to_numpy() <= 1
log(f'[{TAG}] rows {len(D)}; lag-rule {D.LAG.sum()}; habitual drifters {D.HABIT.sum()}; early members rows {D.EARLY.sum()}')


# ------------------------------------------------------------------ quintile flags with cut-off variants
def qflag(col, side, frac=0.2, mode='same', dec='i_react'):
    v = D[col].to_numpy(float)
    q = D.qn.to_numpy()
    out = np.zeros(len(D), bool)
    el = np.isfinite(v)
    hi, lo = 1 - frac, frac
    if mode in ('same', 'prev'):
        qs = pd.DataFrame({'v': v, 'q': q}).dropna().groupby('q').v
        c_hi, c_lo = qs.quantile(hi), qs.quantile(lo)
        if mode == 'prev':
            c_hi = pd.Series({k: c_hi.get(k - 1, c_hi[k]) for k in c_hi.index})
            c_lo = pd.Series({k: c_lo.get(k - 1, c_lo[k]) for k in c_lo.index})
        ch, cl = c_hi.reindex(q).to_numpy(), c_lo.reindex(q).to_numpy()
    else:  # 'trail': results decided in the previous 90 sessions (strictly before), >= 60 of them
        di = D[dec].to_numpy()
        o = np.argsort(di)
        ch, cl = np.full(len(D), np.nan), np.full(len(D), np.nan)
        for r_ in range(len(D)):
            m = (di < di[r_]) & (di >= di[r_] - 90) & el
            if m.sum() >= 60:
                ch[r_] = np.quantile(v[m], hi)
                cl[r_] = np.quantile(v[m], lo)
        el = el & np.isfinite(ch)
    out = (v > ch) if side == 'top' else (v <= cl)
    return out & el, el


A_SPEC = [('A12', -1, 'BASISDEV', 'bot'), ('A22', -1, 'dPIV20', 'top'), ('A15', +1, 'dPCR5', 'top'),
          ('A09', +1, 'OI20', 'top'), ('A10', -1, 'OI20', 'bot'), ('A11', +1, 'BASISDEV', 'top'), ('A13', +1, 'PCR', 'top'),
          ('A14', -1, 'PCR', 'bot'), ('A16', -1, 'dPCR5', 'bot'), ('A17', -1, 'IVREL', 'top'), ('A18', +1, 'IVREL', 'bot'),
          ('A19', +1, 'IVSPREAD', 'top'), ('A20', -1, 'IVSPREAD', 'bot'), ('A21', +1, 'dCIV20', 'top')]
B_SPEC = [('B06', 'OI20', 'top'), ('B07', 'BASISDEV', 'top'), ('B08', 'dBASIS1', 'top'), ('B09', 'PCR', 'top'),
          ('B10', 'dPCR1', 'top'), ('B11', 'IVREL', 'bot'), ('B12', 'IVSPREAD', 'top'), ('B13', 'dCIV20', 'top'),
          ('B14', 'dPIV20', 'bot')]


def flags_all(pre_A='A_', pre_B='B_', mode='same', frac=0.2):
    fl = {}
    for L, base in ((5, 1), (10, 5)):
        dp, do = D[f'{pre_A}dP{L}'], D[f'{pre_A}dOI{L}']
        el = (dp.notna() & do.notna()).to_numpy()
        fl[f'A{base:02d}'] = (+1, ((dp > 0) & (do > 10)).to_numpy() & el, el)
        fl[f'A{base + 1:02d}'] = (-1, ((dp < 0) & (do > 10)).to_numpy() & el, el)
        fl[f'A{base + 2:02d}'] = (+1, ((dp > 0) & (do < -10)).to_numpy() & el, el)
        fl[f'A{base + 3:02d}'] = (-1, ((dp < 0) & (do < -10)).to_numpy() & el, el)
    for t, s, c, side in A_SPEC:
        sig, el = qflag(pre_A + c, side, frac, mode, 'i_cut')
        fl[t] = (s, sig, el)
    el = D[f'{pre_B}dOI1'].notna().to_numpy()
    fl['B01'] = (+1, (D[f'{pre_B}dOI1'] > 0).to_numpy() & el, el)
    fl['B02'] = (+1, (D[f'{pre_B}dOI1'] > 10).to_numpy() & el, el)
    for t, L in (('B03', 5), ('B04', 10)):
        el = (D[f'{pre_B}dP{L}'].notna() & D[f'{pre_B}dOI{L}'].notna()).to_numpy()
        fl[t] = (+1, ((D[f'{pre_B}dP{L}'] > 0) & (D[f'{pre_B}dOI{L}'] > 10)).to_numpy() & el, el)
    el = (D['A_dP5'].notna() & D['A_dOI5'].notna()).to_numpy()
    fl['B05'] = (+1, ((D['A_dP5'] < 0) & (D['A_dOI5'] > 10)).to_numpy() & el, el)
    for t, c, side in B_SPEC:
        sig, el = qflag(pre_B + c, side, frac, mode, 'i_react')
        fl[t] = (+1, sig, el)
    return fl


# ------------------------------------------------------------------ pools
mA = D.three_day.notna().to_numpy()
yA = D.three_day.to_numpy(float)
mW = (D.W & (D.tradable_B == True)).to_numpy()
yB = D.vsN_net_H20.to_numpy(float)
q = D.qn.to_numpy()


def stats(sig, pool, y, s, cost, name='', nperm=20000, extra=True):
    """sig, pool boolean over D rows; y outcome; s sign; returns dict."""
    m = sig & pool & np.isfinite(y)
    pm = pool & np.isfinite(y)
    pnl = s * y
    qm = pd.Series(pnl[pm]).groupby(q[pm]).mean()
    base = qm.reindex(q).to_numpy()
    exc = pnl - base
    n = int(m.sum())
    r = {'test': name, 'n': n}
    if n == 0:
        return r
    net = pnl[m] - cost
    r['net'] = net.mean()
    r['excess'] = exc[m].mean()
    pq_ = pd.Series(net).groupby(q[m]).mean()
    r['q_pos'] = f'{int((pq_ > 0).sum())}/{len(pq_)}'
    for h, hm in (('f14', q <= 13), ('l8', q >= 14)):
        mm = m & hm
        r[f'net_{h}'] = (pnl[mm] - cost).mean() if mm.any() else np.nan
        r[f'exc_{h}'] = exc[mm].mean() if mm.any() else np.nan
    o = np.sort(pnl[m])[::-1]
    for kk in (5, 10):
        r[f'net_wo{kk}'] = (o[kk:] - cost).mean() if n > kk else np.nan
    oe = np.sort(exc[m])[::-1]
    r['exc_wo5'] = oe[5:].mean() if n > 5 else np.nan
    r['exc_wo10'] = oe[10:].mean() if n > 10 else np.nan
    # luck p: within-quarter permutation over the pool
    qs = np.unique(q[pm])
    obs = pnl[m].mean()
    tot = np.zeros(nperm)
    for x in qs:
        k = int((m & (q == x)).sum())
        if k == 0:
            continue
        pool_v = pnl[pm & (q == x)]
        if k == len(pool_v):
            tot += pool_v.sum()
            continue
        idx = np.argpartition(rng.random((nperm, len(pool_v))), k - 1, axis=1)[:, :k]
        tot += pool_v[idx].sum(1)
    r['luck_p'] = (1 + (tot / n >= obs - 1e-12).sum()) / (1 + nperm)
    if extra:
        # leave one quarter out
        lo = []
        for x in qs:
            mm = m & (q != x)
            lo.append(exc[mm].mean() if mm.any() else np.nan)
        r['loqo_min'] = np.nanmin(lo)
        r['loqo_max'] = np.nanmax(lo)
        r['loqo_argmin'] = int(qs[int(np.nanargmin(lo))])
        # by year
        for yy in range(2021, 2027):
            mm = m & (D.yr.to_numpy() == yy)
            r[f'exc_{yy}'] = exc[mm].mean() if mm.any() else np.nan
            r[f'n_{yy}'] = int(mm.sum())
        # symbol-cluster t of excess
        e = pd.DataFrame({'e': exc[m], 's': D.symbol.to_numpy()[m]})
        g = e.groupby('s').e.sum()
        se = np.sqrt((g ** 2).sum() * len(g) / max(len(g) - 1, 1)) / n
        r['t_symclust'] = e.e.mean() / se if se > 0 else np.nan
        r['n_syms'] = int(e.s.nunique())
        r['top_sym_share'] = e.s.value_counts().iloc[0] / n
    return r


def holm(p):
    p = np.asarray(p, float)
    o = np.argsort(p)
    adj = np.empty(len(p))
    run = 0
    for i_, k in enumerate(o):
        run = max(run, min(1, (len(p) - i_) * p[k]))
        adj[k] = run
    return adj


pd.set_option('display.width', 250)
pd.set_option('display.max_columns', 60)
# ------------------------------------------------------------------ 1. all 36 tests with my features
FL = flags_all()
rows = []
for t in sorted(FL):
    s, sig, el = FL[t]
    if t[0] == 'A':
        r = stats(sig, mA, yA, s, COST_A, t, nperm=10000, extra=False)
    else:
        r = stats(sig, mW, yB, s, 0.0, t, nperm=10000, extra=False)
    rows.append(r)
TAB = pd.DataFrame(rows)
TAB['holm'] = holm(TAB.luck_p)
TAB.to_csv(f'{OUT}/all36_{TAG}.csv', index=False, float_format='%.4f')
log('\n=== ALL 36 recomputed (luck p 10k perms; Holm over 36) ===')
log(TAB[['test', 'n', 'net', 'excess', 'q_pos', 'net_f14', 'exc_f14', 'net_l8', 'exc_l8', 'net_wo5', 'luck_p', 'holm']]
    .round(3).to_string(index=False))

# ------------------------------------------------------------------ 2. candidates: stress
CANDS = {'B09': ('B', 'PCR', 'top', +1), 'B13': ('B', 'dCIV20', 'top', +1), 'A12': ('A', 'BASISDEV', 'bot', -1),
         'A22': ('A', 'dPIV20', 'top', -1)}
rows = []
for t, (tr, col, side, s) in CANDS.items():
    if tr == 'B':
        pool, y, cost, pre, dec = mW, yB, 0.0, 'B_', 'i_react'
    else:
        pool, y, cost, pre, dec = mA, yA, COST_A, 'A_', 'i_cut'
    variants = [('as registered (same-quarter quintile)', pre, 'same', 0.2, y),
                ('prev-quarter cut-offs', pre, 'prev', 0.2, y),
                ('trailing 90-session cut-offs (strict PIT)', pre, 'trail', 0.2, y)]
    for fr in (0.10, 0.15, 0.25, 0.30, 0.40, 0.50):
        variants.append((f'top/bottom {int(fr * 100)}% (same quarter)', pre, 'same', fr, y))
    if tr == 'B':
        variants += [('features at k, entry close k+1', pre, 'same', 0.2, D.vsN_k1.to_numpy(float)),
                     ('features at k+1, entry close k+1', 'Bp1_', 'same', 0.2, D.vsN_k1.to_numpy(float)),
                     ('features at k, entry close k+2', pre, 'same', 0.2, D.vsN_k2.to_numpy(float)),
                     ('features at k-1 (before winner day)', 'Bm1_', 'same', 0.2, y)]
    else:
        variants += [('features one session earlier (i_cut-1)', 'A1_', 'same', 0.2, y)]
    for vname, p_, mode, fr, yy in variants:
        if p_ + col not in D.columns:
            continue
        sig, el = qflag(p_ + col, side, fr, mode, dec)
        r = stats(sig, pool, yy, s, cost, t, nperm=20000)
        r['variant'] = vname
        rows.append(r)
ST = pd.DataFrame(rows)
ST.to_csv(f'{OUT}/stress_{TAG}.csv', index=False, float_format='%.4f')
cols = ['test', 'variant', 'n', 'net', 'excess', 'q_pos', 'exc_f14', 'exc_l8', 'net_wo5', 'net_wo10', 'exc_wo10',
        'luck_p', 'loqo_min', 'loqo_argmin', 't_symclust']
log('\n=== STRESS (excess = vs parent same quarter, signed) ===')
log(ST[cols].round(3).to_string(index=False))
log('\nby year (excess, n):')
yc = ['test', 'variant'] + [f'{a}_{y_}' for y_ in range(2021, 2027) for a in ('n', 'exc')]
log(ST[ST.variant.str.startswith('as registered')][yc].round(2).to_string(index=False))

# ------------------------------------------------------------------ 3. B09 overlap / subgroup / survivorship / placebo
sig09, el09 = qflag('B_PCR', 'top')
sig13, el13 = qflag('B_dCIV20', 'top')
WR = mW & (D.cut_rsi14 > 50).to_numpy()
log('\n=== B09 / B13 subgroups: IN vs OUT among winners (net %) ===')


def inout(sig, el, sub, name):
    a = sub & sig & el & mW
    b = sub & ~sig & el & mW
    return {'group': name, 'n_in': int(a.sum()), 'net_in': yB[a].mean(), 'n_out': int(b.sum()), 'net_out': yB[b].mean(),
            'diff': yB[a].mean() - yB[b].mean()}


rr = []
for nm, sig, el in (('B09', sig09, el09), ('B13', sig13, el13)):
    for gname, sub in (('all winners', np.ones(len(D), bool)), ('RSI>50 winners', (D.cut_rsi14 > 50).to_numpy()),
                       ('RSI<=50 winners', (D.cut_rsi14 <= 50).to_numpy()),
                       ('habitual drifters', D.HABIT.to_numpy()), ('not habitual drifters', ~D.HABIT.to_numpy()),
                       ('early F&O members (by qn 1)', D.EARLY.to_numpy()), ('later joiners', ~D.EARLY.to_numpy()),
                       ('XN <= median winner', (D.XN <= np.median(D.XN[mW])).to_numpy()),
                       ('XN > median winner', (D.XN > np.median(D.XN[mW])).to_numpy()),
                       ('financials', D.industry.fillna('').str.contains('Bank|Financ|Insurance|Capital', regex=True).to_numpy()),
                       ('non-financials', ~D.industry.fillna('').str.contains('Bank|Financ|Insurance|Capital', regex=True).to_numpy())):
        r = inout(sig, el, sub, gname)
        r['test'] = nm
        rr.append(r)
SG = pd.DataFrame(rr)
log(SG[['test', 'group', 'n_in', 'net_in', 'n_out', 'net_out', 'diff']].round(2).to_string(index=False))
SG.to_csv(f'{OUT}/subgroups_{TAG}.csv', index=False, float_format='%.4f')
log(f'overlap: B09 {int((sig09 & mW).sum())} trades; with RSI>50 {int((sig09 & WR).sum())}; with habitual drifters '
    f'{int((sig09 & mW & D.HABIT.to_numpy()).sum())} (habitual drifters among winners {int((mW & D.HABIT.to_numpy()).sum())});'
    f' B09 & B13 {int((sig09 & sig13 & mW).sum())}')

# ------------------------------------------------------------------ 4. heavy-tail checks for B09 / B13
def tail_checks(sig, name, y=yB, pool=mW, nd=20000):
    m = sig & pool & np.isfinite(y)
    pm = pool & np.isfinite(y)
    qm = pd.Series(y[pm]).groupby(q[pm]).mean()
    exc = y - qm.reindex(q).to_numpy()
    n = int(m.sum())

    def trim_stat(e, k=10):
        return np.sort(e)[::-1][k:].mean()
    obs10 = trim_stat(exc[m])
    lo_, hi_ = np.percentile(y[pm], [2.5, 97.5])
    yw = np.clip(y, lo_, hi_)
    qmw = pd.Series(yw[pm]).groupby(q[pm]).mean()
    excw = yw - qmw.reindex(q).to_numpy()
    obsw = excw[m].mean()
    # median-based: share of IN trades above their quarter's winner median
    qmed = pd.Series(y[pm]).groupby(q[pm]).median()
    above = (y[m] > qmed.reindex(q[m]).to_numpy()).mean()
    # null: random same-size picks per quarter
    null10, nullw, nullab = np.empty(nd), np.empty(nd), np.empty(nd)
    idx_q = {x: np.flatnonzero(pm & (q == x)) for x in np.unique(q[m])}
    kq = {x: int((m & (q == x)).sum()) for x in idx_q}
    for b in range(nd):
        pick = np.concatenate([rng.choice(idx_q[x], kq[x], replace=False) for x in idx_q])
        null10[b] = trim_stat(exc[pick])
        nullw[b] = excw[pick].mean()
        nullab[b] = (y[pick] > qmed.reindex(q[pick]).to_numpy()).mean()
    log(f'{name}: n {n}; excess w/o best 10 {obs10:+.3f} (null mean {null10.mean():+.3f}, p {(null10 >= obs10).mean():.4f}); '
        f'winsorised 2.5/97.5 excess {obsw:+.3f} (p {(nullw >= obsw).mean():.4f}); share above quarter median {above:.3f} '
        f'(null {nullab.mean():.3f}, p {(nullab >= above).mean():.4f})')


log('\n=== heavy-tail checks (null = random same-size picks per quarter from winners) ===')
tail_checks(sig09, 'B09')
tail_checks(sig13, 'B13')
tail_checks(qflag('B_PCR', 'top', 0.2, 'trail')[0], 'B09 trailing cut-offs')
tail_checks(sig09, 'B09 entry k+1', y=D.vsN_k1.to_numpy(float))


def ols_cluster(y, Xm, groups):
    Xm = np.column_stack([np.ones(len(y)), Xm])
    beta, *_ = np.linalg.lstsq(Xm, y, rcond=None)
    u = y - Xm @ beta
    XtXi = np.linalg.pinv(Xm.T @ Xm)
    meat = np.zeros((Xm.shape[1], Xm.shape[1]))
    G = np.unique(groups)
    for g in G:
        sg = Xm[groups == g].T @ u[groups == g]
        meat += np.outer(sg, sg)
    c = len(G) / (len(G) - 1) * (len(y) - 1) / (len(y) - Xm.shape[1])
    V = c * XtXi @ meat @ XtXi
    return beta[1:], np.sqrt(np.diag(V))[1:]


w = D[mW].copy()
w['B09'] = sig09[mW].astype(float)
w['RSIHI'] = (w.cut_rsi14 > 50).astype(float)
w['HABITf'] = w.HABIT.astype(float)
w['EARLYf'] = w.EARLY.astype(float)
qd_ = pd.get_dummies(w.qn, prefix='q', drop_first=True).astype(float)
for lab, cols_ in (('B09 + XN + RSIHI + HABIT + EARLY', ['B09', 'XN', 'RSIHI', 'HABITf', 'EARLYf']),):
    Xm = np.column_stack([w[cols_].to_numpy(float), qd_.to_numpy()])
    w['ind_q'] = w.industry.fillna('?') + '|' + w.qn.astype(str)
    w['react_week'] = (w.i_react // 5).astype(str)
    for cl in ('qn', 'symbol', 'ind_q', 'react_week'):
        b, se = ols_cluster(w.vsN_net_H20.to_numpy(float), Xm, w[cl].to_numpy())
        log(f'OLS quarter FE ({lab}), clustered by {cl}: ' + '; '.join(f'{c_} {b[i_]:+.2f} (t {b[i_] / se[i_]:+.2f})'
                                                                       for i_, c_ in enumerate(cols_)))
log(f'B09 overlap with lag-rule results rows: {int((sig09 & mW & D.LAG.to_numpy()).sum())}; lag-rule rows that are winners: '
    f'{int((mW & D.LAG.to_numpy()).sum())}')
dte_k = pd.Series(DAYS[D.i_react.to_numpy()])
if 'B_PCRREL' in D.columns:
    log('\n=== post-hoc (not pre-registered): what part of PCR carries it? (winners, net %) ===')
    for lab, col in (('PCR level at cutoff (pre-results)', 'A_PCR'), ('PCR own 60-session median before k', 'B_PCR_MED60'),
                     ('PCR at k vs own 60-session median', 'B_PCRREL'), ('PCR change on k', 'B_dPCR1'),
                     ('PCR at k', 'B_PCR')):
        v = D[col].to_numpy(float)
        g = mW & np.isfinite(v)
        tq = pd.Series(v[g]).groupby(q[g]).transform(lambda s_: s_.rank(pct=True)).to_numpy()
        hi_ = np.zeros(len(D), bool)
        hi_[np.flatnonzero(g)] = tq > 0.5
        lo_ = g & ~hi_
        log(f'  {lab:40s}: winners above their quarter median {int(hi_.sum())} net {yB[hi_].mean():+.2f} | below '
            f'{int(lo_.sum())} net {yB[lo_].mean():+.2f} | diff {yB[hi_].mean() - yB[lo_].mean():+.2f}')

try:
    import statsmodels.api as sm
    w = D[mW].copy()
    w['B09'] = sig09[mW].astype(float)
    w['RSIHI'] = (w.cut_rsi14 > 50).astype(float)
    w['HABIT'] = w.HABIT.astype(float)
    Xo = pd.concat([w[['B09', 'XN', 'RSIHI', 'HABIT']], pd.get_dummies(w.qn, prefix='q', drop_first=True).astype(float)], axis=1)
    Xo = sm.add_constant(Xo)
    for cl in ('qn', 'symbol'):
        g = pd.factorize(w[cl])[0]
        fit = sm.OLS(w.vsN_net_H20.to_numpy(float), Xo).fit(cov_type='cluster', cov_kwds={'groups': g})
        log(f'OLS quarter FE, clustered by {cl}: B09 {fit.params["B09"]:+.3f} (t {fit.tvalues["B09"]:+.2f}); '
            f'XN {fit.params["XN"]:+.3f} (t {fit.tvalues["XN"]:+.2f}); RSIHI {fit.params["RSIHI"]:+.3f} '
            f'(t {fit.tvalues["RSIHI"]:+.2f}); HABIT {fit.params["HABIT"]:+.3f} (t {fit.tvalues["HABIT"]:+.2f})')
except Exception as e:
    log('OLS skipped', repr(e))

# placebo for B09 on quiet-day winners
QF = f'{OUT}/my_quiet_features.csv.gz' if TAG == 'mine' else None
if QF:
    qd = pd.read_csv(QF)
    qd['y'] = hedged(qd.symbol, qd.i)
    qd = qd[np.isfinite(qd.y)].reset_index(drop=True)
    qd['month'] = qd.day.str[:7]
    for cut in ('month, all quiet days', 'quarter cut-off from results'):
        if cut.startswith('month'):
            c80 = qd.groupby('month').B_PCR.transform(lambda s: s.quantile(0.8))
        else:
            # results cut-off of the results season whose reaction days are nearest (same calendar quarter of k)
            rq = pd.DataFrame({'ym': pd.Series(DAYS[D.i_react.to_numpy()]).str[:7], 'qn': q, 'v': D.B_PCR})
            per_q = rq.groupby('qn').v.quantile(0.8)
            qmonth = rq.groupby('ym').qn.agg(lambda s: s.mode().iloc[0])
            allm = pd.Series(sorted(qd.month.unique()))
            qmap = {m_: qmonth.get(m_, np.nan) for m_ in allm}
            qmap = pd.Series(qmap).ffill().bfill()
            c80 = qd.month.map(qmap).map(per_q)
        qd['sig'] = (qd.B_PCR > c80) & qd.B_PCR.notna()
        QW = qd.W.astype(bool)
        g = qd[QW & qd.B_PCR.notna()]
        dm = g.y - g.groupby('month').y.transform('mean')
        pe = dm[g.sig].mean()
        log(f'placebo quiet winners ({cut}): IN {int(g.sig.sum())} net {g.y[g.sig].mean():+.2f} | OUT {int((~g.sig).sum())} '
            f'net {g.y[~g.sig].mean():+.2f} | placebo excess (within month) {pe:+.2f}')
        rres = ST[(ST.test == 'B09') & ST.variant.str.startswith('as registered')].excess.iloc[0]
        log(f'   DiD = results excess {rres:+.2f} - placebo excess {pe:+.2f} = {rres - pe:+.2f}')
        # also k+1 entry on quiet winners (placebo of the k+1 robustness)
        y1 = hedged(g.symbol, g.i + 1)
        log(f'   quiet winners entry k+1: IN {np.nanmean(y1[g.sig.to_numpy()]):+.2f} OUT {np.nanmean(y1[~g.sig.to_numpy()]):+.2f}')
log('done')
