#!/usr/bin/env python3
"""Verifier, own code: recompute the 36 pre-registered F&O-positioning tests from MY features (w3_features.py),
with my own permutation / Holm / maxT / placebo code; compare with the study's tests.csv.

usage: python3 w4_tests.py <scratchpad> <verify_dir>
outputs: work/w4_tests.log, work/w4_tests.csv, work/w4_flags.csv (my flags per results row), work/w4_placebo_*.csv.gz
"""
import sys

import numpy as np
import pandas as pd

SP, VD = sys.argv[1], sys.argv[2]
W = f'{VD}/work'
LOG = open(f'{W}/w4_tests.log', 'w')
pd.set_option('display.width', 260)
pd.set_option('display.max_columns', 40)
CA, CB = 0.17, 0.19
NPERM = 20000


def log(*a):
    s = ' '.join(map(str, a))
    print(s, flush=True)
    LOG.write(s + '\n')
    LOG.flush()


# ------------------------------------------------------------------ data
ses = pd.read_csv(f'{SP}/sector_lab/data/sessions.csv')
DAYS = ses.day.to_numpy()
T = len(DAYS)
ret = pd.read_csv(f'{SP}/sector_lab/data/returns.csv', index_col=0)
SY = ret.columns.tolist()
SJ = {s: j for j, s in enumerate(SY)}
RET = ret.to_numpy(float)
PX = np.cumprod(1 + np.nan_to_num(RET), axis=0)
NIF = pd.read_csv(f'{SP}/sector_lab/data/index_close.csv', index_col=0)['Nifty 50'].to_numpy(float)
NRET = np.r_[np.nan, NIF[1:] / NIF[:-1] - 1]
NVALID = np.cumsum(np.isfinite(RET), axis=0)

pan = pd.read_csv(f'{SP}/perf/features/panel.csv',
                  usecols=['symbol', 'qn', 'quarter', 'period', 'i_cut', 'i_rd', 'i_p1', 'i_react', 'in_fo_events',
                           'lag21', 'vol_ratio_5_60', 'cut_rsi14', 'XN', 'W', 'mean_drift_4_B'])
oc = pd.read_csv(f'{SP}/perf/features/outcomes.csv',
                 usecols=['symbol', 'qn', 'three_day', 'vsN_H20', 'vsN_net_H20', 'tradable_B'])
fe = pd.read_csv(f'{W}/w_results_features.csv').drop(columns=['quarter', 'period', 'i_cut', 'i_react'])
D = pan.merge(oc, on=['symbol', 'qn'], validate='1:1').merge(fe, on=['symbol', 'qn'], validate='1:1')
assert len(D) == 3280
J = D.symbol.map(SJ).to_numpy(int)

# ------------------------------------------------------------------ outcome check from returns.csv / Nifty
ic, ip1, k = D.i_cut.to_numpy(), D.i_p1.to_numpy(), D.i_react.to_numpy()
log('i_p1 - i_cut values:', np.unique(ip1 - ic))
td = (PX[ip1, J] / PX[ic, J] - 1) * 100
ok = D.three_day.notna()
log(f'three_day recomputed: max |diff| {np.nanmax(np.abs(td[ok] - D.three_day[ok])):.2e} over {int(ok.sum())} rows')
kk = np.minimum(k + 20, T - 1)
vs = (PX[kk, J] / PX[k, J] - 1) * 100 - (NIF[kk] / NIF[k] - 1) * 100
okb = D.tradable_B == True
log(f'vsN_H20 recomputed: max |diff| {np.nanmax(np.abs(vs[okb] - D.vsN_H20[okb])):.2e} over {int(okb.sum())} rows;'
    f' vsN_net = vsN - 0.19: max |diff| {np.nanmax(np.abs(D.vsN_H20[okb] - 0.19 - D.vsN_net_H20[okb])):.2e}')
XNm = (RET[k, J] - NRET[k]) * 100
log(f'XN recomputed: max |diff| {np.nanmax(np.abs(XNm - D.XN)):.2e}; W == (XN > 4): {bool(((D.XN > 4) == D.W).all())}')


