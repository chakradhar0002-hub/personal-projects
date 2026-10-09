#!/usr/bin/env python3
"""S7. Implementation and dependence checks (diagnostics, own code).
  (a) next-open entry: buy at the open of k+1 instead of the close of k (the signal needs the close of k).
  (b) calendar-time portfolios: equal-weight daily portfolio of open positions (days k+1..k+20), stock minus Nifty
      daily return; Newey-West t (lag 20) - accounts for overlapping, cross-correlated trades.
      Also HI-winners minus LO-winners and HI-winners minus all-winners long-short series.
"""
import numpy as np
import pandas as pd

from common import DATA, HERE, Log, sg

L = Log('s7_implementation.log')
P = pd.read_csv(f'{HERE}/panel.csv.gz')
W = P[P.W].copy()
W['HIf'] = W.cut_rsi14 > 50

L('(a) NEXT-OPEN ENTRY (buy at the open of k+1; Nifty leg still close k -> close k+20, no Nifty open in the data)')
for lab, m in [('MAIN W&RSI>50', W.HIf), ('all winners', W.HIf | ~W.HIf), ('W&RSI<=50', ~W.HIf)]:
    g = W[m]
    L(f"   {lab:14s} n {len(g)}: overnight gap close k -> open k+1 mean {g.gap_k1_pct.mean():+.2f}% (median "
      f"{g.gap_k1_pct.median():+.2f}); close-entry {g.vsN_net.mean():+.2f} -> next-open entry "
      f"{g.vsN_nextopen_net.mean():+.2f} (median {g.vsN_nextopen_net.median():+.2f})")
qm = W.groupby('qn').vsN_nextopen_net.mean()
hi = W[W.HIf]
L(f"   next-open dW (same-quarter gap to all winners) {(hi.vsN_nextopen_net - hi.qn.map(qm)).mean():+.2f}")
L(f"   all results: gap {P.gap_k1_pct.mean():+.2f}%, next-open {P.vsN_nextopen_net.mean():+.2f}")

# (b) calendar-time
ses = pd.read_csv(f'{DATA}/sessions.csv')
ret = pd.read_csv(f'{DATA}/returns.csv', index_col=0)
ix = pd.read_csv(f'{DATA}/index_close.csv', index_col=0, usecols=['day', 'Nifty 50'])
R = ret.to_numpy(float)
SYM = {s: j for j, s in enumerate(ret.columns)}
N = ix['Nifty 50'].to_numpy(float)
NR = np.r_[np.nan, N[1:] / N[:-1] - 1]
NS = len(ses)


def ct_series(df):
    """daily equal-weight mean of (stock - Nifty) over positions open on that day (days k+1..k+20)."""
    s = np.zeros(NS)
    c = np.zeros(NS)
    for sym, k in zip(df.symbol, df.i_react):
        j = SYM[sym]
        d = np.arange(k + 1, k + 21)
        x = np.nan_to_num(R[d, j]) - NR[d]
        s[d] += x
        c[d] += 1
    with np.errstate(invalid='ignore'):
        return pd.Series(np.where(c > 0, s / c, np.nan), index=ses.day), pd.Series(c, index=ses.day)


def nw_t(x, lag=20):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    e = x - x.mean()
    v = e @ e / n
    for l in range(1, lag + 1):
        v += 2 * (1 - l / (lag + 1)) * (e[l:] @ e[:-l]) / n
    return x.mean() / np.sqrt(v / n), n


hiS, hiC = ct_series(W[W.HIf])
loS, loC = ct_series(W[~W.HIf])
wS, wC = ct_series(W)
aS, aC = ct_series(P)
L('\n(b) CALENDAR-TIME PORTFOLIOS (daily, percent per day, gross of costs; NW lag 20)')
for lab, s in [('main W&RSI>50', hiS), ('all winners', wS), ('W&RSI<=50', loS), ('all F&O results', aS)]:
    t, n = nw_t(s)
    L(f"   {lab:16s}: days with positions {n}, mean {s.mean() * 100:+.4f}%/day (x20 = {s.mean() * 2000:+.2f}% per "
      f"20 sessions), NW t {t:.2f}")
for lab, a, b in [('main minus RSI<=50 winners', hiS, loS), ('main minus all winners', hiS, wS),
                  ('main minus all F&O results', hiS, aS)]:
    d = (a - b).dropna()
    t, n = nw_t(d)
    L(f"   {lab:28s}: overlapping days {n}, mean {d.mean() * 100:+.4f}%/day (x20 = {d.mean() * 2000:+.2f}), "
      f"NW t {t:.2f}")
# by year of the calendar-time long-short
d = (hiS - loS).dropna()
yr = d.groupby(d.index.str[:4]).agg(['mean', 'size'])
L('   main minus RSI<=50 winners by year (x20, % per 20 sessions): ' + ', '.join(
    f"{y} {r['mean'] * 2000:+.2f} ({int(r['size'])}d)" for y, r in yr.iterrows()))
d2 = (hiS - wS).dropna()
yr = d2.groupby(d2.index.str[:4]).agg(['mean', 'size'])
L('   main minus all winners by year (x20): ' + ', '.join(f"{y} {r['mean'] * 2000:+.2f}" for y, r in yr.iterrows()))
pd.DataFrame({'main': hiS, 'w_lo': loS, 'all_w': wS, 'all_res': aS, 'n_main': hiC, 'n_lo': loC}).dropna(
    how='all', subset=['main', 'w_lo', 'all_w']).to_csv(f'{HERE}/s7_calendar_time.csv', float_format='%.6g')
