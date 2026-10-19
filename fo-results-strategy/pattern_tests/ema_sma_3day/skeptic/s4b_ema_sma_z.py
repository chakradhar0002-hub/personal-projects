"""Skeptic 4b: EMA - SMA IC differences with a standardised (z) maxT over the 11 pairs; raw and same-cutoff demeaned."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
from common import *

df = load_events()
df['y_dd'] = df.three_day - df.groupby('i_cut').three_day.transform('mean')
dd = df[df.groupby('i_cut').three_day.transform('size') >= 2]
pairs = [(f'dist_ema_{n}', f'dist_sma_{n}') for n in P] + [(f'slope_ema_{n}', f'slope_sma_{n}') for n in (20, 50, 200)] \
    + [('spread_ema20_50', 'spread_sma20_50'), ('spread_ema50_200', 'spread_sma50_200')]
qs = sorted(df.qn.unique())
for name, d, y in [('raw', df, 'three_day'), ('same-cutoff demeaned', dd, 'y_dd')]:
    B = 10000; rng = np.random.default_rng(55)
    s = np.zeros((B, len(pairs))); o = np.zeros(len(pairs))
    for q in qs:
        g = d[d.qn == q]; ry = zr(g[y].values)
        D = np.column_stack([zr(g[a].values) - zr(g[b].values) for a, b in pairs])
        o += ry @ D; idx = np.argsort(rng.random((B, len(ry))), axis=1); s += ry[idx] @ D
    o /= len(qs); s /= len(qs)
    z = o / s.std(0); zs = np.abs(s / s.std(0)); mx = zs.max(1)
    print(f'== {name}')
    for k, (a, b) in enumerate(pairs):
        p = (1 + (zs[:, k] >= abs(z[k]) - 1e-12).sum()) / (1 + B); pm = (1 + (mx >= abs(z[k]) - 1e-12).sum()) / (1 + B)
        if p < 0.1:
            print(f'  {a} - {b}: IC diff {o[k]:+.3f} z {z[k]:+.2f} p {fpv(p)} maxT(11, z) {fpv(pm)}')
    print(f'  smallest maxT p {min((1 + (mx >= abs(z[k]) - 1e-12).sum()) / (1 + B) for k in range(len(pairs))):.3f}')
