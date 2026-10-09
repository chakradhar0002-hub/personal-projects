#!/usr/bin/env python3
"""Final corrected 22-quarter table: truth_per_quarter.csv (reconcile.py) + next-open diagnostic (claims.py)."""
import os
import numpy as np
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
TQ = pd.read_csv(f'{HERE}/truth_per_quarter.csv')
NO = pd.read_csv(f'{HERE}/claims_per_quarter_next_open.csv').set_index('qn')
T = pd.read_csv(f'{HERE}/truth_trades.csv')
U = pd.read_csv(f'{HERE}/truth_universe.csv')
CP = pd.read_csv(f'{HERE}/claims_panel.csv')
f2 = lambda x: 'n/a' if not np.isfinite(x) else f'{x:+.2f}'
md = ['| # | Results for | Quarter | Trades | Up | Avg vs Nifty (net) | Median | Unhedged avg | Winners RSI<=50 avg (n) | '
      'All winners avg (n) | Main minus all winners | All F&O results avg (n) | Next-open entry, 0.40 cost (diagnostic) | '
      'Stocks (% vs Nifty, net) |', '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
for r in TQ.itertuples():
    md.append(f'| {r.qn} | {r.results_for} | {r.quarter} | {r.trades} | {r.up} | {f2(r.avg)} | {f2(r.median)} | '
              f'{f2(r.unhedged)} | {f2(r.W_LO_avg)} ({r.W_LO_n}) | {f2(r.W_avg)} ({r.W_n}) | {f2(r.avg - r.W_avg)} | '
              f'{f2(r.all_avg)} ({r.all_n}) | {f2(NO.loc[r.qn, "E1a_040"])} | {r.stocks} |')
qW = U[U.W].groupby('qn').vsN_net.mean()
dW = (T.vsN_net - T.qn.map(qW)).mean()
m = CP[CP.MAIN]
e40 = (m.E1a_g - 0.40)
md.append(f"| | **All 22** | | **{len(T)}** | **{int((T.vsN_net > 0).sum())}** | **{f2(T.vsN_net.mean())}** | "
          f"**{f2(T.vsN_net.median())}** | **{f2(T.raw_net.mean())}** | {f2(U.loc[U.W & ~U.HI, 'vsN_net'].mean())} "
          f"({int((U.W & ~U.HI).sum())}) | {f2(U.loc[U.W, 'vsN_net'].mean())} ({int(U.W.sum())}) | {f2(dW)} (d_W, per trade) | "
          f"{f2(U.vsN_net.mean())} ({len(U)}) | {f2(e40.mean())} ({int((NO.E1a_040 > 0).sum())}/22 q+) | "
          f"{int((TQ.avg > 0).sum())}/22 quarters positive; quarter-weighted {f2(TQ.avg.mean())} |")
open(f'{HERE}/final_per_quarter.md', 'w').write('\n'.join(md) + '\n')
print('\n'.join(md))
