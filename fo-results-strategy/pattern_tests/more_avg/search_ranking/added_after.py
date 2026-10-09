#!/usr/bin/env python3
"""ADDED AFTER diagnostics for C11 HAND_T5 (discovery qn 4..13 only). See candidates.txt addendum."""
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.environ.get('LAB_ROOT', os.path.abspath(os.path.join(HERE, '..', '..')))  # scratch data folder
DISC_MAX = 13
LOG = open(f'{HERE}/added_after.log', 'w')


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    LOG.write(s + '\n')


tr = pd.read_csv(f'{SP}/tafa/C_post_results/trades.csv', usecols=['symbol', 'qn', 'i_react', 'raw_H20', 'nifty_H20'])
tr = tr[tr.qn <= DISC_MAX].copy()                       # holdout rows dropped first
tr['vsN_net'] = tr.raw_H20 - tr.nifty_H20 - 0.19
tr['raw_net'] = tr.raw_H20 - 0.17
fr = pd.read_csv(f'{HERE}/features_rank.csv')
fr = fr[fr.qn <= DISC_MAX]
d = fr.merge(tr[['symbol', 'qn', 'i_react', 'vsN_net', 'raw_net']], on=['symbol', 'qn', 'i_react'], validate='1:1')
W = d[d.W].reset_index(drop=True)
W['year'] = W.reaction_day.str[:4].astype(int)


def ecdf(pool, x):
    s = np.sort(pool)
    return np.searchsorted(s, x, side='right') / len(s)


def hand(fr_or_k):
    sel = []
    for q in range(4, DISC_MAX + 1):
        trn, tst = W[W.qn < q], W[W.qn == q]
        st = ecdf(trn.cut_rsi14.values, trn.cut_rsi14.values) + ecdf(trn.XN.values, trn.XN.values)
        ss = ecdf(trn.cut_rsi14.values, tst.cut_rsi14.values) + ecdf(trn.XN.values, tst.XN.values)
        f = fr_or_k if fr_or_k < 1 else min(1.0, fr_or_k * trn.qn.nunique() / len(trn))
        sel += tst.index[ss >= np.quantile(st, 1 - f)].tolist()
    return W.loc[sel]


def st(x):
    v = np.sort(x.vsN_net.values)
    qm = x.groupby('qn').vsN_net.mean()
    return dict(n=len(v), avg=v.mean(), wo5=v[:-5].mean() if len(v) > 5 else np.nan, median=np.median(v),
                q=f'{int((qm > 0).sum())}/{len(qm)}')


P('A15..A21 HAND fixed-fraction curve (qn 4..13):')
rows = []
for f in (0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.60, 1.0 - 1e-9):
    x = hand(f)
    rows.append(dict(f=f if f < 0.99 else 1.0, **st(x)))
x5 = hand(5)
rows.append(dict(f='T5 (C11)', **st(x5)))
P(pd.DataFrame(rows).round(2).to_string(index=False))

C11 = x5
P(f'\nC11 trades {len(C11)}, avg {C11.vsN_net.mean():+.2f}, raw_net (unhedged) avg {C11.raw_net.mean():+.2f}')
P('C11 by year:')
y = C11.groupby('year').vsN_net.agg(['size', 'mean', 'sum'])
y['share_of_total'] = y['sum'] / C11.vsN_net.sum()
P(y.round(2).to_string())
loo = [C11[C11.qn != q].vsN_net.mean() for q in sorted(C11.qn.unique())]
P(f'leave-one-quarter-out avg range {min(loo):+.2f} .. {max(loo):+.2f}')
s = np.sort(C11.vsN_net.values)
P(f'C11 without best 5 {s[:-5].mean():+.2f}, without best 10 {s[:-10].mean():+.2f}; best 5 = {np.round(s[-5:], 1)}')

base = W[(W.cut_rsi14 > 50) & (W.qn >= 4)]
inb = C11[C11.cut_rsi14 > 50]
outb = C11[C11.cut_rsi14 <= 50]
dropped = base[~base.index.isin(C11.index)]
P(f'\nC11 trades with cut_rsi14 > 50 (also baseline): n {len(inb)} avg {inb.vsN_net.mean():+.2f}; '
  f'with cut_rsi14 <= 50: n {len(outb)} avg {outb.vsN_net.mean():+.2f}')
P(f'baseline qn4-13 trades NOT in C11: n {len(dropped)} avg {dropped.vsN_net.mean():+.2f}')
P(f'C11 XN median {C11.XN.median():.2f} vs all winners {W[W.qn >= 4].XN.median():.2f}; '
  f'cut_rsi14 median {C11.cut_rsi14.median():.1f} vs {W[W.qn >= 4].cut_rsi14.median():.1f}')

# A22 random draws, same per-quarter counts
rng = np.random.default_rng(20261009)
cnt = C11.groupby('qn').size()
pools = {q: W[W.qn == q].vsN_net.values for q in cnt.index}
ND = 20000
avg, wo5 = np.empty(ND), np.empty(ND)
for i in range(ND):
    v = np.concatenate([rng.choice(pools[q], cnt[q], replace=False) for q in cnt.index])
    vs = np.sort(v)
    avg[i], wo5[i] = v.mean(), vs[:-5].mean()
P(f'\nA22 random same-count draws: avg mean {avg.mean():+.2f}, P(avg >= C11) = {(avg >= C11.vsN_net.mean()).mean():.4f}; '
  f'wo5 mean {wo5.mean():+.2f}, P(wo5 >= C11) = {(wo5 >= s[:-5].mean()).mean():.4f}')
P('(single-test p-values; C11 was the best of 12 eligible candidates - adjust roughly x12 for selection)')
C11.sort_values(['qn', 'reaction_day']).to_csv(f'{HERE}/C11_trades_discovery.csv', index=False, float_format='%.4f')
