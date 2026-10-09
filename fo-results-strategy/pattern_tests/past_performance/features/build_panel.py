#!/usr/bin/env python3
"""Point-in-time PAST-PERFORMANCE panel for the F&O results universe (one row per in_fo result, 3,280 rows).

Two decision times per result:
  A = cutoff close i_cut  (trade A: pre-results 3-day window, buy close i_cut, sell close i_p1)
  B = reaction close k = i_react (trade B: post-results winner drift, buy close k, hold 20 sessions)

Writes (only into this folder):
  panel.csv     features only - no outcome of the current result (XN / W are the reaction-day move: known at close k,
                trade-B only; see columns.csv known_at)
  outcomes.csv  outcomes of the current result (trade A three_day etc., trade B 20-session drift), key symbol+qn
  history.csv   per-result track-record items for all 4,462 events (td, xn, drift20 + the session each is known at)
  coverage.csv  coverage by qn
  columns.csv   data dictionary
Inputs are read-only. Percent units throughout (1.2 = +1.2%).
"""
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
DATA = f'{SP}/sector_lab/data'
REPO = __import__('os').environ.get('REPO_ROOT', '.')  # this repo
LOG = open(f'{HERE}/build.log', 'w')


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    LOG.write(s + '\n')
    LOG.flush()


# ------------------------------------------------------------------ prices
ses = pd.read_csv(f'{DATA}/sessions.csv')
days = ses.day.tolist()
T = len(days)
ret = pd.read_csv(f'{DATA}/returns.csv', index_col=0)
assert ret.index.tolist() == days
SYMS = ret.columns.tolist()
SYM = {s: j for j, s in enumerate(SYMS)}
R = ret.to_numpy(float)
PX = np.cumprod(1.0 + np.nan_to_num(R), axis=0)          # same construction as tafa run_tests / TA builder
CVALID = np.cumsum(~np.isnan(R), axis=0)
FIRST = np.array([np.argmax(np.isfinite(R[:, j])) for j in range(R.shape[1])])   # first return = listing day
ixc = pd.read_csv(f'{DATA}/index_close.csv', index_col=0)
assert ixc.index.tolist() == days
NIFTY = ixc['Nifty 50'].to_numpy(float)
assert np.isfinite(NIFTY).all()
NRET = np.r_[np.nan, NIFTY[1:] / NIFTY[:-1] - 1]

# adjusted OHLCV for the 52-week high (same definition as the TA builder: close / max high of last 250 traded sessions)
ohl = pd.read_csv(f'{SP}/ta/build/adjusted_ohlcv.csv.gz', usecols=['day', 'symbol', 'high', 'close'])
DIX = {d: i for i, d in enumerate(days)}
ohl = ohl[ohl.symbol.isin(SYM)]
HI = np.full((T, len(SYMS)), np.nan)
CL = np.full((T, len(SYMS)), np.nan)
ii_, jj_ = ohl.day.map(DIX).to_numpy(int), ohl.symbol.map(SYM).to_numpy(int)
HI[ii_, jj_], CL[ii_, jj_] = ohl.high.to_numpy(float), ohl.close.to_numpy(float)
D52 = np.full((T, len(SYMS)), np.nan)
for j in range(len(SYMS)):
    rows = np.flatnonzero(np.isfinite(CL[:, j]))
    if len(rows):
        hh = pd.Series(HI[rows, j]).rolling(250, min_periods=250).max().to_numpy()
        D52[rows, j] = (CL[rows, j] / hh - 1) * 100

LAGS = (21, 63, 126, 252)
MAXBLANK = {21: 2, 63: 3, 126: 6, 252: 12}               # ~5% of the window (2 for 21, as the lag rule's ev.pkl)


def stock_ret(j, i, L):
    """Stock return over sessions (i-L, i] in percent; NaN if the window starts before the listing-day return or has
    too many no-trade sessions."""
    if i - L < FIRST[j] or i - L < 0:
        return np.nan
    blanks = L - (CVALID[i, j] - CVALID[i - L, j])
    if blanks > MAXBLANK[L]:
        return np.nan
    return (PX[i, j] / PX[i - L, j] - 1) * 100


