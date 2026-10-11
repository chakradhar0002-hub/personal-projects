#!/usr/bin/env python3
"""MA4 robustness (information only): the same walk-forward with GBM random_state 0..9. Seed 0 is the registered one."""
import numpy as np
import pandas as pd

SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = f'{SP}/negative_avg/holdout'
E = pd.read_csv(f'{OUT}/eval_panel.csv', usecols=['symbol', 'qn', 'three_day', 'nifty3'])
rows = []
for s in range(10):
    S = pd.read_csv(f'{OUT}/ma4_scores_seed{s}.csv').merge(E, on=['symbol', 'qn'])
    for tag, qs in [('discovery', range(4, 14)), ('holdout', range(14, 22))]:
        a = S[S.qn.isin(list(qs))]
        t = a[a.pick]
        prof = np.sort((-t.three_day - 0.17).to_numpy())
        base = (-a.three_day - 0.17).mean()
        rows.append(dict(seed=s, sample=tag, n=len(t), short=prof.mean(), wo5=prof[:-5].mean(), base=base,
                         margin=prof.mean() - base, hedged=(-(t.three_day - t.nifty3) - 0.19).mean()))
D = pd.DataFrame(rows)
D.to_csv(f'{OUT}/ma4_seeds.csv', index=False, float_format='%.4f')
print(D.round(2).to_string(index=False))
for tag in ['discovery', 'holdout']:
    d = D[D['sample'] == tag]
    print(f'{tag}: short net range {d.short.min():+.2f} .. {d.short.max():+.2f} (mean {d.short.mean():+.2f}); '
          f'w/o 5 range {d.wo5.min():+.2f} .. {d.wo5.max():+.2f}; seeds with short > 0: {(d.short > 0).sum()}/10')
