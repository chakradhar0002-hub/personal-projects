#!/usr/bin/env python3
"""Skeptic step 1 (own code): signals + per-trade outcomes + daily paths for C12 and C42 (and neighbours).

Everything is rebuilt from the raw files (returns.csv, index_close.csv, adjusted_ohlcv.csv.gz, panel.csv,
fa_panel.csv). Nothing is imported from the search or holdout folders. Writes:
  trades.parquet-like CSV  (skeptic_panel.csv): one row per F&O result with my features and outcomes
  stock_day.npz            : per-stock daily TA arrays used again by the placebo script
"""
import numpy as np
import pandas as pd

SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = f'{SP}/negative_avg/skeptic'

days = pd.read_csv(f'{SP}/sector_lab/data/sessions.csv').day.tolist()
T = len(days)
DIX = {d: i for i, d in enumerate(days)}
ret = pd.read_csv(f'{SP}/sector_lab/data/returns.csv', index_col=0)
assert ret.index.tolist() == days
SYMS = list(ret.columns)
SYM = {s: j for j, s in enumerate(SYMS)}
R = ret.to_numpy(float)
N = pd.read_csv(f'{SP}/sector_lab/data/index_close.csv', index_col=0, usecols=['day', 'Nifty 50'])['Nifty 50']
assert N.index.tolist() == days
N = N.to_numpy(float)
NR = np.r_[np.nan, N[1:] / N[:-1] - 1]

# ---------------------------------------------------------------- per-stock daily TA on the stock's traded days,
# mapped back onto the session grid (NaN on sessions where the stock did not trade)
px = pd.read_csv(f'{SP}/ta/build/adjusted_ohlcv.csv.gz', usecols=['day', 'symbol', 'open', 'high', 'low', 'close',
                                                                   'volume'])
px['i'] = px.day.map(DIX).astype(int)
S = len(SYMS)
CL = np.full((T, S), np.nan); SMA50 = CL.copy(); SMA200 = CL.copy(); LOW20 = CL.copy(); VOLR = CL.copy()
OP = CL.copy(); HI = CL.copy(); NH = CL.copy()
for s, g in px.groupby('symbol'):
    if s not in SYM:
        continue
    g = g.sort_values('i')
    j = SYM[s]
    ii = g.i.to_numpy()
    c = g.close.astype(float)
    lo = g.low.astype(float)
    v = g.volume.astype(float)
    CL[ii, j] = c.to_numpy()
    OP[ii, j] = g.open.to_numpy(float)
    HI[ii, j] = g.high.to_numpy(float)
    NH[ii, j] = np.arange(1, len(ii) + 1)
    SMA50[ii, j] = c.rolling(50, min_periods=50).mean().to_numpy()
    SMA200[ii, j] = c.rolling(200, min_periods=200).mean().to_numpy()
    LOW20[ii, j] = lo.shift(1).rolling(20, min_periods=20).min().to_numpy()     # prior 20 traded sessions
    vm = v.shift(1).rolling(50, min_periods=50).mean()
    VOLR[ii, j] = (v / vm.where(vm > 0)).to_numpy()
np.savez_compressed(f'{OUT}/stock_day.npz', CL=CL, SMA50=SMA50, SMA200=SMA200, LOW20=LOW20, VOLR=VOLR, NH=NH,
                    OP=OP, HI=HI)

# ---------------------------------------------------------------- results panel
K = ['symbol', 'qn']
pan = pd.read_csv(f'{SP}/perf/features/panel.csv', usecols=K + ['quarter', 'timing', 'i_cut', 'i_rd', 'i_p1',
                                                                  'i_react', 'XN'])
pan = pan.rename(columns={'XN': 'XN_panel'})
j = pan.symbol.map(SYM).to_numpy(int)
k = pan.i_react.to_numpy(int)
pan['j'] = j
pan['entry_day'] = [days[x] for x in k]
pan['XN'] = (R[k, j] - NR[k]) * 100
pan['c50'] = (CL[k, j] / SMA50[k, j] - 1) * 100
pan['c200'] = (CL[k, j] / SMA200[k, j] - 1) * 100
pan['brk20'] = CL[k, j] < LOW20[k, j]
pan.loc[np.isnan(LOW20[k, j]), 'brk20'] = False
pan['volr50'] = VOLR[k, j]
pan['nhist'] = NH[k, j]

fa = pd.read_csv(f'{SP}/fa/build/fa_panel.csv', usecols=K + ['fin_type', 'rq_pat_yoy_pct',
                                                            'rq_ebitda_margin_chg_yoy_pp', 'rq_net_margin_chg_yoy_pp'])