# ------------------------------------------------------------------ flags (prereg definitions, my implementation)
def qcut(v, grp, q):
    return v.groupby(grp).transform(lambda s: s.quantile(q))


def flags(X, grp, pa='A_', pb='B_', qq=0.2, pre=None):
    """return {test: (signal bool array, eligible bool array)}; X frame with features; grp group labels."""
    pre = pa if pre is None else pre
    f = {}
    for L, b in ((5, 1), (10, 5)):
        dp, do = X[f'{pa}dP{L}'], X[f'{pa}dOI{L}']
        el = dp.notna() & do.notna()
        f[f'A{b:02d}'] = ((dp > 0) & (do > 10), el)
        f[f'A{b + 1:02d}'] = ((dp < 0) & (do > 10), el)
        f[f'A{b + 2:02d}'] = ((dp > 0) & (do < -10), el)
        f[f'A{b + 3:02d}'] = ((dp < 0) & (do < -10), el)
    for t, c, side in (('A09', 'OI20', 1), ('A10', 'OI20', 0), ('A11', 'BASISDEV', 1), ('A12', 'BASISDEV', 0),
                       ('A13', 'PCR', 1), ('A14', 'PCR', 0), ('A15', 'dPCR5', 1), ('A16', 'dPCR5', 0),
                       ('A17', 'IVREL', 1), ('A18', 'IVREL', 0), ('A19', 'IVSPREAD', 1), ('A20', 'IVSPREAD', 0),
                       ('A21', 'dCIV20', 1), ('A22', 'dPIV20', 1)):
        v = X[pa + c]
        f[t] = ((v > qcut(v, grp, 1 - qq)) if side else (v <= qcut(v, grp, qq)), v.notna())
    el = X[pb + 'dOI1'].notna()
    f['B01'] = (X[pb + 'dOI1'] > 0, el)
    f['B02'] = (X[pb + 'dOI1'] > 10, el)
    f['B03'] = ((X[pb + 'dP5'] > 0) & (X[pb + 'dOI5'] > 10), X[pb + 'dP5'].notna() & X[pb + 'dOI5'].notna())
    f['B04'] = ((X[pb + 'dP10'] > 0) & (X[pb + 'dOI10'] > 10), X[pb + 'dP10'].notna() & X[pb + 'dOI10'].notna())
    f['B05'] = ((X[pre + 'dP5'] < 0) & (X[pre + 'dOI5'] > 10), X[pre + 'dP5'].notna() & X[pre + 'dOI5'].notna())
    for t, c, side in (('B06', 'OI20', 1), ('B07', 'BASISDEV', 1), ('B08', 'dBASIS1', 1), ('B09', 'PCR', 1),
                       ('B10', 'dPCR1', 1), ('B11', 'IVREL', 0), ('B12', 'IVSPREAD', 1), ('B13', 'dCIV20', 1),
                       ('B14', 'dPIV20', 0)):
        v = X[pb + c]
        f[t] = ((v > qcut(v, grp, 1 - qq)) if side else (v <= qcut(v, grp, qq)), v.notna())
    return {t: ((s & e).fillna(False).to_numpy(bool), e.fillna(False).to_numpy(bool)) for t, (s, e) in f.items()}


SIGN = {**{f'A{i:02d}': s for i, s in zip(range(1, 23), [1, -1, 1, -1, 1, -1, 1, -1, 1, -1, 1, -1, 1, -1, 1, -1,
                                                         -1, 1, 1, -1, 1, -1])},
        **{f'B{i:02d}': 1 for i in range(1, 15)}}
IDS = list(SIGN)
FL = flags(D, D.qn)
fl_df = D[['symbol', 'qn']].copy()
for t, (s, e) in FL.items():
    fl_df[t] = s
    fl_df['el_' + t] = e
fl_df.to_csv(f'{W}/w4_flags.csv', index=False)

