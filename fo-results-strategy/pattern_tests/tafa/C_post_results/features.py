#!/usr/bin/env python3
"""Features only (NO outcomes) for the post-results TA + FA tests - see PREREGISTRATION.txt in this folder.

Writes features.csv (one row per in_fo result) and quiet_days.csv.gz (placebo stock-days with their TA / last-reported
FA flags). Reads inputs read-only; imports indicators() from the TA builder unchanged.
"""
import importlib.util
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.environ.get('LAB_ROOT', os.path.abspath(os.path.join(HERE, '..', '..')))  # scratch data folder
DATA = f'{SP}/sector_lab/data'
TAB = f'{SP}/ta/build'
FAP = f'{SP}/fa/build/fa_panel.csv'

spec = importlib.util.spec_from_file_location('ta_build_panel', f'{TAB}/build_panel.py')
bp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bp)

ses = pd.read_csv(f'{DATA}/sessions.csv')
days = ses.day.tolist()
DIX = {d: i for i, d in enumerate(days)}
T = len(days)
ret = pd.read_csv(f'{DATA}/returns.csv', index_col=0)
assert ret.index.tolist() == days
syms = ret.columns.tolist()
SYM = {s: j for j, s in enumerate(syms)}
N = len(syms)
R = ret.to_numpy(float)
nifty = pd.read_csv(f'{DATA}/index_close.csv', index_col=0, usecols=['day', 'Nifty 50'])['Nifty 50'].to_numpy(float)
nret = np.r_[np.nan, nifty[1:] / nifty[:-1] - 1]

px = pd.read_csv(f'{TAB}/adjusted_ohlcv.csv.gz', usecols=['day', 'symbol', 'open', 'high', 'low', 'close', 'volume'])
px = px[px.symbol.isin(SYM)]
px['i'] = px.day.map(DIX)
assert px.i.notna().all()
M = {}
for f in ('open', 'high', 'low', 'close', 'volume'):
    a = np.full((T, N), np.nan)
    a[px.i.to_numpy(int), px.symbol.map(SYM).to_numpy(int)] = px[f].to_numpy(float)
    M[f] = a

FIELDS = ['n_hist', 'rsi14', 'close_vs_sma50_pct', 'close_vs_sma200_pct', 'don20_break_up', 'don20_break_dn',
          'gap_pct', 'low_vs_prevclose_pct', 'vol_ratio_50']
X = {k: np.full((T, N), np.nan) for k in FIELDS}
for j in range(N):
    rows = np.flatnonzero(np.isfinite(M['close'][:, j]))
    if len(rows) == 0:
        continue
    o, h, l, c, v = (M[f][rows, j] for f in ('open', 'high', 'low', 'close', 'volume'))
    I = bp.indicators(o, h, l, c, v)
    for k in ['n_hist', 'rsi14', 'close_vs_sma50_pct', 'close_vs_sma200_pct', 'don20_break_up', 'don20_break_dn',
              'gap_pct']:
        X[k][rows, j] = I[k]
    cp = bp.shift(c)
    X['low_vs_prevclose_pct'][rows, j] = (l / cp - 1) * 100
    prior50 = bp.shift(bp.roll(v, 50, 'mean'))           # mean of v over k-50..k-1 (traded days)
    with np.errstate(divide='ignore', invalid='ignore'):
        X['vol_ratio_50'][rows, j] = v / prior50

# ------------------------------------------------------------------ check vs events_ta at the cutoff
eta = pd.read_csv(f'{TAB}/events_ta.csv')
eta = eta[eta.symbol.isin(SYM)].copy()
jj = eta.symbol.map(SYM).to_numpy(int)
ic = eta.i_cut.to_numpy(int)
for k in ['n_hist', 'rsi14', 'close_vs_sma50_pct', 'close_vs_sma200_pct', 'don20_break_up', 'don20_break_dn', 'gap_pct']:
    a, b = X[k][ic, jj], eta[k].to_numpy(float)
    both = np.isfinite(a) & np.isfinite(b)
    assert (np.isfinite(a) == np.isfinite(b)).all(), k
    mx = np.max(np.abs(a[both] - b[both]) / np.maximum(1, np.abs(b[both])))
    print(f'check vs events_ta at cutoff: {k:22s} n={both.sum()} max rel diff {mx:.1e}')
    assert mx < 1e-4, k

# ------------------------------------------------------------------ results features
ev = pd.read_csv(f'{DATA}/events.csv')
fa = pd.read_csv(FAP)
f = fa[fa.in_fo == True].copy()
f = f.merge(ev[['symbol', 'qn', 'i_cut', 'i_rd', 'i_react']], on=['symbol', 'qn'], how='left', validate='1:1')
f = f.merge(eta[['symbol', 'qn', 'rsi14', 'close_vs_sma200_pct']].rename(
    columns={'rsi14': 'cut_rsi14', 'close_vs_sma200_pct': 'cut_close_vs_sma200_pct'}), on=['symbol', 'qn'],
    how='left', validate='1:1')
