"""
03_walkforward.py -- walk-forward rule search inside the lag > 5% group.
For each quarter q = 8..21: conditions/cuts from the group's rows with qn < q only, the same 1/2/3-condition search
(objectives mean / fpos / worst x min trades 15/30/60, picks in >= 6 earlier quarters), then trade in quarter q:
  best_either  the single best rule of either side
  best_long    the single best long rule
  best_short   the single best short rule
  top5_either  all trades of the 5 best rules of either side, pooled (a stock picked by k rules counts k times)
The identical pipeline is run on within-quarter shuffles and sign-flips of three_day (same null y used for every q).

usage: python3 03_walkforward.py UNIVERSE MODE N [--beam B]
  MODE real      -> real run only (trades + chosen rules files)
  MODE shuffle   -> N shuffles;  MODE signflip -> N sign-flips
"""
import sys, os, json, time, argparse
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gsearch as G

ap = argparse.ArgumentParser()
ap.add_argument('universe'); ap.add_argument('mode'); ap.add_argument('n', type=int, nargs='?', default=0)
ap.add_argument('--beam', type=int, default=150); ap.add_argument('--seed', type=int, default=7)
A = ap.parse_args()
MS = (15, 30, 60)
df = G.load_group(A.universe)
y = df.three_day.values.astype(float)
tp = df.tp3.values.astype(float)
qn = df.qn.values
rng = np.random.default_rng(A.seed * 100 + (1 if A.mode == 'shuffle' else 2))
if A.mode == 'real':
    Y = [y]
elif A.mode == 'shuffle':
    Y = [G.shuffle_within(y, qn, rng) for _ in range(A.n)]
else:
    Y = [G.signflip(y, qn, rng) for _ in range(A.n)]

tag = f'{A.universe}_{A.mode}_beam{A.beam}'
agg, trades, chosen = [], [], []
t0 = time.time()
for q in range(8, 22):
    tr = qn < q
    te = qn == q
    M, names, compat = G.build_conditions(df, tr)
    S = G.GSearcher(M[:, tr], qn[tr], compat, ms=MS, minq=6)
    for s, ys in enumerate(Y):
        res = S.run(ys[tr], beam=A.beam, ntop=10)
        for o in G.OBJS:
            for m in MS:
                L, Sh = res[(o, m, 1)], res[(o, m, -1)]
                E = sorted(L + Sh, key=lambda z: (-round(z[0], 9), -z[1], z[3]))
                picks = {'best_either': E[:1], 'best_long': L[:1], 'best_short': Sh[:1], 'top5_either': E[:5]}
                for v, lst in picks.items():
                    tot, n = 0.0, 0
                    for c in lst:
                        mk = G.rule_mask(M, list(c[4])) & te
                        pn = c[5] * ys[mk]
                        tot += pn.sum(); n += len(pn)
                        if A.mode == 'real':
                            for ii, p in zip(np.where(mk)[0], pn):
                                trades.append({'objective': o, 'min_trades': m, 'variant': v, 'qn': q,
                                               'symbol': df.symbol.values[ii], 'side': 'long' if c[5] > 0 else 'short',
                                               'pnl': p, 'tp_pnl': tp[ii] if c[5] > 0 else np.nan,
                                               'rule': G.rule_str(names, c[4], c[5])})
                            if v != 'top5_either':
                                chosen.append({'objective': o, 'min_trades': m, 'variant': v, 'qn': q,
                                               'rule': G.rule_str(names, c[4], c[5]), 'is_obj': c[0],
                                               'is_avg_pct': 100 * c[1], 'is_trades': c[2], 'is_q_pos': c[7],
                                               'is_q': c[6], 'oos_trades': len(pn),
                                               'oos_avg_pct': 100 * pn.mean() if len(pn) else np.nan})
                    agg.append({'mode': A.mode, 'run': s, 'objective': o, 'min_trades': m, 'variant': v, 'qn': q,
                                'sum': tot, 'n': n})
    print(tag, 'quarter', q, 'done', round(time.time() - t0, 1), 'conds', len(names), flush=True)
    pd.DataFrame(agg).to_csv(f'{G.HERE}/wf_{tag}_agg.csv', index=False)
if A.mode == 'real':
    pd.DataFrame(trades).to_csv(f'{G.HERE}/wf_{tag}_trades.csv', index=False)
    pd.DataFrame(chosen).to_csv(f'{G.HERE}/wf_{tag}_chosen.csv', index=False)
print('done', round(time.time() - t0, 1))
