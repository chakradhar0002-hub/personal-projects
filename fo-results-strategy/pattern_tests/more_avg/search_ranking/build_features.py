#!/usr/bin/env python3
"""Entry-time features for all in_fo results (NO outcomes are read here).

Writes features_rank.csv: one row per in_fo result (3,280) with F1..F14 of candidates.txt.
events.csv / fa_panel.csv are read with usecols that exclude their forward-return columns (next5, next20, ...).
"""
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.environ.get('LAB_ROOT', os.path.abspath(os.path.join(HERE, '..', '..')))  # scratch data folder
DATA = f'{SP}/sector_lab/data'

ses = pd.read_csv(f'{DATA}/sessions.csv')
ret = pd.read_csv(f'{DATA}/returns.csv', index_col=0)
assert (ret.index == ses.day).all()
SYM = {s: j for j, s in enumerate(ret.columns)}
R = ret.to_numpy(float)
PX = np.cumprod(1.0 + np.nan_to_num(R), axis=0)          # blank daily return = 0 (same as baseline study)

fe = pd.read_csv(f'{SP}/tafa/C_post_results/features.csv')
ev = pd.read_csv(f'{DATA}/events.csv', usecols=['symbol', 'qn', 'sector_index', 'i_react', 'in_fo'])
fa = pd.read_csv(f'{SP}/fa/build/fa_panel.csv', usecols=['symbol', 'qn', 'log_mcap', 'mcap_cr'])

sec_names = sorted(ev.sector_index.dropna().unique().tolist())
ixc = pd.read_csv(f'{DATA}/index_close.csv', index_col=0, usecols=['day', 'Nifty 50'] + sec_names)
assert (ixc.index == ses.day).all()
NIFTY = ixc['Nifty 50'].to_numpy(float)

d = fe[['symbol', 'quarter', 'qn', 'reaction_day', 'i_cut', 'i_react', 'XN', 'cut_rsi14', 'rx_rsi14',
        'rx_vol_ratio_50', 'rx_gap_pct', 'rx_don20_break_up', 'BREAKOUT_VOL', 'rx_close_vs_sma50_pct',
        'rx_close_vs_sma200_pct', 'rq_pat_yoy_pct', 'rq_sales_yoy_pct']].copy()
d = d.merge(ev[['symbol', 'qn', 'sector_index', 'i_react']].rename(columns={'i_react': 'i_react_ev'}),
            on=['symbol', 'qn'], how='left', validate='1:1')
assert (d.i_react == d.i_react_ev).all()
d = d.merge(fa, on=['symbol', 'qn'], how='left', validate='1:1')
assert len(d) == 3280

k = d.i_react.to_numpy(int)
jx = d.symbol.map(SYM).to_numpy(int)
assert (k >= 300).all()
with np.errstate(divide='ignore', invalid='ignore'):
    d['lvol'] = np.log(d.rx_vol_ratio_50.where(d.rx_vol_ratio_50 > 0))
# F8: stock close(k-22)->close(k-1) minus Nifty same window
stk = PX[k - 1, jx] / PX[k - 22, jx] - 1
nif = NIFTY[k - 1] / NIFTY[k - 22] - 1
d['pre21_rel'] = (stk - nif) * 100
# F11: sector index close(k-21)->close(k) minus Nifty same
sec = np.full(len(d), np.nan)
for s_name, g in d.groupby('sector_index'):
    S = ixc[s_name].to_numpy(float)
    kk = g.i_react.to_numpy(int)
    sec[g.index.to_numpy()] = (S[kk] / S[kk - 21] - 1 - (NIFTY[kk] / NIFTY[kk - 21] - 1)) * 100
d['sec21_rel'] = sec
d['rx_don20_break_up'] = d.rx_don20_break_up.astype(float)
d['BREAKOUT_VOL'] = d.BREAKOUT_VOL.astype(float)
d['W'] = d.XN > 4

FEATS = ['cut_rsi14', 'rx_rsi14', 'XN', 'lvol', 'rx_gap_pct', 'rx_don20_break_up', 'BREAKOUT_VOL', 'pre21_rel',
         'rx_close_vs_sma50_pct', 'rx_close_vs_sma200_pct', 'sec21_rel', 'rq_pat_yoy_pct', 'rq_sales_yoy_pct',
         'log_mcap']
out = d[['symbol', 'quarter', 'qn', 'reaction_day', 'i_react', 'sector_index', 'W'] + FEATS]
out.to_csv(f'{HERE}/features_rank.csv', index=False, float_format='%.6g')
w = out[out.W]
print(f'features_rank.csv: {len(out)} results, winners {len(w)}')
print('missing share among winners:')
print(w[FEATS].isna().mean().round(3).to_string())
print(w[FEATS].describe().T.round(2).to_string())
