#!/usr/bin/env python3
"""Verifier: own delivery features and outcomes, built from the raw-verified table delivery_eq.csv and the base data.
No code of the study is imported. Writes OUT/own_feat.csv (results rows), OUT/own_mats.npz (matrices for placebo work),
OUT/v03_features.log (comparison with the study's feat_results.csv and outcomes.csv).
usage: python3 -P v03_features.py SCRATCH OUTDIR
"""
import sys

import numpy as np
import pandas as pd

SP, OUT = sys.argv[1], sys.argv[2]
D = f'{SP}/more_signals/delivery'
DATA = f'{SP}/sector_lab/data'
LOG = open(f'{OUT}/v03_features.log', 'w')


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.write(s + '\n')


ses = pd.read_csv(f'{DATA}/sessions.csv')
days = ses.day.to_numpy()
T = len(days)
DIX = {d: i for i, d in enumerate(days)}
ret = pd.read_csv(f'{DATA}/returns.csv', index_col=0)
SY = ret.columns.tolist()
SJ = {s: j for j, s in enumerate(SY)}
S = len(SY)
R = ret.to_numpy(float)                      # daily simple returns (fraction)
nifty = pd.read_csv(f'{DATA}/index_close.csv', usecols=['day', 'Nifty 50']).set_index('day')['Nifty 50']
NC = nifty.reindex(days).to_numpy(float)

# ---------------- own forward ticker map
sc = pd.read_csv(f'{SP}/symbolchange.csv', header=None, names=['co', 'old', 'new', 'date'], dtype=str)
for c in sc:
    sc[c] = sc[c].str.strip()
sc['d'] = pd.to_datetime(sc.date, format='%d-%b-%Y', errors='coerce').dt.strftime('%Y-%m-%d')
FWD = {}
for o, n, d in zip(sc.old, sc.new, sc.d):
    if isinstance(d, str):
        FWD.setdefault(o, []).append((d, n))


def fwd(s, d):
    for _ in range(10):
        c = [(dd, n) for dd, n in FWD.get(s, []) if dd > d]   # change after this day -> the row is the old ticker
        if not c:
            return s
        s = min(c)[1]
    return s


eq = pd.read_csv(f'{D}/downloads/delivery_eq.csv', dtype={'symbol': str})
u = eq[['symbol', 'day']].drop_duplicates()
mp = {(s, d): fwd(s, d) for s, d in zip(u.symbol, u.day)}
eq['cur'] = [mp[(s, d)] for s, d in zip(eq.symbol, eq.day)]
eq = eq[eq.cur.isin(SJ) & eq.day.isin(DIX)]
P('rows', len(eq), 'renamed', int((eq.cur != eq.symbol).sum()), 'dup', int(eq.duplicated(['day', 'cur']).sum()))
ii = eq.day.map(DIX).to_numpy(int)
jj = eq.cur.map(SJ).to_numpy(int)


def M(col):
    X = np.full((T, S), np.nan)
    X[ii, jj] = eq[col].to_numpy(float)
    return X


DP, DQ, TQ, CL, PC = M('deliv_per'), M('deliv_qty'), M('ttl_trd_qnty'), M('close'), M('prev_close')
i0, i1 = ii.min(), ii.max()

# ---------------- own share-count factor. NSE PREV_CLOSE in these files is the unadjusted previous close, so a split /
# bonus shows as raw close/prev_close far below the adjusted return of returns.csv: a = (1 + R) / (CL / PC).
# A share-count change is accepted when a is within 1% of a split/bonus ratio (1.1 .. 10); the quantity jump is logged.
SF = np.ones((T, S))           # multiply quantities on day t by SF[t] to express them in the latest share count
events = []
with np.errstate(divide='ignore', invalid='ignore'):
    A = (1 + R) / (CL / PC)
for t, j in zip(*np.where(np.isfinite(A) & (np.abs(A - 1) > 0.03))):
    a = A[t, j]
    pre = np.nanmedian(TQ[max(i0, t - 20):t, j])
    post = np.nanmedian(TQ[t:t + 20, j])
    jump = post / pre if pre > 0 else np.nan
    clean = np.array([1.1, 1.2, 1.25, 4 / 3, 1.5, 2, 2.5, 3, 4, 5, 6, 10])
    split = bool(a >= 1.08 and np.min(np.abs(a / clean - 1)) < 0.01)
    events.append((SY[j], days[t], t, round(a, 4), round(jump, 3), split))
    if split:
        SF[:t, j] *= a
ev_df = pd.DataFrame(events, columns=['symbol', 'day', 'i', 'ratio', 'qty_jump', 'share_change'])
ev_df.to_csv(f'{OUT}/own_ca_events.csv', index=False)
P(f'price-adjustment events |a-1|>3%: {len(ev_df)}; treated as share-count change: {int(ev_df.share_change.sum())}')
DQA = DQ * SF
TQA = TQ * SF


