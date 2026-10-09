#!/usr/bin/env python3
"""Verifier: repeat qualifiers (stock also in the signal in its previous quarter, known ex ante) vs new entrants,
and per-stock concentration. Output: v5_repeat.log (run: python3 v5_repeat.py | tee v5_repeat.log)."""
import pandas as pd
H = __import__('os').environ.get('LAB_ROOT', 'lab') + '/perf/verify_A_pre_results'
F = pd.read_csv(f'{H}/my_features.csv.gz'); F = F[F.td.notna()].reset_index(drop=True)
y = F.td.to_numpy(); qn = F.qn.to_numpy()
QM = pd.Series(y).groupby(qn).mean(); F['exc'] = y - QM.reindex(qn).to_numpy()
for name, col, thr in [('TR05 top quintile', 'pq_mean_td4', 0.8), ('TR05 top decile', 'pq_mean_td4', 0.9),
                       ('TR12 top quintile', 'pq_mean_xn4', 0.8)]:
    F['sig'] = F[col] > thr
    F = F.sort_values(['symbol', 'qn'])
    F['prev_sig'] = F.groupby('symbol').sig.shift(1)
    F['prev_qn'] = F.groupby('symbol').qn.shift(1)
    rep = F.sig & (F.prev_sig == True) & (F.prev_qn == F.qn - 1)
    for lab, m in [('repeat (also in signal last quarter)', rep), ('new entrant', F.sig & ~rep)]:
        m = m.to_numpy(); mh2 = m & (F.qn >= 14).to_numpy()
        print(f'{name} {lab}: n={m.sum()} avg {F.td[m].mean():+.2f} exc {F.exc[m].mean():+.2f} | last8 n={mh2.sum()} avg {F.td[mh2].mean():+.2f}')
    F = F.sort_index()
