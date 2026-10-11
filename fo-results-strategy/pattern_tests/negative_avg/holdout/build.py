#!/usr/bin/env python3
"""Independent holdout evaluator - step 1: per-result signals and outcomes for ALL 22 quarters (own code).

Writes eval_panel.csv (one row per F&O result, 3,280 rows) with
  * my own signal inputs at the reaction close k (XN, SMA50/SMA200 distance, 20-day-low breakdown, 50-day volume ratio,
    BAD / GOOD from fa_panel reported-quarter numbers) and the C12 / C42 flags built from them;
  * the upstream values of the same features (tafa features.csv, panel.csv) for an agreement check only;
  * outcomes: trade B from close k (E0) and from close k+1 (E1, realistic), 20 sessions, stock and Nifty legs;
    trade A three_day (outcomes.csv and my recomputation), Nifty 3-day, and the realistic 2-day window i_cut+1 -> i_p1.
No search script is imported.
"""
import numpy as np
import pandas as pd

SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = f'{SP}/negative_avg/holdout'
K = ['symbol', 'qn']

ses = pd.read_csv(f'{SP}/sector_lab/data/sessions.csv')
days = ses.day.tolist()
T = len(days)
DIX = {d: i for i, d in enumerate(days)}
ret = pd.read_csv(f'{SP}/sector_lab/data/returns.csv', index_col=0)
assert ret.index.tolist() == days
SYM = {s: j for j, s in enumerate(ret.columns)}
R = ret.to_numpy(float)                                  # fractions, NaN = no trade
nif = pd.read_csv(f'{SP}/sector_lab/data/index_close.csv', index_col=0, usecols=['day', 'Nifty 50'])
assert nif.index.tolist() == days
N = nif['Nifty 50'].to_numpy(float)
assert np.isfinite(N).all()
NR = np.r_[np.nan, N[1:] / N[:-1] - 1]

pan = pd.read_csv(f'{SP}/perf/features/panel.csv')
assert len(pan) == 3280
df = pan[K + ['quarter', 'timing', 'fin_type', 'i_cut', 'i_rd', 'i_p1', 'i_react', 'lag21', 'vol_ratio_5_60',
              'XN']].rename(columns={'XN': 'XN_panel'}).copy()
for c in ['i_cut', 'i_rd', 'i_p1', 'i_react']:
    assert df[c].notna().all()
    df[c] = df[c].astype(int)
assert (df.i_p1 - df.i_cut == 3).all()
J = df.symbol.map(SYM)
assert J.notna().all()
J = J.to_numpy(int)
k = df.i_react.to_numpy(int)

# ------------------------------------------------------------------ TA at close k (own code, traded days only)
px = pd.read_csv(f'{SP}/ta/build/adjusted_ohlcv.csv.gz', usecols=['day', 'symbol', 'low', 'close', 'volume'])
px['i'] = px.day.map(DIX)
assert px.i.notna().all()
px['i'] = px.i.astype(int)
G = {s: g.sort_values('i') for s, g in px.groupby('symbol')}

feat = {c: np.full(len(df), np.nan) for c in ['nhist', 'c_vs_sma50', 'c_vs_sma200', 'brk_dn20', 'volr50']}
for r, (s, kk) in enumerate(zip(df.symbol, k)):
    g = G.get(s)
    if g is None:
        continue
    ii = g.i.to_numpy()
    p = np.searchsorted(ii, kk)
    if p >= len(ii) or ii[p] != kk:                      # not traded on k -> no TA at k
        continue
    c, lo, v = g.close.to_numpy(float), g.low.to_numpy(float), g.volume.to_numpy(float)
    feat['nhist'][r] = p + 1
    if p >= 49:
        feat['c_vs_sma50'][r] = (c[p] / c[p - 49:p + 1].mean() - 1) * 100
    if p >= 199:
        feat['c_vs_sma200'][r] = (c[p] / c[p - 199:p + 1].mean() - 1) * 100
    if p >= 20:
        feat['brk_dn20'][r] = float(c[p] < lo[p - 20:p].min())
    if p >= 50:
        m = v[p - 50:p].mean()
        feat['volr50'][r] = v[p] / m if m > 0 else np.nan
for c_, a in feat.items():
    df[c_] = a

# XN: reaction-day stock return minus Nifty that day (%), from returns.csv
df['XN'] = (R[k, J] - NR[k]) * 100

# ------------------------------------------------------------------ BAD / GOOD from fa_panel (reported quarter)
fa = pd.read_csv(f'{SP}/fa/build/fa_panel.csv', usecols=K + ['fin_type', 'rq_pat_yoy_pct', 'rq_sales_yoy_pct',
                                                            'rq_ebitda_margin_chg_yoy_pp', 'rq_net_margin_chg_yoy_pp'])
