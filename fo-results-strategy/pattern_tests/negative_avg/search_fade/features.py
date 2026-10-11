#!/usr/bin/env python3
"""FEATURES ONLY (no forward returns) for the "fade the over-reaction" family.

One row per F&O result (perf/features/panel.csv, 3,280 rows, all qn). Everything here is known at the entry time of
the trade that uses it:
  trade A (short at the cutoff close i_cut): r5vsN_cut, cut_rsi14, lag21 (all use data up to close i_cut).
  trade B entry close k (= i_react): XN, rx_rsi14, CLV_k, gap_k, close<open_k (day-k OHLC), lag21, BAD / rq_pat_yoy
        (the reported quarter is public at the announcement, before the reaction close k).
  trade B entry close k+1: DPK / DQK (day-k delivery file, published after the close of k).
Writes features_fade.csv and prints FEATURE-ONLY counts (no outcomes).
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
nifty = pd.read_csv(f'{DATA}/index_close.csv', index_col=0, usecols=['day', 'Nifty 50'])['Nifty 50'].to_numpy(float)

px = pd.read_csv(f'{SP}/ta/build/adjusted_ohlcv.csv.gz', usecols=['day', 'symbol', 'open', 'high', 'low', 'close'])
px = px[px.symbol.isin(SYM)]
px['i'] = px.day.map(DIX)
assert px.i.notna().all()
OH = {}
for f in ('open', 'high', 'low', 'close'):
    a = np.full((T, len(SYM)), np.nan)
    a[px.i.to_numpy(int), px.symbol.map(SYM).to_numpy(int)] = px[f].to_numpy(float)
    OH[f] = a

pan = pd.read_csv(f'{SP}/perf/features/panel.csv')
assert len(pan) == 3280
keep = ['symbol', 'qn', 'quarter', 'timing', 'i_cut', 'i_rd', 'i_p1', 'i_react', 'lag21', 'vol_ratio_5_60',
        'cut_rsi14', 'XN', 'W']
f = pan[keep].copy()

tf = pd.read_csv(f'{SP}/tafa/C_post_results/features.csv')
f = f.merge(tf[['symbol', 'qn', 'i_react', 'rx_rsi14', 'rx_gap_pct', 'rx_close_vs_sma50_pct', 'E_TA_RX',
                'rq_pat_yoy_pct', 'rq_sales_yoy_pct', 'MCHG', 'GOOD', 'E_GOOD', 'BAD', 'E_BAD']]
            .rename(columns={'i_react': 'i_react_tf'}), on=['symbol', 'qn'], how='left', validate='1:1')
assert (f.i_react_tf == f.i_react).all()
f = f.drop(columns='i_react_tf')

dl = pd.read_csv(f'{SP}/more_signals/delivery/feat_results.csv')
f = f.merge(dl[['symbol', 'qn', 'i_react', 'DPK', 'DQK']].rename(columns={'i_react': 'i_react_dl'}),
            on=['symbol', 'qn'], how='left', validate='1:1')
assert ((f.i_react_dl == f.i_react) | f.i_react_dl.isna()).all()
f = f.drop(columns='i_react_dl')

j = f.symbol.map(SYM)
assert j.notna().all()
j = j.to_numpy(int)
k = f.i_react.to_numpy(int)
ic = f.i_cut.to_numpy(int)

# ---- day-k candle (adjusted OHLC on session k; NaN if the stock did not trade on k)
o, h, l, c = (OH[x][k, j] for x in ('open', 'high', 'low', 'close'))
rng = h - l
with np.errstate(divide='ignore', invalid='ignore'):
    f['clv_k'] = np.where(rng > 0, (c - l) / rng, np.nan)          # 0 = closed at the low, 1 = at the high
f['close_lt_open_k'] = np.where(np.isfinite(o) & np.isfinite(c), (c < o).astype(float), np.nan)
f['oc_k_pct'] = (c / o - 1) * 100                                  # close vs open on day k

# ---- trade A: 5-session return vs Nifty to the cutoff close (sessions i_cut-4 .. i_cut; blank = 0)
r5 = np.full(len(f), np.nan)
for n_, (jj, i0) in enumerate(zip(j, ic)):
    w = R[i0 - 4:i0 + 1, jj]
    if np.isfinite(w).sum() >= 4:                                   # at most 1 blank session
        r5[n_] = (np.prod(1 + np.nan_to_num(w)) - 1) - (nifty[i0] / nifty[i0 - 5] - 1)
f['r5vsN_cut'] = r5 * 100

# ---- stock traded on k and k+1 (entry-day check; prices/returns are features of the entry day itself)
f['traded_k'] = np.isfinite(R[k, j])
f['traded_k1'] = np.isfinite(R[np.minimum(k + 1, T - 1), j]) & (k + 1 < T)

f.to_csv(f'{HERE}/features_fade.csv', index=False)

# ---------------- FEATURE-ONLY counts (no outcomes) -------------------------------------------------------
d = f[f.qn <= 13]
print('discovery rows', len(d), ' holdout rows', (f.qn >= 14).sum())
W = d.XN > 4
cnt = {
    'XN>4': W, 'XN>6': d.XN > 6, 'XN>8': d.XN > 8, 'XN>10': d.XN > 10,
    'XN>6 & clv<1/3': (d.XN > 6) & (d.clv_k < 1 / 3), 'XN>8 & clv<1/3': (d.XN > 8) & (d.clv_k < 1 / 3),
    'XN>10 & clv<1/3': (d.XN > 10) & (d.clv_k < 1 / 3), 'XN>4 & clv<1/3': W & (d.clv_k < 1 / 3),
    'W & rx_rsi14>80': W & (d.rx_rsi14 > 80), 'W & rx_rsi14>75': W & (d.rx_rsi14 > 75),
    'W & DPK<-20': W & (d.DPK < -20), 'W & DQK<2': W & (d.DQK < 2),
    'W & lag21>20': W & (d.lag21 > 20), 'W & lag21>15': W & (d.lag21 > 15), 'W & lag21>10': W & (d.lag21 > 10),
    'gap>5 & C<O': (d.rx_gap_pct > 5) & (d.close_lt_open_k == 1), 'gap>3 & C<O': (d.rx_gap_pct > 3) & (d.close_lt_open_k == 1),
    'W & BAD': W & (d.BAD == True), 'W & pat_yoy<0': W & (d.rq_pat_yoy_pct < 0),
    'r5vsN_cut>8': d.r5vsN_cut > 8, 'r5vsN_cut>5': d.r5vsN_cut > 5, 'r5vsN>8 & rsi>70': (d.r5vsN_cut > 8) & (d.cut_rsi14 > 70),
}
print(f"{'signal':24s} {'n':>5s} {'quarters':>8s}  per-half (0-6 / 7-13)")
for name, m in cnt.items():
    m = m.fillna(False).astype(bool)
    print(f'{name:24s} {m.sum():5d} {d.qn[m].nunique():8d}  {(m & (d.qn <= 6)).sum():4d} / {(m & (d.qn >= 7)).sum():4d}')
print('missing clv_k (disc):', d.clv_k.isna().sum(), ' missing r5vsN_cut:', d.r5vsN_cut.isna().sum(),
      ' missing DPK:', d.DPK.isna().sum(), ' missing rx_rsi14:', d.rx_rsi14.isna().sum())
print('DPK among discovery winners: quantiles', d.DPK[W].quantile([.1, .25, .5, .75, .9]).round(1).tolist())
print('DQK among discovery winners: quantiles', d.DQK[W].quantile([.1, .25, .5, .75, .9]).round(2).tolist())