assert f.i_react.notna().all()
f['i_react'] = f.i_react.astype(int)
assert (np.array(days)[f.i_react] == f.reaction_day.values).all()
j = f.symbol.map(SYM).to_numpy(int)
k = f.i_react.to_numpy(int)
for c_ in FIELDS:
    f['rx_' + c_] = X[c_][k, j]


def flags(d, rq=True):
    """GOOD / BAD and their eligibility from reported-quarter numbers (rq_* columns)."""
    pat, sal = d.rq_pat_yoy_pct, d.rq_sales_yoy_pct
    mchg = pd.Series(np.where(d.fin_type == 'Company', d.rq_ebitda_margin_chg_yoy_pp, d.rq_net_margin_chg_yoy_pp),
                     index=d.index)
    e_str = pat.notna() & sal.notna()
    e_m = mchg.notna()
    good = (e_str & (pat > 25) & (sal > 15)) | (e_m & (mchg > 2))
    bad = (pat.notna() & (pat < -25)) | (e_m & (mchg < -2))
    return mchg, good, e_str | e_m, bad, pat.notna() | e_m


f['MCHG'], f['GOOD'], f['E_GOOD'], f['BAD'], f['E_BAD'] = flags(f)
roe, de, pe = f.roe_pct, f.debt_equity, f.pe
f['E_QHI'] = roe.notna() & de.notna()
f['Q_HI'] = f.E_QHI & (roe > 15) & (de < 0.5)
f['E_QLO'] = f.E_QHI & (f.fin_type == 'Company')
f['Q_LO'] = f.E_QLO & ((roe < 10) | (de > 1))
f['E_PE'] = f.ttm_pat.notna() & f.mcap_cr.notna()
f['CHEAP'] = f.E_PE & pe.notna() & (pe < 15)
f['EXP'] = f.E_PE & pe.notna() & (pe > 50)
s200, rsi = f.cut_close_vs_sma200_pct, f.cut_rsi14
f['E_S200'] = s200.notna()
f['UP200'] = f.E_S200 & (s200 > 0)
f['DN200'] = f.E_S200 & (s200 < 0)
f['E_RSI'] = rsi.notna()
f['RSI_HI'] = f.E_RSI & (rsi > 50)
f['RSI_LO'] = f.E_RSI & (rsi < 50)
f['E_TA_RX'] = (f.rx_n_hist >= 51) & f.rx_vol_ratio_50.notna() & f.rx_close_vs_sma50_pct.notna()
vol15 = f.rx_vol_ratio_50 >= 1.5
f['BRK20'] = f.E_TA_RX & (f.rx_don20_break_up == 1)
f['GAPHOLD'] = f.E_TA_RX & (f.rx_gap_pct > 2) & (f.rx_low_vs_prevclose_pct > 0)
f['VOL15'] = f.E_TA_RX & vol15
f['BREAKOUT_VOL'] = (f.BRK20 | f.GAPHOLD) & f.VOL15
f['BELOW50'] = f.E_TA_RX & (f.rx_close_vs_sma50_pct < 0)
f['BRKDN_VOL'] = f.E_TA_RX & (f.rx_don20_break_dn == 1) & f.VOL15
# reaction vs Nifty (feature of the reaction day itself, known at the entry close)
xn = np.array([(R[a, b] - nret[a]) * 100 for a, b in zip(k, j)])
f['XN'] = xn
f['W'] = f.XN > 4
FLAGS = ['GOOD', 'E_GOOD', 'BAD', 'E_BAD', 'Q_HI', 'E_QHI', 'Q_LO', 'E_QLO', 'CHEAP', 'EXP', 'E_PE', 'UP200', 'DN200',
         'E_S200', 'RSI_HI', 'RSI_LO', 'E_RSI', 'E_TA_RX', 'BRK20', 'GAPHOLD', 'VOL15', 'BREAKOUT_VOL', 'BELOW50',
         'BRKDN_VOL', 'W']
for c_ in FLAGS:
    f[c_] = f[c_].fillna(False).astype(bool)
keep = ['symbol', 'quarter', 'qn', 'fin_type', 'timing', 'results_date', 'reaction_day', 'i_cut', 'i_rd', 'i_react',
        'XN', 'rq_pat_yoy_pct', 'rq_sales_yoy_pct', 'MCHG', 'roe_pct', 'debt_equity', 'pe', 'cut_rsi14',
        'cut_close_vs_sma200_pct'] + ['rx_' + c_ for c_ in FIELDS] + FLAGS
