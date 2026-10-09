"""Cross-check of trade outcomes against RAW exchange closes (report/nse_prices.db, read-only).
  px(day, symbol, open, high, low, close, prevclose, volume) raw unadjusted closes; ca(symbol, ex_date, kind, factor, subject)
  idx(day, name, ..., close) index closes.
Stock 20-session return from raw prices = close(k+20) * prod(split/bonus factors with ex_date in (day_k, day_k+20]) / close(k) - 1
Reaction-day return = close(k) * factor(ex_date == day_k) / close(k-1) - 1 ; Nifty from idx 'Nifty 50'.
Part A: 5 random trades (seed 20261009) in detail, day by day. Part B (extra): every one of the 232 trades, endpoint check,
plus all trades with a corporate action inside k..k+20 listed. Part C (extra): RSI14 at the cutoff from raw closes
(split/bonus back-adjusted; demerger ex-day change set to 0 like the blank-return rule) for every winner -> RSI_HI flags.
Writes raw_check.log, raw_check_trades.csv."""
import sqlite3
import os

import numpy as np
import pandas as pd

SP = os.environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = SP + '/winners_rsi/rebuild'
con = sqlite3.connect(f'file:{SP}/report/nse_prices.db?mode=ro', uri=True)
ses = pd.read_csv(SP + '/sector_lab/data/sessions.csv')
D = ses.day.values
T = pd.read_csv(OUT + '/trades.csv')
U = pd.read_csv(OUT + '/universe.csv')
ca = pd.read_sql('select * from ca', con)
nif = pd.read_sql("select day, close from idx where name='Nifty 50'", con).set_index('day')['close']
log = []
P = lambda *a: (print(*a), log.append(' '.join(str(x) for x in a)))


def px(sym, d0, d1):
    return pd.read_sql('select day, close, prevclose from px where symbol=? and day between ? and ? order by day',
                       con, params=(sym, d0, d1)).set_index('day')


def sb_factor(sym, a, b):
    """product of split/bonus factors with ex_date in (a, b]"""
    x = ca[(ca.symbol == sym) & ca.kind.isin(['split', 'bonus']) & (ca.ex_date > a) & (ca.ex_date <= b)]
    return float(np.prod(x.factor.values)) if len(x) else 1.0, x


def ca_in(sym, a, b):
    return ca[(ca.symbol == sym) & (ca.ex_date > a) & (ca.ex_date <= b)]


def check(r, detail=False):
    k = int(r.i_react)
    dk1, dk, de = D[k - 1], D[k], D[k + 20]
    p = px(r.symbol, dk1, de)
    f_hold, cas = sb_factor(r.symbol, dk, de)
    f_k, _ = sb_factor(r.symbol, dk1, dk)
    stock_raw = (p.close[de] * f_hold / p.close[dk] - 1) * 100
    rk_raw = (p.close[dk] * f_k / p.close[dk1] - 1) * 100
    n_raw = (nif[de] / nif[dk] - 1) * 100
    nk_raw = (nif[dk] / nif[dk1] - 1) * 100
    xn_raw = rk_raw - nk_raw
    vs_raw = stock_raw - n_raw - 0.19
    other = ca_in(r.symbol, dk, de)
    other = other[~other.kind.isin(['split', 'bonus'])]
    missing = [d for d in D[k - 1:k + 21] if d not in p.index]
    out = dict(qn=r.qn, symbol=r.symbol, reaction_day=dk, exit_day=de, close_k=p.close[dk], close_exit=p.close[de],
               ca_factor_in_window=f_hold, ca_in_window='; '.join(f'{x.ex_date} {x.kind} x{x.factor}' for x in
                                                                   ca_in(r.symbol, dk, de).itertuples()),
               missing_px_days=len(missing), XN_rebuild=r.XN, XN_raw=xn_raw, stock20_rebuild=r.raw_gross,
               stock20_raw=stock_raw, nifty20_rebuild=r.nifty_H20, nifty20_raw=n_raw, vsN_net_rebuild=r.vsN_net,
               vsN_net_raw=vs_raw, d_stock=stock_raw - r.raw_gross, d_XN=xn_raw - r.XN, d_nifty=n_raw - r.nifty_H20,
               blanks=r.blanks_k1_k21, other_ca=len(other))
    if detail:
        P(f'\n--- {r.symbol} | {r.period} ({r.quarter}) | reaction {dk} -> exit {de} ---')
        P(f'raw close k-1 {dk1}: {p.close[dk1]:.2f}; close k: {p.close[dk]:.2f}; close k+20: {p.close[de]:.2f}; '
          f'split/bonus inside window: {cas[["ex_date", "kind", "factor"]].values.tolist() or "none"}')
        pp = p.reindex(D[k - 1:k + 21])
        fac = pd.Series(1.0, index=pp.index)
        for x in ca[(ca.symbol == r.symbol) & ca.kind.isin(['split', 'bonus'])].itertuples():
            if x.ex_date in fac.index:
                fac[x.ex_date] *= x.factor
        dr = (pp.close * fac / pp.close.shift(1) - 1)
        rr = pd.read_csv(SP + '/sector_lab/data/returns.csv', index_col=0, usecols=['day', r.symbol]).reindex(pp.index)
        P(f'daily raw-adjusted vs returns.csv, k+1..k+20: max |diff| = {(dr - rr[r.symbol]).iloc[2:22].abs().max():.2e}'
          f' (pct points x100: {(100 * (dr - rr[r.symbol]).iloc[2:22].abs().max()):.2e})')
        P(f'XN       rebuild {r.XN:+.4f}  raw {xn_raw:+.4f}   (stock k {rk_raw:+.4f}, Nifty k {nk_raw:+.4f})')
        P(f'stock20  rebuild {r.raw_gross:+.4f}  raw {stock_raw:+.4f}   diff {stock_raw - r.raw_gross:+.2e}')
        P(f'nifty20  rebuild {r.nifty_H20:+.4f}  raw {n_raw:+.4f}   diff {n_raw - r.nifty_H20:+.2e}')
        P(f'vsN_net  rebuild {r.vsN_net:+.4f}  raw {vs_raw:+.4f}')
    return out


