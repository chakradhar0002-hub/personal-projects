#!/usr/bin/env python3
"""S0. Independent rebuild of the per-result panel (and the quiet-day placebo panel) from the raw-ish inputs.

Own code: XN, tradability, H5/H10/H20 outcomes, Wilder RSI(14) at the cutoff from adjusted_ohlcv closes (own loop, not
the builder's function), alternative benchmarks (Nifty 500, Nifty Midcap 150, Nifty100 Equal Weight, sector index),
pre-cutoff beta, Nifty regime, stock momentum, next-open entry. Cross-checks against tafa trades.csv / features.csv and
the build's trades.csv. Writes panel.csv.gz and quiet_panel.csv.gz into this folder.
"""
import numpy as np
import pandas as pd

from common import DATA, TAFA, BUILD, SP, HERE, COST, C_STK, Log, sg

L = Log('s0_rebuild.log')

# ---------------------------------------------------------------- prices
ses = pd.read_csv(f'{DATA}/sessions.csv')
DAYS = ses.day.to_numpy()
NS = len(ses)
ret = pd.read_csv(f'{DATA}/returns.csv', index_col=0)
assert (ret.index.to_numpy() == DAYS).all()
SYMS = list(ret.columns)
SYM = {s: j for j, s in enumerate(SYMS)}
R = ret.to_numpy(float)
GROW = np.cumprod(1 + np.nan_to_num(R), axis=0)           # blank = 0
NVALID = np.cumsum(~np.isnan(R), axis=0)
ix = pd.read_csv(f'{DATA}/index_close.csv', index_col=0)
assert (ix.index.to_numpy() == DAYS).all()
NIF = ix['Nifty 50'].to_numpy(float)
NIFR = np.r_[np.nan, NIF[1:] / NIF[:-1] - 1]
BENCH = {'N500': 'Nifty 500', 'MID150': 'Nifty Midcap 150', 'N100EW': 'Nifty100 Equal Weight'}

# adjusted OHLCV (split/bonus adjusted) -> session x symbol arrays
ao = pd.read_csv(f'{SP}/ta/build/adjusted_ohlcv.csv.gz', usecols=['day', 'symbol', 'open', 'close'])
di = {d: i for i, d in enumerate(DAYS)}
ao['i'] = ao.day.map(di)
assert ao.i.notna().all()
ao = ao[ao.symbol.isin(SYM)]
AC = np.full((NS, len(SYMS)), np.nan)
AO = np.full((NS, len(SYMS)), np.nan)
jj = ao.symbol.map(SYM).to_numpy(int)
ii = ao.i.to_numpy(int)
AC[ii, jj] = ao.close.to_numpy(float)
AO[ii, jj] = ao.open.to_numpy(float)
L(f'adjusted_ohlcv rows {len(ao):,}, symbols {ao.symbol.nunique()}')


def wilder_rsi(c, n=14):
    """Textbook Wilder RSI on a gap-free close series: first average = simple mean of the first n changes,
    then avg = (prev * (n-1) + x) / n. Own loop implementation."""
    out = np.full(len(c), np.nan)
    if len(c) <= n:
        return out
    d = np.diff(c)
    g = np.clip(d, 0, None)
    lo = np.clip(-d, 0, None)
    ag, al = g[:n].mean(), lo[:n].mean()

    def val(a, b):
        if b == 0:
            return 100.0 if a > 0 else 50.0
        return 100 - 100 / (1 + a / b)
    out[n] = val(ag, al)
    for t in range(n, len(d)):
        ag = (ag * (n - 1) + g[t]) / n
        al = (al * (n - 1) + lo[t]) / n
        out[t + 1] = val(ag, al)
    return out


RSI = np.full((NS, len(SYMS)), np.nan)      # value carried forward over non-traded sessions
for j in range(len(SYMS)):
    idx = np.flatnonzero(np.isfinite(AC[:, j]))
    if len(idx) < 16:
        continue
    r_ = wilder_rsi(AC[idx, j])
    s = pd.Series(np.nan, index=range(NS))
    s.iloc[idx] = r_
    RSI[:, j] = s.ffill().to_numpy()
    # do not carry forward before the first traded day
