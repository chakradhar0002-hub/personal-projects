#!/usr/bin/env python3
"""ADDED AFTER the first run (descriptive; cannot change any verdict).
1. Independent re-computation of features for random rows straight from downloads/delivery_eq.csv (spot check).
2. Re-computation of headline numbers from the trades files.
3. W/WR DQK_HI: is it just the size of the results jump? (XN-tercile control, correlation DQK vs XN)
4. RA1 vs the lag rule: the trades that differ.
usage: python3 addendum.py OUT SP"""
import sys

import numpy as np
import pandas as pd

OUT, SP = sys.argv[1], sys.argv[2]
DATA = f'{SP}/sector_lab/data'
LOG = open(f'{OUT}/addendum.log', 'w')


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    LOG.write(s + '\n')


P('ADDED AFTER the first run - descriptive only, cannot change a verdict')
days = pd.read_csv(f'{DATA}/sessions.csv').day.tolist()
fr = pd.read_csv(f'{OUT}/feat_results.csv')
dl = pd.read_csv(f'{OUT}/downloads/delivery_eq.csv')
adj = pd.read_csv(f'{SP}/ta/build/adjusted_ohlcv.csv.gz', usecols=['day', 'symbol', 'volume_factor'])
REN = {'LTM': ['LTI', 'LTIM'], 'TMPV': ['TATAMOTORS'], 'ETERNAL': ['ZOMATO'], 'GMRAIRPORT': ['GMRINFRA'],
       'GVT&D': ['GET&D'], 'UNITDSPR': ['MCDOWELL-N'], 'LTF': ['L&TFH'], 'ADANIENSOL': ['ADANITRANS'],
       '360ONE': ['IIFLWAM'], 'SHRIRAMFIN': ['SRTRANSFIN'], 'UNOMINDA': ['MINDAIND'], 'MOTHERSON': ['MOTHERSUMI'],
       'ZYDUSLIFE': ['CADILAHC'], 'ANGELONE': ['ANGELBRKG'], 'INDUSTOWER': ['INFRATEL'], 'COFORGE': ['NIITTECH']}


def series(sym, i0, i1):
    """delivery %, adjusted delivery qty on sessions i0..i1 (NaN if no row)."""
    names = [sym] + REN.get(sym, [])
    dd = days[i0:i1 + 1]
    g = dl[dl.symbol.isin(names) & dl.day.isin(dd)].drop_duplicates('day', keep='last').set_index('day')
    a = adj[(adj.symbol == sym) & adj.day.isin(dd)].set_index('day').volume_factor
    dp = g.deliv_per.reindex(dd).to_numpy(float)
    dq = (g.deliv_qty.reindex(dd) * a.reindex(dd)).to_numpy(float)
    return dp, dq


rng = np.random.default_rng(5)
mx = 0.0
for r in fr.iloc[rng.choice(len(fr), 12, replace=False)].itertuples():
    e = r.i_cut - 1
    dp, dq = series(r.symbol, e - 59, e)
    acc = np.nanmean(dp[-5:]) - np.nanmean(dp)
    dqr = np.nanmean(dq[-5:]) / np.nanmean(dq)
    k = r.i_react
    dpk_, dqk_ = series(r.symbol, k - 60, k + 1)
    dpk = dpk_[60] - np.nanmean(dpk_[:60])
    dqk = dqk_[60] / np.nanmean(dqk_[:60])
    dpk1 = dpk_[61] - np.nanmean(dpk_[:60])
    diffs = [abs(acc - r.ACC), abs(dqr - r.DQR) / max(1e-9, abs(r.DQR)), abs(dpk - r.DPK), abs(dqk - r.DQK) / r.DQK,
             abs(dpk1 - r.DPK1)]
    mx = max(mx, max(diffs))
    P(f'  {r.symbol:12s} qn {r.qn:2d}: ACC {acc:+.3f} vs {r.ACC:+.3f}; DQR {dqr:.4f} vs {r.DQR:.4f}; DPK {dpk:+.3f} vs '
      f'{r.DPK:+.3f}; DQK {dqk:.4f} vs {r.DQK:.4f}; DPK1 {dpk1:+.3f} vs {r.DPK1:+.3f}')
P(f'1. spot check of 12 random results rows from the raw parsed file: max abs/rel difference {mx:.2e}')