PA = D.three_day.notna().to_numpy()
PB = ((D.W == True) & (D.tradable_B == True)).to_numpy()
log(f'parents: A {PA.sum()} mean gross {D.three_day[PA].mean():+.3f}; B winners {PB.sum()} mean net '
    f'{D.vsN_net_H20[PB].mean():+.3f}; RSI>50 winners {(PB & (D.cut_rsi14 > 50)).sum()} '
    f'{D.vsN_net_H20[PB & (D.cut_rsi14 > 50)].mean():+.3f}')
LR = PA & (D.lag21 < -10).to_numpy() & (D.vol_ratio_5_60 >= 1).to_numpy() & (D.in_fo_events == True).to_numpy()
log(f'lag rule: {LR.sum()} trades, gross {D.three_day[LR].mean():+.3f}')


def describe(y, q, pool, m, sign, cost):
    """y outcome (full length), q quarter, pool parent mask, m signal mask (subset of pool)."""
    m = m & pool
    pnl = sign * y[m]
    qq = q[m]
    qm = pd.Series(y[pool]).groupby(q[pool]).mean()
    base = sign * qm.reindex(qq).to_numpy()
    net = pnl - cost
    r = {'n': int(m.sum()), 'net': net.mean(), 'excess': (pnl - base).mean()}
    pq = pd.Series(net).groupby(qq).mean()
    r['q_pos'] = f'{int((pq > 0).sum())}/{len(pq)}'
    for h, hm in (('f14', qq <= 13), ('l8', qq >= 14)):
        r[f'net_{h}'] = net[hm].mean() if hm.any() else np.nan
        r[f'exc_{h}'] = (pnl - base)[hm].mean() if hm.any() else np.nan
    o = np.argsort(-pnl)
    for kk_ in (5, 10):
        keep = np.ones(len(pnl), bool)
        keep[o[:kk_]] = False
        r[f'net_wo{kk_}'] = net[keep].mean()
        r[f'exc_wo{kk_}'] = (pnl - base)[keep].mean()
    return r


def joint_perm(y, q, pool, masks, signs, nperm, seed):
    rng = np.random.default_rng(seed)
    idx = np.flatnonzero(pool)
    yy, qq = y[idx], q[idx]
    MM = np.column_stack([m[idx] for m in masks]).astype(float)
    nn = MM.sum(0)
    sg = np.asarray(signs, float)
    obs = sg * (yy @ MM) / nn
    groups = [np.flatnonzero(qq == g) for g in np.unique(qq)]
    st = np.empty((nperm, MM.shape[1]))
    for b0 in range(0, nperm, 500):
        nb = min(500, nperm - b0)
        Y = np.empty((nb, len(yy)))
        for g in groups:
            Y[:, g] = yy[g][rng.permuted(np.tile(np.arange(len(g)), (nb, 1)), axis=1)]
        st[b0:b0 + nb] = sg * (Y @ MM) / nn
    return obs, st


def holm(p):
    p = np.asarray(p)
    o = np.argsort(p)
    adj = np.empty_like(p)
    run = 0
    for r_, i_ in enumerate(o):
        run = max(run, min(1, (len(p) - r_) * p[i_]))
        adj[i_] = run
    return adj


yA = D.three_day.to_numpy(float)
yB = D.vsN_net_H20.to_numpy(float)
qn = D.qn.to_numpy(int)
Aids = [t for t in IDS if t[0] == 'A']
Bids = [t for t in IDS if t[0] == 'B']
oA, sA = joint_perm(np.nan_to_num(yA), qn, PA, [FL[t][0] for t in Aids], [SIGN[t] for t in Aids], NPERM, 1)
oB, sB = joint_perm(np.nan_to_num(yB), qn, PB, [FL[t][0] for t in Bids], [SIGN[t] for t in Bids], NPERM, 2)
obs = np.r_[oA, oB]
st = np.column_stack([sA, sB])
luck = (1 + (st >= obs - 1e-12).sum(0)) / (NPERM + 1)
mu, sd = st.mean(0), st.std(0)
z = (st - mu) / sd
zo = (obs - mu) / sd
mx = z.max(1)
maxT = (1 + (mx[:, None] >= zo[None, :] - 1e-12).sum(0)) / (NPERM + 1)
hp = holm(luck)
log(f'maxT null 95th pct {np.percentile(mx, 95):.2f}; observed max z {zo.max():.2f} ({IDS[int(np.argmax(zo))]})')

