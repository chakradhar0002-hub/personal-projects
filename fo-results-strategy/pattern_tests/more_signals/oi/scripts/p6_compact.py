#!/usr/bin/env python3
"""Compact markdown tables for the summary.  usage: python3 -P p6_compact.py <family_dir>"""
import sys
import pandas as pd
R = f'{sys.argv[1]}/results'
T = pd.read_csv(f'{R}/tests.csv')
f = lambda x: '-' if pd.isna(x) else f'{x:+.2f}'
p = lambda x: '-' if pd.isna(x) else (f'{x:.3f}')
SH = {'A01': 'long buildup 5d', 'A02': 'short buildup 5d', 'A03': 'short covering 5d', 'A04': 'long unwinding 5d',
      'A05': 'long buildup 10d', 'A06': 'short buildup 10d', 'A07': 'short covering 10d', 'A08': 'long unwinding 10d',
      'A09': 'OI/20d avg top Q', 'A10': 'OI/20d avg bottom Q', 'A11': 'basis vs own median top Q',
      'A12': 'basis vs own median bottom Q', 'A13': 'PCR top Q', 'A14': 'PCR bottom Q', 'A15': 'PCR 5d chg top Q',
      'A16': 'PCR 5d chg bottom Q', 'A17': 'IV rich (IV/60d med top Q)', 'A18': 'IV cheap (bottom Q)',
      'A19': 'call-put IV spread top Q', 'A20': 'call-put IV spread bottom Q', 'A21': 'call IV 20d chg top Q',
      'A22': 'put IV 20d chg top Q', 'B01': 'OI up on day k', 'B02': 'OI +10% on day k', 'B03': 'long buildup 5d to k',
      'B04': 'long buildup 10d to k', 'B05': 'short buildup 5d before results', 'B06': 'OI/20d avg top Q at k',
      'B07': 'basis vs own median top Q at k', 'B08': 'basis change on k top Q', 'B09': 'PCR top Q at k',
      'B10': 'PCR change on k top Q', 'B11': 'IV cheap at k (bottom Q)', 'B12': 'call-put IV spread top Q at k',
      'B13': 'call IV 20d chg top Q at k', 'B14': 'put IV 20d chg bottom Q at k'}
def main(tr):
    L = ['| test | rule | dir | n | net % | excess | q+/q | first14 net (exc) | last8 net (exc) | w/o best5 | luck p | Holm | maxT | DiD (placebo p) | works |',
         '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for _, r in T[T.trade == tr].iterrows():
        L.append(f'| {r.test} | {SH[r.test]} | {r.dir[0].upper()} | {int(r.n)} | {f(r.avg_net)} | {f(r.excess)} | {int(r.q_pos)}/{int(r.q_with)} | '
                 f'{f(r.net_f14)} ({f(r.exc_f14)}) | {f(r.net_l8)} ({f(r.exc_l8)}) | {f(r.net_wo5)} | {p(r.luck_p)} | {p(r.holm_p)} | '
                 f'{p(r.maxT_p)} | {f(r.DiD)} ({p(r.placebo_p)}) | {"YES" if r.WORKS else "no"} |')
    return '\n'.join(L)
def split(df):
    L = ['| pool | cond | pred | IN n, net | OUT n, net | diff | IN first14 / last8 net | OUT first14 / last8 net | p (2s) | Holm |',
         '|---|---|---|---|---|---|---|---|---|---|']
    for _, r in df.iterrows():
        L.append(f'| {r.pool} | {r.condition} {SH[r.condition]} | {r.pred} | {int(r.n_in)}, {f(r.net_in)} | {int(r.n_out)}, {f(r.net_out)} | '
                 f'{f(r["diff"])} | {f(r.net_in_f14)} / {f(r.net_in_l8)} | {f(r.net_out_f14)} / {f(r.net_out_l8)} | {p(r.perm_p_2s)} | {p(r.holm_p)} |')
    return '\n'.join(L)
open(f'{R}/compact_A.md', 'w').write(main('A') + '\n')
open(f'{R}/compact_B.md', 'w').write(main('B') + '\n')
open(f'{R}/compact_split_lag.md', 'w').write(split(pd.read_csv(f'{R}/split_lag_rule.csv')) + '\n')
w = pd.read_csv(f'{R}/split_winners.csv')
w['pool'] = w.pool.map({'plain winners 392': 'W392', 'RSI>50 winners 232': 'WR232'})
open(f'{R}/compact_split_winners.md', 'w').write(split(w) + '\n')
