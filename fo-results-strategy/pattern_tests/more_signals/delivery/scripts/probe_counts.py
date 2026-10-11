#!/usr/bin/env python3
"""Feature-only counts before the pre-registration (no outcome column is read; from outcomes.csv only the
tradability flag tradable_B). usage: python3 probe_counts.py OUT SP"""
import sys

import numpy as np
import pandas as pd

OUT, SP = sys.argv[1], sys.argv[2]
LOG = open(f'{OUT}/probe_counts.log', 'w')


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    LOG.write(s + '\n')


r = pd.read_csv(f'{OUT}/feat_results.csv')
tb = pd.read_csv(f'{SP}/perf/features/outcomes.csv', usecols=['symbol', 'qn', 'tradable_B'])
r = r.merge(tb, on=['symbol', 'qn'], validate='1:1')
P('A features at e = i_cut-1 (all 3,280 F&O results)')
for c in ['ACC', 'DQR', 'DPL', 'DQL', 'DP60', 'PR5']:
    s = r[c]
    P(f'  {c:5s} n={s.notna().sum()} p10 {s.quantile(.1):.2f} p20 {s.quantile(.2):.2f} median {s.median():.2f} '
      f'p80 {s.quantile(.8):.2f} p90 {s.quantile(.9):.2f}')
cand = {
    'A01 ACC>0': r.ACC > 0, 'A02 rank_ACC>80': r.rank_ACC > 80, 'A03 rank_ACC<=20': r.rank_ACC <= 20,
    'DQR>=1.5': r.DQR >= 1.5, 'DQR>=1.25': r.DQR >= 1.25, 'DQR>=1.0': r.DQR >= 1.0, 'rank_DQR>80': r.rank_DQR > 80,
    'rank_DPL>80': r.rank_DPL > 80, 'DPL>0': r.DPL > 0,
    'PR5<0 & ACC>0': (r.PR5 < 0) & (r.ACC > 0), 'PR5>0 & ACC>0': (r.PR5 > 0) & (r.ACC > 0),
    'PR5>0 & ACC<0': (r.PR5 > 0) & (r.ACC < 0), 'rank_DP60>80': r.rank_DP60 > 80, 'rank_DP60<=20': r.rank_DP60 <= 20,
}
for k, m in cand.items():
    g = r[m]
    P(f'  {k:18s} n={m.sum():5d}  first14 {int((g.qn <= 13).sum()):4d} last8 {int((g.qn >= 14).sum()):4d} '
      f'quarters {g.qn.nunique()}')
LRm = (r.in_fo_events == True) & (r.lag21 < -10) & (r.vol_ratio_5_60 >= 1.0)
L = r[LRm]
P(f'\nLAG RULE trades {LRm.sum()} (features: ACC {L.ACC.notna().sum()}, DQR {L.DQR.notna().sum()})')
for k, m in {'ACC>0': L.ACC > 0, 'DQR>=1.0': L.DQR >= 1.0, 'DQR>=1.5': L.DQR >= 1.5, 'DPL>0': L.DPL > 0,
             'rank_ACC>80': L.rank_ACC > 80, 'PR5<0&ACC>0': (L.PR5 < 0) & (L.ACC > 0),
             'rank_DP60>50': L.rank_DP60 > 50, 'DQR>=median85': L.DQR >= L.DQR.median()}.items():
    P(f'  {k:16s} IN {m.sum():3d}  OUT (ACC known) {(~m & L.ACC.notna()).sum():3d}')
P(f'  median DQR within the 85: {L.DQR.median():.3f}; vol_ratio median {L.vol_ratio_5_60.median():.3f}')
lag = (r.in_fo_events == True) & (r.lag21 < -10)
P(f'  lag<-10 alone {lag.sum()}; lag & DQR>=1.0 {(lag & (r.DQR >= 1.0)).sum()} (overlap with 85: '
  f'{(lag & (r.DQR >= 1.0) & LRm).sum()}); lag & ACC>0 {(lag & (r.ACC > 0)).sum()} (overlap {(lag & (r.ACC > 0) & LRm).sum()})')

P('\nB pools (tradable_B)')
d = r[r.tradable_B == True]
W = d.W == True
WR = W & (d.cut_rsi14 > 50)
P(f'  W {W.sum()}  WR {WR.sum()}')
for c in ['ACC_pre', 'DQR_pre', 'DPK', 'DQK', 'DPK1']:
    for lab, m in (('W', W), ('WR', WR), ('all', np.ones(len(d), bool))):
        s = d.loc[m, c]
        P(f'  {c:7s} {lab:3s} n={s.notna().sum():4d} p20 {s.quantile(.2):.2f} median {s.median():.2f} '
          f'p80 {s.quantile(.8):.2f}  >0: {(s > 0).sum()}  >=2: {(s >= 2).sum()}  >=3: {(s >= 3).sum()}')
for lab, m in (('W', W), ('WR', WR)):
    g = d[m]
    for k, mm in {'ACC_pre>0': g.ACC_pre > 0, 'DPK>0': g.DPK > 0, 'DPK1>0': g.DPK1 > 0, 'DQK>=2': g.DQK >= 2,
                  'DQK>=3': g.DQK >= 3, 'DPK>0&DPK1>0': (g.DPK > 0) & (g.DPK1 > 0)}.items():
        P(f'  {lab:3s} {k:14s} IN {mm.sum():4d} (first14 {int((g.qn[mm] <= 13).sum())}, last8 '
          f'{int((g.qn[mm] >= 14).sum())})')
q = pd.read_csv(f'{OUT}/feat_placeboB.csv.gz')
qw = q[(q.W == True) & q.no_result_k22]
P(f'\nquiet winners (no result in [k-10,k+22]) {len(qw)}; RSI {int((qw.m2_rsi14 > 50).sum())}')
for k, mm in {'ACC_pre>0': qw.ACC_pre > 0, 'DPK>0': qw.DPK > 0, 'DPK1>0': qw.DPK1 > 0, 'DQK>=2': qw.DQK >= 2,
              'DQK>=3': qw.DQK >= 3}.items():
    P(f'  quiet W {k:12s} IN {mm.sum():5d} of {qw[k.split(">")[0]].notna().sum()}')
pa = pd.read_csv(f'{OUT}/feat_placeboA.csv.gz')
P(f'\nplacebo A days {len(pa)}; ACC>0 {(pa.ACC > 0).sum()}; rank_ACC>80 {(pa.rank_ACC > 80).sum()}; '
  f'DQR>=1.5 {(pa.DQR >= 1.5).sum()}; PR5<0&ACC>0 {((pa.PR5 < 0) & (pa.ACC > 0)).sum()}')
LOG.close()
