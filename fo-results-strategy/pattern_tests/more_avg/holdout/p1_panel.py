#!/usr/bin/env python3
"""Holdout evaluator - step 1: per-result panel (all 22 quarters) with my own recomputed entry features and cash outcomes.

Features (all known at the close of k = i_react):
  XN        = (stock adj return on k - Nifty 50 return on k) * 100, from returns.csv / index_close.csv
  rsi_cut   = Wilder RSI(14) on the stock's own adjusted traded closes (adjusted_ohlcv), SMA seed of first 14 changes,
              value at the last traded close with session index <= i_cut
  brk20     = close(k) > max high over the prior 20 traded rows (needs the stock to trade on k and 20 prior rows)
  volr50    = volume(k) / mean volume over prior 50 traded rows
  vix_k     = India VIX close on session k
Outcomes: H20 / H60 close-entry, pullback entry (C25), next-open entries (need nifty_open.csv from p2).
Writes panel.csv (one row per in_fo result).
"""
import os
import numpy as np
import pandas as pd

SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = f'{SP}/more_avg/holdout'
D = f'{SP}/sector_lab/data'

ses = pd.read_csv(f'{D}/sessions.csv')
NS = len(ses)
LAST = NS - 1
day2i = dict(zip(ses.day, ses.i))
assert (ses.i.to_numpy() == np.arange(NS)).all() and ses.day.iloc[-1] == '2026-09-30'
ret = pd.read_csv(f'{D}/returns.csv', index_col=0)
assert (ret.index == ses.day).all()
ix = pd.read_csv(f'{D}/index_close.csv', index_col=0, usecols=['day', 'Nifty 50', 'India VIX'])
assert (ix.index == ses.day).all()
SYM = {s: j for j, s in enumerate(ret.columns)}
R = ret.to_numpy(float)
PX = np.cumprod(1 + np.nan_to_num(R), axis=0)
CV = np.vstack([np.zeros((1, R.shape[1])), np.cumsum(~np.isnan(R), axis=0)])   # CV[t+1] = valid count in 0..t
N = ix['Nifty 50'].to_numpy(float)
VIX = ix['India VIX'].to_numpy(float)
NRET = np.r_[np.nan, N[1:] / N[:-1] - 1]

fe = pd.read_csv(f'{SP}/tafa/C_post_results/features.csv')
ev = pd.read_csv(f'{D}/events.csv', usecols=['symbol', 'qn', 'quarter', 'period', 'i_cut', 'i_rd', 'i_react', 'in_fo',
                                            'reaction_day', 'mcap', 'fin_type'])
assert len(fe) == 3280
P = fe[['symbol', 'quarter', 'qn', 'reaction_day', 'i_cut', 'i_rd', 'i_react', 'XN', 'cut_rsi14',
        'rx_don20_break_up', 'rx_vol_ratio_50']].rename(columns={'XN': 'XN_fe', 'cut_rsi14': 'rsi_fe',
                                                                 'rx_don20_break_up': 'brk20_fe',
                                                                 'rx_vol_ratio_50': 'volr50_fe'}).copy()
chk = P.merge(ev, on=['symbol', 'qn'], how='left', suffixes=('', '_ev'), validate='1:1')
assert (chk.i_react == chk.i_react_ev).all() and (chk.i_cut == chk.i_cut_ev).all()
P['period'] = chk.period.to_numpy()
k = P.i_react.to_numpy(int)
jx = P.symbol.map(SYM).to_numpy(int)

# ---------------------------------------------------------------- XN, VIX
P['XN'] = (R[k, jx] - NRET[k]) * 100
P['vix_k'] = VIX[k]
P['vix_km1'] = VIX[k - 1]

# ---------------------------------------------------------------- OHLCV-based features
oh = pd.read_csv(f'{SP}/ta/build/adjusted_ohlcv.csv.gz', usecols=['day', 'symbol', 'open', 'high', 'low', 'close',
                                                                  'volume'])
oh['i'] = oh.day.map(day2i)
assert oh.i.notna().all()
oh = oh.sort_values(['symbol', 'i']).reset_index(drop=True)


def wilder_rsi(c, n=14):
    out = np.full(len(c), np.nan)
    if len(c) <= n:
        return out
    d = np.diff(c)
    g, l = np.clip(d, 0, None), np.clip(-d, 0, None)
    ag, al = g[:n].mean(), l[:n].mean()

    def val(a, b):
        if b == 0:
            return 100.0 if a > 0 else 50.0
        return 100 - 100 / (1 + a / b)
    out[n] = val(ag, al)
    for t in range(n, len(d)):
        ag = (ag * (n - 1) + g[t]) / n
        al = (al * (n - 1) + l[t]) / n
        out[t + 1] = val(ag, al)
    return out


feat = {}
OPEN_CLOSE = {}   # (symbol, session i) -> (open, close) adjusted
for s, g in oh.groupby('symbol', sort=False):
    ii = g.i.to_numpy(int)
    c, h, v, o = g.close.to_numpy(float), g.high.to_numpy(float), g.volume.to_numpy(float), g.open.to_numpy(float)
    rs = wilder_rsi(c)
    feat[s] = (ii, c, h, v, o, rs)