# ------------------------------------------------------------------ placebo (own construction from daily data)
dd = np.load(f'{W}/w_daily.npz')
ev = pd.read_csv(f'{SP}/sector_lab/data/events.csv', usecols=['symbol', 'i_rd', 'i_react'])
ev = ev[ev.symbol.isin(SJ)]
near = {}
for s, g in ev.groupby('symbol'):
    near[SJ[s]] = np.unique(np.r_[g.i_rd.to_numpy(), g.i_react.to_numpy()])
FOm = np.isfinite(dd['OIA'])
I0 = 1342


def clean_days(before, after, horizon):
    rows = []
    for j in range(len(SY)):
        ii = np.flatnonzero(FOm[:, j])
        ii = ii[(ii >= I0) & (ii + horizon + 1 < T)]
        ev_j = near.get(j, np.array([], int))
        if len(ev_j):
            lo = np.searchsorted(ev_j, ii - before)
            hi = np.searchsorted(ev_j, ii + after, side='right')
            ii = ii[hi == lo]
        rows.append(np.c_[ii, np.full(len(ii), j)])
    return np.vstack(rows)


FEATS = ['dOI1', 'dOI5', 'dOI10', 'dP1', 'dP5', 'dP10', 'OI20', 'BASIS', 'BASISDEV', 'dBASIS1', 'PCR', 'dPCR5',
         'dPCR1', 'IVREL', 'IVSPREAD', 'dCIV20', 'dPIV20']


def frame(ii, jj, pre_shift=0):
    X = pd.DataFrame({f: dd[f][ii, jj] for f in FEATS})
    return X


# B placebo: no result session in [i-10, i+20]; quiet winners XN > 4; 20-session hedged return net of 0.19
qb = clean_days(10, 20, 21)
ii, jj = qb[:, 0], qb[:, 1]
XB_ = frame(ii, jj).add_prefix('B_')
XA_ = frame(ii - 2, jj).add_prefix('A_')
Xq = pd.concat([XB_, XA_], axis=1)
month = pd.Series(DAYS[ii]).str[:7].to_numpy()
flq = flags(Xq, month)
xn = (RET[ii, jj] - NRET[ii]) * 100
valid = (NVALID[ii + 20, jj] - NVALID[ii, jj]) >= 18
yq = ((PX[ii + 20, jj] / PX[ii, jj] - 1) - (NIF[ii + 20] / NIF[ii] - 1)) * 100 - CB
QW = (xn > 4) & valid & np.isfinite(yq)
log(f'\nB placebo: quiet F&O stock-days {len(ii)}; quiet winners with outcome {QW.sum()}, mean net {yq[QW].mean():+.3f}')
qwm = pd.Series(yq[QW]).groupby(month[QW]).mean()
dq_all = yq - qwm.reindex(month).to_numpy()


def placebo_B(t, e_res, n_res, rng):
    s = flq[t][0] & QW
    if s.sum() < 5:
        return {'pl_n': int(s.sum())}
    d = dq_all[s]
    dr = d[rng.integers(0, len(d), (10000, n_res))].mean(1)
    return {'pl_n': int(s.sum()), 'pl_exc': d.mean(), 'DiD': e_res - d.mean(),
            'pl_p': (1 + (dr >= e_res).sum()) / 10001}


