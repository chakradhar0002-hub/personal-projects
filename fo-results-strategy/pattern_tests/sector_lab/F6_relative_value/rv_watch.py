#!/usr/bin/env python3
"""
F6 robustness diagnostics (NO new trade rules, no new variants) for the post-hoc watch-list
item A_long_badPAT50_goodReaction_h20 (see rv_addendum.py), and per-trade numbers for the
known-edge reference. Output: watch_trades.csv, watch_per_season.csv, run_watch.txt
Run: python3 -I rv_watch.py
"""
import os  # SECTOR_LAB: folder holding data/ from sector_lab_data.py
import sys
sys.path.append('/root/.local/lib/python3.11/site-packages')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import rv_main as M

ev = M.ev
OUT = M.OUT
pd.set_option('display.width', 250)

B = M.build_b(ev, 'pat_yoy')
m = (B.F.values < -0.50) & (B.Pgap.values > 0)
X = B[m].copy()
t = X.t.values; h = 20
fX = M.fwd_stock(X.s.values, t, h); fN = M.fwd_index('Nifty 50', t, h)
X['main'] = 100 * (fX - fN) - M.C_SINGLE
X['raw'] = 100 * fX - M.C_STOCK
X = X[X.main.notna()].merge(ev[['s', 'qn', 'symbol', 'exc', 'pat_yoy', 'reaction_day']], on=['s', 'qn'], how='left')
X['in_known_edge'] = X.exc > 0.04
X.drop(columns=['fo_peers']).to_csv(OUT + 'watch_trades.csv', index=False)

q = X.groupby('qn').agg(trades=('main', 'size'), avg_vs_nifty=('main', 'mean'), avg_raw=('raw', 'mean'))
q.to_csv(OUT + 'watch_per_season.csv')
print('per-season (qn, trades, avg vs Nifty net, avg raw net):')
print(q.round(2).T.to_string())
qm = q.avg_vs_nifty
print(f'\nper-season avg {qm.mean():.2f}, median season {qm.median():.2f}, t {M.tstat(qm.values):.2f}')
print(f'per-trade avg {X.main.mean():.2f}, median trade {X.main.median():.2f}, win% {100*(X.main>0).mean():.1f}')
# trimmed: drop best 5% trades
cut = X.main.quantile(0.95)
Xt = X[X.main <= cut]
qt = Xt.groupby('qn').main.mean()
print(f'drop best 5% trades: per-season avg {qt.mean():.2f}, t {M.tstat(qt.values):.2f}')
# winsorised at +-15%
Xw = X.assign(main=X.main.clip(-15, 15)); qw = Xw.groupby('qn').main.mean()
print(f'winsorised +-15%: per-season avg {qw.mean():.2f}, t {M.tstat(qw.values):.2f}')
# leave one season out
lo = [M.tstat(qm.drop(k).values) for k in qm.index]
print(f'leave-one-season-out t: min {min(lo):.2f}, max {max(lo):.2f}')
print('\nby group:')
print(X.groupby('grp').main.agg(['size', 'mean']).round(2).sort_values('size', ascending=False).to_string())
print('\nby known-edge overlap:')
print(X.groupby('in_known_edge').main.agg(['size', 'mean']).round(2).to_string())
print('\nby X reaction excess bucket (absolute bins):')
X['exc_bin'] = pd.cut(X.exc, [-1, 0, 0.02, 0.04, 1])
print(X.groupby('exc_bin', observed=True).main.agg(['size', 'mean']).round(2).to_string())
print(f'\nshare with own reaction excess < 0 (stock fell vs Nifty but less than peers): {(X.exc < 0).mean():.2f}')

# known-edge reference per-trade
K = ev[ev.fo & (ev.exc > 0.04)]
tk = K.i_react.values
v = 100 * (M.fwd_stock(K.s.values, tk, 20) - M.fwd_index('Nifty 50', tk, 20)) - M.C_SINGLE
print(f'\nknown edge reference (F&O, reaction excess > +4%, hold 20, vs Nifty net): trades {np.isfinite(v).sum()}, '
      f'per-trade avg {np.nanmean(v):.2f}')
