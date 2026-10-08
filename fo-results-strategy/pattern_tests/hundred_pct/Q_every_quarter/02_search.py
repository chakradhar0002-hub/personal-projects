"""
02_search.py -- every-quarter-positive rule search, real data and nulls.

usage: python3 02_search.py MODE UNIVERSE NULL NRUNS SEED [--real] [--beam B]
  MODE      full  = hindsight: search all 22 quarters (cuts on all rows)
            split = choose on qn 0..13 (cuts on those rows), report qn 14..21
  UNIVERSE  fo | all
  NULL      shuffle | signflip | none
  --real    also run the real data first (and write the rule tables)
Writes  out/<mode>_<universe>_<null>_<seed>.json  (one summary row per run and setting)
        out/<mode>_<universe>_real_rules.csv       (real: qualifying rules, top 300 per setting)
"""
import sys, os, json, time, argparse
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qengine as E

ap = argparse.ArgumentParser()
ap.add_argument('mode'); ap.add_argument('universe'); ap.add_argument('null'); ap.add_argument('nruns', type=int)
ap.add_argument('seed', type=int); ap.add_argument('--real', action='store_true'); ap.add_argument('--beam', type=int, default=1000)
A = ap.parse_args()
OUT = os.path.join(E.HERE, 'out'); os.makedirs(OUT, exist_ok=True)

df = E.load(A.universe)
if A.mode == 'full':
    S = E.Search(df, range(22), (), beam=A.beam)
    ntest = 0
else:
    S = E.Search(df, range(14), range(14, 22), beam=A.beam)
    ntest = 8
SETTINGS = [(fam, cov, net) for fam in ('3day', 'tp') for cov in ('strict', 'hi', 'lo') for net in (False, True)]
t0 = time.time()
print(A, 'conditions', S.C, 'pairs', int(S.upper.sum()), 'req', S.req, flush=True)


def one_run(Y, keep_rules=False):
    res = S.run(Y)
    rows, rules = [], []
    n_rules_evaluated = 2 * 2 * (S.C + int(S.upper.sum()) + int(res['valid3'].sum()))  # x long/short x 3day/tp
    for fam, cov, net in SETTINGS:
        Q = S.qualifying(res, fam, cov, net)
        d = {'fam': fam, 'cov': cov, 'net': net, 'n_rules_evaluated_all_settings': n_rules_evaluated}
        d.update(E.summarize(Q, ntest, net))
        if len(Q):
            if keep_rules or cov != 'lo':     # distinct pick-sets: skipped for the big 'lo' sets in null runs (time)
                f1, f2 = S.fingerprints(res, Q)
                d['n_distinct_picksets'] = int(len(set(zip(f1.round(0), f2.round(0)))))
            for k in (50, 100, 200, 400):
                d[f'n_K_ge{k}'] = int((Q.K >= k).sum())
            for k in (1, 10):
                T = E.rank_top(Q, k)
                s = E.summarize(T, ntest, net)
                d[f'top{k}'] = s
                if k == 1:
                    t = T.iloc[0]
                    d['top1_is'] = {'nq': int(t.nq), 'trades': int(t.K), 'avg_pct': 100 * float(t.S / t.K),
                                    'worst_q_pct': 100 * float(t.mn)}
            if keep_rules:
                T = E.rank_top(Q, 300)
                for rank, (_, t) in enumerate(T.iterrows()):
                    conds = S.conds_of(res, t.level, t.r, t.c)
                    r = {'fam': fam, 'cov': cov, 'net': net, 'rank': rank + 1, 'level': int(t.level),
                         'rule': S.rule_str(conds, t.u), 'conds': json.dumps(list(conds)), 'u': t.u,
                         'is_nq': int(t.nq), 'is_trades': int(t.K), 'is_avg_pct': 100 * float(t.S / t.K),
                         'is_worst_q_pct': 100 * float(t.mn)}
                    if ntest:
                        r.update(oos_nq=int(t.te_nq), oos_pos=int(t.te_pos), oos_trades=int(t.te_K),
                                 oos_avg_pct=100 * float(t.te_S / t.te_K) if t.te_K else np.nan,
                                 oos_worst_q_pct=100 * float(t.te_mn) if t.te_K else np.nan)
                    rules.append(r)
        rows.append(d)
    return rows, rules


allrows = []
if A.real:
    rows, rules = one_run(E.real_Y(df), keep_rules=True)
    for r in rows:
        r['run'] = 'real'
    allrows += rows
    pd.DataFrame(rules).to_csv(f'{OUT}/{A.mode}_{A.universe}_real_rules.csv', index=False)
    print('real done', round(time.time() - t0, 1), flush=True)
    for r in rows:
        print(r['fam'], r['cov'], r['net'], r['n_rules'], r.get('n_distinct_picksets'),
              {k: r.get(k) for k in ('oos_mean_frac_quarters_pos', 'oos_frac_rules_all_pos', 'oos_pooled_avg_pct')},
              flush=True)
if A.null != 'none':
    rng = np.random.default_rng(A.seed)
    for s in range(A.nruns):
        Y = E.null_Y(df, A.null, rng)
        rows, _ = one_run(Y)
        for r in rows:
            r['run'] = f'{A.null}_{A.seed}_{s}'
        allrows += rows
        print('run', s, round(time.time() - t0, 1), [r['n_rules'] for r in rows], flush=True)
        json.dump(allrows, open(f'{OUT}/{A.mode}_{A.universe}_{A.null}_{A.seed}.json', 'w'), default=float)
json.dump(allrows, open(f'{OUT}/{A.mode}_{A.universe}_{A.null}_{A.seed}.json', 'w'), default=float)
print('done', round(time.time() - t0, 1))