L('own Wilder RSI(14) computed for all symbols with >= 16 traded sessions')


def stock_ret(jx, a, b):
    """compounded adjusted stock return from close a to close b (blank = 0), fraction."""
    return GROW[b, jx] / GROW[a, jx] - 1


def outcomes(jx, k, H):
    W = max(21, H + 1)
    ok = k + W <= NS - 1
    kk = np.where(ok, k, 0)
    blanks = W - (NVALID[np.minimum(kk + W, NS - 1), jx] - NVALID[kk, jx])
    ok = ok & (blanks <= 2)
    e = np.minimum(kk + H, NS - 1)
    st = stock_ret(jx, kk, e)
    nf = NIF[e] / NIF[kk] - 1
    st[~ok] = np.nan
    nf[~ok] = np.nan
    return st * 100, nf * 100, ok


def beta_at(jx, i_end, win=250, minobs=120):
    out = np.full(len(jx), np.nan)
    for t, (j, e) in enumerate(zip(jx, i_end)):
        a = max(1, e - win + 1)
        y = R[a:e + 1, j]
        x = NIFR[a:e + 1]
        m = np.isfinite(y) & np.isfinite(x)
        if m.sum() >= minobs:
            xm = x[m] - x[m].mean()
            out[t] = (xm @ (y[m] - y[m].mean())) / (xm @ xm)
    return out


def build_rows(df, k_col, cut_col, label):
    """Common columns for a frame of (symbol, k, cutoff)."""
    jx = df.symbol.map(SYM).to_numpy(int)
    k = df[k_col].to_numpy(int)
    c = df[cut_col].to_numpy(int)
    out = pd.DataFrame(index=df.index)
    out['XN_mine'] = (R[k, jx] - NIFR[k]) * 100
    for H in (5, 10, 20):
        st, nf, ok = outcomes(jx, k, H)
        out[f'stock_H{H}'] = st
        out[f'nifty_H{H}'] = nf
        out[f'vsN_H{H}'] = st - nf - COST
        out[f'ok_H{H}'] = ok
    out['vsN_net'] = out.vsN_H20
    out['raw_net'] = out.stock_H20 - C_STK
    e20 = np.minimum(k + 20, NS - 1)
    ok = out.ok_H20.to_numpy()
    for key, col in BENCH.items():
        B = ix[col].to_numpy(float)
        b = (B[e20] / B[k] - 1) * 100
        out[f'vs{key}_net'] = np.where(ok, out.stock_H20 - b - COST, np.nan)
    out['rsi_mine'] = RSI[c, jx]
    out['nifty_pre20'] = (NIF[c] / NIF[c - 20] - 1) * 100
    out['nifty_pre60'] = (NIF[c] / NIF[c - 60] - 1) * 100
    out['stock_pre21'] = stock_ret(jx, c - 21, c) * 100
    out['beta250'] = beta_at(jx, c)
    out['abn_beta_net'] = out.stock_H20 - out.beta250 * out.nifty_H20 - COST
    # next-open entry: buy at the adjusted open of k+1 (if traded), sell close k+20; Nifty close k -> close k+20
    k1 = np.minimum(k + 1, NS - 1)
    gap = AO[k1, jx] / AC[k, jx] - 1
    out['gap_k1_pct'] = gap * 100
    out['vsN_nextopen_net'] = np.where(ok, ((1 + out.stock_H20 / 100) / (1 + gap) - 1) * 100 - out.nifty_H20 - COST,
                                       np.nan)
    # adjusted close ratio check (adjusted_ohlcv vs returns.csv) over k..k+20
    out['acl_H20'] = (AC[e20, jx] / AC[k, jx] - 1) * 100
    L(f'{label}: {len(out):,} rows built')
    return out


