#!/usr/bin/env python3
"""Verifier, own code: stress tests for the candidates (B09, B13, A12, A22) on MY features and flags.
usage: python3 w6_stress.py <scratchpad> <verify_dir>
"""
import sys

import numpy as np
import pandas as pd

SP, VD = sys.argv[1], sys.argv[2]
W = f'{VD}/work'
LOG = open(f'{W}/w6_stress.log', 'w')
pd.set_option('display.width', 250)
pd.set_option('display.max_columns', 30)
CA, CB = 0.17, 0.19
rng = np.random.default_rng(77)


def log(*a):
    s = ' '.join(map(str, a))
    print(s, flush=True)
    LOG.write(s + '\n')
    LOG.flush()


ses = pd.read_csv(f'{SP}/sector_lab/data/sessions.csv')
DAYS = ses.day.to_numpy()
T = len(DAYS)
ret = pd.read_csv(f'{SP}/sector_lab/data/returns.csv', index_col=0)
SY = ret.columns.tolist()
SJ = {s: j for j, s in enumerate(SY)}
RET = ret.to_numpy(float)
PX = np.cumprod(1 + np.nan_to_num(RET), axis=0)
NIF = pd.read_csv(f'{SP}/sector_lab/data/index_close.csv', index_col=0)['Nifty 50'].to_numpy(float)
NV = np.cumsum(np.isfinite(RET), axis=0)
ohl = pd.read_csv(f'{SP}/ta/build/adjusted_ohlcv.csv.gz', usecols=['day', 'symbol', 'open', 'close'])
ohl = ohl[ohl.symbol.isin(SJ) & ohl.day.isin(set(DAYS))]
DI = {d: i for i, d in enumerate(DAYS)}
OPEN = np.full((T, len(SY)), np.nan)
CLOSE = np.full((T, len(SY)), np.nan)
OPEN[ohl.day.map(DI).to_numpy(), ohl.symbol.map(SJ).to_numpy()] = ohl.open.to_numpy(float)
CLOSE[ohl.day.map(DI).to_numpy(), ohl.symbol.map(SJ).to_numpy()] = ohl.close.to_numpy(float)

pan = pd.read_csv(f'{SP}/perf/features/panel.csv',
                  usecols=['symbol', 'qn', 'quarter', 'period', 'i_cut', 'i_rd', 'i_p1', 'i_react', 'in_fo',
                           'in_fo_events', 'lag21', 'vol_ratio_5_60', 'cut_rsi14', 'XN', 'W', 'mean_drift_4_B',
                           'fin_type', 'sector_index'])
oc = pd.read_csv(f'{SP}/perf/features/outcomes.csv', usecols=['symbol', 'qn', 'three_day', 'vsN_net_H20', 'tradable_B'])
fe = pd.read_csv(f'{W}/w_results_features.csv').drop(columns=['quarter', 'period', 'i_cut', 'i_react'])
fl = pd.read_csv(f'{W}/w4_flags.csv')
ev = pd.read_csv(f'{SP}/sector_lab/data/events.csv', usecols=['symbol', 'qn', 'mcap'])
D = pan.merge(oc, on=['symbol', 'qn']).merge(fe, on=['symbol', 'qn']).merge(fl, on=['symbol', 'qn']).merge(
    ev, on=['symbol', 'qn'], how='left')