rsi_cut, brk, volr, oc_k1 = [], [], [], []
for s, icut, kk in zip(P.symbol, P.i_cut, P.i_react):
    ii, c, h, v, o, rs = feat[s]
    p = np.searchsorted(ii, icut, side='right') - 1
    rsi_cut.append(rs[p] if p >= 0 else np.nan)
    q = np.searchsorted(ii, kk)
    if q < len(ii) and ii[q] == kk and q >= 20:
        brk.append(float(c[q] > h[q - 20:q].max()))
    else:
        brk.append(np.nan)
    if q < len(ii) and ii[q] == kk and q >= 50:
        volr.append(v[q] / v[q - 50:q].mean())
    else:
        volr.append(np.nan)
P['rsi_cut'] = rsi_cut
P['brk20'] = brk
P['volr50'] = volr


def ohlc_at(s, i):
    ii, c, h, v, o, rs = feat[s]
    q = np.searchsorted(ii, i)
    if q < len(ii) and ii[q] == i:
        return o[q], c[q]
    return np.nan, np.nan


# ---------------------------------------------------------------- outcomes
def blanks(j, a, b):
    """blank daily returns in sessions a..b inclusive"""
    return (b - a + 1) - (CV[b + 1, j] - CV[a, j])


def close_trade(j, e, H):
    """long at close e, exit close e+H; tradable if e+max(21,H+1) <= LAST and <= 2 blanks in e+1..e+W."""
    W = max(21, H + 1)
    if e + W > LAST:
        return np.nan, np.nan, 'data_end'
    if blanks(j, e + 1, e + W) > 2:
        return np.nan, np.nan, 'blanks'
    return (PX[e + H, j] / PX[e, j] - 1) * 100, (N[e + H] / N[e] - 1) * 100, 'ok'


rows = []
for r_, (s, kk, j) in enumerate(zip(P.symbol, k, jx)):
    o = {}
    for H in (20, 60):
        st, nf, why = close_trade(j, kk, H)
        o[f'stk_H{H}'], o[f'nif_H{H}'], o[f'ok_H{H}'] = st, nf, why
    # pullback entry: first session in k+1..k+5 with return < 0 (blank does not count)
    e = np.nan
    for t in range(kk + 1, min(kk + 5, LAST) + 1):
        if np.isfinite(R[t, j]) and R[t, j] < 0:
            e = t
            break
    o['pb_e'] = e
    if np.isfinite(e):
        st, nf, why = close_trade(j, int(e), 60)
    else:
        st, nf, why = np.nan, np.nan, 'no_down_day'
    o['stk_PB60'], o['nif_PB60'], o['ok_PB60'] = st, nf, why
    # next-open data: stock open/close on k+1 (adjusted), for open-entry versions
    if kk + 1 <= LAST:
        op, cl = ohlc_at(s, kk + 1)
        o['oc_k1'] = cl / op if op > 0 else np.nan
    else:
        o['oc_k1'] = np.nan
    if np.isfinite(e) and e + 1 <= LAST:
        op, cl = ohlc_at(s, int(e) + 1)
        o['oc_e1'] = cl / op if op > 0 else np.nan
    else:
        o['oc_e1'] = np.nan
    rows.append(o)
O = pd.DataFrame(rows)
P = pd.concat([P, O], axis=1)

# checks vs features.csv / trades.csv (all quarters: features are not outcomes; outcomes checked vs tafa trades.csv)
P.to_csv(f'{OUT}/panel.csv', index=False, float_format='%.6f')
print('XN max abs diff vs features:', np.nanmax(np.abs(P.XN - P.XN_fe)))
dr = np.abs(P.rsi_cut - P.rsi_fe)
print('RSI max abs diff vs features:', np.nanmax(dr), ' n>0.01:', int((dr > 0.01).sum()), ' rsi NaN:', int(P.rsi_cut.isna().sum()))
side = ((P.rsi_cut > 50) != (P.rsi_fe > 50)).sum()
print('RSI>50 classification disagreements:', int(side))
b = P[['brk20', 'brk20_fe']].dropna()
print('brk20 rows', len(b), 'disagree', int((b.brk20 != b.brk20_fe).sum()), ' brk NaN mine', int(P.brk20.isna().sum()),
      ' fe NaN', int(P.brk20_fe.isna().sum()))
v = P[['volr50', 'volr50_fe']].dropna()
print('volr50 max abs diff', float(np.abs(v.volr50 - v.volr50_fe).max()), ' NaN mine', int(P.volr50.isna().sum()),
      ' fe NaN', int(P.volr50_fe.isna().sum()))
print('VIX NaN at k:', int(P.vix_k.isna().sum()))
print('ok_H20 counts:', P.ok_H20.value_counts().to_dict())
print('ok_H60 counts by holdout/discovery:', P.groupby(P.qn >= 14).ok_H60.value_counts().to_dict())
print('oc_k1 NaN:', int(P.oc_k1.isna().sum()))
