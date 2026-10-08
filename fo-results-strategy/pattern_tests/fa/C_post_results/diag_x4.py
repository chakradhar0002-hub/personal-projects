#!/usr/bin/env python3
"""X4 diagnostic (ADDED AFTER, no new test): I5 flipped long, E0 H20, split by reaction size and fin_type."""
import os, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
t = pd.read_csv(os.path.join(HERE, 'trades.csv'))
t['x'] = t.raw_E0H20 - t.nif_E0H20 - 0.19
s = t[t.I5_SURPBOT_XNpos == 1]
pool = t[t.rq_pat_surprise_vs_trend_pp.notna() & t.surp_P80.notna() & (t.XN > 0)]
out = []
for nm, m, pm in [('0<XN<=4', s.XN <= 4, pool.XN <= 4), ('XN>4', s.XN > 4, pool.XN > 4)]:
    out.append((nm, int(m.sum()), s[m].x.mean(), int(pm.sum()), pool[pm].x.mean()))
for ft in ['Company', 'Bank', 'NBFC / financial']:
    m = s.fin_type == ft; pm = pool.fin_type == ft
    out.append((ft, int(m.sum()), s[m].x.mean(), int(pm.sum()), pool[pm].x.mean()))
print(pd.DataFrame(out, columns=['split', 'n_I5', 'I5_long_vsN_net', 'n_pool', 'pool_vsN_net']).round(2).to_string(index=False))
print('PAT YoY of I5 trades: median %.1f%%, share with PAT YoY < -25%%: %.0f%%' %
      (s.rq_pat_yoy_pct.median(), 100 * (s.rq_pat_yoy_pct < -25).mean()))