fa = fa.rename(columns={'fin_type': 'fin_type_fa'})
df = df.merge(fa, on=K, how='left', validate='1:1')
# panel.fin_type is blank for 153 rows; fa_panel's fin_type (the one tafa uses) decides Company vs Bank/NBFC
assert ((df.fin_type == df.fin_type_fa) | df.fin_type.isna()).all()
df['MCHG'] = np.where(df.fin_type_fa == 'Company', df.rq_ebitda_margin_chg_yoy_pp, df.rq_net_margin_chg_yoy_pp)
pat, sal, mchg = df.rq_pat_yoy_pct, df.rq_sales_yoy_pct, df.MCHG
df['BAD'] = ((pat < -25) | (mchg < -2)).fillna(False).astype(bool)
df['GOOD'] = (((pat > 25) & (sal > 15)) | (mchg > 2)).fillna(False).astype(bool)

# ------------------------------------------------------------------ signals
df['L4'] = (df.XN < -4).fillna(False)
df['B50'] = (df.c_vs_sma50 < 0).fillna(False)
df['B200'] = (df.c_vs_sma200 < 0).fillna(False)
df['BRKDN_VOL'] = ((df.nhist >= 51) & df.c_vs_sma50.notna() & (df.brk_dn20 == 1) & (df.volr50 >= 1.5)).fillna(False)
df['BELOW50'] = ((df.nhist >= 51) & df.volr50.notna() & (df.c_vs_sma50 < 0)).fillna(False)
df['C12'] = df.L4 & df.B50 & df.B200
df['C42'] = df.BAD & df.BRKDN_VOL
df['W'] = (df.XN > 4).fillna(False)

# upstream copies for the agreement check (not used for any signal)
tf = pd.read_csv(f'{SP}/tafa/C_post_results/features.csv',
                 usecols=K + ['XN', 'rx_close_vs_sma50_pct', 'rx_close_vs_sma200_pct', 'rx_don20_break_dn',
                              'rx_vol_ratio_50', 'rx_n_hist', 'BAD', 'GOOD', 'BRKDN_VOL', 'BELOW50'])
tf.columns = K + ['up_' + c for c in tf.columns[2:]]
df = df.merge(tf, on=K, how='left', validate='1:1')
oi = pd.read_csv(f'{SP}/more_signals/oi/work/results_features.csv', usecols=K + ['A_dP5', 'A_dOI5'])
df = df.merge(oi, on=K, how='left', validate='1:1')
df['SB_cut'] = ((df.A_dP5 < 0) & (df.A_dOI5 > 10)).fillna(False)

# ------------------------------------------------------------------ outcomes (all quarters)
def window(entry, H):
    """stock / Nifty return from close `entry` to close entry+H; tradable flag."""
    st, nf, ok = np.full(len(df), np.nan), np.full(len(df), np.nan), np.zeros(len(df), bool)
    for r, (e, j) in enumerate(zip(entry, J)):
        x = e + H
        if x > T - 1:
            continue
        w = R[e + 1:x + 1, j]
        if np.isnan(w).sum() > 2:
            continue
        st[r] = (np.prod(1 + np.nan_to_num(w)) - 1) * 100
        nf[r] = (N[x] / N[e] - 1) * 100
        ok[r] = True
    return st, nf, ok


traded_k = np.isfinite(R[k, J])
traded_k1 = np.array([kk + 1 <= T - 1 and np.isfinite(R[kk + 1, j]) for kk, j in zip(k, J)])
st, nf, ok = window(k, 20)
df['B0_stock'], df['B0_nifty'], df['B0_ok'] = st, nf, ok & traded_k
st, nf, ok = window(k + 1, 20)
df['B1_stock'], df['B1_nifty'], df['B1_ok'] = st, nf, ok & traded_k & traded_k1
for c_ in ['B0_stock', 'B0_nifty']:
    df.loc[~df.B0_ok, c_] = np.nan
for c_ in ['B1_stock', 'B1_nifty']:
    df.loc[~df.B1_ok, c_] = np.nan
df['B0_vsN'] = df.B0_stock - df.B0_nifty
# info only (not a finalist): 40-session hold from close k, for the search's C22 (L4 & B200, H40)
st, nf, ok = window(k, 40)
ok = ok & traded_k
df['B40_vsN'] = np.where(ok, st - nf, np.nan)
df['B40_stock'] = np.where(ok, st, np.nan)
df['B40_ok'] = ok
df['B1_vsN'] = df.B1_stock - df.B1_nifty

out = pd.read_csv(f'{SP}/perf/features/outcomes.csv', usecols=K + ['three_day', 'd1', 'd2', 'd3', 'raw_H20',
                                                                  'nifty_H20'])