pan = pan.merge(fa, on=K, how='left', validate='1:1')
mchg = np.where(pan.fin_type == 'Company', pan.rq_ebitda_margin_chg_yoy_pp, pan.rq_net_margin_chg_yoy_pp)
pan['BAD'] = ((pan.rq_pat_yoy_pct < -25) | (mchg < -2))
pan['BRKDN_VOL'] = pan.brk20 & (pan.volr50 >= 1.5) & (pan.nhist >= 51)
pan['L4'] = pan.XN < -4
pan['C12'] = pan.L4 & (pan.c50 < 0) & (pan.c200 < 0)
pan['C42'] = pan.BAD & pan.BRKDN_VOL
pan['C22'] = pan.L4 & (pan.c200 < 0)

# ---------------------------------------------------------------- outcomes: short stock / long Nifty from close e
def outcome(e, jj, H):
    x = e + H
    if x > T - 1 or not np.isfinite(R[e, jj]):
        return np.nan, np.nan, np.nan, np.nan, np.nan, np.nan
    w = R[e + 1:x + 1, jj]
    if np.isnan(w).sum() > 2:
        return (np.nan,) * 6
    w = np.nan_to_num(w)
    path = np.cumprod(1 + w)                       # stock value / entry
    npath = N[e + 1:x + 1] / N[e]
    st = (path[-1] - 1) * 100
    nf = (npath[-1] - 1) * 100
    max_up_day = np.max(w) * 100                   # biggest one-day rise of the stock against the short
    max_rel_day = np.max(w - NR[e + 1:x + 1]) * 100  # biggest one-day rise vs Nifty
    mae = np.max((path - 1) - (npath - 1)) * 100   # worst point of the hedged short during the hold
    return st, nf, max_up_day, max_rel_day, mae, x


for H in (10, 20, 40):
    res = np.array([outcome(e, jj, H) for e, jj in zip(k, j)], float)
    pan[f'st{H}'] = res[:, 0]
    pan[f'nf{H}'] = res[:, 1]
    if H == 20:
        pan['max_up_day'] = res[:, 2]
        pan['max_rel_day'] = res[:, 3]
        pan['mae_hedged'] = res[:, 4]
# realistic: enter close k+1 (requires a trade on k+1)
res = []
for e, jj in zip(k, j):
    if e + 1 > T - 1 or not np.isfinite(R[e + 1, jj]):
        res.append((np.nan, np.nan)); continue
    o = outcome(e + 1, jj, 20)
    res.append((o[0], o[1]))
res = np.array(res, float)
pan['st20_k1'], pan['nf20_k1'] = res[:, 0], res[:, 1]

# pre-entry beta to Nifty (250 sessions ending k-1, at least 120 traded days)
beta = np.full(len(pan), np.nan)
for r, (e, jj) in enumerate(zip(k, j)):
    a = R[max(0, e - 250):e, jj]; b = NR[max(0, e - 250):e]
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() >= 120:
        beta[r] = np.cov(a[m], b[m])[0, 1] / np.var(b[m], ddof=1)
pan['beta250'] = beta
# Nifty regime at entry: above / below its 200-session average; Nifty 20-session return before entry
NS200 = pd.Series(N).rolling(200).mean().to_numpy()
pan['nifty_above200'] = N[k] > NS200[k]
pan['nifty_pre20'] = (N[k] / N[k - 20] - 1) * 100

first_qn = pan.groupby('symbol').qn.transform('min')
pan['first_qn'] = first_qn
pan['sample'] = np.where(pan.qn <= 13, 'discovery', 'holdout')
pan.drop(columns=['rq_ebitda_margin_chg_yoy_pp', 'rq_net_margin_chg_yoy_pp']).to_csv(
    f'{OUT}/skeptic_panel.csv', index=False, float_format='%.6g')

# ---------------------------------------------------------------- checks against the holdout evaluator's numbers
ev = pd.read_csv(f'{SP}/negative_avg/holdout/eval_panel.csv', usecols=K + ['C12', 'C42', 'B0_vsN', 'B0_stock'])
m = pan.merge(ev, on=K, suffixes=('', '_ev'))
print('C12 flag disagreements', int((m.C12 != m.C12_ev).sum()), ' C42', int((m.C42 != m.C42_ev).sum()))
print('XN vs panel max diff', np.nanmax(np.abs(pan.XN - pan.XN_panel)))
d = (m.st20 - m.nf20) - m.B0_vsN
print('20d vsN max diff vs holdout evaluator', np.nanmax(np.abs(d)), 'nan mismatch',
      int((m.st20.isna() != m.B0_vsN.isna()).sum()))
for c in ['C12', 'C42', 'C22']:
    print(c, pan.groupby('sample')[c].sum().to_dict())