out = pd.read_csv(f'{SP}/perf/features/outcomes.csv', usecols=['symbol', 'qn', 'three_day'])
ta = pd.read_csv(f'{OUT}/trades_A.csv')
tb = pd.read_csv(f'{OUT}/trades_B.csv')
for t in ['A10', 'A06', 'RA1', 'LAGRULE']:
    g = ta[ta.test == t].merge(out, on=['symbol', 'qn'], suffixes=('', '_o'))
    P(f'2. {t}: n {len(g)} mean three_day (outcomes.csv) {g.three_day_o.mean():+.3f} (net {g.three_day_o.mean() - 0.17:+.3f})')
for t in ['W_DQK_HI', 'WR_DQK_HI']:
    g = tb[tb.test == t]
    P(f'2. {t}: n {len(g)} mean vsN_net {g.vsN_net.mean():+.3f}, mean gain {g.d_par.mean():+.3f}')

# 3. DQK vs the size of the jump
fr2 = fr.merge(pd.read_csv(f'{SP}/perf/features/outcomes.csv', usecols=['symbol', 'qn', 'tradable_B']),
               on=['symbol', 'qn'])
W = fr2[(fr2.W == True) & (fr2.tradable_B == True)]
P(f'3. winners: Spearman corr(DQK, XN) {W.DQK.corr(W.XN, method="spearman"):+.3f}; median XN DQK>=3 '
  f'{W.XN[W.DQK >= 3].median():.2f} vs DQK<3 {W.XN[W.DQK < 3].median():.2f}; corr(DQK, vol_ratio_5_60 at cutoff) '
  f'{W.DQK.corr(W.vol_ratio_5_60, method="spearman"):+.3f}')
for t in ['W_DQK_HI', 'WR_DQK_HI']:
    g = tb[tb.test == t].merge(W[['symbol', 'qn', 'XN']], on=['symbol', 'qn'], suffixes=('', '_w'))
    lo = tb[tb.test == t.replace('_HI', '_LO')]
    par = pd.concat([g[['symbol', 'qn', 'XN', 'vsN_net']], lo[['symbol', 'qn', 'XN', 'vsN_net']]])
    par['hi'] = par.symbol.isin(g.symbol) & par.set_index(['symbol', 'qn']).index.isin(g.set_index(['symbol', 'qn']).index)
    par['terc'] = pd.qcut(par.XN, 3, labels=False)
    par['cell'] = par.qn * 10 + par.terc
    cm = par.groupby('cell').vsN_net.transform('mean')
    gain = (par.vsN_net - cm)[par.hi]
    P(f'3. {t}: gain within quarter x XN tercile {gain.mean():+.3f} (n {par.hi.sum()}); first14 '
      f'{gain[par.qn[par.hi] <= 13].mean():+.3f}, last8 {gain[par.qn[par.hi] >= 14].mean():+.3f}; '
      f'by XN tercile (pooled, HI minus LO): ' + ', '.join(
          f'T{int(k)} {par.vsN_net[par.hi & (par.terc == k)].mean() - par.vsN_net[~par.hi & (par.terc == k)].mean():+.2f}'
          f' (n {int((par.hi & (par.terc == k)).sum())}/{int((~par.hi & (par.terc == k)).sum())})' for k in range(3)))
    srt = g.sort_values('vsN_net', ascending=False)
    P(f'   best 5 trades: ' + '; '.join(f'{r.symbol} {r.results_for[12:]} {r.vsN_net:+.1f}' for r in srt.head(5).itertuples()))

# 4. RA1 vs the lag rule
r1 = ta[ta.test == 'RA1'].set_index(['symbol', 'qn'])
lr = ta[ta.test == 'LAGRULE'].set_index(['symbol', 'qn'])
only_r1 = r1.loc[~r1.index.isin(lr.index)]
only_lr = lr.loc[~lr.index.isin(r1.index)]
both = r1.loc[r1.index.isin(lr.index)]
P(f'4. RA1 (lag & delivery qty ratio >= 1) vs lag rule (lag & volume ratio >= 1): shared {len(both)} avg '
  f'{both.three_day.mean():+.2f}; only RA1 {len(only_r1)} avg {only_r1.three_day.mean():+.2f}; only lag rule '
  f'{len(only_lr)} avg {only_lr.three_day.mean():+.2f}')
P(f'   union {len(both) + len(only_r1) + len(only_lr)} avg '
  f'{pd.concat([both.three_day, only_r1.three_day, only_lr.three_day]).mean():+.2f}')
LOG.close()
