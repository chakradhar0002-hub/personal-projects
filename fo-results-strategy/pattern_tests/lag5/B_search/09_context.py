"""
09_context.py -- descriptive splits of the lag > 5% group (no search; a handful of pre-named splits), each with
first-14 / last-8 numbers and the placebo (same split on non-results dates of the same F&O stocks).
Splits: depth of the month lag; 6-month return; distance below the 200-day average; 2- and 3-session drop into the
cutoff; Nifty's last week; stock vs its own sector over the month; volume surge (no placebo: no volume in the panel).
Output: context_splits.csv
"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gsearch as G

df = G.load_group('fo')
L = pd.read_pickle(f'{G.HERE}/placebo_panel.pkl')
L = L[L.vs_nifty_1m < -0.05]
L['nifty_1w'] = np.nan
# Nifty 1-week (5-session) return for the placebo rows
IX = pd.read_csv(os.environ.get('LAB_ROOT', 'lab') + '/sector_lab/data/index_close.csv')
n = IX['Nifty 50'].values
n1w = n / np.r_[np.full(5, np.nan), n[:-5]] - 1
L['nifty_1w'] = n1w[L.i.values]
SPLITS = {
    'vs_nifty_1m': [-0.05, -0.10, -0.15, -0.20, -9],
    'r6m': [9, 0.10, 0.0, -0.10, -0.20, -9],
    'vs_ma200': [9, 0.0, -0.10, -0.20, -9],
    'r2d': [9, 0.0, -0.02, -0.04, -9],
    'r3d': [9, 0.0, -0.04, -0.08, -9],
    'nifty_1w': [9, 0.01, 0.0, -0.01, -0.02, -9],
    'vs_sector_1m': [9, 0.0, -0.05, -0.10, -9],
    'volume_5d_vs_60d': [9, 1.5, 1.0, 0.75, -9],
}
rows = []
for f, edges in SPLITS.items():
    hi_first = edges[0] > edges[-1]
    for a, b in zip(edges[:-1], edges[1:]):
        lo, hi = (b, a) if hi_first else (a, b)
        lo, hi = min(lo, hi), max(lo, hi)
        mk = (df[f] > lo) & (df[f] <= hi)
        d = df[mk]
        r = {'feature': f, 'from': lo, 'to': hi, 'trades': len(d), 'avg_pct': 100 * d.three_day.mean(),
             'tp_avg_pct': 100 * d.tp3.mean(), 'up_pct': 100 * (d.three_day > 0).mean(),
             'first14_n': int((d.qn <= 13).sum()), 'first14_avg_pct': 100 * d[d.qn <= 13].three_day.mean(),
             'last8_n': int((d.qn >= 14).sum()), 'last8_avg_pct': 100 * d[d.qn >= 14].three_day.mean()}
        qa = d.groupby('qn').three_day.mean()
        r['q_pos'] = f'{int((qa > 0).sum())}/{len(qa)}'
        if f in L.columns:
            p = L[(L[f] > lo) & (L[f] <= hi)]
            r['placebo_n'] = len(p); r['placebo_avg_pct'] = 100 * p.fwd3.mean()
            r['placebo_date_avg_pct'] = 100 * p.groupby('day').fwd3.mean().mean()
        rows.append(r)
C = pd.DataFrame(rows)
C.to_csv(f'{G.HERE}/context_splits.csv', index=False)
pd.set_option('display.width', 250)
print(C.round(2).to_string())
