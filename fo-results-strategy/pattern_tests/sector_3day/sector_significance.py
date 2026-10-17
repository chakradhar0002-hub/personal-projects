#!/usr/bin/env python3
"""Is any sector's average three-day results move different from chance?
For each sector: average excess over all F&O results of the same quarter; luck p from 20,000 random same-size picks
per quarter from all F&O results (two-sided); Holm across the 15 sectors; both halves; without the best/worst 5;
after costs (0.17) as a long or a short. Reads OUT/results_3day.csv written by sector_quarter_table.py."""
import os
import numpy as np
import pandas as pd

OUT = os.environ.get('OUT', os.path.join(os.environ.get('REPO_ROOT', '.'), 'results', 'sector_3day'))
ev = pd.read_csv(f'{OUT}/results_3day.csv')
ev['td'] = ev.three_day * 100
rng = np.random.default_rng(20261017)
qmean = ev.groupby('qn').td.mean()
ev['ex'] = ev.td - ev.qn.map(qmean)
by_q = {q: g.td.to_numpy() for q, g in ev.groupby('qn')}
rows = []
for s, g in ev.groupby('sector'):
    n_q = g.groupby('qn').size()
    obs = g.ex.mean()
    sims = np.zeros(20000)
    for q, k in n_q.items():
        pool = by_q[q] - qmean[q]
        idx = rng.integers(0, len(pool), size=(20000, k))
        sims += pool[idx].sum(axis=1)
    sims /= len(g)
    p = (1 + (np.abs(sims) >= abs(obs)).sum()) / 20001
    qa = g.groupby('qn').ex.mean()
    srt = np.sort(g.td.to_numpy())
    rows.append(dict(sector=s, results=len(g), avg=g.td.mean(), excess=obs, q_excess_pos=int((qa > 0).sum()), q=len(qa),
                     t_quarters=qa.mean() / (qa.std(ddof=1) / np.sqrt(len(qa))),
                     ex_first14=g[g.qn <= 13].ex.mean(), ex_last8=g[g.qn >= 14].ex.mean(),
                     avg_wo_best5=srt[:-5].mean(), avg_wo_worst5=srt[5:].mean(),
                     long_net=g.td.mean() - 0.17, short_net=-g.td.mean() - 0.17, p=p))
r = pd.DataFrame(rows).sort_values('p').reset_index(drop=True)
m = len(r)
holm = np.maximum.accumulate([min(1, (m - i) * p) for i, p in enumerate(r.p)])
r['holm'] = holm
r.round(3).to_csv(f'{OUT}/sector_significance.csv', index=False)
print(r.round(2).to_string())
