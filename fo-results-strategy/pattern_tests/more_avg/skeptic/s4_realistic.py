#!/usr/bin/env python3
"""Skeptic review, part 4: realistic F3 (hold 60) per trade - next-open entry, 0.42 cost, by F&O tenure, minus the
same-quarter drift of all F&O results; full-sample calendar-time extension vs universe; qn-21 partial tail."""
import numpy as np
import pandas as pd

SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = f'{SP}/more_avg/skeptic'
D = f'{SP}/sector_lab/data'
days = pd.read_csv(f'{D}/sessions.csv').day.tolist()
T = len(days)
LAST = T - 1
ret = pd.read_csv(f'{D}/returns.csv', index_col=0)
SYM = {s: j for j, s in enumerate(ret.columns)}
R = ret.to_numpy(float)
N = pd.read_csv(f'{D}/index_close.csv', index_col=0, usecols=['day', 'Nifty 50'])['Nifty 50'].to_numpy(float)
CP = np.vstack([np.ones((1, R.shape[1])), np.cumprod(1 + np.nan_to_num(R[1:]), axis=0)])
nop = pd.read_csv(f'{SP}/more_avg/holdout/nifty_open.csv').set_index('i')['open']
px = pd.read_csv(f'{SP}/ta/build/adjusted_ohlcv.csv.gz', usecols=['day', 'symbol', 'open', 'close'])
DIX = {d: i for i, d in enumerate(days)}
px['i'] = px.day.map(DIX)
OC = px.set_index(['symbol', 'i'])[['open', 'close']]
ev = pd.read_csv(f'{D}/events.csv', usecols=['symbol', 'qn', 'in_fo'])
early = set(ev[(ev.in_fo == True) & (ev.qn <= 1)].symbol)

P = pd.read_csv(f'{OUT}/panel_skeptic.csv')
L = []


def pr(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    L.append(s)


B = P[(P.XN > 4) & (P.rsi > 50)].copy()


def real(r, H):
    k = int(r.k)
    if k + H + 1 > LAST or not np.isfinite(getattr(r, f'v{H}')):
        return np.nan
    j = SYM[r.symbol]
    try:
        o, c = OC.loc[(r.symbol, k + 1)]
    except KeyError:
        return np.nan
    stk = (c / o) * CP[k + H, j] / CP[k + 1, j] - 1
    nif = N[k + H] / nop.loc[k + 1] - 1
    return (stk - nif) * 100 - 0.42


B['r20'] = [real(r, 20) for r in B.itertuples()]
B['r60'] = [real(r, 60) for r in B.itertuples()]
B['early'] = B.symbol.isin(early)
# same-quarter drift of all F&O results
qd60 = P.groupby('qn').v60.mean()
qd20 = P.groupby('qn').v20.mean()
B['d60'] = B.v60 - B.qn.map(qd60)
B['d20'] = B.v20 - B.qn.map(qd20)
# early-member-only drift (less survivorship): same-quarter mean of all results of early members
Pe = P[P.symbol.isin(early)]
B['d60e'] = B.v60 - B.qn.map(Pe.groupby('qn').v60.mean())
B['d20e'] = B.v20 - B.qn.map(Pe.groupby('qn').v20.mean())
X = B[B.v60.notna()]
pr('=== F3 realistic per trade (vsN %, 60 sessions) vs baseline (20 sessions) on the same signals ===')
for smp, m in [('DISC', X.qn <= 13), ('HOLD', X.qn >= 14), ('FULL', X.qn >= 0)]:
    for grp, g in [('all', X.early | ~X.early), ('early F&O (by qn 1)', X.early), ('later joiners', ~X.early)]:
        x = X[m & g]
        pr(f'{smp} {grp:20s} n {len(x):3d} | close-k 0.19: F3 {x.v60.mean():+.2f} base {x.v20.mean():+.2f} | '
           f'next-open 0.42: F3 {x.r60.mean():+.2f} base {x.r20.mean():+.2f} | minus all-results drift: F3 {x.d60.mean():+.2f} '
           f'base {x.d20.mean():+.2f} | minus early-member drift: F3 {x.d60e.mean():+.2f} base {x.d20e.mean():+.2f}')
x = X[X.early]
pr(f'\nMost conservative full-sample cut (early members, next open, 0.42 cost): F3 {x.r60.mean():+.2f} (median {x.r60.median():+.2f}) '
   f'vs base {x.r20.mean():+.2f}; minus early-member drift F3 {x.d60e.mean():+.2f} vs base {x.d20e.mean():+.2f}')
xx = x.copy()
xx['yr'] = xx.k.map(lambda k: days[k][:4])
pr('  by year (early members, next open 0.42): ' + ', '.join(
    f"{y}: n {len(g)} F3 {g.r60.mean():+.2f} base {g.r20.mean():+.2f}" for y, g in xx.groupby('yr')))
ex = xx[xx.yr != '2023']
pr(f'  ex-2023: n {len(ex)} F3 {ex.r60.mean():+.2f} base {ex.r20.mean():+.2f}')

# qn 21 partial tail (days 21..end of data) - only data not yet in the published hold tables beyond H40
pr('\n=== qn 21 signals: return from close k+20 to the last available close (<= k+60), vs Nifty, no cost ===')
q21 = P[(P.qn == 21) & (P.XN > 4) & (P.rsi > 50)]
allq = P[P.qn == 21]
for nm, g in [('BASE qn21', q21), ('all qn21 results', allq)]:
    v, ln = [], []
    for r in g.itertuples():
        k = int(r.k)
        if k + 20 >= LAST:
            continue
        e = min(k + 60, LAST)
        j = SYM[r.symbol]
        v.append((CP[e, j] / CP[k + 20, j] - (N[e] / N[k + 20])) * 100)
        ln.append(e - k - 20)
    pr(f'{nm}: n {len(v)} avg {np.mean(v):+.2f} median sessions observed {np.median(ln):.0f}')
open(f'{OUT}/s4_realistic.log', 'w').write('\n'.join(L) + '\n')
B.to_csv(f'{OUT}/f3_trades_skeptic.csv', index=False, float_format='%.5g')
