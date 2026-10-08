"""04_volume_by_depth.py -- POST-HOC decomposition (added after seeing 02/03): S20 capitulation volume inside each lag
band, results vs placebo, first 14 vs last 8.  Descriptive; not used to pick anything."""
import numpy as np, pandas as pd, os
HERE = os.path.dirname(os.path.abspath(__file__))
G = pd.read_csv(f'{HERE}/group_fo.csv'); P = pd.read_csv(f'{HERE}/placebo_vol.csv'); P = P[P.in_fo == True]
rows = []
for lab, a, b in [('5-10%', -0.10, -0.05), ('10-15%', -0.15, -0.10), ('>15%', -9, -0.15), ('all >5%', -9, -0.05)]:
    for vlab, lo, hi in [('vol>=1.5', 1.5, 99), ('1.0-1.5', 1.0, 1.5), ('vol<1.0', 0, 1.0)]:
        g = G[(G.lag >= a) & (G.lag < b) & (G.volume_5d_vs_60d >= lo) & (G.volume_5d_vs_60d < hi)]
        p = P[(P.lag >= a) & (P.lag < b) & (P.volume_5d_vs_60d >= lo) & (P.volume_5d_vs_60d < hi)]
        rows.append(dict(lag=lab, volume=vlab, n=len(g), avg=g.three_day_pct.mean(), tp=g.tp_pct.mean(), up=100*(g.three_day_pct>0).mean(),
                         f14=g[g.qn < 14].three_day_pct.mean(), n14=(g.qn < 14).sum(), l8=g[g.qn >= 14].three_day_pct.mean(), n8=(g.qn >= 14).sum(),
                         placebo_n=len(p), placebo_avg=p.three_day_pct.mean(), res_minus_pl=g.three_day_pct.mean() - p.three_day_pct.mean()))
D = pd.DataFrame(rows); D.to_csv(f'{HERE}/volume_by_depth.csv', index=False)
print(D.round(2).to_string())
