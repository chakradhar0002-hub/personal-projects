#!/usr/bin/env python3
"""Verifier extras: lag-rule date-matched reference, RA1-only trades, A10 per-quarter. usage: python3 -P v08_extra.py OUTDIR"""
import sys
import numpy as np
import pandas as pd
OUT = sys.argv[1]
f = pd.read_csv(f'{OUT}/own_feat_stress.csv')
QN = f.qn.to_numpy()
y = f.three_day.to_numpy()
qm = pd.Series(y).groupby(QN).transform('mean').to_numpy()
ew = f.ew3.to_numpy()
allx = np.nanmean(y - ew)
lag = (f.in_fo_events == True) & (f.lag21 < -10) & (f.vol_ratio_5_60 >= 1)
ra1 = (f.in_fo_events == True) & (f.lag21 < -10) & (f.DQR >= 1)
a10 = f.rank_DP60 > 80
out = open(f'{OUT}/v08_extra.log', 'w')
def P(*a):
    s = ' '.join(str(x) for x in a); print(s); out.write(s + '\n')
for lab, m in [('lag rule', lag), ('RA1', ra1), ('A10', a10)]:
    m = m.to_numpy() & np.isfinite(y)
    P(f'{lab}: n {m.sum()} gross {y[m].mean():+.3f} quarter-matched excess {(y - qm)[m].mean():+.3f} '
      f'date-matched (vs EW universe, minus all results) {(y - ew)[m].mean() - allx:+.3f}')
P('\nRA1-only trades (not in the lag rule):')
P(f.loc[ra1 & ~lag, ['symbol', 'qn', 'lag21', 'vol_ratio_5_60', 'DQR', 'three_day']].round(3).to_string(index=False))
P('\nlag-only trades (not in RA1):')
P(f.loc[lag & ~ra1, ['symbol', 'qn', 'lag21', 'vol_ratio_5_60', 'DQR', 'three_day']].round(3).to_string(index=False))
g = pd.DataFrame({'qn': QN[a10], 'net': y[a10] - 0.17, 'ex': (y - qm)[a10]}).groupby('qn').agg(n=('net', 'size'), net=('net', 'mean'), ex=('ex', 'mean'))
P('\nA10 per quarter:'); P(g.round(3).T.to_string())
P('A10 quarters with net > 0:', int((g.net > 0).sum()), '/', len(g), '; excess > 0:', int((g.ex > 0).sum()))
out.close()
