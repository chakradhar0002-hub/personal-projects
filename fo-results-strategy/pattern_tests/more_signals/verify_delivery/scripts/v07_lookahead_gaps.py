#!/usr/bin/env python3
"""Verifier: window gaps, point-in-time rank universe, survivorship of the symbol list, lag-rule date-matched reference.
usage: python3 -P v07_lookahead_gaps.py SCRATCH OUTDIR"""
import sys

import numpy as np
import pandas as pd

SP, OUT = sys.argv[1], sys.argv[2]
DATA = f'{SP}/sector_lab/data'
LOG = open(f'{OUT}/v07_lookahead_gaps.log', 'w')


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.write(s + '\n')


ses = pd.read_csv(f'{DATA}/sessions.csv')
days = ses.day.to_numpy()
ret = pd.read_csv(f'{DATA}/returns.csv', index_col=0)
SY = ret.columns.tolist()
SJ = {s: j for j, s in enumerate(SY)}
R = ret.to_numpy(float)
Mz = np.load(f'{OUT}/own_mats.npz')
DP, DP60 = Mz['DP'], Mz['DP60']
f = pd.read_csv(f'{OUT}/own_feat_stress.csv')
j = f.symbol.map(SJ).to_numpy(int)
e = f.i_cut.to_numpy(int) - 1
k = f.i_react.to_numpy(int)
QN = f.qn.to_numpy(int)
y3 = f.three_day.to_numpy(float)
qmean = pd.Series(y3).groupby(QN).transform('mean').to_numpy()

# 1. gaps inside the feature windows
n60 = np.array([np.isfinite(DP[ee - 59:ee + 1, jj]).sum() for ee, jj in zip(e, j)])
n5 = np.array([np.isfinite(DP[ee - 4:ee + 1, jj]).sum() for ee, jj in zip(e, j)])
t60 = np.array([np.isfinite(R[ee - 59:ee + 1, jj]).sum() for ee, jj in zip(e, j)])
nk = np.array([np.isfinite(DP[kk - 60:kk + 2, jj]).sum() for kk, jj in zip(k, j)])
tk = np.array([np.isfinite(R[kk - 60:kk + 2, jj]).sum() for kk, jj in zip(k, j)])
P('1. delivery values present in the A windows (60 sessions to cutoff-1): rows with < traded days:',
  int((n60 < t60).sum()), 'of', len(f), '; min present', int(n60.min()), '; 5-day window < 5:', int((n5 < 5).sum()))
P('   B window k-60..k+1: rows with fewer delivery values than traded days:', int((nk < tk).sum()))
bad = f.loc[n60 < t60, ['symbol', 'qn']].assign(n60=n60[n60 < t60], traded=t60[n60 < t60])
P(bad.head(15).to_string())
A10 = (f.rank_DP60 > 80).to_numpy()
P('   A10 trades affected:', int((A10 & (n60 < t60)).sum()))

# 2. point-in-time rank universes for A10
#   (a) universe = the PREVIOUS quarter's F&O results list (known before the season starts)
#   (b) universe = every stock with a DP60 value that session (no membership information at all)
U = {q: g.symbol.map(SJ).to_numpy(int) for q, g in f.groupby('qn')}


def rank_with(univ_fn):
    v = np.full(len(f), np.nan)
    for n_, (q, ee, jj) in enumerate(zip(QN, e, j)):
        uni = univ_fn(q)
        vals = DP60[ee, uni]
        vals = vals[np.isfinite(vals)]
        x = DP60[ee, jj]
        if np.isfinite(x) and len(vals) > 20:
            v[n_] = (np.sum(vals < x) + (np.sum(vals == x) + 1) / 2) / len(vals) * 100
    return v


ALL = np.arange(len(SY))
for lab, fn in [('previous quarter list', lambda q: U[max(q - 1, 0)]), ('all stocks with data', lambda q: ALL)]:
    rk = rank_with(fn)
    m = (rk > 80) & np.isfinite(y3)
    ex = (y3 - qmean)[m]
    P(f'2. A10 with rank universe = {lab}: n {m.sum()}, net {(y3[m] - 0.17).mean():+.3f}, excess {ex.mean():+.3f}, '
      f'first14 {ex[QN[m] <= 13].mean():+.3f}, last8 {ex[QN[m] >= 14].mean():+.3f}; same trades as A10: {(m & A10).sum()}')

# 3. symbol list survivorship
P('\n3. symbol list: returns.csv has', len(SY), 'symbols. F&O results per quarter:',
  f.groupby('qn').size().to_dict())
known_exits = ['ZEEL', 'IDEA', 'PVRINOX', 'BATAINDIA', 'GUJGASLTD', 'ABFRL', 'INDIACEM', 'DELTACORP', 'BALRAMCHIN',
               'CANFINHOME', 'LALPATHLAB', 'MGL', 'IGL', 'ATUL', 'GNFC', 'HINDCOPPER', 'IPCALAB', 'METROPOLIS', 'MRF',
               'NAVINFLUOR', 'RAMCOCEM', 'SUNTV', 'TATACOMM', 'WHIRLPOOL', 'AARTIIND', 'ESCORTS', 'GRANULES', 'L&TFH',
               'COROMANDEL', 'CHAMBLFERT', 'DEEPAKNTR', 'ABBOTINDIA', 'BERGEPAINT', 'JKCEMENT', 'LTTS', 'OFSS', 'IBULHSGFIN',
               'SAMMAANCAP', 'RBLBANK', 'PEL', 'PIRAMALENT', 'HDFC', 'MINDTREE', 'SRTRANSFIN', 'CADILAHC', 'TORNTPOWER',
               'MFSL', 'SYNGENE', 'MUTHOOTFIN', 'APOLLOTYRE', 'EXIDEIND', 'BHARATFORG']
P('   present in returns.csv:', [s for s in known_exits if s in SJ])
P('   absent from returns.csv:', [s for s in known_exits if s not in SJ])
LOG.close()