# ---------------------------------------------------------------- results panel
ev = pd.read_csv(f'{DATA}/events.csv')
fa = pd.read_csv(f'{SP}/fa/build/fa_panel.csv', usecols=['symbol', 'qn', 'in_fo'])
U = fa[fa.in_fo == True][['symbol', 'qn']].merge(ev, on=['symbol', 'qn'], how='left', validate='1:1')
L(f'universe (fa_panel in_fo == True): {len(U):,} results; quarters {U.qn.nunique()}')
assert len(U) == 3280 and U.i_react.notna().all()
# cutoff check: i_cut = i_rd - 2
L(f'i_cut == i_rd - 2 for {(U.i_cut == U.i_rd - 2).mean() * 100:.1f}% of results; i_react - i_rd in '
  f'{sorted((U.i_react - U.i_rd).unique().tolist())}')
P = pd.concat([U[['symbol', 'company', 'quarter', 'qn', 'period', 'results_date', 'timing', 'reaction_day', 'industry',
                  'peer_group', 'sector_index', 'fin_type', 'mcap', 'i_cut', 'i_rd', 'i_react']],
               build_rows(U, 'i_react', 'i_cut', 'results')], axis=1)
# sector-index benchmark
sec = np.full(len(P), np.nan)
for s_, g in P.groupby('sector_index'):
    if s_ not in ix.columns:
        continue
    B = ix[s_].to_numpy(float)
    k = g.i_react.to_numpy(int)
    e = np.minimum(k + 20, NS - 1)
    sec[P.index.get_indexer(g.index)] = (B[e] / B[k] - 1) * 100
P['vsSEC_net'] = np.where(P.ok_H20, P.stock_H20 - sec - COST, np.nan)
L(f"sector-index benchmark available for {np.isfinite(P.vsSEC_net).sum()} of {len(P)} results")

# features (feature flags only, no outcomes) + events_ta RSI
fe = pd.read_csv(f'{TAFA}/features.csv')
flags = ['XN', 'cut_rsi14', 'rx_rsi14', 'cut_close_vs_sma200_pct', 'GOOD', 'E_GOOD', 'BAD', 'E_BAD', 'Q_HI', 'E_QHI',
         'Q_LO', 'E_QLO', 'CHEAP', 'EXP', 'E_PE', 'UP200', 'DN200', 'E_S200', 'RSI_HI', 'RSI_LO', 'E_RSI']
P = P.merge(fe[['symbol', 'qn'] + flags], on=['symbol', 'qn'], how='left', validate='1:1')
eta = pd.read_csv(f'{SP}/ta/build/events_ta.csv', usecols=['symbol', 'qn', 'rsi14', 'traded_at_cut'])
P = P.merge(eta, on=['symbol', 'qn'], how='left', validate='1:1')

# ---------------------------------------------------------------- checks
L('\nCHECKS')
L(f"XN own vs features: max abs diff {np.nanmax(np.abs(P.XN_mine - P.XN)):.2e}")
L(f"all 3,280 tradable at H20: {P.ok_H20.all()} (H5 {P.ok_H5.all()}, H10 {P.ok_H10.all()})")
d_r = np.abs(P.rsi_mine - P.rsi14)
L(f"own Wilder RSI vs events_ta rsi14: max abs diff {np.nanmax(d_r):.2e}; >0.01 in {(d_r > 0.01).sum()} rows; "
  f"own NaN {P.rsi_mine.isna().sum()}, eta NaN {P.rsi14.isna().sum()}; not traded at cutoff {(P.traded_at_cut == 0).sum()}")
L(f"events_ta rsi14 == features cut_rsi14: max abs diff {np.nanmax(np.abs(P.rsi14 - P.cut_rsi14)):.2e}")
side_flip = ((P.rsi_mine > 50) != (P.cut_rsi14 > 50)) & P.rsi_mine.notna()
L(f"RSI>50 classification disagreements (own vs build): {int(side_flip.sum())}")
tr = pd.read_csv(f'{TAFA}/trades.csv', usecols=['symbol', 'qn', 'raw_H20', 'nifty_H20', 'raw_H5', 'raw_H10', 'W',
                                                  'W_RSI_HI'])
