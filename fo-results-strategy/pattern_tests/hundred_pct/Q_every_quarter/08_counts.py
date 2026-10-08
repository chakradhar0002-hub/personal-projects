"""08_counts.py -- count everything tried; writes 99_counts.json"""
import os, json, glob
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
c = {}
runs = {}
evaluated = {}
for f in sorted(glob.glob(f'{OUT}/*_*.json')):
    b = os.path.basename(f)
    if not (b.startswith('full_') or b.startswith('split_')):
        continue
    rows = json.load(open(f))
    mode, uni = b.split('_')[:2]
    for r in rows:
        key = f'{mode}_{uni}_{r["run"].split("_")[0]}'
        runs.setdefault(key, set()).add(r['run'])
        if r['run'] == 'real':
            evaluated[f'{mode}_{uni}'] = r.get('n_rules_evaluated_all_settings')
c['search_runs'] = {k: len(v) for k, v in sorted(runs.items())}
c['rule_variants_evaluated_per_real_search (1-3 conditions x long/short x 3day/TP)'] = evaluated
wf = {}
for f in sorted(glob.glob(f'{OUT}/wf_*.json')):
    rows = json.load(open(f))
    for r in rows:
        wf.setdefault(r['run'].split('_')[0] + '_' + os.path.basename(f).split('_')[1], set()).add(r['run'])
c['walkforward_runs'] = {k: len(v) for k, v in wf.items()}
settings = 2 * 3 * 2          # exit (3day, TP) x coverage (strict, hi, lo) x gross / after costs
c['criteria_per_search'] = settings
c['hindsight_criteria_tested'] = settings * len([k for k in evaluated if k.startswith('full')])
c['split_criteria_x_selections'] = settings * 3 * len([k for k in evaluated if k.startswith('split')])   # top1, top10, all
c['walkforward_criteria_x_selections'] = settings * 3
B = pd.read_csv(f'{OUT}/baselines.csv')
c['baseline_filters_x_direction_x_exit'] = int(len(B))
c['lagged_nifty_variants'] = int(len(pd.read_csv(f'{OUT}/lagged_nifty.csv')))
c['lagged_nifty_placebo_rows'] = int(len(pd.read_csv(f'{OUT}/lagged_nifty_placebo.csv')))
c['candidate_detail_rows'] = int(len(pd.read_csv(f'{OUT}/candidates.csv')))
c['candidate_A_neighbour_grid'] = int(len(pd.read_csv(f'{OUT}/candidate_A_grid.csv')))
c['things_tried_total (criteria/selections/filters/variants, not counting individual rules)'] = int(
    c['hindsight_criteria_tested'] + c['split_criteria_x_selections'] + c['walkforward_criteria_x_selections'] +
    c['baseline_filters_x_direction_x_exit'] + c['lagged_nifty_variants'] + c['lagged_nifty_placebo_rows'] +
    c['candidate_detail_rows'] + c['candidate_A_neighbour_grid'])
json.dump(c, open(os.path.join(HERE, '99_counts.json'), 'w'), indent=1)
print(json.dumps(c, indent=1))
