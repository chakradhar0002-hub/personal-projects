#!/usr/bin/env python3
"""Holdout evaluator - step 6: markdown tables from finalist_table.csv and per_quarter_all.csv."""
import sys
import numpy as np
import pandas as pd

OUT = __import__('os').environ.get('LAB_ROOT', 'lab') + '/more_avg/holdout'
T = pd.read_csv(f'{OUT}/finalist_table.csv')
pq = pd.read_csv(f'{OUT}/per_quarter_all.csv')


def g(x, d=2):
    return 'n/a' if not np.isfinite(x) else f'{x:+.{d}f}'


L = ['| Finalist | Disc n / avg (mine) | Hold n | Hold avg | Hold median | Hold w/o best 5 | Hold q+ | Hold unhedged | '
     'Baseline same hold quarters avg (w/o5) | p (one-sided) | Holm p | Next-open +0.40 hold avg (n) | Full n / avg (in-sample) | Survivor |',
     '|' + '---|' * 14]
for _, r in T.iterrows():
    L.append(f"| {r.F} {r['name']} | {r.disc_n} / {g(r.disc_avg)} | {r.hold_n} | {g(r.hold_avg)} | {g(r.hold_med)} | "
             f"{g(r.hold_wo5)} | {r.hold_qpos}/{r.hold_qtr} | {g(r.hold_raw)} | {g(r.cmpA_avg)} ({g(r.cmpA_wo5)}) | "
             f"{r.p_raw:.4f} | {r.p_holm:.4f} | {g(r.real_avg)} ({r.real_n}) | {r.full_n} / {g(r.full_avg)} | "
             f"{'YES' if r.survivor else 'no'} |")
md = '\n'.join(L)
open(f'{OUT}/finalist_table.md', 'w').write(md + '\n')
print(md)

cols = sys.argv[1:] if len(sys.argv) > 1 else []
H = ['| qn | quarter | Baseline n | Baseline avg | Plain winners n | Plain winners avg |']
for F in cols:
    H[0] += f' {F} n | {F} avg |'
H.append('|' + '---|' * (6 + 2 * len(cols)))
for _, r in pq.iterrows():
    s = f"| {r.qn}{'*' if r.qn >= 14 else ''} | {r.quarter} | {r.BASE_n} | {g(r.BASE_avg)} | {r.WIN_n} | {g(r.WIN_avg)} |"
    for F in cols:
        s += f" {r[F + '_n']} | {g(r[F + '_avg'])} |"
    H.append(s)
pmd = '\n'.join(H) + '\n(* = holdout quarter; all values vsN_net % per trade, H20 close-of-k for baseline/winners)'
open(f'{OUT}/per_quarter.md', 'w').write(pmd + '\n')
print(pmd)
