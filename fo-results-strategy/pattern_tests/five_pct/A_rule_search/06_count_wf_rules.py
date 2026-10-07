"""06_count_wf_rules.py -- count the rules evaluated by each walk-forward re-search on real data (bookkeeping only)."""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rulelib as R
out = {}
for uni in ('fo', 'all'):
    df = R.load(uni); qn = df.qn.values; y = df.three_day.values
    tot = 0
    for q in range(6, 22):
        tr = qn < q
        M, names, compat = R.build_conditions(df, tr)
        S = R.Searcher(M[:, tr], qn[tr], compat)
        r = S.run(y[tr], beam=500, ntop=10)
        tot += 2 * (r['n_conditions'] + r['n_pairs'] + r['n_triples_evaluated'])
    out[uni] = tot
    print(uni, tot, flush=True)
json.dump(out, open(f'{R.HERE}/wf_rule_counts.json', 'w'))