def index_ret(arr, i, L):
    if i - L < 0 or not (np.isfinite(arr[i]) and np.isfinite(arr[i - L])):
        return np.nan
    return (arr[i] / arr[i - L] - 1) * 100


# ------------------------------------------------------------------ events and universe
ev = pd.read_csv(f'{DATA}/events.csv')
assert not ev.duplicated(['symbol', 'qn']).any()
for c in ('i_cut', 'i_m1', 'i_rd', 'i_p1', 'i_react'):
    assert ev[c].notna().all()
    ev[c] = ev[c].astype(int)
assert (ev.i_cut < ev.i_m1).all() and (ev.i_m1 < ev.i_rd).all() and (ev.i_rd < ev.i_p1).all()
assert ((ev.i_react == ev.i_rd) | (ev.i_react == ev.i_p1)).all()
ev['in_fo_events'] = ev.in_fo.map({True: True, False: False, 'True': True, 'False': False})
tf = pd.read_csv(f'{SP}/tafa/C_post_results/features.csv')
assert len(tf) == 3280 and not tf.duplicated(['symbol', 'qn']).any()
ukeys = set(zip(tf.symbol, tf.qn))
ev['universe'] = [(s, q) in ukeys for s, q in zip(ev.symbol, ev.qn)]
assert ev.universe.sum() == 3280
P('universe (tafa features = fa_panel in_fo): 3280; events in_fo True', int((ev.in_fo_events == True).sum()),
  '; in universe with events in_fo NaN:', ev[ev.universe & ev.in_fo_events.isna()][['symbol', 'quarter']].values.tolist())
assert (ev[ev.universe].in_fo_events != False).all() and (ev[~ev.universe].in_fo_events == False).all()

# ------------------------------------------------------------------ per-result history items (all 4,462 events)
j_all = ev.symbol.map(SYM).to_numpy(int)
k_all = ev.i_react.to_numpy(int)
ev['h_td'] = ev.three_day * 100                                    # 3-day window, known at close i_p1
ev['h_td_end'] = ev.i_p1
ev['h_xn'] = (R[k_all, j_all] - NRET[k_all]) * 100                # reaction day vs Nifty, known at close i_react
ev['h_xn_end'] = ev.i_react
dr = np.full(len(ev), np.nan)
for n, (j, k) in enumerate(zip(j_all, k_all)):
    e = k + 20
    if e > T - 1:
        continue
    if 20 - (CVALID[e, j] - CVALID[k, j]) > 2:
        continue
    dr[n] = ((PX[e, j] / PX[k, j] - 1) - (NIFTY[e] / NIFTY[k] - 1)) * 100
ev['h_dr'] = dr                                                    # 20-session drift vs Nifty (gross), known at k+20
ev['h_dr_end'] = ev.i_react + 20
P('history items: td non-NaN', int(ev.h_td.notna().sum()), 'xn non-NaN', int(ev.h_xn.notna().sum()),
  'drift non-NaN', int(ev.h_dr.notna().sum()), 'of', len(ev))
ev[['symbol', 'qn', 'quarter', 'period', 'in_fo_events', 'i_cut', 'i_p1', 'i_react', 'h_td', 'h_td_end', 'h_xn',
    'h_xn_end', 'h_dr', 'h_dr_end']].to_csv(f'{HERE}/history.csv', index=False, float_format='%.6g')

# ------------------------------------------------------------------ track record (point in time)
TR = ['n_prev', 'prev1_qn', 'prev1_three_day', 'prev1_xn', 'prev1_drift20', 'prev1_winner',
      'n_pos_three_day_4', 'mean_three_day_4', 'n_winner_4', 'mean_xn_4', 'mean_abs_xn_4',
      'n_drift_4', 'n_pos_drift_4', 'mean_drift_4', 'mean_three_day_all', 'mean_xn_all', 'n_drift_all',
      'mean_drift_all']
