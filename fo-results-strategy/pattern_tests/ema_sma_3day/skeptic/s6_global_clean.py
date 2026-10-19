"""Skeptic 6: global tests (all 27 continuous) on the raw, minus-Nifty and same-cutoff-demeaned outcomes; placebo
day-demeaned ICs for all 27."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
from common import *

df = load_events()
df['y_dd'] = df.three_day - df.groupby('i_cut').three_day.transform('mean')
dd = df[df.groupby('i_cut').three_day.transform('size') >= 2]
qs = sorted(df.qn.unique())
B = 10000
for name, d, y in [('raw three_day', df, 'three_day'), ('three_day - Nifty', df, 'xs_nifty'), ('same-cutoff demeaned', dd, 'y_dd')]:
    rng = np.random.default_rng(31)
    s = np.zeros((B, 27)); o = np.zeros(27)
    for q in qs:
        g = d[d.qn == q]
        R = np.column_stack([zr(g[f].values) for f in CONT]); ry = zr(g[y].values)
        o += ry @ R
        idx = np.argsort(rng.random((B, len(ry))), axis=1); s += ry[idx] @ R
    o /= len(qs); s /= len(qs)
    pind = (1 + (np.abs(s) >= np.abs(o) - 1e-12).sum(0)) / (1 + B)
    mx = np.abs(s).max(1)
    pmax = (1 + (mx >= np.abs(o).max() - 1e-12).sum()) / (1 + B)
    comp = (1 + (np.abs(s.mean(1)) >= abs(o.mean())).sum()) / (1 + B)
    thr = np.quantile(np.abs(s), .95, axis=0); cnt = (np.abs(s) > thr).sum(1); k = (pind < 0.05).sum()
    j = int(np.argmax(np.abs(o)))
    print(f'{name:22s}: best {CONT[j]} {o[j]:+.3f} maxT27 p {pmax:.3f}; average IC of 27 {o.mean():+.4f} p {comp:.3f}; '
          f'negative {int((o < 0).sum())}/27; unadjusted p<0.05: {k} (P null >= k: {(cnt >= k).mean():.3f})')
pl = pd.read_csv(os.path.join(RES, 'features_placebo.csv.gz'), usecols=['i', 'qn', 'three_day'] + CONT)
pl['y_dd'] = pl.three_day - pl.groupby('i').three_day.transform('mean')
raw = np.array([ic_by_q(pl, f).mean() for f in CONT]); dm = np.array([ic_by_q(pl, f, 'y_dd').mean() for f in CONT])
print(f'placebo raw ICs: {raw.min():+.3f} .. {raw.max():+.3f} ({int((raw < 0).sum())}/27 negative); day-demeaned: {dm.min():+.3f} .. {dm.max():+.3f} '
      f'({int((dm < 0).sum())}/27 negative), mean |IC| {np.abs(dm).mean():.3f}')
for f, a, b in sorted(zip(CONT, raw, dm), key=lambda x: x[2])[:4]:
    print(f'   most negative day-demeaned placebo: {f} raw {a:+.3f} demeaned {b:+.3f}')
