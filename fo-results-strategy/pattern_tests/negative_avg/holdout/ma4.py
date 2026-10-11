#!/usr/bin/env python3
"""Independent holdout evaluator - step 2: MA4 (walk-forward gradient-boosting fall ranker, bottom decile, trade A).

Own implementation from the written definition. Steps:
  1. Re-build the 112-column cutoff feature matrix by my own merge of the source files and check it equals
     search_model/features_A.csv (so the model sees exactly the registered features).
  2. Walk-forward for every season q = 4..21 (4..13 = discovery reproduction, 14..21 = holdout):
       pool  = eligible rows (three_day known) with qn < q and i_p1 < min(i_cut of season q)
       prep  = drop features < 50% non-missing in the pool or with pool p1 == p99; clip at pool p1 / p99 (NaN kept)
       target= three_day - mean(three_day of the same season within the pool), clipped at the pool p1 / p99
       model = HistGradientBoostingRegressor(squared_error, lr 0.03, 200 iters, depth 3, min leaf 40, l2 1.0,
               max_features 0.5, no early stopping, random_state=seed)
       thresh= 10th percentile of out-of-fold scores of the last 4 seasons in the pool (each season j scored by the
               model refit, with its own prep, on the pool without season j)
       trade = every eligible season-q row with score <= threshold.
Usage: python3 ma4.py [seed ...]   (default seed 0 = the registered model; other seeds = robustness only)
Writes ma4_scores_seed{s}.csv.
"""
import sys
import time

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = f'{SP}/negative_avg/holdout'
K = ['symbol', 'qn']
SEEDS = [int(x) for x in sys.argv[1:]] or [0]

# ------------------------------------------------------------------ 1. feature matrix (own merge) + equality check
pan = pd.read_csv(f'{SP}/perf/features/panel.csv')
ta_cols = ['rsi2', 'stoch_k14', 'willr14', 'cci20', 'mfi14', 'bb_pctb', 'bb_width_pct', 'macd_pct', 'macd_hist_pct',
           'close_vs_sma20_pct', 'close_vs_sma50_pct', 'close_vs_sma200_pct', 'sma50_vs_sma200_pct', 'adx14',
           'plus_di14', 'minus_di14', 'atr14_pct', 'gap_pct', 'dist_52w_low_pct', 'dist_20d_high_pct',
           'dist_20d_low_pct', 'don20_pos', 'obv_slope20', 'price_slope20_pct', 'ret_5d_pct']
fa_cut = ['log_mcap', 'pe', 'earnings_yield_pct', 'pb', 'roe_pct', 'debt_equity', 'ps', 'pe_vs_own3y_pct',
          'pe_vs_peers_pct', 'ttm_pat_yoy_pct', 'ttm_sales_yoy_pct', 'l1_sales_yoy_pct', 'l1_pat_yoy_pct',
          'l1_ebitda_margin_chg_yoy_pp', 'pat_up_yoy_4q', 'sales_up_yoy_4q', 'loss_any_4q', 'piotroski_frac',
          'pat_yoy_std8_pct', 'days_since_dividend']
oi_cols = ['A1_' + c for c in ['dOI1', 'dOI5', 'dOI10', 'dP1', 'dP5', 'dP10', 'OI20', 'BASIS', 'BASISDEV', 'PCR',
                               'dPCR5', 'IV', 'IVREL', 'IVSPREAD', 'dCIV20', 'dPIV20']]
dl_cols = ['ACC', 'DQR', 'DPL', 'DQL', 'DP60', 'PR5']
news_cols = ['NEWS30', 'NEWSR', 'PR30', 'ORDER30', 'ACQ30', 'CRUP90', 'CRDN90', 'BIZ_N45', 'PROMBUY90', 'PROMSELL90',
             'HOLDBUY90', 'HOLDSELL90', 'CALLPRE']
trk = ['n_prev_A', 'prev1_three_day_A', 'prev1_xn_A', 'prev1_drift20_A', 'prev1_winner_A', 'n_pos_three_day_4_A',
       'mean_three_day_4_A', 'n_winner_4_A', 'mean_xn_4_A', 'mean_abs_xn_4_A', 'n_pos_drift_4_A', 'mean_drift_4_A',
       'mean_three_day_all_A', 'mean_xn_all_A', 'mean_drift_all_A', 'vsN_21_A', 'vsN_63_A', 'vsN_126_A', 'vsN_252_A',
       'vsSec_63_A', 'vsSec_252_A', 'rank_vsN_63_A', 'rank_vsN_126_A', 'rank_vsN_252_A', 'dist_52wh_A']
FEATS = (['lag21', 'vol_ratio_5_60', 'cut_rsi14'] + trk + ta_cols + fa_cut + oi_cols + dl_cols + news_cols
         + ['tm_after', 'tm_during', 'ft_bank', 'ft_nbfc'])
assert len(FEATS) == 112