f[keep].to_csv(f'{HERE}/features.csv', index=False, float_format='%.6g')
print(f'features.csv: {len(f)} in_fo results')

# ------------------------------------------------------------------ quiet days (placebo), no outcomes
evs = ev[ev.symbol.isin(SYM)].copy()
fa_all = fa.merge(ev[['symbol', 'qn', 'i_rd', 'i_react']], on=['symbol', 'qn'], how='left', validate='1:1')
_, fa_all['GOOD'], fa_all['E_GOOD'], fa_all['BAD'], fa_all['E_BAD'] = flags(fa_all)
fa_all = fa_all.set_index(['symbol', 'qn'])
parts = []
LAST = T - 1
for s, g in evs.sort_values('i_rd').groupby('symbol'):
    jx = SYM[s]
    g = g.reset_index(drop=True)
    res = np.zeros(T + 40, bool)
    res[g.i_rd.to_numpy(int)] = True
    res[g.i_react.to_numpy(int)] = True
    cres = np.concatenate([[0], np.cumsum(res)])
    kk = np.arange(T - 21)
    lo, hi = np.clip(kk - 10, 0, None), kk + 21                 # result sessions in [k-10, k+20] disqualify
    quiet = (cres[hi] - cres[lo]) == 0
    rd = g.i_rd.to_numpy(int)
    nxt = np.searchsorted(rd, kk, side='right')
    prv = nxt - 1
    has_prev, has_next = prv >= 0, nxt < len(g)
    traded = np.isfinite(M['close'][kk, jx])
    keepk = quiet & has_prev & traded
    kk, prv, nxt, has_next = kk[keepk], prv[keepk], nxt[keepk], has_next[keepk]
    fo_prev = g.in_fo.to_numpy()[prv]
    fo_next = np.where(has_next, g.in_fo.to_numpy()[np.minimum(nxt, len(g) - 1)], None)
    both = np.array([(a == True) and (b is None or b == True) for a, b in zip(fo_prev, fo_next)])
    kk, prv = kk[both], prv[both]
    if len(kk) == 0:
        continue
    qprev = g.qn.to_numpy()[prv]
    fx = fa_all.loc[[(s, q) for q in qprev], ['GOOD', 'E_GOOD', 'BAD', 'E_BAD', 'i_react']]
    assert (fx.i_react.to_numpy() < kk).all()
    part = pd.DataFrame({'symbol': s, 'i': kk, 'day': np.array(days)[kk], 'qn_prev': qprev,
                         'XN': (R[kk, jx] - nret[kk]) * 100})
    for c_ in ['GOOD', 'E_GOOD', 'BAD', 'E_BAD']:
        part['L_' + c_] = fx[c_].to_numpy().astype(bool)
    for c_ in FIELDS:
        part['rx_' + c_] = X[c_][kk, jx]
    km2 = kk - 2
    part['m2_rsi14'] = X['rsi14'][km2, jx]
    part['m2_close_vs_sma200_pct'] = X['close_vs_sma200_pct'][km2, jx]
    parts.append(part)
q = pd.concat(parts, ignore_index=True)
q['E_TA_RX'] = (q.rx_n_hist >= 51) & q.rx_vol_ratio_50.notna() & q.rx_close_vs_sma50_pct.notna()
v15 = q.rx_vol_ratio_50 >= 1.5
q['BREAKOUT_VOL'] = q.E_TA_RX & ((q.rx_don20_break_up == 1) | ((q.rx_gap_pct > 2) & (q.rx_low_vs_prevclose_pct > 0))) & v15
q['BELOW50'] = q.E_TA_RX & (q.rx_close_vs_sma50_pct < 0)
q['BRKDN_VOL'] = q.E_TA_RX & (q.rx_don20_break_dn == 1) & v15
q['E_S200'] = q.m2_close_vs_sma200_pct.notna()
q['UP200'] = q.E_S200 & (q.m2_close_vs_sma200_pct > 0)
q['DN200'] = q.E_S200 & (q.m2_close_vs_sma200_pct < 0)
q['E_RSI'] = q.m2_rsi14.notna()
q['RSI_HI'] = q.E_RSI & (q.m2_rsi14 > 50)
q['RSI_LO'] = q.E_RSI & (q.m2_rsi14 < 50)
q['W'] = q.XN > 4
q.to_csv(f'{HERE}/quiet_days.csv.gz', index=False, float_format='%.6g', compression='gzip')
print(f'quiet_days.csv.gz: {len(q)} stock-days, symbols {q.symbol.nunique()}, {q.day.min()}..{q.day.max()}, '
      f'quiet winners {int(q.W.sum())}')