assert len(D) == 3280
D['label'] = 'Results for ' + D.period + ' (' + D.quarter + ')'
J = D.symbol.map(SJ).to_numpy(int)
k = D.i_react.to_numpy()
qn = D.qn.to_numpy()
yA = D.three_day.to_numpy(float)
yB = D.vsN_net_H20.to_numpy(float)
PA = np.isfinite(yA)
PB = ((D.W == True) & (D.tradable_B == True)).to_numpy()
WR = PB & (D.cut_rsi14 > 50).to_numpy()
LR = PA & (D.lag21 < -10).to_numpy() & (D.vol_ratio_5_60 >= 1).to_numpy() & (D.in_fo_events == True).to_numpy()
# habitual drifters: mean_drift_4_B >= quarter 80th pct over tradable F&O results with the value (any reaction)
md = D.mean_drift_4_B.where(D.tradable_B == True)
HD = ((md >= md.groupby(D.qn).transform(lambda s: s.quantile(0.8))) & (D.tradable_B == True)).to_numpy()
log(f'habitual drifters (tradable, top fifth of last-4 drift): {HD.sum()} mean net {yB[HD].mean():+.3f} (documented 569 +1.80)')
first_fo = D[D.in_fo == True].groupby('symbol').qn.min()
EARLY = D.symbol.map(first_fo).fillna(99).to_numpy() <= 1
log(f'early F&O members (F&O result at qn<=1): {D[EARLY].symbol.nunique()} symbols; later joiners '
    f'{D[~EARLY].symbol.nunique()}')


def hedged(start, end, j):
    ok = (end < T) & ((NV[np.minimum(end, T - 1), j] - NV[start, j]) >= (end - start) - 2)
    e = np.minimum(end, T - 1)
    v = ((PX[e, j] / PX[start, j] - 1) - (NIF[e] / NIF[start] - 1)) * 100 - CB
    return np.where(ok, v, np.nan)


yB_k1 = hedged(k + 1, k + 21, J)                              # entry close k+1, hold 20
e20 = np.minimum(k + 20, T - 1)
yB_o1 = np.where(np.isfinite(OPEN[np.minimum(k + 1, T - 1), J]) & (k + 20 < T),
                 ((CLOSE[e20, J] / OPEN[np.minimum(k + 1, T - 1), J] - 1) - (NIF[e20] / NIF[k] - 1)) * 100 - CB,
                 np.nan)                                       # entry open k+1, exit close k+20 (Nifty from close k)


def stat(y, pool, m, sign=1, cost=0.0, q=qn):
    """n, net, excess vs same-quarter parent mean (signed)."""
    pool = pool & np.isfinite(y)
    m = m & pool
    if m.sum() == 0:
        return dict(n=0, net=np.nan, exc=np.nan)
    qm = pd.Series(y[pool]).groupby(q[pool]).mean()
    pnl = sign * y[m]
    base = sign * qm.reindex(q[m]).to_numpy()
    return dict(n=int(m.sum()), net=pnl.mean() - cost, exc=(pnl - base).mean())


def luck(y, pool, m, sign=1, nd=10000, q=qn):
    pool = pool & np.isfinite(y)
    m = m & pool
    obs = sign * y[m].mean()
    tot = np.zeros(nd)
    for g in np.unique(q[m]):
        cnt = int((m & (q == g)).sum())
        pv = sign * y[pool & (q == g)]
        if cnt == len(pv):
            tot += pv.sum()
            continue
        pick = np.argpartition(rng.random((nd, len(pv))), cnt - 1, axis=1)[:, :cnt]
        tot += pv[pick].sum(1)
    return (1 + (tot / m.sum() >= obs - 1e-12).sum()) / (nd + 1)


def line(name, y, pool, m, sign=1, cost=0.0, do_luck=True, q=qn):
    s = stat(y, pool, m, sign, cost, q)
    p = luck(y, pool, m, sign, q=q) if (do_luck and s['n'] > 0) else np.nan
    return {'variant': name, 'n': s['n'], 'net': round(s['net'], 3), 'excess': round(s['exc'], 3), 'luck_p': round(p, 4)}


def qcut(v, grp, q):
    return v.groupby(grp).transform(lambda s: s.quantile(q))


def trailing_cut(v, day_i, q, back=250, minn=60):
    """strictly point in time: quantile of v over results whose decision day is in [d-back, d-1]."""
    vv, di = v.to_numpy(float), np.asarray(day_i)
    out = np.full(len(vv), np.nan)
    order = np.argsort(di)
    for r_ in range(len(vv)):
        msk = (di < di[r_]) & (di >= di[r_] - back) & np.isfinite(vv)
        if msk.sum() >= minn:
            out[r_] = np.quantile(vv[msk], q)
    return out


