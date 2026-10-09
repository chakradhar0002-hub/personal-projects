#!/usr/bin/env python3
"""EXPLORATORY (not pre-registered) follow-ups to run_tests.py. Writes extras.log and per_quarter_candidates.csv."""
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
LOG = open(f'{HERE}/extras.log', 'w')
COST = 0.17


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    LOG.write(s + '\n')


sig = pd.read_csv(f'{HERE}/signals_results.csv.gz')
out = pd.read_csv(f'{SP}/perf/features/outcomes.csv', usecols=['symbol', 'qn', 'three_day'])
D = sig.merge(out, on=['symbol', 'qn'], validate='1:1')
D = D[D.three_day.notna()].reset_index(drop=True)
y = D.three_day.to_numpy()
qn = D.qn.to_numpy()
QS = np.unique(qn)
qidx = {q: np.flatnonzero(qn == q) for q in QS}
rng = np.random.default_rng(99)


def luck(mask, B=20000):
    obs = y[mask].mean()
    nq = pd.Series(qn[mask]).value_counts()
    tot = np.zeros(B)
    for q, k in nq.items():
        ix = qidx[q]
        keys = rng.random((B, len(ix)))
        tot += y[ix][np.argsort(keys, axis=1)[:, :k]].sum(1)
    return (1 + (tot / mask.sum() >= obs).sum()) / (1 + B)


def line(name, m):
    v = y[m]
    h1, h2 = m & (qn <= 13), m & (qn >= 14)
    P(f'{name:58s} n={m.sum():4d} avg {v.mean():+.3f} net {v.mean() - COST:+.3f} | first 14 n={h1.sum()} '
      f'{y[h1].mean():+.3f} | last 8 n={h2.sum()} {y[h2].mean():+.3f} | luck p {luck(m):.3f}')


R1 = D.RP1.to_numpy(bool)
LR = D.LAGRULE.to_numpy(bool)
P('EXPLORATORY - not part of the pre-registered families')
P('\n1) RP1 (volume >= 1.0 AND 3-month vs Nifty bottom quintile) split by overlap with the 85 lag-rule trades')
line('RP1 all', R1)
line('RP1 trades that are also lag-rule trades', R1 & LR)
line('RP1 trades NOT in the lag rule (lag21 >= -10)', R1 & ~LR)
line('lag rule trades NOT in RP1', LR & ~R1)

P('\n2) lag rule + condition (descriptive only; small n)')
for c, lab in [('TR15', 'habitual post-results drift top quintile'), ('PP12', '30%+ below 52-week high'),
               ('PP04', '3-month vs Nifty bottom quintile'), ('TR05', 'mean last-4 windows top quintile')]:
    line(f'lag rule AND {c} ({lab})', LR & D[c].to_numpy(bool))

P('\n3) track-record candidates by year-half (decay check)')
for c in ['TR05', 'TR12', 'TR03', 'TR11', 'TR15']:
    m = D[c].to_numpy(bool)
    line(c, m)
rows = []
per = D.groupby('qn').agg(quarter=('quarter', 'first'), period=('period', 'first'))
for c in ['TR05', 'TR12', 'TR03', 'RP1', 'LAGRULE']:
    m = D[c].to_numpy(bool)
    for q in QS:
        mm = m & (qn == q)
        rows.append({'test': c, 'qn': q, 'results_for': f'Results for {per.period[q]} ({per.quarter[q]})',
                     'n': int(mm.sum()), 'avg': y[mm].mean() if mm.any() else np.nan,
                     'all_fo_avg': y[qn == q].mean()})
pq = pd.DataFrame(rows)
pq.to_csv(f'{HERE}/per_quarter_candidates.csv', index=False, float_format='%.3f')
wide = pq.pivot(index=['qn', 'results_for'], columns='test', values='avg').round(2)
wide['all_fo'] = pq.drop_duplicates('qn').set_index(['qn', 'results_for']).all_fo_avg.round(2)
P('\nper-quarter average three_day (%, gross):')
P(wide.to_string())
