#!/usr/bin/env python3
"""C11 HAND_T5 selections for every quarter q = 4..21 - FEATURES ONLY (reads no outcome file).

Walk-forward: for quarter q, pool = winners (XN > 4) of quarters 0..q-1.
score(x) = share of pool with cut_rsi14 <= x.cut_rsi14 + share of pool with XN <= x.XN
f = min(1, 5 * q / len(pool)); threshold = numpy.quantile(scores of the pool rows themselves, 1 - f) (linear)
trade quarter-q winner if score >= threshold. Entry close of i_react, exit close i_react+20, short Nifty 50 same value.
Writes c11_picks_all_quarters.csv (symbol, qn, reaction_day, i_react, XN, cut_rsi14, score, threshold, f) so a
validator can attach vsN_net = raw_H20 - nifty_H20 - 0.19 for qn 14..21 later.
"""
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.environ.get('LAB_ROOT', os.path.abspath(os.path.join(HERE, '..', '..')))  # scratch data folder
f = pd.read_csv(f'{SP}/tafa/C_post_results/features.csv',
                usecols=['symbol', 'qn', 'reaction_day', 'i_react', 'XN', 'cut_rsi14'])
w = f[f.XN > 4].reset_index(drop=True)


def score(pool, x):
    return ((pool.cut_rsi14.values[None, :] <= x.cut_rsi14.values[:, None]).mean(1)
            + (pool.XN.values[None, :] <= x.XN.values[:, None]).mean(1))


out = []
for q in range(4, int(w.qn.max()) + 1):
    pool, te = w[w.qn < q], w[w.qn == q].copy()
    fr = min(1.0, 5 * pool.qn.nunique() / len(pool))
    thr = np.quantile(score(pool, pool), 1 - fr)
    te['score'], te['threshold'], te['f'] = score(pool, te), thr, fr
    out.append(te[te.score >= thr])
o = pd.concat(out)
o.to_csv(f'{HERE}/c11_picks_all_quarters.csv', index=False, float_format='%.4f')
print(o.groupby('qn').agg(n=('symbol', 'size'), f=('f', 'first'), thr=('threshold', 'first')).round(3).to_string())
print('winners per quarter:', w.groupby('qn').size().to_dict())
