#!/usr/bin/env python3
"""FAMILY 'ranking model for falls' - point-in-time feature matrices. NO outcome of any trade is read here.

Writes (this folder):
  features_A.csv : decision at the CUTOFF close (session i_cut) - trade A (3-day window, i_cut close -> i_p1 close)
  features_B.csv : decision at the REACTION close k (session i_react) - trade B (20 sessions, k close -> k+20 close)
  feature_lists.txt : the exact model feature columns for A and B
Rows: all 3,280 F&O results (qn 0..21). Features for qn >= 14 are allowed by the protocol; outcomes are not touched.

Point-in-time rules used:
  * prices / TA known at the close of the decision session (entry at that close).
  * F&O bhavcopy and delivery files for session t are published after t's close -> for a decision at the close of d only
    files up to d-1 are used: trade A uses OI features A1_* (session i_cut-1) and delivery ACC..PR5 (sessions <= i_cut-1);
    trade B uses OI features A_* (session i_cut <= k-2) and delivery ACC_pre / DQR_pre (sessions <= k-1).
  * news: counts in windows ending at the cutoff (as built by more_signals/news). Results-date-change and board-meeting
    lead features (RDCHG, LEAD, LEADCHG) are left out (intimation timing vs the cutoff not guaranteed).
  * fundamentals: fa_panel point-in-time filings (published before the cutoff); reported-quarter numbers (rq_*, GOOD/BAD)
    only for trade B (published by the results, before the reaction close).
  * XN / W and any *_B column only for trade B.
"""
import os
import numpy as np
import pandas as pd

SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = os.path.dirname(os.path.abspath(__file__))
K = ['symbol', 'qn']

FORBIDDEN = {'three_day', 'three_day_net', 'd1', 'd2', 'd3', 'take_profit', 'next5', 'next20', 'next20_vs_nifty',
             'ret_dm1', 'ret_rd', 'ret_dp1', 'tp3', 'excess_nifty_3d', 'move', 'nifty_react', 'react_excess_nifty',
             'raw_H5', 'raw_H10', 'raw_H20', 'nifty_H5', 'nifty_H10', 'nifty_H20', 'vsN_H20', 'vsN_net_H20',
             'tradable_B', 'gap', 'sector_3d', 'nifty_3d', 'excess_nifty', 'excess_sector'}

pan = pd.read_csv(f'{SP}/perf/features/panel.csv')
assert len(pan) == 3280 and not FORBIDDEN & set(pan.columns)

ta_cols = ['rsi2', 'stoch_k14', 'willr14', 'cci20', 'mfi14', 'bb_pctb', 'bb_width_pct', 'macd_pct', 'macd_hist_pct',
           'close_vs_sma20_pct', 'close_vs_sma50_pct', 'close_vs_sma200_pct', 'sma50_vs_sma200_pct', 'adx14',
           'plus_di14', 'minus_di14', 'atr14_pct', 'gap_pct', 'dist_52w_low_pct', 'dist_20d_high_pct',
           'dist_20d_low_pct', 'don20_pos', 'obv_slope20', 'price_slope20_pct', 'ret_5d_pct']
ta = pd.read_csv(f'{SP}/ta/build/events_ta.csv', usecols=K + ta_cols)

fa_cut = ['log_mcap', 'pe', 'earnings_yield_pct', 'pb', 'roe_pct', 'debt_equity', 'ps', 'pe_vs_own3y_pct',
          'pe_vs_peers_pct', 'ttm_pat_yoy_pct', 'ttm_sales_yoy_pct', 'l1_sales_yoy_pct', 'l1_pat_yoy_pct',
          'l1_ebitda_margin_chg_yoy_pp', 'pat_up_yoy_4q', 'sales_up_yoy_4q', 'loss_any_4q', 'piotroski_frac',
          'pat_yoy_std8_pct', 'days_since_dividend']
fa_rq = ['rq_sales_yoy_pct', 'rq_sales_qoq_pct', 'rq_ebitda_yoy_pct', 'rq_pat_yoy_pct', 'rq_pat_qoq_pct',
         'rq_ebitda_margin_chg_yoy_pp', 'rq_net_margin_chg_yoy_pp', 'rq_pat_surprise_vs_trend_pp',
         'rq_sales_surprise_vs_trend_pp', 'rq_pat_yoy_accel_pp']
fa = pd.read_csv(f'{SP}/fa/build/fa_panel.csv', usecols=K + fa_cut + fa_rq)
for c in ['pat_up_yoy_4q', 'sales_up_yoy_4q', 'loss_any_4q']:
    fa[c] = pd.to_numeric(fa[c].map({True: 1, False: 0, 'True': 1, 'False': 0}).fillna(fa[c]), errors='coerce')

oi_core = ['dOI1', 'dOI5', 'dOI10', 'dP1', 'dP5', 'dP10', 'OI20', 'BASIS', 'BASISDEV', 'PCR', 'dPCR5', 'IV', 'IVREL',
           'IVSPREAD', 'dCIV20', 'dPIV20']