def rmean(X, w, mp_):
    v = np.nan_to_num(X)
    c = np.isfinite(X).astype(float)
    cv = np.vstack([np.zeros((1, S)), np.cumsum(v, 0)])
    cc = np.vstack([np.zeros((1, S)), np.cumsum(c, 0)])
    out = np.full((T, S), np.nan)
    for t in range(T):
        lo = max(0, t - w + 1)
        n = cc[t + 1] - cc[lo]
        s = cv[t + 1] - cv[lo]
        out[t] = np.where(n >= mp_, s / np.where(n > 0, n, 1), np.nan)
    return out


DP5 = rmean(DP, 5, 4)
DP60 = rmean(DP, 60, 40)
DQ5 = rmean(DQA, 5, 4)
DQ60 = rmean(DQA, 60, 40)
ACC = DP5 - DP60
DQR = np.where(DQ60 > 0, DQ5 / np.where(DQ60 > 0, DQ60, 1), np.nan)
DP60p = np.vstack([np.full((1, S), np.nan), DP60[:-1]])
DQ60p = np.vstack([np.full((1, S), np.nan), DQ60[:-1]])
DPL = DP - DP60p
DQL = np.where(DQ60p > 0, DQA / np.where(DQ60p > 0, DQ60p, 1), np.nan)
# total-volume ratio (for the lag rule check) and 5-session price change
TV5, TV60 = rmean(TQA, 5, 1), rmean(TQA, 60, 1)
LR = np.log1p(np.nan_to_num(R))
cl = np.vstack([np.zeros((1, S)), np.cumsum(LR, 0)])
PR5 = np.full((T, S), np.nan)
cnt = np.vstack([np.zeros((1, S)), np.cumsum(np.isfinite(R), 0)])
for t in range(4, T):
    n = cnt[t + 1] - cnt[t - 4]
    PR5[t] = np.where(n >= 4, (np.exp(cl[t + 1] - cl[t - 4]) - 1) * 100, np.nan)
np.savez_compressed(f'{OUT}/own_mats.npz', DP=DP, DP60=DP60, ACC=ACC, DQR=DQR, DPL=DPL, DQL=DQL, PR5=PR5,
                    DQA=DQA, SF=SF)

# ---------------- results rows
pan = pd.read_csv(f'{SP}/perf/features/panel.csv')
oc = pd.read_csv(f'{SP}/perf/features/outcomes.csv')
f = pan[['symbol', 'qn', 'quarter', 'period', 'industry', 'i_cut', 'i_rd', 'i_p1', 'i_react', 'in_fo_events', 'lag21',
         'vol_ratio_5_60', 'cut_rsi14', 'XN', 'W', 'mean_drift_4_B']].merge(
    oc[['symbol', 'qn', 'three_day', 'tradable_B', 'vsN_H20', 'vsN_net_H20']], on=['symbol', 'qn'])
j = f.symbol.map(SJ).to_numpy(int)
e = f.i_cut.to_numpy(int) - 1
k = f.i_react.to_numpy(int)
for nm, X in [('ACC', ACC), ('DQR', DQR), ('DPL', DPL), ('DP60', DP60), ('PR5', PR5)]:
    f[nm] = X[e, j]
f['DQK'] = DQL[k, j]
f['DPK'] = DPL[k, j]
f['DPK1'] = DP[k + 1, j] - DP60p[k, j]
f['ACC_pre'] = ACC[k - 1, j]
f['own_vr'] = TV5[f.i_cut.to_numpy(int), j] / TV60[f.i_cut.to_numpy(int), j]
# window contains a share-count change?
f['split_win_A'] = [bool(np.any(SF[max(0, ee - 60):ee + 1, jj_] != SF[ee, jj_])) for ee, jj_ in zip(e, j)]
f['split_win_k'] = [bool(np.any(SF[max(0, kk - 61):kk + 1, jj_] != SF[kk, jj_])) for kk, jj_ in zip(k, j)]
# within-quarter ranks on the same session (own implementation, average ties, pct x 100)
U = {q: g.symbol.map(SJ).to_numpy(int) for q, g in f.groupby('qn')}
# pandas pct rank (average) = (count_less + (count_equal+1)/2) / n ; equality count includes itself
# -> recompute exactly that way for clarity
for nm, X in [('ACC', ACC), ('DQR', DQR), ('DPL', DPL), ('DP60', DP60)]:
    v = np.full(len(f), np.nan)
    for n_, (q, ee, jj_) in enumerate(zip(f.qn, e, j)):
        vals = X[ee, U[q]]
        x = X[ee, jj_]
        vals = vals[np.isfinite(vals)]
        if np.isfinite(x):
            v[n_] = (np.sum(vals < x) + (np.sum(vals == x) + 1) / 2) / len(vals) * 100
    f['rank_' + nm] = v

