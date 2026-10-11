#!/usr/bin/env python3
"""Skeptic step 6: C22 40-session hold entered one session late (close k+1, cost 0.27), and the dropouts gap
(results per quarter in the panel) for the survivorship note."""
import numpy as np, pandas as pd
SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = f'{SP}/negative_avg/skeptic'
days = pd.read_csv(f'{SP}/sector_lab/data/sessions.csv').day.tolist(); T = len(days)
ret = pd.read_csv(f'{SP}/sector_lab/data/returns.csv', index_col=0); R = ret.to_numpy(float)
SYM = {s: j for j, s in enumerate(ret.columns)}
N = pd.read_csv(f'{SP}/sector_lab/data/index_close.csv', index_col=0, usecols=['day', 'Nifty 50'])['Nifty 50'].to_numpy(float)
P = pd.read_csv(f'{OUT}/skeptic_panel.csv')
out = []
for r in P[P.C22.astype(bool)].itertuples():
    e = int(r.i_react) + 1; j = SYM[r.symbol]
    if e + 40 > T - 1 or not np.isfinite(R[e, j]):
        out.append(np.nan); continue
    w = R[e + 1:e + 41, j]
    if np.isnan(w).sum() > 2:
        out.append(np.nan); continue
    out.append(-((np.prod(1 + np.nan_to_num(w)) - 1) * 100 - (N[e + 40] / N[e] - 1) * 100) - 0.27)
d = P[P.C22.astype(bool)].copy(); d['sh40_k1'] = out
for smp in ['discovery', 'holdout']:
    x = d[(d['sample'] == smp)].sh40_k1.dropna()
    print(f'C22 H40 entered close k+1, cost 0.27, {smp}: n {len(x)} mean {x.mean():+.2f} wo5 {np.sort(x)[::-1][5:].mean():+.2f}')
print('panel results per quarter:', P.groupby('qn').size().to_dict())