df = df.merge(out, on=K, how='left', validate='1:1')
ic = df.i_cut.to_numpy(int)
df['three_day_my'] = [np.sum(R[c + 1:c + 4, j]) * 100 for c, j in zip(ic, J)]   # NaN if any day blank
df['nifty3'] = [np.sum(NR[c + 1:c + 4]) * 100 for c in ic]
df['two_day'] = df.d2 + df.d3                                                       # close i_cut+1 -> close i_p1
df['two_day_my'] = [np.sum(R[c + 2:c + 4, j]) * 100 for c, j in zip(ic, J)]
df['nifty2'] = [np.sum(NR[c + 2:c + 4]) * 100 for c in ic]

# ------------------------------------------------------------------ checks
P = []
a, b = df.XN, df.up_XN
P.append(f'XN vs tafa: both finite {np.sum(a.notna() & b.notna())}, NaN mismatch {np.sum(a.isna() != b.isna())}, '
         f'max |diff| {np.nanmax(np.abs(a - b)):.2e}')
a, b = df.XN, df.XN_panel
P.append(f'XN vs panel: NaN mismatch {np.sum(a.isna() != b.isna())}, max |diff| {np.nanmax(np.abs(a - b)):.2e}')
for mine, up in [('c_vs_sma50', 'up_rx_close_vs_sma50_pct'), ('c_vs_sma200', 'up_rx_close_vs_sma200_pct'),
                 ('brk_dn20', 'up_rx_don20_break_dn'), ('volr50', 'up_rx_vol_ratio_50'), ('nhist', 'up_rx_n_hist')]:
    a, b = df[mine], df[up]
    both = a.notna() & b.notna()
    P.append(f'{mine:12s} vs {up}: NaN mismatch {np.sum(a.isna() != b.isna())}, max |diff| '
             f'{np.max(np.abs(a[both] - b[both])):.2e}')
for mine, up in [('BAD', 'up_BAD'), ('GOOD', 'up_GOOD'), ('BRKDN_VOL', 'up_BRKDN_VOL'), ('BELOW50', 'up_BELOW50')]:
    P.append(f'{mine:10s} flag disagreements vs tafa: {int((df[mine] != df[up].astype(bool)).sum())}')
upC12 = (df.up_XN < -4) & (df.up_rx_close_vs_sma50_pct < 0) & (df.up_rx_close_vs_sma200_pct < 0)
upC42 = df.up_BAD.astype(bool) & df.up_BRKDN_VOL.astype(bool)
P.append(f'C12 flag disagreements vs tafa-built: {int((df.C12 != upC12).sum())}; C42: {int((df.C42 != upC42).sum())}')
P.append(f'C12 signals qn<=13 {int(df.C12[df.qn <= 13].sum())}, qn>=14 {int(df.C12[df.qn >= 14].sum())}; '
         f'C42 qn<=13 {int(df.C42[df.qn <= 13].sum())}, qn>=14 {int(df.C42[df.qn >= 14].sum())}')
a, b = df.three_day_my, df.three_day
P.append(f'three_day recomputed vs outcomes.csv: NaN mismatch {np.sum(a.isna() != b.isna())}, max |diff| '
         f'{np.nanmax(np.abs(a - b)):.2e}')
a, b = df.two_day_my, df.two_day
P.append(f'two_day (d2+d3) recomputed: NaN mismatch {np.sum(a.isna() != b.isna())}, max |diff| '
         f'{np.nanmax(np.abs(a - b)):.2e}')
m = df.B0_ok & df.raw_H20.notna()
P.append(f'B0 H20 vs outcomes raw_H20 / nifty_H20 (rows both present {m.sum()}): max |diff| stock '
         f'{np.max(np.abs(df.B0_stock[m] - df.raw_H20[m])):.2e}, nifty {np.max(np.abs(df.B0_nifty[m] - df.nifty_H20[m])):.2e}')
P.append(f'B0 tradable rows: {int(df.B0_ok.sum())} (qn>=14: {int(df.B0_ok[df.qn >= 14].sum())}); '
         f'B1 tradable {int(df.B1_ok.sum())}; three_day finite {int(df.three_day.notna().sum())}')
P.append(f'last session {days[-1]}; latest exit used by B1: '
         f'{days[int((df.i_react[df.B1_ok] + 21).max())]}')
df = df.drop(columns=['raw_H20', 'nifty_H20', 'fin_type_fa'])
df.to_csv(f'{OUT}/eval_panel.csv', index=False, float_format='%.6g')
with open(f'{OUT}/build_checks.log', 'w') as fh:
    fh.write('\n'.join(P) + '\n')
print('\n'.join(P))
