#!/usr/bin/env python3
"""Skeptic review, part 2: placebo on quiet (non-results) stock-days. Same filter as the baseline signal
(XN > 4 on day k, RSI14 two sessions before k > 50), same trade (buy close k, short Nifty, H20 vs H60).
Question: does the extra from holding 60 instead of 20 also appear without results?"""
import numpy as np
import pandas as pd

SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = f'{SP}/more_avg/skeptic'
D = f'{SP}/sector_lab/data'
ses = pd.read_csv(f'{D}/sessions.csv')
days = ses.day.tolist()
T = len(days)
LAST = T - 1
ret = pd.read_csv(f'{D}/returns.csv', index_col=0)
SYM = {s: j for j, s in enumerate(ret.columns)}
R = ret.to_numpy(float)
N = pd.read_csv(f'{D}/index_close.csv', index_col=0, usecols=['day', 'Nifty 50'])['Nifty 50'].to_numpy(float)
CP = np.vstack([np.ones((1, R.shape[1])), np.cumprod(1 + np.nan_to_num(R[1:]), axis=0)])
NB = np.vstack([np.zeros((1, R.shape[1])), np.cumsum(np.isnan(R[1:]), axis=0)])

q = pd.read_csv(f'{SP}/tafa/C_post_results/quiet_days.csv.gz', usecols=['symbol', 'i', 'day', 'qn_prev', 'XN', 'm2_rsi14'])
j = q.symbol.map(SYM).to_numpy()
k = q.i.to_numpy()
for H in (20, 60):
    ok = (k + H + 1 <= LAST)
    kh = np.minimum(k + H, LAST)
    kh1 = np.minimum(k + H + 1, LAST)
    blanks = NB[kh1, j] - NB[k, j]
    ok &= blanks <= 2
    s = (CP[kh, j] / CP[k, j] - 1) * 100
    n = (N[kh] / N[k] - 1) * 100
    q[f'v{H}'] = np.where(ok, s - n - 0.19, np.nan)
q = q[q.v60.notna()].copy()
q['ext'] = q.v60 - q.v20
q['month'] = q.day.str[:7]
q['W'] = q.XN > 4
q['HI'] = q.m2_rsi14 > 50
q['HOLD'] = q.qn_prev >= 14   # quiet day after a holdout-season result

L = []


def pr(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    L.append(s)


def cl_se(x, g):
    """standard error of the mean clustered by g"""
    x = np.asarray(x, float)
    mu = x.mean()
    e = pd.Series(x - mu).groupby(np.asarray(g)).sum()
    return np.sqrt((e ** 2).sum()) / len(x)


pr('=== Placebo: quiet stock-days (no results in [k-10, k+20]); vsN_net %, buy close k, short Nifty; SE clustered by month ===')
groups = {'quiet W & RSI>50': q.W & q.HI, 'quiet W & RSI<=50': q.W & ~q.HI, 'quiet all winners': q.W,
          'quiet non-W & RSI>50': ~q.W & q.HI, 'all quiet days': q.W | ~q.W}
res = []
for smp, mm in [('DISC (qn_prev<=13)', ~q.HOLD), ('HOLD (qn_prev>=14)', q.HOLD), ('ALL', q.W | ~q.W)]:
    for nm, g in groups.items():
        x = q[g & mm]
        if len(x) < 5:
            continue
        se20, se60, sex = cl_se(x.v20, x.month), cl_se(x.v60, x.month), cl_se(x.ext, x.month)
        pr(f'{smp:20s} {nm:22s} n {len(x):6d} H20 {x.v20.mean():+.2f} (se {se20:.2f}) H60 {x.v60.mean():+.2f} (se {se60:.2f}) '
           f'ext {x.ext.mean():+.2f} (se {sex:.2f})')
        res.append(dict(sample=smp, group=nm, n=len(x), H20=x.v20.mean(), H60=x.v60.mean(), ext=x.ext.mean(), se_ext=sex))
# thinned: first quiet winner day per symbol per qn_prev
pr('\nThinned (first qualifying quiet day per stock per season):')
for smp, mm in [('DISC', ~q.HOLD), ('HOLD', q.HOLD)]:
    x = q[q.W & q.HI & mm].sort_values('i').groupby(['symbol', 'qn_prev']).head(1)
    pr(f'{smp} quiet W & RSI>50 thinned n {len(x)} H20 {x.v20.mean():+.2f} H60 {x.v60.mean():+.2f} ext {x.ext.mean():+.2f} '
       f'(se {cl_se(x.ext, x.month):.2f}); median ext {x.ext.median():+.2f}')
    y = q[mm].sort_values('i').groupby(['symbol', 'qn_prev']).head(1)
    pr(f'{smp} all quiet thinned          n {len(y)} H20 {y.v20.mean():+.2f} H60 {y.v60.mean():+.2f} ext {y.ext.mean():+.2f}')

# results-side comparison (from panel_skeptic.csv, own rebuild)
P = pd.read_csv(f'{OUT}/panel_skeptic.csv')
P = P[P.v60.notna()]
pr('\nResults side (same filter, same H20/H60 rule, own rebuild):')
for smp, mm in [('DISC', P.qn <= 13), ('HOLD', P.qn >= 14)]:
    b = P[mm & (P.XN > 4) & (P.rsi > 50)]
    a = P[mm]
    pr(f'{smp} results W & RSI>50 n {len(b)} H20 {b.v20.mean():+.2f} H60 {b.v60.mean():+.2f} ext {(b.v60 - b.v20).mean():+.2f} | '
       f'all results ext {(a.v60 - a.v20).mean():+.2f}')
pd.DataFrame(res).to_csv(f'{OUT}/placebo_quiet.csv', index=False, float_format='%.4f')
open(f'{OUT}/s2_placebo.log', 'w').write('\n'.join(L) + '\n')
