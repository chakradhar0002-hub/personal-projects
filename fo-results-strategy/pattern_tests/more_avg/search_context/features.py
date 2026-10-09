"""Context features for every in_fo result (NO outcomes computed here).
Writes features.csv and cutpoints.csv (terciles over DISCOVERY baseline signals).
Tradability (a forward data-availability flag) is computed only for qn <= 13."""
import numpy as np
import pandas as pd

SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = SP + '/more_avg/search_context'
H = 20
DISC_MAX = 13

ev = pd.read_csv(SP + '/sector_lab/data/events.csv')
ses = pd.read_csv(SP + '/sector_lab/data/sessions.csv')
ret = pd.read_csv(SP + '/sector_lab/data/returns.csv', index_col=0)
idx = pd.read_csv(SP + '/sector_lab/data/index_close.csv', index_col=0)
ohl = pd.read_csv(SP + '/ta/build/adjusted_ohlcv.csv.gz', usecols=['day', 'symbol', 'close'])
fa = pd.read_csv(SP + '/fa/build/fa_panel.csv', usecols=['symbol', 'qn', 'in_fo', 'fin_type'])

assert (ses.i.values == np.arange(len(ses))).all()
assert list(ret.index) == list(ses.day) and list(idx.index) == list(ses.day)
NS = len(ses)
day2i = dict(zip(ses.day, ses.i))
R = ret.values
col = {s: j for j, s in enumerate(ret.columns)}
N = idx['Nifty 50'].values
VIX = idx['India VIX'].values
N500 = idx['Nifty 500'].values

# ---------------- universe (same as rebuild.py)
fa = fa.rename(columns={'in_fo': 'in_fo_fa', 'fin_type': 'fin_type_fa'})
ev = ev.merge(fa, on=['symbol', 'qn'], how='left')
tf = {True: True, False: False, 'True': True, 'False': False}
in_fo_ev = ev['in_fo'].map(tf)
ev['in_fo_u'] = in_fo_ev.fillna(ev['in_fo_fa'].map(tf))
u = ev[ev['in_fo_u'] == True].copy().reset_index(drop=True)
print('in_fo universe', len(u))


def wilder_rsi(close, n=14):
    c = np.asarray(close, float)
    out = np.full(len(c), np.nan)
    if len(c) <= n:
        return out
    d = np.diff(c)
    g = np.where(d > 0, d, 0.0)
    l = np.where(d < 0, -d, 0.0)
    ag, al = g[:n].mean(), l[:n].mean()

    def rsi(a, b):
        if b == 0:
            return 100.0 if a > 0 else 50.0
        return 100.0 - 100.0 / (1.0 + a / b)
    out[n] = rsi(ag, al)
    for t in range(n, len(d)):
        ag = (ag * (n - 1) + g[t]) / n
        al = (al * (n - 1) + l[t]) / n
        out[t + 1] = rsi(ag, al)
    return out


ohl = ohl.sort_values(['symbol', 'day']).reset_index(drop=True)
ohl['i'] = ohl['day'].map(day2i)
rsi_tab = {s: (g['i'].values.astype(int), wilder_rsi(g['close'].values)) for s, g in ohl.groupby('symbol', sort=False)}


def rsi_asof(sym, i):
    if sym not in rsi_tab:
        return np.nan
    ii, rr = rsi_tab[sym]
    p = np.searchsorted(ii, i, side='right') - 1
    return rr[p] if p >= 0 else np.nan


def sma_up(x, k, n):
    w = x[k - n + 1:k + 1]
    return bool(x[k] > w.mean())


