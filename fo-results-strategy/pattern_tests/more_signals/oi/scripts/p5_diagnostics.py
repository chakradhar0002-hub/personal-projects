#!/usr/bin/env python3
"""POST-HOC diagnostics (not pre-registered, not part of the family; written after p3_tests.py results were seen).
What is behind B09 (winners with PCR top quintile at k) and B13 (call-IV run-up)? Is B09 a proxy for the size of
the reaction (XN), for RSI>50, or for the pre-results PCR level?
usage: python3 -P p5_diagnostics.py <family_dir> <scratchpad>
"""
import sys

import numpy as np
import pandas as pd

FAM, SP = sys.argv[1], sys.argv[2]
OUTD = f'{FAM}/results'
LOG = open(f'{OUTD}/diagnostics_posthoc.log', 'w')


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    LOG.write(s + '\n')


R = pd.read_csv(f'{FAM}/work/results_features.csv')
out = pd.read_csv(f'{SP}/perf/features/outcomes.csv', usecols=['symbol', 'qn', 'vsN_net_H20', 'tradable_B'])
D = R.merge(out, on=['symbol', 'qn'])
W = D[(D.tradable_B == True) & (D.W == True)].copy()
assert len(W) == 392
y = W.vsN_net_H20
W['WR'] = W.cut_rsi14 > 50
P('POST-HOC DIAGNOSTICS - not pre-registered; for understanding only\n')
for t in ('B09', 'B13'):
    i, o = W[W[t]], W[W['el_' + t] & ~W[t]]
    P(f'{t}: IN n {len(i)} net {i.vsN_net_H20.mean():+.2f} | OUT n {len(o)} net {o.vsN_net_H20.mean():+.2f}')
    P(f'   mean XN IN {i.XN.mean():.2f} OUT {o.XN.mean():.2f}; share RSI>50 IN {i.WR.mean():.2f} OUT {o.WR.mean():.2f}; '
      f'PCR at k IN {i.B_PCR.median():.2f} OUT {o.B_PCR.median():.2f}; PCR at cutoff IN {i.A_PCR.median():.2f} '
      f'OUT {o.A_PCR.median():.2f}; dPCR1 on k IN {i.B_dPCR1.median():+.3f} OUT {o.B_dPCR1.median():+.3f}')
# stratify B09 by XN half and by RSI
W['XN_hi'] = W.XN > W.XN.median()
P('\nB09 IN - OUT within strata (net %):')
for name, g in (('XN below median', W[~W.XN_hi]), ('XN above median', W[W.XN_hi]), ('RSI<=50', W[~W.WR]),
                ('RSI>50', W[W.WR]), ('first 14', W[W.qn <= 13]), ('last 8', W[W.qn >= 14])):
    i, o = g[g.B09], g[g.el_B09 & ~g.B09]
    P(f'   {name:16s} IN {len(i):3d} {i.vsN_net_H20.mean():+.2f}  OUT {len(o):3d} {o.vsN_net_H20.mean():+.2f}  '
      f'diff {i.vsN_net_H20.mean() - o.vsN_net_H20.mean():+.2f}')
P('\nplain winners by XN half (net %):', W.groupby('XN_hi').vsN_net_H20.agg(['size', 'mean']).round(2).to_dict())
# OLS: drift on B09 + XN + RSI_HI + quarter fixed effects (descriptive)
X = pd.get_dummies(W.qn, prefix='q', drop_first=True).astype(float)
X['B09'] = W.B09.astype(float)
X['XN'] = W.XN
X['RSI_HI'] = W.WR.astype(float)
X['const'] = 1.0
b, *_ = np.linalg.lstsq(X.to_numpy(float), y.to_numpy(float), rcond=None)
res_ = y.to_numpy(float) - X.to_numpy(float) @ b
cl = W.qn.to_numpy()
XtX_inv = np.linalg.inv(X.T.to_numpy() @ X.to_numpy())
meat = sum(np.outer(X.to_numpy()[cl == c].T @ res_[cl == c], X.to_numpy()[cl == c].T @ res_[cl == c]) for c in np.unique(cl))
se = np.sqrt(np.diag(XtX_inv @ meat @ XtX_inv))
for k in ('B09', 'XN', 'RSI_HI'):
    j = list(X.columns).index(k)
    P(f'   OLS (quarter FE, quarter-clustered se) {k}: {b[j]:+.3f} (se {se[j]:.3f}, t {b[j] / se[j]:+.2f})')
# pre-results PCR level among winners (same top-quintile rule, PCR at the cutoff)
q80 = D.groupby('qn').A_PCR.transform(lambda s: s.quantile(0.8))
D['PCRcut_top'] = D.A_PCR > q80
W = W.merge(D[['symbol', 'qn', 'PCRcut_top']], on=['symbol', 'qn'])
i, o = W[W.PCRcut_top], W[~W.PCRcut_top & W.A_PCR.notna()]
P(f'\nwinners with PCR top quintile at the CUTOFF (pre-results): IN {len(i)} {i.vsN_net_H20.mean():+.2f} | OUT {len(o)} '
  f'{o.vsN_net_H20.mean():+.2f}')
# B09 per quarter
pq = W.groupby('qn').apply(lambda g: pd.Series({'n_in': int(g.B09.sum()), 'in': g.vsN_net_H20[g.B09].mean(),
                                                 'out': g.vsN_net_H20[~g.B09].mean()}))
P('\nB09 per quarter (net %):')
P(pq.round(2).to_string())