c_ = P.merge(tr, on=['symbol', 'qn'], suffixes=('', '_t'))
for H in (5, 10, 20):
    L(f"stock H{H} own vs tafa trades.csv: max abs diff {np.nanmax(np.abs(c_[f'stock_H{H}'] - c_[f'raw_H{H}'])):.2e}")
L(f"Nifty H20 own vs tafa: max abs diff {np.nanmax(np.abs(c_.nifty_H20 - c_.nifty_H20_t)):.2e}")
dd = np.abs(P.acl_H20 - P.stock_H20)
L(f"adjusted_ohlcv close ratio k->k+20 vs compounded returns.csv: median abs diff {np.nanmedian(dd):.3f}, "
  f">0.5 pts in {(dd > 0.5).sum()} rows (dividend / data differences)")
P['W'] = P.XN_mine > 4
P['HI'] = P.cut_rsi14 > 50
P['MAIN'] = P.W & P.HI
L(f"winners {P.W.sum()}, main rule {P.MAIN.sum()}, winners RSI<=50 {(P.W & ~P.HI).sum()}; matches tafa W_RSI_HI: "
  f"{(c_.W_RSI_HI.astype(bool).to_numpy() == (c_.XN_mine > 4).to_numpy() & (c_.cut_rsi14 > 50).to_numpy()).all()}")
bt = pd.read_csv(f'{BUILD}/trades.csv')
cm = bt.merge(P[['symbol', 'qn', 'vsN_net', 'raw_net']], on=['symbol', 'qn'], suffixes=('_b', ''))
L(f"build trades.csv: {len(bt)} rows; matched {len(cm)}; vsN_net max abs diff {np.abs(cm.vsN_net - cm.vsN_net_b).max():.2e}")
L(f"main-rule mean vsN_net own {P.loc[P.MAIN, 'vsN_net'].mean():+.4f}; plain winners {P.loc[P.W, 'vsN_net'].mean():+.4f}; "
  f"winners RSI<=50 {P.loc[P.W & ~P.HI, 'vsN_net'].mean():+.4f}; all {P.vsN_net.mean():+.4f}")
nw = ~P.W
L(f"non-winners: RSI>50 n {int((nw & P.HI).sum())} {P.loc[nw & P.HI, 'vsN_net'].mean():+.3f}; RSI<=50 n "
  f"{int((nw & ~P.HI).sum())} {P.loc[nw & ~P.HI, 'vsN_net'].mean():+.3f}")
P['year'] = P.reaction_day.str[:4].astype(int)
P['month'] = P.reaction_day.str[:7]
P.drop(columns=['acl_H20']).to_csv(f'{HERE}/panel.csv.gz', index=False, float_format='%.6g')

# ---------------------------------------------------------------- quiet-day placebo panel
qd = pd.read_csv(f'{TAFA}/quiet_days.csv.gz', usecols=['symbol', 'i', 'day', 'XN', 'm2_rsi14', 'W'])
qd = qd[qd.symbol.isin(SYM)].reset_index(drop=True)
qd['i_m2'] = qd.i - 2
Q = pd.concat([qd, build_rows(qd, 'i', 'i_m2', 'quiet days')], axis=1)
L(f"\nquiet days: {len(Q):,} rows; XN own vs file max abs diff {np.nanmax(np.abs(Q.XN_mine - Q.XN)):.2e}; "
  f"tradable H20 {Q.ok_H20.mean() * 100:.1f}%")
dq = np.abs(Q.rsi_mine - Q.m2_rsi14)
L(f"quiet RSI at k-2 own vs file: max abs diff {np.nanmax(dq):.2e}; >0.01 in {(dq > 0.01).sum()}; "
  f"file NaN {Q.m2_rsi14.isna().sum()}, own NaN {Q.rsi_mine.isna().sum()}")
Q['month'] = Q.day.str[:7]
Q['year'] = Q.day.str[:4].astype(int)
Q.to_csv(f'{HERE}/quiet_panel.csv.gz', index=False, float_format='%.6g')
L('wrote panel.csv.gz, quiet_panel.csv.gz')
