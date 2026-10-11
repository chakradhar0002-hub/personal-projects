#!/usr/bin/env python3
"""Placebo for A12 BIZ_UP and the post-hoc 'any business update' effect on own ordinary days.
usage: python3 v2_biz_placebo.py SCRATCH WORKDIR"""
import sys
import numpy as np, pandas as pd
SC, W = sys.argv[1:3]
pl = pd.read_csv(f'{W}/feat_placebo.csv.gz')
biz = pd.read_csv(f'{W}/biz_items.csv'); biz = biz[~biz.own_rd]
biz['t'] = pd.to_datetime(biz.an_dt, format='%d-%b-%Y %H:%M:%S')
ses = pd.read_csv(f'{SC}/sector_lab/data/sessions.csv'); sday = pd.to_datetime(ses.day).values
pl['T'] = pd.to_datetime(sday[pl.i.values]) + pd.Timedelta(hours=15)
out = []
for s, g in pl.groupby('symbol'):
    b = biz[biz.symbol == s].sort_values('t')
    n45 = np.zeros(len(g), int); rx = np.full(len(g), np.nan)
    if len(b):
        bt = b.t.values; bs = b.s.values; brx = b.rx.values
        for j, (T, i) in enumerate(zip(g['T'].values, g.i.values)):
            m = (bt >= T - np.timedelta64(45, 'D')) & (bt < T)
            n45[j] = m.sum()
            mm = m & (bs < i)
            if mm.any():
                _, u = np.unique(bs[mm], return_index=True)
                rx[j] = brx[mm][u].sum()
    out.append(pd.DataFrame({'BIZ45': n45, 'BIZ_RX': rx}, index=g.index))
pl = pl.join(pd.concat(out))
pl['qmean'] = pl.groupby('qn_next').fwd3.transform('mean'); pl['exc'] = pl.fwd3 - pl.qmean
f = pd.read_csv(f'{W}/feat_results.csv'); A = f[f.three_day.notna()].copy()
A['exc'] = A.three_day - A.groupby('qn').three_day.transform('mean')
for nm, ra, pa in [('A12 BIZ_RX>0', A.BIZ_RX > 0, pl.BIZ_RX > 0), ('A13 BIZ_RX<0 (long side shown)', A.BIZ_RX < 0, pl.BIZ_RX < 0),
                   ('any BIZ item in 45d', A.BIZ45 > 0, pl.BIZ45 > 0)]:
    wq = A[ra].groupby('qn').size()
    pe = pl[pa].groupby('qn_next').exc.mean().reindex(wq.index)
    pex = (pe * wq).sum() / wq[pe.notna()].sum()
    print(f'{nm}: results n {ra.sum()} excess {A[ra].exc.mean():+.3f}; placebo days {pa.sum()} excess {pex:+.3f}; DiD {A[ra].exc.mean() - pex:+.3f}')
