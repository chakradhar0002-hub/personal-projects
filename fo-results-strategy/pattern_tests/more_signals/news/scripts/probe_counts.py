#!/usr/bin/env python3
"""Feature-only counts for the pre-registration (reads features and the tradable_B flag only; no outcome).
usage: python3 probe_counts.py OUT SP"""
import sys
import numpy as np
import pandas as pd
OUT, SP = sys.argv[1], sys.argv[2]
r = pd.read_csv(f'{OUT}/work/feat_results.csv')
tb = pd.read_csv(f'{SP}/perf/features/outcomes.csv', usecols=['symbol', 'qn', 'tradable_B'])
r = r.merge(tb, on=['symbol', 'qn'], validate='1:1')
Wm = (r.W == True) & (r.tradable_B == True)
WR = Wm & (r.cut_rsi14 > 50)
LR = (r.in_fo_events == True) & (r.lag21 < -10) & (r.vol_ratio_5_60 >= 1.0)
pl = pd.read_csv(f'{OUT}/work/feat_placeboA.csv.gz')
qd = pd.read_csv(f'{OUT}/work/feat_placeboB.csv.gz')
qd = qd[qd.no_result_k22 == True]
QW = qd.W == True
QWR = QW & (qd.m2_rsi14 > 50)
C = [('LATE RDCHG>7', 'RDCHG > 7'), ('EARLY RDCHG<-7', 'RDCHG < -7'), ('LEADCHG<=-7', 'LEADCHG <= -7'),
     ('LEADCHG>=7', 'LEADCHG >= 7'), ('LEAD<=7', 'LEAD <= 7'), ('NEWSR>=1.5', 'NEWSR >= 1.5'),
     ('NEWSR<=0.5', 'NEWSR <= 0.5'), ('NEWSR<1', 'NEWSR < 1'), ('NEWSR>=1', 'NEWSR >= 1'), ('PR30>=1', 'PR30 >= 1'),
     ('ORDER30>=1', 'ORDER30 >= 1'), ('ACQ30>=1', 'ACQ30 >= 1'), ('CRUP90>=1', 'CRUP90 >= 1'), ('CALLPRE==0', 'CALLPRE == 0'),
     ('CALLPRE>=1', 'CALLPRE >= 1'), ('BIZ_RX>0', 'BIZ_RX > 0'), ('BIZ_RX<0', 'BIZ_RX < 0'),
     ('PROMBUY90>=1', 'PROMBUY90 >= 1'), ('PROMSELL90>=1', 'PROMSELL90 >= 1'), ('PROMBUY30>=1', 'PROMBUY30 >= 1'),
     ('PROMSELL30>=1', 'PROMSELL30 >= 1'), ('HOLDBUY90>=1', 'HOLDBUY90 >= 1'), ('HOLDSELL90>=1', 'HOLDSELL90 >= 1'),
     ('EVENT_K>=1', 'EVENT_K >= 1'), ('ORDER_K>=1', 'ORDER_K >= 1'), ('BUSY_K>=15', 'BUSY_K >= 15')]
print(f'W {Wm.sum()} WR {WR.sum()} lag rule {LR.sum()}; placebo A days {len(pl)}; quiet winners {QW.sum()} '
      f'(RSI>50 {QWR.sum()})')
print(f'{"feature":14s} {"all":>5s} {"%":>5s} {"h1":>4s} {"h2":>4s} {"q":>3s} {"W":>4s} {"WR":>4s} {"LR in":>5s} '
      f'{"plA":>6s} {"qW":>5s} {"qWR":>5s}')
for nm, ex in C:
    m = r.eval(ex).fillna(False)
    pa = pl.eval(ex).fillna(False) if all(c in pl.columns for c in [ex.split()[0]]) else None
    pb = qd.eval(ex).fillna(False) if ex.split()[0] in qd.columns else None
    print(f'{nm:14s} {m.sum():5d} {m.mean() * 100:5.1f} {(m & (r.qn <= 13)).sum():4d} {(m & (r.qn >= 14)).sum():4d} '
          f'{r[m].qn.nunique():3d} {(m & Wm).sum():4d} {(m & WR).sum():4d} {(m & LR).sum():5d} '
          f'{pa.sum() if pa is not None else -1:6d} {(pb & QW).sum() if pb is not None else -1:5d} '
          f'{(pb & QWR).sum() if pb is not None else -1:5d}')
print('BUSY_K distribution of results rows by quarter (80th pct):', r.groupby('qn').BUSY_K.quantile(.8).to_dict())
