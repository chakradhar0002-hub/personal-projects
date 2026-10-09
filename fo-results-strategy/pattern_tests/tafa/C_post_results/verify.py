#!/usr/bin/env python3
"""Independent re-computation of the headline numbers (does not import features.py / run_tests.py / build_panel.py).

Rebuilds from raw inputs with plain pandas: XN, plain winners, reaction-day breakout / SMA50 / breakdown / volume
flags (rolling windows on adjusted_ohlcv per symbol), GOOD / BAD from fa_panel, cutoff RSI / SMA200 from events_ta,
20/10/5-session hedged outcomes, then compares with results_tests.csv.
"""
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.path.abspath(os.path.join(HERE, '..', '..'))
D = f'{SP}/sector_lab/data'
ses = pd.read_csv(f'{D}/sessions.csv').day.tolist()
ret = pd.read_csv(f'{D}/returns.csv', index_col=0)
nif = pd.read_csv(f'{D}/index_close.csv', index_col=0)['Nifty 50']
ev = pd.read_csv(f'{D}/events.csv')
fa = pd.read_csv(f'{SP}/fa/build/fa_panel.csv')
eta = pd.read_csv(f'{SP}/ta/build/events_ta.csv')
px = pd.read_csv(f'{SP}/ta/build/adjusted_ohlcv.csv.gz')

# reaction-day TA, independent rolling code per symbol on traded days
px = px.sort_values(['symbol', 'day'])
g = px.groupby('symbol')
px['hh20_prior'] = g.high.transform(lambda s: s.shift(1).rolling(20).max())
px['ll20_prior'] = g.low.transform(lambda s: s.shift(1).rolling(20).min())
px['v50_prior'] = g.volume.transform(lambda s: s.shift(1).rolling(50).mean())
px['sma50'] = g.close.transform(lambda s: s.rolling(50).mean())
px['prev_close'] = g.close.shift(1)
px['nh'] = g.cumcount() + 1
px = px.set_index(['symbol', 'day'])

f = fa[fa.in_fo == True].merge(ev[['symbol', 'qn', 'i_react']], on=['symbol', 'qn'])
f = f.merge(eta[['symbol', 'qn', 'rsi14', 'close_vs_sma200_pct']], on=['symbol', 'qn'])
f['rday'] = [ses[i] for i in f.i_react]
t = px.reindex(list(zip(f.symbol, f.rday)))
for c in ['open', 'high', 'low', 'close', 'volume', 'hh20_prior', 'll20_prior', 'v50_prior', 'sma50', 'prev_close', 'nh']:
    f['t_' + c] = t[c].to_numpy()
el = (f.t_nh >= 51)
vol = el & (f.t_volume >= 1.5 * f.t_v50_prior)
brk = (f.t_close > f.t_hh20_prior * (1 + 1e-9)) | ((f.t_open / f.t_prev_close - 1 > 0.02) & (f.t_low > f.t_prev_close))
f['BO'] = el & brk & vol
f['B50'] = el & (f.t_close < f.t_sma50)
f['BD'] = el & (f.t_close < f.t_ll20_prior * (1 - 1e-9)) & vol
mchg = np.where(f.fin_type == 'Company', f.rq_ebitda_margin_chg_yoy_pp, f.rq_net_margin_chg_yoy_pp)
f['GOOD'] = ((f.rq_pat_yoy_pct > 25) & (f.rq_sales_yoy_pct > 15)) | (mchg > 2)
f['BAD'] = (f.rq_pat_yoy_pct < -25) | (mchg < -2)

# outcomes
G = (1 + ret.fillna(0)).cumprod()
cols = {s: k for k, s in enumerate(ret.columns)}
Gv, Nv, Rv = G.to_numpy(), nif.to_numpy(), ret.to_numpy()
jj = f.symbol.map(cols).to_numpy()
k = f.i_react.to_numpy()
f['XN'] = (Rv[k, jj] - (Nv[k] / Nv[k - 1] - 1)) * 100
for H in (5, 10, 20):
    f[f'v{H}'] = ((Gv[k + H, jj] / Gv[k, jj] - 1) - (Nv[k + H] / Nv[k] - 1)) * 100
W = f.XN > 4


def show(name, m, H, d=1):
    x = d * f.loc[m, f'v{H}'] - 0.19
    q = f.loc[m, 'qn']
    qm = x.groupby(q).mean()
    wq = (f.loc[W, f'v{H}'] - 0.19).groupby(f.loc[W, 'qn']).mean()
    dW = (x - wq.reindex(q).to_numpy()).mean()
    return dict(test=name, H=H, n=int(m.sum()), vsN_net=x.mean(), q_pos=int((qm > 0).sum()), nq=len(qm), dW=dW)


rows = [show('PLAIN_WINNERS', W, H) for H in (5, 10, 20)]
for H in (5, 10, 20):
    rows.append(show('P1_GOOD_BREAKOUT_VOL', f.GOOD & f.BO, H))
    rows.append(show('P2_GOOD_BELOW50', f.GOOD & f.B50, H))
    rows.append(show('P3_BAD_BRKDN_VOL', f.BAD & f.BD, H, -1))
    rows.append(show('W_RSI_HI', W & (f.rsi14 > 50), H))
    rows.append(show('W_RSI_LO', W & (f.rsi14 < 50), H))
    rows.append(show('W_GOOD&RSI_HI', W & f.GOOD & (f.rsi14 > 50), H))
    rows.append(show('W_ALL_BULL', W & f.GOOD & (f.rsi14 > 50) & (f.close_vs_sma200_pct > 0), H))
v = pd.DataFrame(rows)
r = pd.read_csv(f'{HERE}/results_tests.csv')
m = v.merge(r[['test', 'H', 'n', 'vsN_net', 'q_pos', 'dW']], on=['test', 'H'], how='left', suffixes=('', '_main'))
pd.set_option('display.width', 200)
print(m.round(4).to_string(index=False))
chk = m.dropna(subset=['n_main'])
assert (chk.n == chk.n_main).all()
print("max abs diff vsN_net", (chk.vsN_net - chk.vsN_net_main).abs().max(), "dW", (chk.dW - chk.dW_main).abs().max())
assert np.allclose(chk.vsN_net, chk.vsN_net_main, atol=1e-3) and np.allclose(chk.dW, chk.dW_main, atol=1e-3)
print('\nOK: independent recomputation matches results_tests.csv (n, vsN_net, dW) for', len(chk), 'rows')

# independent luck p for W_RSI_HI H20 (5,000 draws)
rng = np.random.default_rng(1)
x = f.loc[W & (f.rsi14 > 50), 'v20'] - 0.19
pool = f[W & f.rsi14.notna()]
qs = f.loc[W & (f.rsi14 > 50), 'qn'].value_counts()
draws = np.zeros(5000)
for q, kq in qs.items():
    vals = pool.loc[pool.qn == q, 'v20'].to_numpy() - 0.19
    draws += np.array([rng.choice(vals, kq, replace=False).sum() for _ in range(5000)])
draws /= qs.sum()
print(f'W_RSI_HI H20 independent luck p = {(1 + (draws >= x.mean()).sum()) / 5001:.4f} (main: '
      f"{r[(r.test == 'W_RSI_HI') & (r.H == 20)].p_W_ELIG.iloc[0]:.4f})")
