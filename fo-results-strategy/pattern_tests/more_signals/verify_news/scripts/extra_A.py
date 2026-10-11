#!/usr/bin/env python3
"""Extra stress for A08: cluster bootstrap by symbol / by entry date, auto sector split, contributions, results-date
known at the cutoff, EARLY-flag counts by quarter (COVID contamination check), placebo with summed returns.
usage: python3 -P extra_A.py SP VDIR NEWSDIR"""
import sys

import numpy as np
import pandas as pd

SP, V, NW = sys.argv[1:4]
D = f'{SP}/sector_lab/data'
LOG = open(f'{V}/extra_A.log', 'w')


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.write(s + '\n')


A = pd.read_csv(f'{V}/work/my_A.csv')
f = pd.read_csv(f'{V}/work/my_feat.csv')
pan = pd.read_csv(f'{SP}/perf/features/panel.csv', usecols=['symbol', 'qn', 'industry'])
A = A.merge(pan, on=['symbol', 'qn']).merge(f[['symbol', 'qn', 'pr_norm', 'rdchg', 'rdchg_ok', 'rd', 'results_time',
                                                'timing']], on=['symbol', 'qn'])
pr = A.pr30 >= 1
rng = np.random.default_rng(11)
NB = int(sys.argv[4]) if len(sys.argv) > 4 else 4000

# cluster bootstrap by symbol of (mean excess of PR) and (PR minus no-PR difference)
syms = A.symbol.unique()
G = {s: g for s, g in A.groupby('symbol')}
b1, b2 = [], []
for _ in range(NB):
    pick = rng.choice(syms, len(syms), replace=True)
    d = pd.concat([G[s] for s in pick])
    m = d.pr30 >= 1
    b1.append(d.exc[m].mean())
    b2.append(d.exc[m].mean() - d.exc[~m].mean())
b1, b2 = np.array(b1), np.array(b2)
P(f'symbol-cluster bootstrap: A08 excess {A.exc[pr].mean():+.3f}, 90% CI {np.percentile(b1, 5):+.3f} .. '
  f'{np.percentile(b1, 95):+.3f}, P(<=0) {np.mean(b1 <= 0):.4f}; PR-noPR {A.exc[pr].mean() - A.exc[~pr].mean():+.3f}, '
  f'90% CI {np.percentile(b2, 5):+.3f} .. {np.percentile(b2, 95):+.3f}, P(<=0) {np.mean(b2 <= 0):.4f}')
# cluster bootstrap by entry date (i_cut)
dates = A.i_cut.unique()
GD = {s: g for s, g in A.groupby('i_cut')}
b3 = []
for _ in range(NB):
    pick = rng.choice(dates, len(dates), replace=True)
    d = pd.concat([GD[s] for s in pick])
    b3.append(d.exc[d.pr30 >= 1].mean())
b3 = np.array(b3)
P(f'entry-date cluster bootstrap: 90% CI {np.percentile(b3, 5):+.3f} .. {np.percentile(b3, 95):+.3f}, '
  f'P(<=0) {np.mean(b3 <= 0):.4f}')
# same-day excess one-sided permutation within entry date
y = A.exc_date.to_numpy()
ok = np.isfinite(y)
P(f'same-entry-day excess (vs other results with the same cutoff): PR {np.nanmean(y[pr & ok]):+.3f} (n {int((pr & ok).sum())}), '
  f'no-PR {np.nanmean(y[~pr & ok]):+.3f}')

# autos
auto = A.industry.fillna('').str.contains('Automobile')
P('\nautomobile results: PR vs no PR')
P(A[auto].groupby(A.pr30[auto] >= 1).agg(n=('exc', 'size'), exc=('exc', 'mean')).round(3).to_string())
P('non-auto results: PR vs no PR')
P(A[~auto].groupby(A.pr30[~auto] >= 1).agg(n=('exc', 'size'), exc=('exc', 'mean')).round(3).to_string())
# within-stock non-auto
ws = A[~auto].groupby('symbol').filter(lambda g: (g.pr30 >= 1).any() and (g.pr30 == 0).any())
ws = ws.assign(dm=ws.exc - ws.groupby('symbol').exc.transform('mean'))
P(f'non-auto within-stock: PR {ws.dm[ws.pr30 >= 1].mean():+.3f} (n {(ws.pr30 >= 1).sum()}), '
  f'no-PR {ws.dm[ws.pr30 == 0].mean():+.3f}, stocks {ws.symbol.nunique()}')
