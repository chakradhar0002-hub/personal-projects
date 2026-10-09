#!/usr/bin/env python3
"""Discovery-only diagnostics (qn 0..13) for the two finalists picked by the pre-stated rule.
Not used for selection. Holdout rows are dropped right after reading trades.csv.
  - split halves (qn 0-6 vs 7-13), ex-2023, the trades each filter REMOVES from the baseline
  - random-subset test: draw random subsets of the 122 baseline trades of the finalist's size; how often is the
    subset's avg w/o best 5 >= the finalist's?  Plus a search-adjusted version: for every draw, the MAX over all
    38 candidate sizes (independent random subsets) vs the winner's value - a crude look-elsewhere check.
"""
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.environ.get('LAB_ROOT', os.path.abspath(os.path.join(HERE, '..', '..')))  # scratch data folder
sys.path.insert(0, HERE)
from candidates import CANDS, W  # noqa: E402

rng = np.random.default_rng(20261009)
tr = pd.read_csv(f'{SP}/tafa/C_post_results/trades.csv', usecols=['symbol', 'qn', 'raw_H20', 'nifty_H20'])
tr = tr[tr.qn <= 13].copy()
tr['vsN_net'] = tr.raw_H20 - tr.nifty_H20 - 0.19
fe = pd.read_csv(f'{HERE}/features_signal.csv')
fe = fe[fe.qn <= 13]
d = fe.merge(tr, on=['symbol', 'qn'], how='inner', validate='1:1')
d['year'] = d.reaction_day.str[:4].astype(int)
base = W(d)
b = d.loc[base, 'vsN_net'].to_numpy()
LOG = open(f'{HERE}/diagnostics.log', 'w')


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    LOG.write(s + '\n')


def wo5(v):
    v = np.sort(v)
    return v[:-5].mean()


FIN = ['C05_XN5', 'C27_BRK20_VOL1.5']
sizes = [int(f(d).fillna(False).astype(bool).sum()) for _, _, f in CANDS]
NDRAW = 20000
# random subsets for every candidate size (for the look-elsewhere max)
draws = {}
for n in sorted(set(sizes)):
    if n <= 5:
        continue
    idx = np.argsort(rng.random((NDRAW, len(b))), axis=1)[:, :n]
    s = np.sort(b[idx], axis=1)
    draws[n] = s[:, :-5].mean(1)
elig_sizes = [n for (nm, _, f), n in zip(CANDS, sizes) if n >= 35]
mx = np.max(np.vstack([draws[n] for n in elig_sizes]), axis=0)

P(f'BASE discovery n {len(b)} avg {b.mean():+.3f} w/o best5 {wo5(b):+.3f}')
for name in FIN:
    f = [c for c in CANDS if c[0] == name][0][2]
    m = f(d).fillna(False).astype(bool)
    x, rem = d.loc[m], d.loc[base & ~m]
    v = x.vsN_net.to_numpy()
    obs = wo5(v)
    p1 = (draws[len(v)] >= obs).mean()
    p2 = (mx >= obs).mean()
    P(f'\n{name}: n {len(v)} avg {v.mean():+.3f} w/o best5 {obs:+.3f} median {np.median(v):+.3f}')
    P(f'  removed from baseline: n {len(rem)} avg {rem.vsN_net.mean():+.3f} median {rem.vsN_net.median():+.3f}')
    for lab, mm in [('qn 0-6', x.qn <= 6), ('qn 7-13', x.qn >= 7), ('ex-2023', x.year != 2023),
                    ('2023 only', x.year == 2023)]:
        y = x.loc[mm, 'vsN_net']
        bb = d.loc[base & (d.qn <= 6 if lab == 'qn 0-6' else d.qn >= 7 if lab == 'qn 7-13' else
                           d.year != 2023 if lab == 'ex-2023' else d.year == 2023), 'vsN_net']
        P(f'  {lab:9s}: n {len(y):3d} avg {y.mean():+.3f} median {y.median():+.3f} | baseline same slice n {len(bb)} '
          f'avg {bb.mean():+.3f}')
    P(f'  random subset of the 122 baseline trades, size {len(v)}: P(w/o best5 >= {obs:+.3f}) = {p1:.4f}')
    P(f'  look-elsewhere (max over {len(elig_sizes)} eligible candidate sizes, independent random subsets): '
      f'P = {p2:.4f}')
    P(f'  distinct stocks {x.symbol.nunique()}, max trades in one stock {x.symbol.value_counts().max()}')
LOG.close()
