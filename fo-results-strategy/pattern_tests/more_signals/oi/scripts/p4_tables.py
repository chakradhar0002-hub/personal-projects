#!/usr/bin/env python3
"""Markdown tables from results/*.csv (p3_tests.py).  usage: python3 -P p4_tables.py <family_dir>"""
import sys

import numpy as np
import pandas as pd

FAM = sys.argv[1]
R = f'{FAM}/results'
T = pd.read_csv(f'{R}/tests.csv')


def f(x, nd=2, sign=True):
    if pd.isna(x):
        return '-'
    return f'{x:+.{nd}f}' if sign else f'{x:.{nd}f}'


def pv(x):
    if pd.isna(x):
        return '-'
    return f'{x:.4f}' if x < 0.001 else f'{x:.3f}'


def main_table(tr):
    X = T[T.trade == tr]
    head = ('| test | rule (dir) | n | avg net % | excess vs parent | q+ / q | first 14: n, net, exc | last 8: n, net, exc '
            '| net w/o best 5 | luck p | Holm p | maxT p | placebo n, excess | DiD (placebo p) | works |')
    sep = '|' + '---|' * 15
    lines = [head, sep]
    for _, r in X.iterrows():
        crit = ''.join(c for c, k in (('H', 'c_halves'), ('M', 'c_holm'), ('P', 'c_placebo'), ('5', 'c_wo5'))
                       if bool(r[k]))
        lines.append(
            f"| {r.test} | {r.label} ({r.dir}) | {int(r.n)} | {f(r.avg_net)} | {f(r.excess)} | {int(r.q_pos)}/{int(r.q_with)} "
            f"| {int(r.n_f14)}, {f(r.net_f14)}, {f(r.exc_f14)} | {int(r.n_l8)}, {f(r.net_l8)}, {f(r.exc_l8)} "
            f"| {f(r.net_wo5)} | {pv(r.luck_p)} | {pv(r.holm_p)} | {pv(r.maxT_p)} | {int(r.pl_n) if pd.notna(r.pl_n) else '-'}, "
            f"{f(r.pl_excess)} | {f(r.DiD)} ({pv(r.placebo_p)}) | {'YES' if r.WORKS else 'no'} [{crit}] |")
    return '\n'.join(lines)


def split_table(df):
    head = ('| pool | cond | pred | IN n | IN net | OUT n | OUT net | diff | IN first14 n, net | OUT first14 net '
            '| IN last8 n, net | OUT last8 net | perm p (2-sided) | Holm p |')
    lines = [head, '|' + '---|' * 14]
    for _, r in df.iterrows():
        lines.append(f"| {r.pool} | {r.condition} | {r.pred} | {int(r.n_in)} | {f(r.net_in)} | {int(r.n_out)} | "
                     f"{f(r.net_out)} | {f(r['diff'])} | {int(r.n_in_f14)}, {f(r.net_in_f14)} | {f(r.net_out_f14)} | "
                     f"{int(r.n_in_l8)}, {f(r.net_in_l8)} | {f(r.net_out_l8)} | {pv(r.perm_p_2s)} | {pv(r.holm_p)} |")
    return '\n'.join(lines)


A = main_table('A')
B = main_table('B')
SA = split_table(pd.read_csv(f'{R}/split_lag_rule.csv'))
SB = split_table(pd.read_csv(f'{R}/split_winners.csv'))
open(f'{R}/table_A.md', 'w').write(A + '\n')
open(f'{R}/table_B.md', 'w').write(B + '\n')
open(f'{R}/split_lag_rule.md', 'w').write(SA + '\n')
open(f'{R}/split_winners.md', 'w').write(SB + '\n')
print(A, '\n\n', B, '\n\n', SA, '\n\n', SB)