# ---------------- Part A: 5 random trades
rng = np.random.default_rng(20261009)
pick = sorted(rng.choice(len(T), size=5, replace=False))
P('PART A - 5 random trades (numpy default_rng(20261009), rows', pick, 'of trades.csv)')
A = pd.DataFrame([check(T.iloc[i], detail=True) for i in pick])

# ---------------- Part B: every trade, endpoint check
B = pd.DataFrame([check(r) for r in T.itertuples(index=False)])
B.to_csv(OUT + '/raw_check_trades.csv', index=False, float_format='%.6f')
P('\nPART B (extra) - all', len(B), 'trades vs raw closes')
for c in ['d_stock', 'd_XN', 'd_nifty']:
    P(f'  {c}: max |diff| {B[c].abs().max():.2e} pts; > 0.01 pts: {int((B[c].abs() > 0.01).sum())}')
P('  trades with a corporate action inside (day_k, day_k+20]:')
P(B[B.ca_in_window != ''][['qn', 'symbol', 'reaction_day', 'exit_day', 'ca_in_window', 'stock20_rebuild', 'stock20_raw',
                           'd_stock', 'blanks']].to_string(index=False))
P('  detail for each trade with a split/bonus inside the holding window:')
for i in B.index[B.ca_factor_in_window != 1.0]:
    check(T.iloc[i], detail=True)
P('  trades with any blank daily return in k+1..k+21:',
  B[B.blanks > 0][['qn', 'symbol', 'blanks', 'd_stock']].to_string(index=False))
P('  trades with missing raw px rows in k-1..k+20:', int((B.missing_px_days > 0).sum()))

# ---------------- Part C: RSI from raw closes for all winners
P('\nPART C (extra) - RSI14 at the cutoff from raw px closes (own back-adjustment) for all winners')
syms = U.loc[U.W, 'symbol'].unique()
pxall = pd.read_sql('select day, symbol, close from px where symbol in (%s) order by symbol, day' %
                    ','.join('?' * len(syms)), con, params=list(syms))
ca_sb = ca[ca.kind.isin(['split', 'bonus'])]
ca_dm = ca[ca.kind == 'demerger']
day2i = dict(zip(ses.day, ses.i))


def wilder(c, n=14):
    d = np.diff(c)
    g, l = np.clip(d, 0, None), np.clip(-d, 0, None)
    out = np.full(len(c), np.nan)
    if len(d) < n:
        return out
    ag, al = g[:n].mean(), l[:n].mean()
    f = lambda a, b: 100.0 if b == 0 else 100 - 100 / (1 + a / b)
    out[n] = f(ag, al)
    for t in range(n, len(d)):
        ag, al = (ag * (n - 1) + g[t]) / n, (al * (n - 1) + l[t]) / n
        out[t + 1] = f(ag, al)
    return out


rsi_raw = {}
for s, g in pxall.groupby('symbol'):
    g = g[g.day.isin(day2i)].reset_index(drop=True)      # exchange sessions only (sessions.csv calendar)
    c = g.close.values.astype(float)
    adj = np.ones(len(c))                                  # backward factor for each row
    for x in ca_sb[ca_sb.symbol == s].itertuples():
        adj[g.day.values < x.ex_date] /= x.factor
    for x in ca_dm[ca_dm.symbol == s].itertuples():        # demerger: ex-day change set to 0
        pos = np.searchsorted(g.day.values, x.ex_date)
        if 0 < pos < len(c) and g.day.values[pos] == x.ex_date:
            adj[:pos] *= (c[pos] * adj[pos]) / (c[pos - 1] * adj[pos - 1])
    rsi_raw[s] = (g.day.map(day2i).values, wilder(c * adj))
W = U[U.W].copy()
vals = []
for r in W.itertuples(index=False):
    ii, rr = rsi_raw[r.symbol]
    p = np.searchsorted(ii, r.i_cut, side='right') - 1
    vals.append(rr[p] if p >= 0 else np.nan)
W['rsi_raw'] = vals
W['d'] = W.rsi_raw - W.rsi14_cut
P(f'  winners {len(W)}: max |RSI raw - RSI rebuild| = {W.d.abs().max():.2e}; > 0.01: {int((W.d.abs() > 0.01).sum())}; '
  f'RSI>50 flag disagreements: {int(((W.rsi_raw > 50) != (W.rsi14_cut > 50)).sum())}')
if (W.d.abs() > 0.01).any():
    P(W[W.d.abs() > 0.01][['symbol', 'qn', 'rsi14_cut', 'rsi_raw', 'd']].to_string(index=False))
open(OUT + '/raw_check.log', 'w').write('\n'.join(log) + '\n')
