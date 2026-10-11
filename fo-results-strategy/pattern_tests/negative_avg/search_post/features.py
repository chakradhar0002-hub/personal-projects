#!/usr/bin/env python3
"""FEATURES ONLY (no outcome of any kind) for the post-results "losers keep falling" short search.

One row per F&O result (3,280). Every column is known at (or before) the entry time of the candidates that use it;
see candidates.txt. Reads data read-only, writes features_all.csv into this folder.

The day k+1 follow-through return (FT1, a feature for close-k+1 entries) is ALSO the first day of the close-k trades'
outcome, so it is computed ONLY for discovery rows (qn <= 13); it is NaN for qn >= 14 (holdout sealed). The holdout
evaluator recomputes it at evaluation time with the same definition.
"""
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
DATA = f'{SP}/sector_lab/data'
DISC_MAX = 13

ses = pd.read_csv(f'{DATA}/sessions.csv')
days = ses.day.tolist()
DIX = {d: i for i, d in enumerate(days)}
T = len(days)
ret = pd.read_csv(f'{DATA}/returns.csv', index_col=0)
assert ret.index.tolist() == days
SYM = {s: j for j, s in enumerate(ret.columns)}
R = ret.to_numpy(float)
ixc = pd.read_csv(f'{DATA}/index_close.csv', index_col=0)
assert ixc.index.tolist() == days
NIFTY = ixc['Nifty 50'].to_numpy(float)
nret = np.r_[np.nan, NIFTY[1:] / NIFTY[:-1] - 1]

# ---------------------------------------------------------------- base panel + tafa (TA at k, GOOD / BAD)
p = pd.read_csv(f'{SP}/perf/features/panel.csv')
keep_p = ['symbol', 'qn', 'quarter', 'timing', 'industry', 'sector_index', 'fin_type', 'i_cut', 'i_rd', 'i_p1',
          'i_react', 'lag21', 'vol_ratio_5_60', 'cut_rsi14', 'XN', 'W', 'n_drift_4_B', 'n_pos_drift_4_B',
          'mean_drift_4_B', 'n_drift_all_B', 'mean_drift_all_B', 'vsN_126_B', 'vsN_252_B', 'rank_vsN_252_B',
          'dist_52wh_B']
f = p[keep_p].copy()
t = pd.read_csv(f'{SP}/tafa/C_post_results/features.csv')
tk = ['symbol', 'qn', 'rq_pat_yoy_pct', 'rq_sales_yoy_pct', 'MCHG', 'rx_n_hist', 'rx_rsi14', 'rx_close_vs_sma50_pct',
      'rx_close_vs_sma200_pct', 'rx_don20_break_dn', 'rx_gap_pct', 'rx_vol_ratio_50', 'GOOD', 'E_GOOD', 'BAD',
      'E_BAD', 'E_TA_RX', 'BELOW50', 'BRKDN_VOL', 'XN']
f = f.merge(t[tk].rename(columns={'XN': 'XN_tafa'}), on=['symbol', 'qn'], how='left', validate='1:1')
assert np.allclose(f.XN, f.XN_tafa, equal_nan=True, atol=1e-3)
f = f.drop(columns='XN_tafa')

# ---------------------------------------------------------------- F&O OI features (bhavcopy)
o = pd.read_csv(f'{SP}/more_signals/oi/work/results_features.csv',
                usecols=['symbol', 'qn', 'A_dP5', 'A_dOI5', 'B_dP1', 'B_dOI1', 'B_dP5', 'B_dOI5'])
f = f.merge(o, on=['symbol', 'qn'], how='left', validate='1:1')

# ---------------------------------------------------------------- delivery on day k (file published after close k)
d = pd.read_csv(f'{SP}/more_signals/delivery/feat_results.csv', usecols=['symbol', 'qn', 'DPK', 'DQK'])
f = f.merge(d, on=['symbol', 'qn'], how='left', validate='1:1')

# ---------------------------------------------------------------- day-k candle: close location in the day's range
px = pd.read_csv(f'{SP}/ta/build/adjusted_ohlcv.csv.gz', usecols=['day', 'symbol', 'open', 'high', 'low', 'close'])
px = px[px.symbol.isin(SYM)]
px['i'] = px.day.map(DIX)
px = px.dropna(subset=['i'])
px['i'] = px.i.astype(int)
pk = px.set_index(['symbol', 'i'])
key = list(zip(f.symbol, f.i_react.astype(int)))
cand = pk.reindex(key)
rng = (cand.high - cand.low).to_numpy()
with np.errstate(divide='ignore', invalid='ignore'):
    f['CLV_k'] = np.where(rng > 0, (cand.close.to_numpy() - cand.low.to_numpy()) / rng, np.nan)

# ---------------------------------------------------------------- sector index 21-session return to close k
k = f.i_react.astype(int).to_numpy()
sec = np.full(len(f), np.nan)
for idx, (s_ix, kk) in enumerate(zip(f.sector_index, k)):
    a = ixc[s_ix].to_numpy(float)
    if kk - 21 >= 0 and np.isfinite(a[kk]) and np.isfinite(a[kk - 21]) and a[kk - 21] > 0:
        sec[idx] = (a[kk] / a[kk - 21] - 1) * 100
f['SEC21_k'] = sec

# ---------------------------------------------------------------- day k+1 follow-through (discovery rows only)
j = f.symbol.map(SYM).to_numpy(int)
ft = np.full(len(f), np.nan)
disc = (f.qn <= DISC_MAX).to_numpy()
for idx in np.flatnonzero(disc):
    kk = k[idx]
    if kk + 1 < T and np.isfinite(R[kk + 1, j[idx]]):
        ft[idx] = (R[kk + 1, j[idx]] - nret[kk + 1]) * 100
f['FT1'] = ft          # stock return on k+1 minus Nifty that day, %; NaN for qn >= 14 by design

for c in ['GOOD', 'E_GOOD', 'BAD', 'E_BAD', 'E_TA_RX', 'BELOW50', 'BRKDN_VOL', 'W']:
    f[c] = f[c].fillna(False).astype(bool)
f.to_csv(f'{HERE}/features_all.csv', index=False, float_format='%.6g')
print('features_all.csv', f.shape)
print('NaN share (all rows):')
print(f[['cut_rsi14', 'XN', 'rx_close_vs_sma50_pct', 'rx_close_vs_sma200_pct', 'CLV_k', 'SEC21_k', 'B_dP5', 'B_dOI5',
         'B_dOI1', 'DQK', 'n_drift_4_B', 'vsN_252_B']].isna().mean().round(3).to_string())