def prevq_cut(v, q):
    c = v.groupby(D.qn).quantile(q)
    return D.qn.map({g: c.get(g - 1, c[g]) for g in c.index}).to_numpy()


def report(title, rows):
    log(f'\n--- {title}')
    log(pd.DataFrame(rows).to_string(index=False))


def per_quarter(y, pool, m, sign, cost):
    rows = []
    for g in range(22):
        s = stat(y, pool & (qn == g), m & (qn == g), sign, cost)
        rows.append({'qn': g, 'label': D.label[qn == g].iloc[0], 'n': s['n'], 'net': s['net'], 'exc': s['exc']})
    return pd.DataFrame(rows)


def loqo(y, pool, m, sign, cost):
    rows = []
    for g in range(22):
        keep = qn != g
        s = stat(y, pool & keep, m & keep, sign, cost)
        rows.append({'drop_qn': g, 'n': s['n'], 'exc': s['exc'], 'luck_p': luck(y, pool & keep, m & keep, sign, nd=3000)})
    return pd.DataFrame(rows)


def concentration(y, pool, m, sign, cost):
    pool_ = pool & np.isfinite(y)
    mm = m & pool_
    qm = pd.Series(y[pool_]).groupby(qn[pool_]).mean()
    ex = sign * (y[mm] - qm.reindex(qn[mm]).to_numpy())
    sy = D.symbol.to_numpy()[mm]
    g = pd.DataFrame({'s': sy, 'ex': ex}).groupby('s').ex.agg(['size', 'sum', 'mean']).sort_values('sum')
    out = {'distinct_symbols': len(g), 'top5_by_count': g['size'].sort_values().tail(5).to_dict(),
           'top5_excess_sum': g['sum'].tail(5).round(1).to_dict(), 'total_excess_sum': round(ex.sum(), 1)}
    # leave-one-symbol-out and dropping the 5 symbols contributing the most excess
    loso = [(s, (ex[sy != s]).mean()) for s in g.index]
    out['loso_min_exc'] = min(loso, key=lambda x: x[1])
    top5 = set(g.index[-5:])
    out['exc_wo_top5_symbols'] = round(ex[~np.isin(sy, list(top5))].mean(), 3)
    # symbol-cluster bootstrap of the excess
    syms = g.index.to_numpy()
    bs = []
    idx = {s: np.flatnonzero(sy == s) for s in syms}
    for _ in range(4000):
        pick = rng.choice(syms, len(syms))
        v = np.concatenate([ex[idx[s]] for s in pick])
        bs.append(v.mean())
    out['cluster_boot_exc_5_95'] = (round(np.percentile(bs, 5), 3), round(np.percentile(bs, 95), 3))
    out['cluster_boot_p_le0'] = round(float(np.mean(np.array(bs) <= 0)), 4)
    return out


def ols_cluster(y, X, cl):
    X = np.column_stack(X)
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ b
    XtXi = np.linalg.pinv(X.T @ X)
    meat = np.zeros((X.shape[1], X.shape[1]))
    for g in np.unique(cl):
        s = X[cl == g].T @ e[cl == g]
        meat += np.outer(s, s)
    G = len(np.unique(cl))
    V = XtXi @ meat @ XtXi * G / (G - 1)
    return b, np.sqrt(np.diag(V))