X = pan[K + ['i_cut', 'i_p1'] + ['lag21', 'vol_ratio_5_60', 'cut_rsi14'] + trk + ['timing', 'fin_type']].copy()
for path, cols in [(f'{SP}/ta/build/events_ta.csv', ta_cols), (f'{SP}/fa/build/fa_panel.csv', fa_cut),
                   (f'{SP}/more_signals/oi/work/results_features.csv', oi_cols),
                   (f'{SP}/more_signals/delivery/feat_results.csv', dl_cols),
                   (f'{SP}/more_signals/news/work/feat_results.csv', news_cols)]:
    d = pd.read_csv(path, usecols=K + cols)
    X = X.merge(d, on=K, how='left', validate='1:1')
assert len(X) == 3280
X['tm_after'] = (X.timing == 'After close').astype(float)
X['tm_during'] = (X.timing == 'During market').astype(float)
X['ft_bank'] = (X.fin_type == 'Bank').astype(float)
X['ft_nbfc'] = (X.fin_type == 'NBFC / financial').astype(float)
for c in FEATS:
    s = X[c]
    if s.dtype == object or s.dtype == bool:
        s = s.map({True: 1.0, False: 0.0, 'True': 1.0, 'False': 0.0})
    X[c] = pd.to_numeric(s, errors='coerce').astype(float)
    X.loc[~np.isfinite(X[c]), c] = np.nan

ref = pd.read_csv(f'{SP}/negative_avg/search_model/features_A.csv')
assert list(ref.columns[7:]) == FEATS
cmp = X[K + FEATS].merge(ref[K + FEATS], on=K, suffixes=('', '_r'), validate='1:1')
worst = 0.0
for c in FEATS:
    a, b = cmp[c].to_numpy(), cmp[c + '_r'].to_numpy()
    assert (np.isnan(a) == np.isnan(b)).all(), c
    m = ~np.isnan(a)
    rel = np.max(np.abs(a[m] - b[m]) / np.maximum(1, np.abs(b[m]))) if m.any() else 0
    worst = max(worst, rel)
print(f'feature matrix rebuilt: 112 columns, NaN pattern identical, max relative diff vs features_A.csv {worst:.1e} '
      f'(features_A.csv is written with 6 significant digits)')
# use the reference file's rounded values so the model input is byte-identical to the registered matrix
X = X[K + ['i_cut', 'i_p1']].merge(ref[K + FEATS], on=K, validate='1:1')

ev = pd.read_csv(f'{OUT}/eval_panel.csv', usecols=K + ['three_day'])
X = X.merge(ev, on=K, validate='1:1')
X['elig'] = X.three_day.notna()


# ------------------------------------------------------------------ 2. walk-forward
def prep(pool):
    F = pool[FEATS]
    keep = []
    lo, hi = {}, {}
    for c in FEATS:
        v = F[c].to_numpy()
        if np.mean(~np.isnan(v)) < 0.5:
            continue
        p1, p99 = np.nanpercentile(v, [1, 99])
        if p1 == p99:
            continue
        keep.append(c)
        lo[c], hi[c] = p1, p99
    return keep, lo, hi


def mat(d, keep, lo, hi):
    return np.column_stack([d[c].clip(lo[c], hi[c]).to_numpy(float) for c in keep])


def fit(pool, seed):
    keep, lo, hi = prep(pool)
    y = pool.three_day - pool.groupby('qn').three_day.transform('mean')
    a, b = np.percentile(y, [1, 99])
    y = y.clip(a, b)
    m = HistGradientBoostingRegressor(loss='squared_error', learning_rate=0.03, max_iter=200, max_depth=3,
                                      min_samples_leaf=40, l2_regularization=1.0, max_features=0.5,
                                      early_stopping=False, random_state=seed)
    m.fit(mat(pool, keep, lo, hi), y.to_numpy())
    return lambda d: m.predict(mat(d, keep, lo, hi))


for seed in SEEDS:
    t0 = time.time()
    rows = []
    for q in range(4, 22):
        Dq = X.i_cut[X.qn == q].min()
        pool = X[X.elig & (X.qn < q) & (X.i_p1 < Dq)]
        excl = int((X.elig & (X.qn < q)).sum() - len(pool))
        score = fit(pool, seed)
        cur = X[X.elig & (X.qn == q)].copy()
        cur['score'] = score(cur)
        oof = []
        for j in sorted(pool.qn.unique())[-4:]:
            sj = fit(pool[pool.qn != j], seed)
            oof.append(sj(pool[pool.qn == j]))
        tq = np.percentile(np.concatenate(oof), 10)
        cur['thr'] = tq
        cur['pick'] = cur.score <= tq
        cur['pool_n'] = len(pool)
        cur['pool_excluded'] = excl
        rows.append(cur[K + ['score', 'thr', 'pick', 'pool_n', 'pool_excluded']])
        print(f'seed {seed} q {q:2d}: pool {len(pool)} (excluded by label rule {excl}), scored {len(cur)}, '
              f'threshold {tq:+.4f}, picks {int(cur.pick.sum())}', flush=True)
    S = pd.concat(rows, ignore_index=True)
    S.to_csv(f'{OUT}/ma4_scores_seed{seed}.csv', index=False, float_format='%.8g')
    print(f'seed {seed} done in {time.time() - t0:.0f}s')
