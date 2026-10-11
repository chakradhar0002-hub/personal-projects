#!/usr/bin/env python3
"""List log(underlying / adjusted price) steps between 2% and 15% (feature diagnostics only).
usage: p2c_steps.py <work_dir> <scratchpad>"""
import sys
import numpy as np, pandas as pd
W, SP = sys.argv[1], sys.argv[2]
z = np.load(f'{W}/daily.npz', allow_pickle=False)
UND, syms, days = z['UND'], z['syms'], z['days']
ret = pd.read_csv(f'{SP}/sector_lab/data/returns.csv', index_col=0)
assert list(ret.columns) == list(syms)
PX = np.cumprod(1 + np.nan_to_num(ret.to_numpy(float)), axis=0)
G = np.log(UND) - np.log(PX)
rows = []
for j in range(G.shape[1]):
    idx = np.flatnonzero(np.isfinite(G[:, j]))
    if len(idx) < 2: continue
    dg = np.diff(G[idx, j])
    for k in np.flatnonzero((np.abs(dg) > np.log(1.02)) & (np.abs(dg) <= np.log(1.15))):
        rows.append((syms[j], days[idx[k]], days[idx[k + 1]], round(float(np.exp(dg[k])), 4), int(idx[k + 1] - idx[k])))
x = pd.DataFrame(rows, columns=['sym', 'from', 'to', 'ratio', 'gap'])
print(len(x), 'steps in (2%, 15%]; gap>1 sessions:', int((x.gap > 1).sum()))
print(x.to_string())
allg = np.concatenate([np.diff(G[np.isfinite(G[:, j]), j]) for j in range(G.shape[1])])
print('all consecutive |dg| quantiles', np.quantile(np.abs(allg), [0.5, 0.9, 0.99, 0.999]))