# A placebo: no result session in [i-10, i+13]; 3-day forward return
qa = clean_days(10, 13, 4)
ia, ja = qa[:, 0], qa[:, 1]
Xa = frame(ia, ja).add_prefix('A_')
Xa = pd.concat([Xa, Xa.rename(columns=lambda c: 'B_' + c[2:])], axis=1)
mon_a = pd.Series(DAYS[ia]).str[:7].to_numpy()
fla = flags(Xa, mon_a)
ya = (PX[ia + 3, ja] / PX[ia, ja] - 1) * 100
va = (NVALID[ia + 3, ja] - NVALID[ia, ja]) >= 3
yam = pd.Series(ya[va]).groupby(mon_a[va]).mean()
da_all = ya - yam.reindex(mon_a).to_numpy()
log(f'A placebo: ordinary F&O stock-days with 3-day outcome {int(va.sum())}, mean {ya[va].mean():+.3f}')


def placebo_A(t, e_res, n_res, rng):
    s = fla[t][0] & va
    d = SIGN[t] * da_all[s]
    dr = d[rng.integers(0, len(d), (10000, n_res))].mean(1)
    return {'pl_n': int(s.sum()), 'pl_exc': d.mean(), 'DiD': e_res - d.mean(),
            'pl_p': (1 + (dr >= e_res).sum()) / 10001}


rng = np.random.default_rng(5)
rows = []
for n_, t in enumerate(IDS):
    if t[0] == 'A':
        r = describe(yA, qn, PA, FL[t][0], SIGN[t], CA)
        r.update(placebo_A(t, r['excess'], r['n'], rng))
    else:
        r = describe(yB, qn, PB, FL[t][0], 1, 0.0)
        r.update(placebo_B(t, r['excess'], r['n'], rng))
    r.update(test=t, luck_p=luck[n_], holm=hp[n_], maxT=maxT[n_])
    r['works'] = bool((r['exc_f14'] > 0) and (r['exc_l8'] > 0) and (r['net_f14'] > 0) and (r['net_l8'] > 0) and
                      (r['holm'] < 0.10) and (r.get('DiD', -1) > 0) and (r.get('pl_p', 1) < 0.10) and
                      (r['net_wo5'] > 0))
    rows.append(r)
R = pd.DataFrame(rows).set_index('test')
R.to_csv(f'{W}/w4_tests.csv')
th = pd.read_csv(f'{SP}/more_signals/oi/results/tests.csv').set_index('test')
cmp = pd.DataFrame({'n_mine': R.n, 'n_study': th.n, 'net_mine': R.net.round(3), 'net_study': th.avg_net.round(3),
                    'exc_mine': R.excess.round(3), 'exc_study': th.excess.round(3), 'luck_mine': R.luck_p.round(3),
                    'luck_study': th.luck_p.round(3), 'holm_mine': R.holm.round(3), 'holm_study': th.holm_p.round(3),
                    'maxT_mine': R.maxT.round(3), 'DiD_mine': R.DiD.round(2), 'DiD_study': th.DiD.round(2),
                    'plp_mine': R.pl_p.round(3), 'plp_study': th.placebo_p.round(3), 'works_mine': R.works})
log('\nALL 36: mine vs study')
log(cmp.to_string())
log('\nmy full table:')
log(R.drop(columns=['works']).round(3).to_string())

# flag agreement with the study
sf = pd.read_csv(f'{SP}/more_signals/oi/work/results_features.csv', usecols=['symbol', 'qn'] + IDS)
mf = fl_df[['symbol', 'qn'] + IDS].merge(sf, on=['symbol', 'qn'], suffixes=('', '_s'))
ag = []
for t in IDS:
    a_, b_ = mf[t].to_numpy(bool), mf[t + '_s'].to_numpy(bool)
    pool = PB if t[0] == 'B' else np.ones(len(mf), bool)
    ag.append(f'{t}: both {int((a_ & b_ & pool).sum())} mine-only {int((a_ & ~b_ & pool).sum())} '
              f'study-only {int((~a_ & b_ & pool).sum())}')
log('\nflag agreement (B within winners):')
for x in ag:
    log('  ', x)
np.savez_compressed(f'{W}/w4_placebo.npz', qb=qb, yq=yq, QW=QW, month=month, qa=qa, ya=ya, va=va, mon_a=mon_a,
                    **{'qflag_' + t: flq[t][0] for t in Bids}, **{'aflag_' + t: fla[t][0] for t in Aids})
log('done')