# ---------------- own outcomes
CR = np.vstack([np.zeros((1, S)), np.cumsum(LR, 0)])


def stock_ret(a, b, jj_):       # buy close a, sell close b
    return (np.exp(CR[b + 1, jj_] - CR[a + 1, jj_]) - 1) * 100


f['own_three_day'] = stock_ret(f.i_cut.to_numpy(int), f.i_p1.to_numpy(int), j)
nan_cnt = np.vstack([np.zeros((1, S)), np.cumsum(~np.isfinite(R), 0)])
for lag in (0, 1, 2):
    a = k + lag
    b = a + 20
    okb = b < T
    bb = np.where(okb, b, T - 1)
    sr = stock_ret(a, bb, j)
    nr = (NC[bb] / NC[a] - 1) * 100
    v = np.where(okb, sr - nr - 0.19, np.nan)
    trad = okb & ((nan_cnt[bb + 1, j] - nan_cnt[a + 1, j]) <= 2)
    f[f'vsN_net_k{lag}'] = v
    f[f'trad_k{lag}'] = trad
f.to_csv(f'{OUT}/own_feat.csv', index=False, float_format='%.6g')

# ---------------- compare with the study
th = pd.read_csv(f'{D}/feat_results.csv')
c = f.merge(th, on=['symbol', 'qn'], suffixes=('', '_th'))
P(f'\nrows compared {len(c)}')
for nm, tol in [('ACC', 1e-3), ('DQR', 1e-3), ('DPL', 1e-3), ('DP60', 1e-3), ('PR5', 1e-3), ('DQK', 1e-3),
                ('DPK', 1e-3), ('DPK1', 1e-3), ('ACC_pre', 1e-3), ('rank_ACC', 1e-6), ('rank_DQR', 1e-6),
                ('rank_DPL', 1e-6), ('rank_DP60', 1e-6)]:
    a, b = c[nm].to_numpy(float), c[nm + '_th'].to_numpy(float)
    both = np.isfinite(a) & np.isfinite(b)
    rel = np.abs(a - b) / np.maximum(1, np.abs(b))
    bad = both & (rel > tol)
    P(f'  {nm:10s} both {both.sum():5d}  only-mine {int((np.isfinite(a) & ~np.isfinite(b)).sum())}  only-theirs '
      f'{int((~np.isfinite(a) & np.isfinite(b)).sum())}  differ(>{tol}) {bad.sum()}  max rel diff {np.nanmax(np.where(both, rel, np.nan)):.2e}')
    if bad.any():
        x = c.loc[bad, ['symbol', 'qn', nm, nm + '_th', 'split_win_A', 'split_win_k']].head(8)
        P(x.to_string())
P('\nsignal membership differences (mine vs theirs)')
for lab, mine, theirs in [
        ('A10 rank_DP60>80', c.rank_DP60 > 80, c.rank_DP60_th > 80),
        ('A06 rank_DPL>80', c.rank_DPL > 80, c.rank_DPL_th > 80),
        ('RA1 lag<-10 & DQR>=1', (c.in_fo_events == True) & (c.lag21 < -10) & (c.DQR >= 1),
         (c.in_fo_events == True) & (c.lag21 < -10) & (c.DQR_th >= 1)),
        ('W_DQK_HI', (c.W == True) & (c.DQK >= 3), (c.W == True) & (c.DQK_th >= 3))]:
    P(f'  {lab}: mine {int(mine.sum())} theirs {int(theirs.sum())} both {int((mine & theirs).sum())}; '
      f'only mine {c.loc[mine & ~theirs, ["symbol", "qn"]].values.tolist()[:6]} only theirs '
      f'{c.loc[~mine & theirs, ["symbol", "qn"]].values.tolist()[:6]}')
d3 = np.abs(c.own_three_day - c.three_day)
P(f'\nthree_day own vs outcomes.csv: max abs diff {d3.max():.2e}, > 1e-3: {(d3 > 1e-3).sum()}')
mk = c.tradable_B == True
dv = np.abs(c.vsN_net_k0 - c.vsN_net_H20)[mk]
P(f'vsN_net entry k own vs outcomes.csv (tradable_B): n {mk.sum()}, max abs diff {dv.max():.2e}, > 1e-3: {(dv > 1e-3).sum()}; '
  f'own tradable_k0 agrees {(c.trad_k0 == c.tradable_B).mean() * 100:.2f}%')
dvr = np.abs(c.own_vr / c.vol_ratio_5_60 - 1)
P(f'own total-volume 5/60 ratio vs panel vol_ratio_5_60: within 1% {np.mean(dvr < 0.01) * 100:.2f}%, within 5% {np.mean(dvr < 0.05) * 100:.2f}%')
LOG.close()