oi = pd.read_csv(f'{SP}/more_signals/oi/work/results_features.csv',
                 usecols=K + ['A1_' + c for c in oi_core] + ['A_' + c for c in oi_core])

dl = pd.read_csv(f'{SP}/more_signals/delivery/feat_results.csv',
                 usecols=K + ['ACC', 'DQR', 'DPL', 'DQL', 'DP60', 'PR5', 'ACC_pre', 'DQR_pre'])
news_cols = ['NEWS30', 'NEWSR', 'PR30', 'ORDER30', 'ACQ30', 'CRUP90', 'CRDN90', 'BIZ_N45', 'PROMBUY90', 'PROMSELL90',
             'HOLDBUY90', 'HOLDSELL90', 'CALLPRE']
nw = pd.read_csv(f'{SP}/more_signals/news/work/feat_results.csv', usecols=K + news_cols)

tf_cols = ['MCHG', 'rx_rsi14', 'rx_close_vs_sma50_pct', 'rx_close_vs_sma200_pct', 'rx_don20_break_up',
           'rx_don20_break_dn', 'rx_gap_pct', 'rx_low_vs_prevclose_pct', 'rx_vol_ratio_50', 'GOOD', 'BAD', 'Q_HI',
           'Q_LO', 'CHEAP', 'EXP']
tf = pd.read_csv(f'{SP}/tafa/C_post_results/features.csv', usecols=K + tf_cols)
for c in ['GOOD', 'BAD', 'Q_HI', 'Q_LO', 'CHEAP', 'EXP']:
    tf[c] = tf[c].astype(str).map({'True': 1.0, 'False': 0.0})

base = pan.copy()
for d in (ta, fa, oi, dl, nw, tf):
    n0 = len(base)
    base = base.merge(d, on=K, how='left', validate='1:1')
    assert len(base) == n0
assert not FORBIDDEN & set(base.columns)

# categorical dummies (static)
base['tm_after'] = (base.timing == 'After close').astype(float)
base['tm_during'] = (base.timing == 'During market').astype(float)
base['ft_bank'] = (base.fin_type == 'Bank').astype(float)
base['ft_nbfc'] = (base.fin_type == 'NBFC / financial').astype(float)
base['prev1_winner_A'] = base.prev1_winner_A.astype(float)
base['prev1_winner_B'] = base.prev1_winner_B.astype(float)

trkA = ['n_prev_A', 'prev1_three_day_A', 'prev1_xn_A', 'prev1_drift20_A', 'prev1_winner_A', 'n_pos_three_day_4_A',
        'mean_three_day_4_A', 'n_winner_4_A', 'mean_xn_4_A', 'mean_abs_xn_4_A', 'n_pos_drift_4_A', 'mean_drift_4_A',
        'mean_three_day_all_A', 'mean_xn_all_A', 'mean_drift_all_A']
ppA = ['vsN_21_A', 'vsN_63_A', 'vsN_126_A', 'vsN_252_A', 'vsSec_63_A', 'vsSec_252_A', 'rank_vsN_63_A',
       'rank_vsN_126_A', 'rank_vsN_252_A', 'dist_52wh_A']
static = ['tm_after', 'tm_during', 'ft_bank', 'ft_nbfc']

FA_ = (['lag21', 'vol_ratio_5_60', 'cut_rsi14'] + trkA + ppA + ta_cols + fa_cut + ['A1_' + c for c in oi_core]
       + ['ACC', 'DQR', 'DPL', 'DQL', 'DP60', 'PR5'] + news_cols + static)
FB_ = (['lag21', 'vol_ratio_5_60', 'cut_rsi14', 'XN', 'W'] + [c.replace('_A', '_B') for c in trkA]
       + [c.replace('_A', '_B') for c in ppA] + ta_cols + fa_cut + fa_rq + tf_cols + ['A_' + c for c in oi_core]
       + ['ACC_pre', 'DQR_pre'] + news_cols + static)
base['W'] = base.W.astype(float)
keys = ['symbol', 'qn', 'quarter', 'i_cut', 'i_rd', 'i_p1', 'i_react']
A = base[keys + FA_].copy()
B = base[keys + FB_].copy()
for X, F in ((A, FA_), (B, FB_)):
    for c in F:
        X[c] = pd.to_numeric(X[c], errors='coerce').astype(float)
        X.loc[~np.isfinite(X[c]), c] = np.nan
A.to_csv(f'{OUT}/features_A.csv', index=False, float_format='%.6g')
B.to_csv(f'{OUT}/features_B.csv', index=False, float_format='%.6g')
with open(f'{OUT}/feature_lists.txt', 'w') as fh:
    fh.write(f'A ({len(FA_)}): ' + ', '.join(FA_) + '\n\n')
    fh.write(f'B ({len(FB_)}): ' + ', '.join(FB_) + '\n')
print('A features', len(FA_), 'B features', len(FB_))
print('coverage A (min non-missing share):', A[FA_].notna().mean().sort_values().head(8).round(2).to_dict())
print('coverage B (min non-missing share):', B[FB_].notna().mean().sort_values().head(8).round(2).to_dict())