G = {s: g.sort_values('qn') for s, g in ev.groupby('symbol')}
USED_MAX = {}          # (row, tag) -> latest session any used history item became known (for the look-ahead assert)


def nmean(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return x.mean() if len(x) else np.nan


def npos(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return float((x > 0).sum()) if len(x) else np.nan


def track(sym, qn, dec):
    g = G[sym]
    # earlier results: earlier quarter AND its 3-day window and reaction day both closed before the decision session
    h = g[(g.qn < qn) & (g.h_td_end < dec) & (g.h_xn_end < dec)].sort_values('qn', ascending=False)
    out = dict.fromkeys(TR, np.nan)
    n = len(h)
    out['n_prev'] = n
    if n == 0:
        return out, -1
    drk = h.h_dr.where(h.h_dr_end < dec)             # drift only if its exit session is before the decision
    used = [h.h_td_end.max(), h.h_xn_end.max()]
    if drk.notna().any():
        used.append(h.h_dr_end[drk.notna()].max())
    p = h.iloc[0]
    out.update(prev1_qn=p.qn, prev1_three_day=p.h_td, prev1_xn=p.h_xn, prev1_drift20=drk.iloc[0],
               prev1_winner=(float(p.h_xn > 4) if np.isfinite(p.h_xn) else np.nan))
    if n >= 4:
        h4, d4 = h.iloc[:4], drk.iloc[:4]
        xn4 = h4.h_xn.to_numpy(float)
        out.update(n_pos_three_day_4=npos(h4.h_td), mean_three_day_4=nmean(h4.h_td),
                   n_winner_4=(float((xn4[np.isfinite(xn4)] > 4).sum()) if np.isfinite(xn4).any() else np.nan),
                   mean_xn_4=nmean(xn4), mean_abs_xn_4=nmean(np.abs(xn4)),
                   n_drift_4=float(d4.notna().sum()), n_pos_drift_4=npos(d4), mean_drift_4=nmean(d4))
    out.update(mean_three_day_all=nmean(h.h_td), mean_xn_all=nmean(h.h_xn), n_drift_all=float(drk.notna().sum()),
               mean_drift_all=nmean(drk))
    return out, max(used)


U = ev[ev.universe].copy().reset_index(drop=True)
rows = []
for r in U.itertuples():
    o = {}
    for tag, dec in (('A', r.i_cut), ('B', r.i_react)):
        t, um = track(r.symbol, r.qn, dec)
        assert um < dec, (r.symbol, r.qn, tag, um, dec)          # look-ahead assert (history)
        USED_MAX[(r.Index, tag)] = um
        o.update({f'{k}_{tag}': v for k, v in t.items()})
    rows.append(o)
TRK = pd.DataFrame(rows)
P('look-ahead assert passed: every history item used ended strictly before the decision session (A: i_cut, B: i_react)')

# ------------------------------------------------------------------ price performance at A (i_cut) and B (i_react)
UJ = U.symbol.map(SYM).to_numpy(int)
PP = {}
for tag, col in (('A', 'i_cut'), ('B', 'i_react')):
    I_ = U[col].to_numpy(int)
    for L in LAGS:
        PP[f'vsN_{L}_{tag}'] = [stock_ret(j, i, L) - index_ret(NIFTY, i, L) for j, i in zip(UJ, I_)]
    for L in (63, 252):
        v = []
        for j, i, sx in zip(UJ, I_, U.sector_index):
            if isinstance(sx, str) and sx in ixc.columns:
                v.append(stock_ret(j, i, L) - index_ret(ixc[sx].to_numpy(float), i, L))
            else:
                v.append(np.nan)
        PP[f'vsSec_{L}_{tag}'] = v
    # percentile rank among the same quarter's F&O results, all measured at THIS row's decision session (point in
    # time: other stocks' returns are taken on the same day, not at their own later cutoffs)
    for L in (63, 126, 252):
        rk = np.full(len(U), np.nan)
        for q, gq in U.groupby('qn'):
            jq = gq.symbol.map(SYM).to_numpy(int)
            for i in np.unique(gq[col]):
                xs = np.array([stock_ret(j, i, L) for j in jq])
                ok = np.isfinite(xs)
                if ok.sum() < 2:
                    continue
                rks = pd.Series(xs[ok]).rank(pct=True).to_numpy() * 100
                rr = np.full(len(xs), np.nan)
                rr[ok] = rks
                sel = (gq[col] == i).to_numpy()
                rk[gq.index[sel]] = rr[sel]
        PP[f'rank_vsN_{L}_{tag}'] = rk
    PP[f'dist_52wh_{tag}'] = D52[I_, UJ]
PPF = pd.DataFrame(PP)

# ------------------------------------------------------------------ copies: lag rule inputs, tafa features
eta = pd.read_csv(f'{SP}/ta/build/events_ta.csv')
evp = pd.read_pickle(f'{SP}/lag15_vol15_verify/ev.pkl')
base = U[['symbol', 'qn', 'quarter', 'period', 'timing', 'industry', 'sector_index', 'fin_type', 'cutoff',
          'reaction_day', 'i_cut', 'i_rd', 'i_p1', 'i_react', 'in_fo_events']].copy()
base['in_fo'] = True
base = base.merge(eta[['symbol', 'qn', 'lag_pct', 'vol_ratio_5_60', 'dist_52w_high_pct']].rename(
    columns={'lag_pct': 'lag21', 'dist_52w_high_pct': 'eta_d52'}), on=['symbol', 'qn'], how='left', validate='1:1')
base = base.merge(evp[['symbol', 'qn', 'lag', 'vr']].rename(columns={'lag': 'evp_lag', 'vr': 'evp_vr'}),
                  on=['symbol', 'qn'], how='left', validate='1:1')
base = base.merge(tf[['symbol', 'qn', 'XN', 'W', 'cut_rsi14', 'RSI_HI']], on=['symbol', 'qn'], how='left',
                  validate='1:1')
panel = pd.concat([base, TRK, PPF], axis=1)
assert len(panel) == 3280

# cross-checks of copied / recomputed fields
d = (panel.lag21 - panel.evp_lag * 100).abs()
P(f'lag21 (events_ta) vs ev.pkl lag x100: n={d.notna().sum()} max abs diff {d.max():.2e}; '
  f'NaN events_ta {panel.lag21.isna().sum()}, NaN ev.pkl {panel.evp_lag.isna().sum()}')
d = (panel.vol_ratio_5_60 - panel.evp_vr).abs()
P(f'vol_ratio_5_60 (events_ta) vs ev.pkl vr: n={d.notna().sum()} max abs diff {d.max():.2e}')
d = (panel.vsN_21_A - panel.lag21).abs()
P(f'vsN_21_A (this build) vs lag21: n={d.notna().sum()} max abs diff {d.max():.2e}; vsN_21_A NaN {panel.vsN_21_A.isna().sum()}')
d = (panel.dist_52wh_A - panel.eta_d52).abs()
P(f'dist_52wh_A vs events_ta dist_52w_high_pct: n={d.notna().sum()} max abs diff {d.max():.2e}')
ux = U.symbol.map(SYM).to_numpy(int)
xn_re = (R[U.i_react.to_numpy(int), ux] - NRET[U.i_react.to_numpy(int)]) * 100
d = np.abs(xn_re - panel.XN.to_numpy(float))
P(f'XN (tafa) vs recomputed: max abs diff {np.nanmax(d):.2e}')
assert np.nanmax(d) < 1e-3
panel = panel.drop(columns=['evp_lag', 'evp_vr', 'eta_d52'])

# ------------------------------------------------------------------ outcomes (current result) -> outcomes.csv only
out = U[['symbol', 'qn', 'quarter', 'period']].copy()
out['three_day'] = U.three_day * 100
out['three_day_net'] = out.three_day - 0.17
out = out.merge(eta[['symbol', 'qn', 'd1', 'd2', 'd3', 'take_profit']], on=['symbol', 'qn'], how='left',
                validate='1:1')
out['next20'] = U.next20 * 100
out['next20_vs_nifty'] = U.next20_vs_nifty * 100
# trade B outcome: exactly tafa run_tests.outcomes() (tradable needs k+21 <= last session and <= 2 blanks in k+1..k+21)
k = U.i_react.to_numpy(int)
ok = (k + 21 <= T - 1)
kk = np.where(ok, k, 0)
ok &= (21 - (CVALID[np.minimum(kk + 21, T - 1), ux] - CVALID[kk, ux])) <= 2
ok &= panel.XN.notna().to_numpy()
for H in (5, 10, 20):
    e_ = np.minimum(kk + H, T - 1)
    raw = (PX[e_, ux] / PX[kk, ux] - 1) * 100
    nif = (NIFTY[e_] / NIFTY[kk] - 1) * 100
    out[f'raw_H{H}'] = np.where(ok, raw, np.nan)
    out[f'nifty_H{H}'] = np.where(ok, nif, np.nan)
out['tradable_B'] = ok
out['vsN_H20'] = out.raw_H20 - out.nifty_H20
out['vsN_net_H20'] = out.vsN_H20 - 0.19
tt = pd.read_csv(f'{SP}/tafa/C_post_results/trades.csv')
m = out.merge(tt[['symbol', 'qn', 'raw_H20', 'nifty_H20']], on=['symbol', 'qn'], suffixes=('', '_tafa'))
assert len(m) == 3280
d1 = (m.raw_H20 - m.raw_H20_tafa).abs().max()
d2 = (m.nifty_H20 - m.nifty_H20_tafa).abs().max()
P(f'trade-B outcome vs tafa trades.csv: max abs diff raw_H20 {d1:.1e}, nifty_H20 {d2:.1e}, '
  f'NaN pattern equal {bool((m.raw_H20.isna() == m.raw_H20_tafa.isna()).all())}')
assert d1 < 1e-3 and d2 < 1e-3 and (m.raw_H20.isna() == m.raw_H20_tafa.isna()).all()

# ------------------------------------------------------------------ write
pcols = ['symbol', 'qn', 'quarter', 'period', 'timing', 'industry', 'sector_index', 'fin_type', 'cutoff',
         'reaction_day', 'i_cut', 'i_rd', 'i_p1', 'i_react', 'in_fo', 'in_fo_events', 'lag21', 'vol_ratio_5_60',
         'cut_rsi14', 'RSI_HI', 'XN', 'W'] + list(TRK.columns) + list(PPF.columns)
panel = panel[pcols]
forbidden = {'three_day', 'ret_dm1', 'ret_rd', 'ret_dp1', 'move', 'gap', 'next5', 'next20', 'next20_vs_nifty',
             'excess_nifty', 'excess_sector', 'sector_3d', 'nifty_3d', 'raw_H20', 'take_profit'}
assert not forbidden & set(panel.columns)
panel.to_csv(f'{HERE}/panel.csv', index=False, float_format='%.6g')
out.to_csv(f'{HERE}/outcomes.csv', index=False, float_format='%.6g')
P(f'panel.csv {panel.shape}, outcomes.csv {out.shape}')

# ------------------------------------------------------------------ data dictionary
DOC = [
    ('symbol, qn, quarter, period', 'key', '', 'qn 0 = Results for Jan-Mar 2021 (Q4 FY21) .. 21 = Apr-Jun 2026 (Q1 FY27)'),
    ('timing, industry, sector_index, fin_type', 'static', '', 'from events.csv'),
    ('cutoff, reaction_day, i_cut, i_rd, i_p1, i_react', 'static', 'date / session', 'events.csv sessions'),
    ('in_fo', 'static', 'bool', 'True for all 3,280 rows (universe = tafa features / fa_panel in_fo)'),
    ('in_fo_events', 'static', 'bool', 'events.csv in_fo (blank for RELIANCE Q1 FY24, VEDL Q4 FY26; the repo lag rule uses == True)'),
    ('lag21', 'A: close i_cut', '%', '21-session stock return minus Nifty 50 (events_ta lag_pct = repo vs_nifty_1m x100)'),
    ('vol_ratio_5_60', 'A: close i_cut', 'ratio', '5 / 60-session mean split-adjusted volume (events_ta = repo volume_ratio)'),
    ('cut_rsi14, RSI_HI', 'A: close i_cut', '0-100 / bool', 'tafa features: Wilder RSI(14) at the cutoff; RSI_HI = > 50'),
    ('XN, W', 'B: close i_react', '% / bool', 'reaction-day stock return minus Nifty (tafa); W = XN > 4. Part of the current results move: NOT usable for trade A'),
    ('*_A', 'A: close i_cut', '', 'track record / price performance known at the cutoff close'),
    ('*_B', 'B: close i_react', '', 'track record / price performance known at the reaction close k'),
    ('n_prev_X', 'X', 'count', 'earlier results of the same stock (any in_fo status) whose 3-day window (i_p1) and reaction day ended before the decision session'),
    ('prev1_qn_X', 'X', '', 'qn of the most recent such result'),
    ('prev1_three_day_X', 'X', '%', 'its 3-day window return (Day-1 + Result day + Day+1, gross)'),
    ('prev1_xn_X', 'X', '%', 'its reaction-day return minus Nifty'),
    ('prev1_drift20_X', 'X', '%', 'its 20-session return minus Nifty from its reaction close (gross); NaN unless its exit session (i_react+20) < decision session'),
    ('prev1_winner_X', 'X', '0/1', 'prev1_xn > 4'),
    ('n_pos_three_day_4_X, mean_three_day_4_X', 'X', 'count / %', 'over the last 4 earlier results (NaN if n_prev < 4)'),
    ('n_winner_4_X, mean_xn_4_X, mean_abs_xn_4_X', 'X', 'count / %', 'last 4: reaction-day vs Nifty > 4 count, mean, mean absolute (typical size of the results move)'),
    ('n_drift_4_X, n_pos_drift_4_X, mean_drift_4_X', 'X', 'count / %', 'last 4: drifts already ended before the decision (count), positive count, mean over those known'),
    ('mean_three_day_all_X, mean_xn_all_X, n_drift_all_X, mean_drift_all_X', 'X', '% / count', 'over all earlier results (drift: only those ended)'),
    ('vsN_{21,63,126,252}_X', 'X', '%', 'stock return over the last L sessions minus Nifty 50 (NaN if window starts on/before the listing-day return or > ~5% no-trade sessions)'),
    ('vsSec_{63,252}_X', 'X', '%', 'stock return minus its events.sector_index (Nifty 500 for unmapped industries) over L sessions; NaN if the index has no data at the window start'),
    ('rank_vsN_{63,126,252}_X', 'X', 'percentile 0-100', "rank of the L-session return among the same quarter's F&O results, ALL measured at this row's decision session (100 = best)"),
    ('dist_52wh_X', 'X', '%', 'adjusted close / max adjusted high of the last 250 traded sessions - 1 (TA builder definition); NaN if < 250 traded sessions'),
]
pd.DataFrame(DOC, columns=['columns', 'known_at', 'unit', 'meaning']).to_csv(f'{HERE}/columns.csv', index=False)
ODOC = [
    ('three_day, three_day_net', 'trade A outcome', '%', 'events three_day x100 (sum of the 3 daily returns, close i_cut -> close i_p1); net = -0.17'),
    ('d1, d2, d3, take_profit', 'trade A outcome', '%', 'events_ta'),
    ('next20, next20_vs_nifty', 'outcome', '%', 'events.csv x100'),
    ('raw_H{5,10,20}, nifty_H{5,10,20}', 'trade B outcome', '%', 'stock / Nifty return close k -> close k+H (tafa run_tests definition)'),
    ('tradable_B', 'trade B', 'bool', 'k+21 <= last session, <= 2 no-trade sessions in k+1..k+21, XN known'),
    ('vsN_H20, vsN_net_H20', 'trade B outcome', '%', 'raw_H20 - nifty_H20; net = -0.19'),
]
pd.DataFrame(ODOC, columns=['columns', 'kind', 'unit', 'meaning']).to_csv(f'{HERE}/columns_outcomes.csv', index=False)
