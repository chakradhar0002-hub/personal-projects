"""
03_walkforward.py -- walk-forward version of the same search.
For every quarter q = 6..21: rebuild the condition cuts from quarters < q only, run the 1/2/3-condition
search on quarters < q (min trades m, picks in >= 4 quarters), take the best rule (variants below) and
trade it in quarter q.  The identical pipeline is run on N within-quarter shuffles of three_day.

Variants (each counted as a thing tried):
  best_all    single best rule of any size (1, 2 or 3 conditions)
  best_upto2  single best rule with 1 or 2 conditions
  best_1      single best 1-condition rule
  top10_pool  all trades of the 10 best rules (any size) pooled
usage: python3 03_walkforward.py UNIVERSE NSHUF [--beam B] [--n0 X]
"""
import sys, os, json, time, argparse
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rulelib as R

ap = argparse.ArgumentParser()
ap.add_argument('universe'); ap.add_argument('nshuf', type=int)
ap.add_argument('--beam', type=int, default=500); ap.add_argument('--n0', type=float, default=0.0)
A = ap.parse_args()
tag = f"{A.universe}_n0{int(A.n0)}_beam{A.beam}"
MS = (10, 20, 30)
VARIANTS = ('best_all', 'best_upto2', 'best_1', 'top10_pool')

df = R.load(A.universe)
y = df.three_day.values.astype(float)
qn = df.qn.values
rng = np.random.default_rng(777)
Y = [y] + [R.shuffle_within(y, qn, rng) for _ in range(A.nshuf)]

agg = {}      # (s, m, variant) -> [sum, n, list of per-quarter avg]
trades = []   # real trades
chosen = []   # real chosen rules per quarter
t0 = time.time()
for q in range(6, 22):
    tr = qn < q
    te = qn == q
    M, names, compat = R.build_conditions(df, tr)
    S = R.Searcher(M[:, tr], qn[tr], compat)
    for s, ys in enumerate(Y):
        res = S.run(ys[tr], ms=MS, minq=4, beam=A.beam, n0=A.n0, ntop=10)
        for m in MS:
            r = res[m]
            picks = {'best_all': r['top'][:1], 'best_upto2': r['top_upto2'][:1], 'best_1': r['top_upto1'][:1],
                     'top10_pool': r['top'][:10]}
            for v in VARIANTS:
                pn_all = []
                for c in picks[v]:
                    mk = R.rule_mask(M, list(c[4])) & te
                    pn = c[5] * ys[mk]
                    pn_all.append(pn)
                    if s == 0:
                        for ii, p in zip(np.where(mk)[0], pn):
                            trades.append({'variant': v, 'min_trades': m, 'qn': q, 'symbol': df.symbol.values[ii],
                                           'pnl': p, 'in_fo': bool(df.in_fo.values[ii]),
                                           'rule': R.rule_str(names, c[4], c[5])})
                    if s == 0 and v != 'top10_pool':
                        chosen.append({'variant': v, 'min_trades': m, 'qn': q, 'rule': R.rule_str(names, c[4], c[5]),
                                       'is_avg_pct': 100 * c[1], 'is_trades': c[2], 'oos_trades': int(mk.sum()),
                                       'oos_avg_pct': 100 * pn.mean() if len(pn) else np.nan})
                pn = np.concatenate(pn_all) if pn_all else np.array([])
                a = agg.setdefault((s, m, v), [0.0, 0, [], 0.0, 0])
                a[0] += pn.sum(); a[1] += len(pn)
                if len(pn):
                    a[2].append(pn.mean())
                if q >= 14:
                    a[3] += pn.sum(); a[4] += len(pn)
    print('quarter', q, 'done', round(time.time() - t0, 1), 'conds', len(names), flush=True)

rows = []
for (s, m, v), a in agg.items():
    rows.append({'shuffle': s, 'min_trades': m, 'variant': v, 'trades': a[1],
                 'pooled_avg_pct': 100 * a[0] / a[1] if a[1] else np.nan,
                 'avg_of_quarter_avgs_pct': 100 * np.mean(a[2]) if a[2] else np.nan, 'quarters_with_picks': len(a[2]),
                 'trades_q14plus': a[4], 'pooled_q14plus_pct': 100 * a[3] / a[4] if a[4] else np.nan})
W = pd.DataFrame(rows)
W.to_csv(f'{R.HERE}/wf_{tag}_all_runs.csv', index=False)
T = pd.DataFrame(trades); T.to_csv(f'{R.HERE}/wf_{tag}_real_trades.csv', index=False)
pd.DataFrame(chosen).to_csv(f'{R.HERE}/wf_{tag}_chosen_rules.csv', index=False)
summ = {}
for m in MS:
    for v in VARIANTS:
        real = W[(W.shuffle == 0) & (W.min_trades == m) & (W.variant == v)].iloc[0]
        sh = W[(W.shuffle > 0) & (W.min_trades == m) & (W.variant == v)]
        tt = T[(T.variant == v) & (T.min_trades == m)]
        st = R.trade_stats(tt.pnl.values, tt.qn.values) if len(tt) else {}
        d = {k: (float(x) if isinstance(x, (np.floating, float, int, np.integer)) else x) for k, x in real.items()}
        d.update({'stats': st, 'shuf_pooled_mean': float(sh.pooled_avg_pct.mean()),
                  'shuf_pooled_p95': float(sh.pooled_avg_pct.quantile(0.95)),
                  'p_shuf_ge_real': float((sh.pooled_avg_pct >= real.pooled_avg_pct).mean()) if len(sh) else None})
        summ[f'{v}_m{m}'] = d
        print(v, m, 'real WF pooled %.2f%% on %d trades (%d qtrs), q14+ %.2f%% on %d | shuffled mean %.2f p95 %.2f p=%s' % (
            real.pooled_avg_pct, real.trades, real.quarters_with_picks, real.pooled_q14plus_pct, real.trades_q14plus,
            d['shuf_pooled_mean'], d['shuf_pooled_p95'], d['p_shuf_ge_real']))
json.dump(summ, open(f'{R.HERE}/wf_{tag}.json', 'w'), indent=1, default=float)
print('done', round(time.time() - t0, 1))
