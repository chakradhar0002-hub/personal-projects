#!/usr/bin/env python3
"""Post-hoc look at 'any business update in 45d' (BIZ45>0): industry mix, within-stock, luck p, halves.
usage: python3 v2_biz_posthoc.py WORKDIR"""
import sys
import numpy as np, pandas as pd
W = sys.argv[1]
f = pd.read_csv(f'{W}/feat_results.csv'); A = f[f.three_day.notna()].copy()
A['exc'] = A.three_day - A.groupby('qn').three_day.transform('mean')
BZ = A.BIZ45 > 0
print('BIZ45>0 by industry (top):')
print(A[BZ].groupby('industry').exc.agg(['size', 'mean']).sort_values('size', ascending=False).head(10).round(2).to_string())
print('symbols', A[BZ].symbol.nunique())
cs = A[BZ].groupby('symbol').exc.agg(['size', 'sum']).sort_values('sum', ascending=False)
print('top 5 symbols', cs.head(5).round(1).to_dict('index'))
print(f'without top-5 symbols: excess {A[BZ & ~A.symbol.isin(cs.index[:5])].exc.mean():+.3f}')
# within-stock: issuers' quarters with vs without a BIZ item
iss = A[A.symbol.isin(A[BZ].symbol.unique())]
print(f'issuer stocks: quarters with BIZ {BZ[iss.index].sum()} excess {iss[BZ[iss.index]].exc.mean():+.3f}; '
      f'without {(~BZ[iss.index]).sum()} excess {iss[~BZ[iss.index]].exc.mean():+.3f}')
rng = np.random.default_rng(5)
obs = A[BZ].three_day.mean(); tot = np.zeros(20000)
for q, k in A[BZ].groupby('qn').size().items():
    v = A.loc[A.qn == q, 'three_day'].values
    idx = np.argpartition(rng.random((20000, len(v))), k - 1, axis=1)[:, :k]
    tot += v[idx].sum(1)
print(f'luck p (post hoc, not pre-registered) {(1 + (tot / BZ.sum() >= obs).sum()) / 20001:.4f}')
