"""
02b_compare_null.py -- real fixed-split search vs the identical search on 50 within-quarter shuffles and 50 sign-flips.
For each objective x min trades x side (long / short / either):
  p_is     share of null runs whose best in-sample objective >= the real best (how special the real winner is)
  null_is  median / 95th pct of the null best in-sample average
  real_l8  the real chosen rule's last-8 average;  null_l8 mean / 95th pct of the null chosen rule's last-8 average
  p_l8     share of null runs whose chosen rule did at least as well in the last 8 as the real one
Output: fixed_fo_null_comparison.csv
"""
import json, os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
U = sys.argv[1] if len(sys.argv) > 1 else 'fo'
real = json.load(open(f'{HERE}/fixed_{U}_real.json'))
rows = []
for mode in ('shuffle', 'signflip'):
    N = pd.read_csv(f'{HERE}/fixed_{U}_null_{mode}_1.csv')
    for key, r in real['best'].items():
        o, m, side = key.split('_')
        m = int(m[1:])
        n = N[(N.objective == o) & (N.min_trades == m) & (N.side == side)]
        rows.append({'null': mode, 'objective': o, 'min_trades': m, 'side': side, 'n_null_runs': len(n),
                     'real_rule': r['rule'], 'real_is_obj': r['is_obj'], 'real_is_avg_pct': r['is_avg_pct'],
                     'p_is': float((n.is_obj >= r['is_obj'] - 1e-9).mean()),
                     'null_is_avg_median': n.is_avg_pct.median(), 'null_is_avg_p95': n.is_avg_pct.quantile(.95),
                     'real_l8_pct': r['last8_avg_pct'], 'real_l8_trades': r['last8_trades'],
                     'null_l8_mean': n.last8_avg_pct.mean(), 'null_l8_p95': n.last8_avg_pct.quantile(.95),
                     'p_l8': float((n.last8_avg_pct >= r['last8_avg_pct']).mean()) if r['last8_avg_pct'] is not None else np.nan,
                     'real_top10_l8_pct': r['top10_last8_mean_of_rule_avgs_pct'],
                     'null_top10_l8_mean': n.top10_last8_pct.mean(), 'null_top10_l8_p95': n.top10_last8_pct.quantile(.95),
                     'p_top10_l8': float((n.top10_last8_pct >= r['top10_last8_mean_of_rule_avgs_pct']).mean())})
C = pd.DataFrame(rows)
C.to_csv(f'{HERE}/fixed_{U}_null_comparison.csv', index=False)
pd.set_option('display.width', 250, 'display.max_colwidth', 60)
print(C.drop(columns=['real_rule', 'real_is_obj', 'n_null_runs']).round(2).to_string())
# pooled view: across the 9 objective x m settings (either side), average real vs null
for mode in ('shuffle', 'signflip'):
    c = C[(C.null == mode) & (C.side == 'either')]
    print(mode, 'either-side, 9 settings: mean real last-8 %.2f%% vs null chosen-rule last-8 mean %.2f%%; mean p_is %.2f; mean p_l8 %.2f'
          % (c.real_l8_pct.mean(), c.null_l8_mean.mean(), c.p_is.mean(), c.p_l8.mean()))
    c = C[(C.null == mode) & (C.side == 'long')]
    print(mode, 'long, 9 settings: mean real last-8 %.2f%% vs null %.2f%%; real top10 %.2f vs null top10 %.2f; mean p_l8 %.2f'
          % (c.real_l8_pct.mean(), c.null_l8_mean.mean(), c.real_top10_l8_pct.mean(), c.null_top10_l8_mean.mean(), c.p_l8.mean()))
    c = C[(C.null == mode) & (C.side == 'short')]
    print(mode, 'short, 9 settings: mean real last-8 %.2f%% vs null %.2f%%; real top10 %.2f vs null top10 %.2f; mean p_l8 %.2f'
          % (c.real_l8_pct.mean(), c.null_l8_mean.mean(), c.real_top10_l8_pct.mean(), c.null_top10_l8_mean.mean(), c.p_l8.mean()))