# ================================================================== B candidates
for t, feat in (('B09', 'PCR'), ('B13', 'dCIV20')):
    m = D[t].to_numpy(bool)
    el = D['el_' + t].to_numpy(bool)
    log(f'\n================ {t} ({feat} top quintile at k, long plain winners)')
    rows = [line('as pre-registered (my features)', yB, PB, m)]
    s = stat(yB, PB, m)
    pq = per_quarter(yB, PB, m, 1, 0)
    log(pq.round(3).to_string(index=False))
    rows.append(line('OUT (eligible, not signal)', yB, PB, el & ~m))
    for qq in (0.10, 0.15, 0.25, 0.30, 0.333, 0.5):
        v = D['B_' + feat]
        mm = (v > qcut(v, D.qn, 1 - qq)).to_numpy()
        rows.append(line(f'top {qq:.0%} within quarter', yB, PB, mm))
    v = D['B_' + feat]
    rows.append(line('PIT: previous-quarter cut-off', yB, PB, (v > prevq_cut(v, 0.8)).to_numpy()))
    tc = trailing_cut(v, D.i_react, 0.8)
    rows.append(line('PIT: trailing 250-session results cut-off', yB, PB, v.to_numpy() > tc))
    if feat == 'PCR':
        rows.append(line('PIT: same-day rank among all F&O stocks > 80%', yB, PB, (D.B_PCR_XS > 0.8).to_numpy()))
        rows.append(line('PIT: same-day rank > 60%', yB, PB, (D.B_PCR_XS > 0.6).to_numpy()))
        v2 = D.B_PCRREL
        rows.append(line('own-history: PCR / own 60d median top quintile', yB, PB,
                         (v2 > qcut(v2, D.qn, 0.8)).to_numpy()))
        for tag, nm in (('Bm1_', 'PCR at k-1 (before the reaction close)'), ('A_', 'PCR at cutoff'),
                        ('A1_', 'PCR at cutoff-1')):
            v3 = D[tag + 'PCR']
            rows.append(line(nm + ' top quintile', yB, PB, (v3 > qcut(v3, D.qn, 0.8)).to_numpy()))
        v4 = D.B_dPCR1
        rows.append(line('dPCR1 (change on k) top quintile [=B10]', yB, PB, (v4 > qcut(v4, D.qn, 0.8)).to_numpy()))
    else:
        v3 = D['Bm1_dCIV20']
        rows.append(line('dCIV20 at k-1 top quintile', yB, PB, (v3 > qcut(v3, D.qn, 0.8)).to_numpy()))
        v3 = D['A_dCIV20']
        rows.append(line('dCIV20 at cutoff top quintile', yB, PB, (v3 > qcut(v3, D.qn, 0.8)).to_numpy()))
    # entry timing (implementable with end-of-day data of k)
    rows.append(line('entry close k+1 (hold to k+21)', yB_k1, PB, m))
    rows.append(line('entry open k+1 (to close k+20)', yB_o1, PB, m))
    # without best trades
    pool_ = PB & np.isfinite(yB)
    qm = pd.Series(yB[pool_]).groupby(qn[pool_]).mean()
    mm = m & pool_
    ex = yB[mm] - qm.reindex(qn[mm]).to_numpy()
    o = np.argsort(-yB[mm])
    for kk_ in (5, 10, 20):
        rows.append({'variant': f'without best {kk_} trades', 'n': int(mm.sum()) - kk_,
                     'net': round(np.delete(yB[mm], o[:kk_]).mean(), 3), 'excess': round(np.delete(ex, o[:kk_]).mean(), 3),
                     'luck_p': np.nan})
    # subsets / overlaps
    for nm, sub in (('within RSI>50 winners', WR), ('within RSI<=50 winners', PB & ~WR),
                    ('within habitual drifters', PB & HD), ('outside habitual drifters', PB & ~HD),
                    ('early F&O members (qn<=1)', PB & EARLY), ('later F&O joiners', PB & ~EARLY),
                    ('first 14 (qn 0-13)', PB & (qn <= 13)), ('last 8 (qn 14-21)', PB & (qn >= 14)),
                    ('financials (fin_type != Company)', PB & (D.fin_type != 'Company').to_numpy()),
                    ('non-financials', PB & (D.fin_type == 'Company').to_numpy()),
                    ('XN 4-6%', PB & (D.XN <= 6).to_numpy()), ('XN > 6%', PB & (D.XN > 6).to_numpy())):
        s_in = stat(yB, sub, m & sub)
        s_out = stat(yB, sub, ~m & el & sub)
        rows.append({'variant': f'{nm}: IN', 'n': s_in['n'], 'net': round(s_in['net'], 3),
                     'excess': round(s_in['exc'], 3), 'luck_p': round(luck(yB, sub, m & sub), 4) if s_in['n'] else np.nan,
                     'OUT_n': s_out['n'], 'OUT_net': round(s_out['net'], 3)})
    report(f'{t} variants (excess = vs same-quarter plain-winner parent of the pool)', rows)
    log(f'overlap: {t} & RSI>50 {int((m & WR).sum())} of {int((m & PB).sum())}; & habitual drifters {int((m & PB & HD).sum())};'
        f' & early members {int((m & PB & EARLY).sum())}')
    # by calendar year of k
    yr = pd.Series(DAYS[k]).str[:4].to_numpy()
    rows = []
    for y_ in sorted(set(yr[PB])):
        s_ = stat(yB, PB & (yr == y_), m & (yr == y_))
        rows.append({'year': y_, 'n': s_['n'], 'net': round(s_['net'], 3), 'excess': round(s_['exc'], 3),
                     'parent_n': int((PB & (yr == y_)).sum()), 'parent_net': round(yB[PB & (yr == y_)].mean(), 3)})
    report(f'{t} by calendar year of k', rows)
    L = loqo(yB, PB, m, 1, 0)
    log(f'\n--- {t} leave-one-quarter-out: excess min {L.exc.min():+.3f} (drop qn {int(L.drop_qn[L.exc.idxmin()])}) '
        f'max {L.exc.max():+.3f}; luck p max {L.luck_p.max():.4f} (drop qn {int(L.drop_qn[L.luck_p.idxmax()])}); '
        f'luck p < 0.05 in {(L.luck_p < 0.05).sum()}/22')
    log(L.round(4).to_string(index=False))
    log(f'\n--- {t} concentration: {concentration(yB, PB, m, 1, 0)}')
    # regression among winners: y ~ flag + XN + RSI_HI + log notional + quarter FE (quarter-clustered)
    msk = PB & np.isfinite(yB) & el & np.isfinite(D.B_NOTIONAL.to_numpy())
    X = [m[msk].astype(float), D.XN.to_numpy()[msk], (D.cut_rsi14 > 50).to_numpy()[msk].astype(float),
         np.log(D.B_NOTIONAL.to_numpy()[msk])]
    X += [(qn[msk] == g).astype(float) for g in np.unique(qn[msk])]
    b, se = ols_cluster(yB[msk], X, qn[msk])
    b2, se2 = ols_cluster(yB[msk], X, D.symbol.to_numpy()[msk])
    log(f'--- {t} OLS among winners (quarter FE): flag {b[0]:+.3f} (se quarter-cl {se[0]:.3f}, t {b[0] / se[0]:+.2f}; '
        f'se symbol-cl {se2[0]:.3f}, t {b2[0] / se2[0]:+.2f}); XN {b[1]:+.3f} (t {b[1] / se[1]:+.2f}); RSI_HI {b[2]:+.3f} '
        f'(t {b[2] / se[2]:+.2f}); log futures OI notional {b[3]:+.3f} (t {b[3] / se[3]:+.2f}); n {int(msk.sum())}')
    log(f'    size: median futures OI notional (Rs cr) IN {np.nanmedian(D.B_NOTIONAL[m & PB]):.0f} OUT '
        f'{np.nanmedian(D.B_NOTIONAL[~m & el & PB]):.0f}; median mcap IN {np.nanmedian(D.mcap[m & PB]):.0f} OUT '
        f'{np.nanmedian(D.mcap[~m & el & PB]):.0f}; mean XN IN {D.XN[m & PB].mean():.2f} OUT {D.XN[~m & el & PB].mean():.2f}')

