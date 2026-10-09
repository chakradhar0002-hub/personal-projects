#!/usr/bin/env python3
"""ADDED AFTER diagnostics (discovery only): C28 hold 50, C29 hold 55, paired quarter differences, bootstrap."""
import os, sys
import numpy as np
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv = [sys.argv[0]]
# reuse search.py machinery without re-running its main body: exec only the definitions
src = open(f'{HERE}/search.py').read()
defs = src.split('ALL, TR = [], []')[0]
defs = defs.replace("LOG = open(f'{HERE}/run.log', 'w')", "LOG = open(f'{HERE}/added_after.log', 'w')")
exec(compile(defs, 'search_defs', 'exec'))
DESC.update({'C28': 'close k, hold 50 (ADDED AFTER, diagnostic)', 'C29': 'close k, hold 55 (ADDED AFTER, diagnostic)'})
out = {}
for cid, ek, hc, rule, mh in [('R0', 'close', 20, [], 0), ('C02', 'close', 40, [], 0), ('C28', 'close', 50, [], 0),
                               ('C29', 'close', 55, [], 0), ('C03', 'close', 60, [], 0), ('C25', 'pull', 60, [], 0),
                               ('C17', 'close', 60, [('TP', 0.10)], 0)]:
    T = run(cid, ek, hc, rule, mh)
    out[cid] = T[T.ok].reset_index(drop=True)
rows = [summ(c, out[c].assign(ok=True)) for c in out]
P('DISCOVERY hold-length plateau check (qn 0..13):')
P(pd.DataFrame(rows)[['id', 'desc', 'n', 'avg', 'wo_best5', 'median', 'win', 'q_pos', 'q_with', 'held', 'per20']]
  .round(2).to_string(index=False))
pd.DataFrame(rows).to_csv(f'{HERE}/added_after_results.csv', index=False)
rng = np.random.default_rng(20261009)
base = out['R0'].set_index(['symbol', 'qn'])
for c in ('C03', 'C25', 'C17'):
    t = out[c].set_index(['symbol', 'qn'])
    j = t[['vsN_net']].join(base[['vsN_net']], rsuffix='_R0', how='inner')
    j['d'] = j.vsN_net - j.vsN_net_R0
    qd = j.groupby(level='qn').d.mean()
    P(f"\n{c} - R0 paired (n={len(j)}): trade mean diff {j.d.mean():+.2f}; quarter means: "
      + ' '.join(f'{v:+.1f}' for v in qd.values))
    P(f"   mean of 14 quarter diffs {qd.mean():+.2f}, sd {qd.std():.2f}, t {qd.mean() / (qd.std() / np.sqrt(len(qd))):.2f};"
      f" quarters where {c} beats R0: {(qd > 0).sum()}/{len(qd)}")
    # quarter-block bootstrap of the gap in avg-without-best-5
    qs = j.index.get_level_values('qn').unique().to_numpy()
    gaps = []
    for _ in range(5000):
        pick = rng.choice(qs, len(qs), replace=True)
        jj = pd.concat([j.xs(q, level='qn') for q in pick])
        a = jj.vsN_net.sort_values(ascending=False).iloc[5:].mean()
        b = jj.vsN_net_R0.sort_values(ascending=False).iloc[5:].mean()
        gaps.append(a - b)
    gaps = np.array(gaps)
    P(f"   quarter-block bootstrap of (wo_best5 {c} - wo_best5 R0): median {np.median(gaps):+.2f}, "
      f"5-95% [{np.percentile(gaps, 5):+.2f}, {np.percentile(gaps, 95):+.2f}], P(gap >= 0.5) {np.mean(gaps >= 0.5):.2f}, "
      f"P(gap > 0) {np.mean(gaps > 0):.2f}")
# drawdown inside the 60-session hold (path risk), discovery, C03
P('\nC03 path risk (discovery): worst hedged close-to-close mark during the 60 sessions, per trade')
SYMI = SYM
worst = []
for r in out['C03'].itertuples():
    j_ = SYMI[r.symbol]
    k = int(S.loc[(S.symbol == r.symbol) & (S.qn == r.qn), 'i_react'].iloc[0])
    path = (PX[k + 1:k + 61, j_] / PX[k, j_] - NIF[k + 1:k + 61] / NIF[k]) * 100
    worst.append(path.min())
worst = np.array(worst)
P(f"   median worst mark {np.median(worst):+.1f}%, 10th pct {np.percentile(worst, 10):+.1f}%, "
  f"share of trades marked below -10% at some close: {np.mean(worst < -10) * 100:.0f}%")
