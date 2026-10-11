#!/usr/bin/env python3
"""Compare own features with the study's feat_results.csv. usage: python3 v2_compare_feats.py MINE THEIRS"""
import sys
import numpy as np
import pandas as pd
m = pd.read_csv(sys.argv[1]); t = pd.read_csv(sys.argv[2])
x = m.merge(t[['symbol', 'qn', 'PR30', 'BIZ_N45', 'BIZ_RX', 'RDCHG', 'dtq', 'dtq_ly', 'dtq_fr', 'NEWS30']], on=['symbol', 'qn'], suffixes=('', '_t'))
print('rows', len(x))
print('PR30 equal', (x.PR30 == x.PR30_t).mean(), ' flag>=1 disagreements', ((x.PR30 >= 1) != (x.PR30_t >= 1)).sum())
d = x[(x.PR30 >= 1) != (x.PR30_t >= 1)]
print(d[['symbol', 'qn', 'PR30', 'PR30_t', 'PR30_incl', 'PR30_1530']].to_string())
print('PR30 counts differ (any):', (x.PR30 != x.PR30_t).sum())
print('PR30 incl own-rd vs excl: flag differs', ((x.PR30_incl >= 1) != (x.PR30 >= 1)).sum())
both = x.RDCHG.notna() & x.RDCHG_t.notna()
print('RDCHG known mine', x.RDCHG.notna().sum(), 'theirs', x.RDCHG_t.notna().sum(), 'both', both.sum(),
      'equal', (x.RDCHG[both] == x.RDCHG_t[both]).mean())
dd = x[both & (x.RDCHG != x.RDCHG_t)]
print(dd[['symbol', 'qn', 'RDCHG', 'RDCHG_t', 'rdays', 'rdays_ly', 'dtq', 'dtq_ly', 'dtq_fr']].head(20).to_string())
print('EARLY flag disagreements', ((x.RDCHG < -7) != (x.RDCHG_t < -7)).sum(), ' LATE', ((x.RDCHG > 7) != (x.RDCHG_t > 7)).sum())
print('only mine known', (x.RDCHG.notna() & x.RDCHG_t.isna()).sum(), 'only theirs', (x.RDCHG.isna() & x.RDCHG_t.notna()).sum())
print('BIZ: mine BIZ45>0', (x.BIZ45 > 0).sum(), 'theirs BIZ_N45>0', (x.BIZ_N45 > 0).sum(),
      ' RX>0 mine', (x.BIZ_RX > 0).sum(), 'theirs', (x.BIZ_RX_t > 0).sum(), ' both RX>0', ((x.BIZ_RX > 0) & (x.BIZ_RX_t > 0)).sum(),
      ' RX<0 mine', (x.BIZ_RX < 0).sum(), 'theirs', (x.BIZ_RX_t < 0).sum())