# contributions by symbol (sum of excess)
c = A[pr].groupby('symbol').exc.agg(['size', 'sum', 'mean']).sort_values('sum', ascending=False)
P(f'\nA08 excess sum {A.exc[pr].sum():+.1f}; top 10 symbols contribute {c["sum"].head(10).sum():+.1f}; '
  f'bottom 10 {c["sum"].tail(10).sum():+.1f}')
P(c.head(10).round(2).to_string())
pos = c['sum'] > 0
P(f'symbols with positive excess sum: {pos.sum()} of {len(c)}')

# EARLY counts by quarter across all F&O results
e = f[f.rdchg_ok]
P('\nEARLY / LATE share by quarter (all F&O results with RDCHG):')
P(e.groupby('qn').agg(n=('rdchg', 'size'), early=('rdchg', lambda v: (v < -7).mean() * 100),
                      late=('rdchg', lambda v: (v > 7).mean() * 100), med=('rdchg', 'median')).round(1).T.to_string())

# results date known before the cutoff? board-meeting intimation broadcast vs cutoff decision time
bm = pd.read_csv(f'{NW}/downloads/board_meetings.csv')
bm['bd'] = pd.to_datetime(bm.bm_date, format='%d-%b-%Y', errors='coerce')
bm['ts'] = pd.to_datetime(bm.bm_timestamp, format='%d-%b-%Y %H:%M:%S', errors='coerce')
ses = pd.read_csv(f'{D}/sessions.csv')
SD = pd.to_datetime(ses.day)
A['Tdec'] = SD.iloc[A.i_cut.to_numpy(int)].to_numpy() + pd.Timedelta(hours=15)
A['rd'] = pd.to_datetime(A.rd)
first = []
BM = {s: g for s, g in bm.groupby('symbol')}
for s, rd in zip(A.symbol, A.rd):
    g = BM.get(s)
    if g is None:
        first.append(pd.NaT)
        continue
    m = (g.bd - rd).dt.days.between(-2, 1)
    first.append(g.ts[m].min() if m.any() else pd.NaT)
A['bm_first'] = first
A['known'] = A.bm_first < A.Tdec
P(f'\nresults date intimated before the cutoff decision: all {A.known.mean() * 100:.1f}%, A08 {A.known[pr].mean() * 100:.1f}%; '
  f'intimation after T: all {(A.bm_first >= A.Tdec).sum()}, A08 {(A.bm_first[pr] >= A.Tdec[pr]).sum()}; no match: all '
  f'{A.bm_first.isna().sum()}, A08 {A.bm_first[pr].isna().sum()}')
k = A.known
P(f'A08 restricted to results date known at T: n {int((pr & k).sum())}, excess {A.exc[pr & k].mean():+.3f}, '
  f'net {A.three_day[pr & k].mean() - 0.17:+.3f}')

# placebo with summed 3-day returns (three_day convention = sum of 3 daily returns)
pl = pd.read_csv(f'{V}/work/my_placeboA.csv.gz')
ret = pd.read_csv(f'{D}/returns.csv', index_col=0)
RC = {s: j for j, s in enumerate(ret.columns)}
R = ret.to_numpy(float)
pl['ys'] = [R[i + 1:i + 4, RC[s]].sum() * 100 for s, i in zip(pl.symbol, pl.i)]
pl['exs'] = pl.ys - pl.groupby('qn').ys.transform('mean')
w = A[pr].qn.value_counts()
pe = pl[pl.pr30 >= 1].groupby('qn').exs.mean()
pexc = (pe.reindex(w.index) * w).sum() / w.sum()
P(f'\nplacebo (summed returns): PR days excess {pexc:+.4f}; DiD {A.exc[pr].mean() - pexc:+.3f}; PR-noPR placebo '
  f'{pl.exs[pl.pr30 >= 1].mean() - pl.exs[pl.pr30 == 0].mean():+.4f}')
# placebo restricted to 'habitual issuer gone quiet' on ordinary days
P(f'placebo days n {len(pl)}, symbols {pl.symbol.nunique()}')
LOG.close()