# ================================================================== A candidates
for t, feat, sign in (('A12', 'BASISDEV', -1), ('A22', 'dPIV20', -1)):
    m = D[t].to_numpy(bool)
    el = D['el_' + t].to_numpy(bool)
    log(f'\n================ {t} ({feat}, short the 3-day window)')
    rows = [line('as pre-registered (my features)', yA, PA, m, sign, CA)]
    v = D['A_' + feat]
    side_bot = t == 'A12'
    for qq in (0.10, 0.15, 0.25, 0.30, 0.333):
        mm = ((v <= qcut(v, D.qn, qq)) if side_bot else (v > qcut(v, D.qn, 1 - qq))).to_numpy()
        rows.append(line(f'{"bottom" if side_bot else "top"} {qq:.0%}', yA, PA, mm, sign, CA))
    pc = prevq_cut(v, 0.2 if side_bot else 0.8)
    rows.append(line('PIT previous-quarter cut-off', yA, PA, (v.to_numpy() <= pc) if side_bot else (v.to_numpy() > pc),
                     sign, CA))
    tc = trailing_cut(v, D.i_cut, 0.2 if side_bot else 0.8)
    rows.append(line('PIT trailing 250-session cut-off', yA, PA, (v.to_numpy() <= tc) if side_bot else (v.to_numpy() > tc),
                     sign, CA))
    v1 = D['A1_' + feat]
    mm = ((v1 <= qcut(v1, D.qn, 0.2)) if side_bot else (v1 > qcut(v1, D.qn, 0.8))).to_numpy()
    rows.append(line('features at cutoff-1', yA, PA, mm, sign, CA))
    pool_ = PA
    qm = pd.Series(yA[pool_]).groupby(qn[pool_]).mean()
    mm = m & pool_
    pnl = sign * yA[mm]
    ex = pnl - sign * qm.reindex(qn[mm]).to_numpy()
    o = np.argsort(-pnl)
    for kk_ in (5, 10, 20):
        rows.append({'variant': f'without best {kk_}', 'n': int(mm.sum()) - kk_,
                     'net': round(np.delete(pnl, o[:kk_]).mean() - CA, 3), 'excess': round(np.delete(ex, o[:kk_]).mean(), 3),
                     'luck_p': np.nan})
    for nm, sub in (('within lag-rule trades', PA & LR), ('early F&O members', PA & EARLY), ('later joiners', PA & ~EARLY),
                    ('first 14', PA & (qn <= 13)), ('last 8', PA & (qn >= 14))):
        s_in = stat(yA, sub, m & sub, sign, CA)
        rows.append({'variant': f'{nm}: IN', 'n': s_in['n'], 'net': round(s_in['net'], 3), 'excess': round(s_in['exc'], 3),
                     'luck_p': round(luck(yA, sub, m & sub, sign), 4) if s_in['n'] > 0 else np.nan})
    report(f'{t} variants', rows)
    yr = pd.Series(DAYS[D.i_cut.to_numpy()]).str[:4].to_numpy()
    rows = []
    for y_ in sorted(set(yr)):
        s_ = stat(yA, PA & (yr == y_), m & (yr == y_), sign, CA)
        rows.append({'year': y_, 'n': s_['n'], 'net': round(s_['net'], 3), 'excess': round(s_['exc'], 3)})
    report(f'{t} by calendar year of the cutoff', rows)
    L = loqo(yA, PA, m, sign, CA)
    log(f'--- {t} LOQO: excess min {L.exc.min():+.3f} max {L.exc.max():+.3f}; luck p max {L.luck_p.max():.4f}; '
        f'luck p < 0.05 in {(L.luck_p < 0.05).sum()}/22')
    log(f'--- {t} concentration: {concentration(yA, PA, m, sign, CA)}')
log('done')
