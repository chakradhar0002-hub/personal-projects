#!/usr/bin/env python3
"""FEATURES ONLY (no outcomes / forward returns) for the 'signal strength' family.

One row per in_fo result (all 22 seasons; feature values for qn >= 14 are allowed - no outcome is touched here).
Every feature is known at the close of the reaction day k (entry), or earlier.

Reads (read-only):
  sector_lab/data/{sessions,returns,index_close,events}.csv
  ta/build/adjusted_ohlcv.csv.gz, ta/build/events_ta.csv
  tafa/C_post_results/features.csv   (XN, cut_rsi14, rx_*, GOOD, rq_* ... ; no outcomes in that file)
Writes: features_signal.csv in this folder.
"""
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.environ.get('LAB_ROOT', os.path.abspath(os.path.join(HERE, '..', '..')))  # scratch data folder
DATA = f'{SP}/sector_lab/data'

ses = pd.read_csv(f'{DATA}/sessions.csv')
days = ses.day.tolist()
DIX = {d: i for i, d in enumerate(days)}
T = len(days)
ret = pd.read_csv(f'{DATA}/returns.csv', index_col=0)
assert ret.index.tolist() == days
SYM = {s: j for j, s in enumerate(ret.columns)}
R = ret.to_numpy(float)
PX = np.cumprod(1.0 + np.nan_to_num(R), axis=0)
ev = pd.read_csv(f'{DATA}/events.csv')
fe = pd.read_csv(f'{SP}/tafa/C_post_results/features.csv')
eta = pd.read_csv(f'{SP}/ta/build/events_ta.csv', usecols=['symbol', 'qn', 'lag_pct', 'stock_21d_pct', 'nifty_21d_pct'])
sec_names = sorted(ev.sector_index.dropna().unique().tolist())
ixc = pd.read_csv(f'{DATA}/index_close.csv', index_col=0, usecols=['day', 'Nifty 50'] + sec_names)
assert ixc.index.tolist() == days

d = fe.merge(ev[['symbol', 'qn', 'sector_index', 'mcap', 'period']], on=['symbol', 'qn'], how='left', validate='1:1')
d = d.merge(eta, on=['symbol', 'qn'], how='left', validate='1:1')
assert len(d) == 3280

# ---------------------------------------------------------------- OHLC on day k (adjusted)
px = pd.read_csv(f'{SP}/ta/build/adjusted_ohlcv.csv.gz', usecols=['day', 'symbol', 'open', 'high', 'low', 'close'])
px = px[px.symbol.isin(set(d.symbol))]
px['i'] = px.day.map(DIX)
px = px[px.i.notna()]
px['i'] = px.i.astype(int)
clv, brk52, hist = {}, {}, {}
for s, g in px.sort_values('i').groupby('symbol'):
    h, l, c = g.high.to_numpy(float), g.low.to_numpy(float), g.close.to_numpy(float)
    hh250_prior = pd.Series(h).rolling(250, min_periods=250).max().shift(1).to_numpy()
    eps = 1e-9 * c
    rg = h - l
    with np.errstate(divide='ignore', invalid='ignore'):
        cl = np.where(rg > eps, (c - l) / rg, np.nan)
    b52 = np.where(np.isnan(hh250_prior), np.nan, (c > hh250_prior + eps).astype(float))
    for ii, a, b in zip(g.i.to_numpy(), cl, b52):
        clv[(s, ii)] = a
        brk52[(s, ii)] = b
keys = list(zip(d.symbol, d.i_react.astype(int)))
d['rx_clv'] = [clv.get(k, np.nan) for k in keys]          # (C-L)/(H-L) on day k
d['rx_brk52'] = [brk52.get(k, np.nan) for k in keys]      # C_k > max high of prior 250 traded sessions

# ---------------------------------------------------------------- stock vs own sector index, 21 sessions to cutoff
ic = d.i_cut.astype(int).to_numpy()
jx = d.symbol.map(SYM).to_numpy(int)
stk21 = (PX[ic, jx] / PX[ic - 21, jx] - 1) * 100
sec21 = np.array([(ixc[s].iat[i] / ixc[s].iat[i - 21] - 1) * 100 if isinstance(s, str) else np.nan
                  for s, i in zip(d.sector_index, ic)])
d['stk21_cut'] = stk21
d['sec21_cut'] = sec21
d['secrel21'] = stk21 - sec21
# sanity: our stock 21-session return equals events_ta stock_21d_pct
m = d.stock_21d_pct.notna()
print('stock 21d check, max abs diff vs events_ta:', np.nanmax(np.abs(d.loc[m, 'stk21_cut'] - d.loc[m, 'stock_21d_pct'])))

keep = ['symbol', 'quarter', 'qn', 'period', 'timing', 'reaction_day', 'i_cut', 'i_react', 'XN', 'cut_rsi14',
        'rx_rsi14', 'rx_vol_ratio_50', 'rx_gap_pct', 'rx_low_vs_prevclose_pct', 'rx_don20_break_up', 'rx_clv',
        'rx_brk52', 'lag_pct', 'stk21_cut', 'sec21_cut', 'secrel21', 'sector_index', 'GOOD', 'rq_pat_yoy_pct',
        'rq_sales_yoy_pct', 'MCHG', 'mcap', 'E_TA_RX', 'GAPHOLD', 'BRK20']
d[keep].to_csv(f'{HERE}/features_signal.csv', index=False, float_format='%.6g')
W = (d.XN > 4) & (d.cut_rsi14 > 50)
print('rows', len(d), '| baseline-signal rows (all qn, features only):', int(W.sum()),
      '| discovery:', int((W & (d.qn <= 13)).sum()))
print('feature coverage among baseline signals (count non-null):')
print(d.loc[W, ['rx_vol_ratio_50', 'rx_clv', 'rx_brk52', 'lag_pct', 'secrel21', 'rq_pat_yoy_pct',
                'rq_sales_yoy_pct', 'mcap']].notna().sum().to_string())
