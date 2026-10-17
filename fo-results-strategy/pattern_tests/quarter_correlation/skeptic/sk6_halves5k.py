"""Halves p for the last-4 top tenth / top fifth (random picks within quarter, 50,000)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from sk_common import *
ev, allev, qq = load()
allev['h_td'] = allev.three_day * 100
H = {s: g.sort_values('qn', ascending=False) for s, g in allev.groupby('symbol')}
td4 = []
for s, q, dec in zip(ev.symbol, ev.qn, ev.i_cut):
    g = H[s]; h = g[(g.qn < q) & (g.i_p1 < dec) & (g.i_react < dec)]
    td4.append(h.h_td.iloc[:4].mean() if len(h) >= 4 else np.nan)
ev['td4'] = td4
f4 = ev[ev.td4.notna()].copy().reset_index(drop=True)
f4['pct4'] = f4.groupby('qn').td4.rank(pct=True)
rng = np.random.default_rng(20261105)
for thr in (0.8, 0.9):
    for nm, qs in (('q4-10', range(0, 11)), ('q11-21', range(11, 22)), ('q4-13 (PAST_PERF first part)', range(0, 14)), ('q14-21 (last 8)', range(14, 22))):
        d = f4[f4.qn.isin(qs)].reset_index(drop=True)
        m = d.pct4.to_numpy() > thr
        o = np.argsort(d.qn.to_numpy(), kind='stable'); xq = d.x.to_numpy()[o]; qn = d.qn.to_numpy()[o].astype(float); mk = m[o]
        null = np.concatenate([xq[np.argsort(qn[None] + rng.random((5000, len(xq))), axis=1)][:, mk].mean(1) for _ in range(10)])
        print(f'top {100*(1-thr):.0f}% {nm}: {m.sum()} results, x {fp(d.x[m].mean())}, td {fp(d.td[m].mean())}%, p {fpv(p2c(d.x[m].mean(), null))}')
