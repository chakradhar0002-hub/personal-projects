#!/usr/bin/env python3
"""Diagnostics for the finalist MA4 (window A, GBM, decile) - DISCOVERY quarters 4..13 only (reported, not selection).
  1. GBM seed stability (random_state 0..9; max_features=0.5 makes the fit seed-dependent)
  2. threshold dose-response (p = 0.05, 0.10, 0.15, 0.20, 0.30) with the pre-registered seed
  3. per-quarter table, concentration (symbols, biggest trades), overlap with the known lag-10%-quiet-volume group
  4. GBM permutation importance of the q=13 model on its own training pool (what the model leans on)
"""
import os
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance

HERE = os.path.dirname(os.path.abspath(__file__))
SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
sys.argv = [sys.argv[0]]
LOG = open(f'{HERE}/robustness.txt', 'w')


def P(*x):
    s = ' '.join(str(v) for v in x)
    print(s, flush=True)
    LOG.write(s + '\n')


FL = {}
for line in open(f'{HERE}/feature_lists.txt'):
    if line.strip():
        w, rest = line.split(':', 1)
        FL[w.split()[0]] = [c.strip() for c in rest.split(',')]
FA = pd.read_csv(f'{HERE}/features_A.csv')
out = pd.read_csv(f'{SP}/perf/features/outcomes.csv')
out = out[out.qn <= 13][['symbol', 'qn', 'three_day']]
assert out.qn.max() <= 13
A = FA.merge(out, on=['symbol', 'qn'], how='left')
A['y'] = A.three_day
A['elig'] = (A.qn <= 13) & A.y.notna()
A['short'] = -A.y - 0.17
QS = list(range(4, 14))
feats = FL['A']


def keep_feats(tr):
    k = []
    for f in feats:
        v = tr[f]
        if v.notna().mean() < 0.5:
            continue
        lo, hi = v.quantile(0.01), v.quantile(0.99)
        if np.isfinite(lo) and hi > lo:
            k.append(f)
    return k


def target(tr):
    yd = tr.y - tr.groupby('qn').y.transform('mean')
    return yd.clip(yd.quantile(0.01), yd.quantile(0.99)).to_numpy()


def gbm(tr, te, seed, ret_model=False):
    k = keep_feats(tr)
    lo, hi = tr[k].quantile(0.01), tr[k].quantile(0.99)
    Xtr, Xte = tr[k].clip(lo, hi, axis=1), te[k].clip(lo, hi, axis=1)
    m = HistGradientBoostingRegressor(loss='squared_error', learning_rate=0.03, max_iter=200, max_depth=3,
                                      min_samples_leaf=40, l2_regularization=1.0, max_features=0.5,
                                      early_stopping=False, random_state=seed).fit(Xtr.to_numpy(), target(tr))
    if ret_model:
        return m, k, Xtr
    return m.predict(Xte.to_numpy())


def run(seed, ps=(0.10,)):
    res = {p: [] for p in ps}
    for q in QS:
        Dq = A.loc[A.qn == q, 'i_cut'].min()
        pool = A[A.elig & (A.qn < q) & (A.i_p1 < Dq)].reset_index(drop=True)
        tq = sorted(pool.qn.unique())
        ref = np.concatenate([gbm(pool[pool.qn != j], pool[pool.qn == j], seed) for j in tq[-4:]])
        te = A[A.elig & (A.qn == q)].copy()
        te['s'] = gbm(pool, te, seed)
        for p in ps:
            res[p].append(te[te.s <= np.quantile(ref, p)])
    return {p: pd.concat(v) for p, v in res.items()}


def stats(tr):
    sh = np.sort(tr.short.to_numpy())
    qm = tr.groupby('qn').short.mean()
    return (f'n {len(tr):4d}  avg ret {tr.y.mean():+.2f}  short net {tr.short.mean():+.2f}  w/o5 {sh[:-5].mean():+.2f}  '
            f'q+ {int((qm > 0).sum())}/{tr.qn.nunique()}  h1 {tr[tr.qn <= 6].short.mean():+.2f}  '
            f'h2 {tr[tr.qn >= 7].short.mean():+.2f}  median ret {tr.y.median():+.2f}')


base = A[A.elig & A.qn.isin(QS)]
P(f'BASE (all eligible results, qn 4-13): n {len(base)}  avg ret {base.y.mean():+.2f}  short net {base.short.mean():+.2f}'
  f'  median ret {base.y.median():+.2f}')
P('\n1. GBM seed stability (decile, p=0.10):')
seed_rows = []
for seed in range(10):
    tr = run(seed)[0.10]
    seed_rows.append(tr.short.mean())
    P(f'  seed {seed}: ' + stats(tr))
P(f'  short net over seeds: mean {np.mean(seed_rows):+.2f}, min {np.min(seed_rows):+.2f}, max {np.max(seed_rows):+.2f}')

P('\n2. threshold dose-response, seed 0 (pre-registered):')
R0 = run(0, ps=(0.05, 0.10, 0.15, 0.20, 0.30))
for p, tr in R0.items():
    P(f'  p={p:.2f}: ' + stats(tr))

tr = R0[0.10].copy()
P('\n3. per quarter (decile, seed 0):')
for q in QS:
    g = tr[tr.qn == q]
    b = base[base.qn == q]
    P(f'  qn {q:2d}: trades {len(g):3d} of {len(b):3d}  avg ret {g.y.mean():+6.2f}  short net {g.short.mean():+6.2f}  '
      f'base short {b.short.mean():+6.2f}')
P(f'  distinct symbols {tr.symbol.nunique()}; most frequent: {tr.symbol.value_counts().head(8).to_dict()}')
P('  5 biggest falls (best short trades): ' + '; '.join(f'{r.symbol} q{r.qn} {r.y:+.1f}%' for r in
                                                       tr.nsmallest(5, 'y').itertuples()))
P('  5 biggest rises (worst short trades): ' + '; '.join(f'{r.symbol} q{r.qn} {r.y:+.1f}%' for r in
                                                        tr.nlargest(5, 'y').itertuples()))
P(f'  share of trades with return < 0: {(tr.y < 0).mean() * 100:.0f}% (base {(base.y < 0).mean() * 100:.0f}%)')
lagq = (tr.lag21 < -10) & (tr.vol_ratio_5_60 < 1.0)
P(f'  overlap with the known lag-10%-quiet-volume group: {int(lagq.sum())} trades; without them: '
  + stats(tr[~lagq]))
for c, lab in (('lag21', 'lag21'), ('vsN_63_A', 'vsN_63'), ('cut_rsi14', 'RSI14'), ('vol_ratio_5_60', 'vol 5/60'),
               ('atr14_pct', 'ATR%'), ('log_mcap', 'log mcap')):
    P(f'  median {lab}: trades {tr[c].median():+.2f}  all {base[c].median():+.2f}')

P('\n4. permutation importance, q=13 model on its training pool (top 15, drop in R2):')
pool = A[A.elig & (A.qn < 13)].reset_index(drop=True)
m, k, Xtr = gbm(pool, pool, 0, ret_model=True)
pi = permutation_importance(m, Xtr.to_numpy(), target(pool), n_repeats=5, random_state=0)
imp = pd.Series(pi.importances_mean, index=k).sort_values(ascending=False).head(15)
for f, v in imp.items():
    P(f'  {f:28s} {v:.4f}')
tr.to_csv(f'{HERE}/MA4_trades_discovery.csv', index=False, columns=['symbol', 'qn', 'quarter', 'i_cut', 'i_p1', 's',
                                                                     'y', 'short', 'lag21', 'vol_ratio_5_60'],
          float_format='%.4g')