rows = []
for r in u.itertuples(index=False):
    k, sym, qn = int(r.i_react), r.symbol, int(r.qn)
    j = col.get(sym)
    rk = R[k, j] if j is not None else np.nan
    nret = N[k] / N[k - 1] - 1
    rec = dict(symbol=sym, qn=qn, quarter=r.quarter, reaction_day=ses.day[k], i_cut=int(r.i_cut), i_react=k,
               industry=r.industry, sector_index=r.sector_index,
               fin_type=r.fin_type_fa if pd.notna(r.fin_type_fa) else r.fin_type)
    rec['XN'] = (rk - nret) * 100 if pd.notna(rk) else np.nan
    rec['rsi14_cut'] = rsi_asof(sym, int(r.i_cut))
    # market
    rec['nifty_sma50_up'] = sma_up(N, k, 50)
    rec['nifty_sma200_up'] = sma_up(N, k, 200)
    rec['nifty_r20'] = (N[k] / N[k - 20] - 1) * 100
    rec['vix'] = VIX[k]
    # sector (fallback Nifty 500)
    S = idx[r.sector_index].values if isinstance(r.sector_index, str) and r.sector_index in idx.columns else None
    ok = S is not None and not np.isnan(S[k]) and np.isfinite(S[k - 49:k + 1]).sum() == 50 and not np.isnan(S[k - 20])
    if not ok:
        S = N500
    rec['sec_fallback'] = not ok
    w = S[k - 49:k + 1]
    rec['sec_sma50_up'] = bool(S[k] > np.nanmean(w))
    rec['sec_r20'] = (S[k] / S[k - 20] - 1) * 100
    rec['sec_rel20'] = rec['sec_r20'] - rec['nifty_r20']
    # tradability (data availability) only for discovery
    if qn <= DISC_MAX:
        has_k21 = k + H + 1 <= NS - 1
        nblank = int(np.isnan(R[k + 1:k + H + 2, j]).sum()) if (j is not None and has_k21) else 99
        rec['tradable'] = bool(pd.notna(rk) and has_k21 and nblank <= 2)
    else:
        rec['tradable'] = np.nan
    rows.append(rec)

F = pd.DataFrame(rows)
F['fin'] = F.fin_type.isin(['Bank', 'NBFC / financial'])
F['W'] = F.XN > 4
F['RSI_HI'] = F.rsi14_cut > 50
F['BASE'] = F.W & F.RSI_HI

# breadth + season position (strictly earlier reaction days, same qn)
F['breadth_w'] = np.nan
F['n_before'] = 0
F['season_pos'] = np.nan
for qn, g in F.groupby('qn'):
    tot = len(g)
    ik = g.i_react.values
    xn = g.XN.values
    for idx_row, kk in zip(g.index, ik):
        m = ik < kk
        nb = int(m.sum())
        F.at[idx_row, 'n_before'] = nb
        F.at[idx_row, 'season_pos'] = nb / tot
        valid = m & ~np.isnan(xn)
        nv = int(valid.sum())
        if nv >= 10:
            F.at[idx_row, 'breadth_w'] = (xn[valid] > 4).mean()

F.to_csv(OUT + '/features.csv', index=False, float_format='%.6f')

# tercile cut points over discovery baseline signals (features only)
D = F[(F.qn <= DISC_MAX) & (F.tradable == True) & F.BASE]
print('discovery baseline signals (tradable):', len(D), ' all in_fo baseline signals (no tradability):', int(F.BASE.sum()))
cp = []
for c in ['nifty_r20', 'vix', 'sec_r20', 'breadth_w', 'season_pos']:
    x = D[c].dropna()
    cp.append(dict(feature=c, t1=x.quantile(1 / 3), t2=x.quantile(2 / 3), n_nonnull=len(x)))
CP = pd.DataFrame(cp)
CP.to_csv(OUT + '/cutpoints.csv', index=False, float_format='%.6f')
print(CP.to_string(index=False))
print('sector fallback among discovery signals:', int(D.sec_fallback.sum()), D[D.sec_fallback].sector_index.value_counts().to_dict())
print('breadth NaN among discovery signals:', int(D.breadth_w.isna().sum()))
print('fin among discovery signals:', int(D.fin.sum()))
for c in ['nifty_sma50_up', 'nifty_sma200_up', 'sec_sma50_up']:
    print(c, int(D[c].sum()))
print('sec_r20>0', int((D.sec_r20 > 0).sum()), 'sec_rel20>0', int((D.sec_rel20 > 0).sum()))
