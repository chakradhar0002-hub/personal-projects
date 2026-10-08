"""
02_fixed_split.py -- exhaustive 1/2-condition + beam 3-condition search INSIDE the lag > 5% group on qn 0..13,
honest test on qn 14..21.  Objectives mean / fpos / worst x min trades 15/30/60 x long/short, picks in >= 6 quarters.

usage:
  python3 02_fixed_split.py UNIVERSE real                 -> fixed_<U>_real_top.csv, fixed_<U>_real.json
  python3 02_fixed_split.py UNIVERSE shuffle N [--seed S] -> fixed_<U>_null_shuffle_<S>.csv
  python3 02_fixed_split.py UNIVERSE signflip N [--seed S]-> fixed_<U>_null_signflip_<S>.csv
The null runs use the identical conditions/cuts (from the real training rows) and the identical search.
"""
import sys, os, json, time, argparse
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gsearch as G

ap = argparse.ArgumentParser()
ap.add_argument('universe'); ap.add_argument('mode'); ap.add_argument('n', type=int, nargs='?', default=0)
ap.add_argument('--seed', type=int, default=1); ap.add_argument('--beam', type=int, default=300)
A = ap.parse_args()
MS = (15, 30, 60)
df = G.load_group(A.universe)
y = df.three_day.values.astype(float)
tp = df.tp3.values.astype(float)
qn = df.qn.values
tr = qn <= 13
te = ~tr
M, names, compat = G.build_conditions(df, tr)
S = G.GSearcher(M[:, tr], qn[tr], compat, ms=MS, minq=6)
print(A.universe, A.mode, 'rows', len(df), 'train', tr.sum(), 'conditions', len(names), 'pairs', S.n_pairs,
      'eligible pairs', S.n_pairs_eligible, flush=True)
t0 = time.time()


def side_lists(res, o, m):
    L, Sh = res[(o, m, 1)], res[(o, m, -1)]
    E = sorted(L + Sh, key=lambda z: (-round(z[0], 9), -z[1], z[3]))
    return {'long': L, 'short': Sh, 'either': E}


def oos(c, yv):
    mk = G.rule_mask(M, list(c[4]))
    p = c[5] * yv[mk & te]
    return p


if A.mode == 'real':
    res = S.run(y[tr], beam=A.beam)
    counts = {k: res[k] for k in ('n_conditions', 'n_pairs', 'n_beam_pairs', 'n_triples')}
    print('real run', round(time.time() - t0, 1), counts, flush=True)
    rows = []
    for o in G.OBJS:
        for m in MS:
            for sgn in (1, -1):
                for rank, c in enumerate(res[(o, m, sgn)]):
                    mk = G.rule_mask(M, list(c[4]))
                    pn = c[5] * y[mk]
                    row = {'objective': o, 'min_trades': m, 'side': 'long' if sgn > 0 else 'short', 'rank': rank + 1,
                           'level': c[3], 'rule': G.rule_str(names, c[4], c[5]), 'conds': json.dumps(list(c[4])),
                           'sign': sgn, 'is_obj': c[0], 'is_avg_pct': 100 * c[1], 'is_trades': c[2],
                           'is_quarters': c[6], 'is_q_pos': c[7]}
                    row.update(G.stats(pn[tr[mk]], qn[mk][tr[mk]], 'first14_'))
                    row.update(G.stats(pn[te[mk]], qn[mk][te[mk]], 'last8_'))
                    row.update(G.stats(pn, qn[mk], 'all22_'))
                    if sgn > 0:
                        row['all22_tp_avg_pct'] = 100 * tp[mk].mean()
                        row['last8_tp_avg_pct'] = 100 * tp[mk & te].mean() if (mk & te).any() else np.nan
                    rows.append(row)
    T = pd.DataFrame(rows)
    T.to_csv(f'{G.HERE}/fixed_{A.universe}_real_top.csv', index=False)
    summ = {'counts': counts, 'rules_evaluated_per_objective_and_side': counts['n_conditions'] + counts['n_pairs'] + counts['n_triples'],
            'group_rows': int(len(df)), 'train_rows': int(tr.sum()), 'test_rows': int(te.sum()),
            'group_first14_avg_pct': 100 * y[tr].mean(), 'group_last8_avg_pct': 100 * y[te].mean(), 'best': {}}
    for o in G.OBJS:
        for m in MS:
            sl = side_lists(res, o, m)
            for side, lst in sl.items():
                c = lst[0]
                p = oos(c, y)
                top10 = [oos(cc, y) for cc in lst[:10]]
                summ['best'][f'{o}_m{m}_{side}'] = {
                    'rule': G.rule_str(names, c[4], c[5]), 'is_obj': c[0], 'is_avg_pct': 100 * c[1], 'is_trades': c[2],
                    'is_q': c[6], 'is_q_pos': c[7], 'last8_avg_pct': 100 * p.mean() if len(p) else None,
                    'last8_trades': int(len(p)),
                    'top10_last8_mean_of_rule_avgs_pct': 100 * float(np.mean([x.mean() for x in top10 if len(x)])),
                    'top10_is_mean_pct': 100 * float(np.mean([cc[1] for cc in lst[:10]]))}
                print(o, m, side, summ['best'][f'{o}_m{m}_{side}'], flush=True)
    json.dump(summ, open(f'{G.HERE}/fixed_{A.universe}_real.json', 'w'), indent=1, default=float)
else:
    rng = np.random.default_rng(1000 * A.seed + (1 if A.mode == 'shuffle' else 2))
    rows = []
    for s in range(A.n):
        ys = G.shuffle_within(y, qn, rng) if A.mode == 'shuffle' else G.signflip(y, qn, rng)
        res = S.run(ys[tr], beam=A.beam)
        for o in G.OBJS:
            for m in MS:
                sl = side_lists(res, o, m)
                for side, lst in sl.items():
                    c = lst[0]
                    p = oos(c, ys)
                    top10 = [oos(cc, ys) for cc in lst[:10]]
                    rows.append({'run': s, 'objective': o, 'min_trades': m, 'side': side, 'is_obj': c[0],
                                 'is_avg_pct': 100 * c[1], 'is_trades': c[2], 'is_q_pos': c[7], 'is_q': c[6],
                                 'chosen_side': 'long' if c[5] > 0 else 'short',
                                 'last8_avg_pct': 100 * p.mean() if len(p) else np.nan, 'last8_trades': len(p),
                                 'top10_last8_pct': 100 * float(np.mean([x.mean() for x in top10 if len(x)])),
                                 'top10_is_pct': 100 * float(np.mean([cc[1] for cc in lst[:10]]))})
        print(A.mode, 'run', s + 1, round(time.time() - t0, 1), flush=True)
        pd.DataFrame(rows).to_csv(f'{G.HERE}/fixed_{A.universe}_null_{A.mode}_{A.seed}.csv', index=False)
print('done', round(time.time() - t0, 1))
