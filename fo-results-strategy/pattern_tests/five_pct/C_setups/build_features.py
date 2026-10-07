"""Build cutoff features for (a) results events and (b) placebo non-results windows.
Outputs: events_feat.csv, placebo.csv.gz  (in this folder). Read-only on the source data."""
import numpy as np, pandas as pd, os
HERE = os.path.dirname(os.path.abspath(__file__))
D = os.environ.get('LAB_ROOT', 'lab') + '/'
f = pd.read_csv(D + 'search22/features.csv')
e = pd.read_csv(D + 'sector_lab/data/events.csv')
r = pd.read_csv(D + 'sector_lab/data/returns.csv')
intra = pd.read_csv(D + 'sector_lab/data/intraday.csv')
idx = pd.read_csv(D + 'sector_lab/data/index_close.csv')
assert (r.day.values == intra.day.values).all() and (r.day.values == idx.day.values).all()
syms = list(r.columns[1:]); col = {s: j for j, s in enumerate(syms)}
R = r[syms].values.astype(float); IN = intra[syms].values.astype(float)
T, NS = R.shape
# price index, NaN before first trade
first = np.array([np.argmax(~np.isnan(R[:, j])) if (~np.isnan(R[:, j])).any() else T for j in range(NS)])
P = np.nancumprod(np.where(np.isnan(R), 0, R) + 1, axis=0)
for j in range(NS): P[:first[j], j] = np.nan
Pd = pd.DataFrame(P)
nifty = idx['Nifty 50'].values

def lagret(k):
    out = np.full_like(P, np.nan); out[k:] = P[k:] / P[:-k] - 1; return out
r1w, r1m, r3d = lagret(5), lagret(21), lagret(3)
n1w = np.full(T, np.nan); n1w[5:] = nifty[5:] / nifty[:-5] - 1
n1m = np.full(T, np.nan); n1m[21:] = nifty[21:] / nifty[:-21] - 1
ma50 = Pd.rolling(50, min_periods=50).mean().values
hi250 = Pd.rolling(250, min_periods=250).max().values
lo250 = Pd.rolling(250, min_periods=250).min().values
vol60 = pd.DataFrame(R).rolling(60, min_periods=60).std().values * np.sqrt(252)
# streaks (a NaN day breaks a streak)
dn = (R < 0).astype(int); up = (R > 0).astype(int)
def streak(b):
    s = np.zeros_like(b)
    for t in range(T):
        s[t] = (s[t-1] + 1) * b[t] if t > 0 else b[t]
    return s
down_streak, up_streak = streak(dn), streak(up)
down10 = pd.DataFrame(dn).rolling(10, min_periods=10).sum().values
gap = (1 + R) / (1 + IN) - 1
z1w = r1w / (vol60 * np.sqrt(5 / 252))
fwd = {k: np.vstack([R[k:], np.full((k, NS), np.nan)]) for k in (1, 2, 3)}   # return on day t+k

NEW = dict(ret_c0=R, r3d=r3d, down_streak=down_streak, up_streak=up_streak, down10=down10, gap_c0=gap, z1w=z1w)

# ---------------- events ------------------------------------------------------------
m = f.merge(e[['symbol', 'quarter', 'i_cut', 'i_m1', 'i_rd', 'i_p1', 'i_react', 'ret_dm1', 'ret_rd', 'ret_dp1', 'sector_index']],
            on=['symbol', 'quarter'], how='left')
assert m.i_cut.notna().all()
ic = m.i_cut.values.astype(int); jj = m.symbol.map(col).values
for k, A in NEW.items(): m[k] = A[ic, jj]
assert np.nanmax(np.abs(m.ret_dm1 + m.ret_rd + m.ret_dp1 - m.three_day)) < 1e-9
assert np.nanmax(np.abs(R[m.i_m1.values.astype(int), jj] - m.ret_dm1)) < 1e-5
m['big_washout'] = ((m.vs_nifty_1w <= -0.10) | (m.vs_nifty_1m <= -0.20) | (m.vs_ma50 <= -0.15)).astype(int)
d1 = m.ret_dm1; d2 = m.ret_dm1 + m.ret_rd
m['tp3s'] = np.where(-d1 > 0.03, -d1, np.where(-d2 > 0.03, -d2, -m.three_day))   # short take-profit P&L
# sanity: recomputed vol-based z
print('events', m.shape, 'z1w non-null', m.z1w.notna().sum())
# check prev1_3d == previous result's three_day for same stock
mm = m.sort_values(['symbol', 'qn'])
prev = mm.groupby('symbol').three_day.shift(1)
ok = mm.prev1_3d.notna() & prev.notna()
print('prev1_3d == previous three_day:', np.mean(np.abs(mm.prev1_3d[ok] - prev[ok]) < 1e-9), ' prev1_3d present at qn0:', m.loc[m.qn == 0, 'prev1_3d'].notna().sum())
# check sector_1m equals sector_index 21-session return
sec_ok = []
for sname, g in m.groupby('sector_index'):
    if sname not in idx.columns: continue
    s = idx[sname].values; i = g.i_cut.values.astype(int)
    sec_ok.append(np.nanmedian(np.abs(s[i] / s[i - 21] - 1 - g.sector_1m.values)))
print('sector_1m matches sector_index 21-session return (median abs diff per sector, max):', np.nanmax(sec_ok))
m.drop(columns=['ret_dm1', 'ret_rd', 'ret_dp1']).to_csv(os.path.join(HERE, 'events_feat.csv'), index=False)
# outcome columns stored separately so the feature file can be inspected without outcomes
m[['symbol', 'quarter', 'qn', 'in_fo', 'three_day', 'tp3', 'tp3s', 'ret_dm1', 'ret_rd', 'ret_dp1']].to_csv(os.path.join(HERE, 'events_outcomes.csv'), index=False)

# ---------------- placebo ----------------------------------------------------------
# stock's sector index = most common sector_index in events
sec_of = e.groupby('symbol').sector_index.agg(lambda s: s.mode().iloc[0] if s.notna().any() else None)
ev = m.sort_values(['symbol', 'i_rd'])
t0 = int(m.loc[m.qn == 0, 'i_cut'].min()) - 63
t1 = int(m.i_p1.max())
rows = []
hist_cols = ['prev1_3d', 'past_avg_3d', 'past_pct_up', 'prev_pat_yoy', 'profit_rising_4q']
for s, g in ev.groupby('symbol'):
    j = col[s]
    res_sess = np.unique(np.concatenate([g.i_rd.values, g.i_react.values]).astype(int))
    ts = np.arange(max(t0, first[j] + 1), t1 - 3)
    # no result session within 10 sessions of the window [t+1, t+3]
    bad = np.zeros(len(ts), bool)
    for rs in res_sess:
        bad |= (rs >= ts - 9) & (rs <= ts + 13)
    ts = ts[~bad]
    if len(ts) == 0: continue
    # next result row (for quarter label, in_fo and stock-history features) and previous row (mcap)
    gi = g.i_cut.values.astype(int)
    nxt = np.searchsorted(gi, ts, side='right')        # first event with i_cut > t
    keep = nxt < len(g)
    ts, nxt = ts[keep], nxt[keep]
    prv = nxt - 1
    G = g.reset_index(drop=True)
    d = pd.DataFrame({'symbol': s, 't': ts, 'qn': G.qn.values[nxt], 'in_fo': G.in_fo.values[nxt]})
    for c in hist_cols: d[c] = G[c].values[nxt]
    d['log_mcap'] = np.where(prv >= 0, G.log_mcap.values[np.maximum(prv, 0)], np.nan)
    d['r1w'] = r1w[ts, j]; d['r1m'] = r1m[ts, j]
    d['vs_nifty_1w'] = r1w[ts, j] - n1w[ts]; d['vs_nifty_1m'] = r1m[ts, j] - n1m[ts]
    d['vs_ma50'] = P[ts, j] / ma50[ts, j] - 1
    d['from_52w_high'] = P[ts, j] / hi250[ts, j] - 1; d['from_52w_low'] = P[ts, j] / lo250[ts, j] - 1
    d['vol60'] = vol60[ts, j]
    sn = sec_of.get(s)
    if sn in idx.columns:
        sv = idx[sn].values; s1m = np.full(len(ts), np.nan); ok = ts >= 21
        s1m[ok] = sv[ts[ok]] / sv[ts[ok] - 21] - 1
        d['sector_1m'] = s1m; d['vs_sector_1m'] = d.r1m - s1m
    else:
        d['sector_1m'] = np.nan; d['vs_sector_1m'] = np.nan
    for k, A in NEW.items(): d[k] = A[ts, j]
    d['d1'] = fwd[1][ts, j]; d['d2'] = fwd[2][ts, j]; d['d3'] = fwd[3][ts, j]
    rows.append(d)
pl = pd.concat(rows, ignore_index=True)
pl = pl[pl[['d1', 'd2', 'd3']].notna().all(axis=1)].copy()
pl['three_day'] = pl.d1 + pl.d2 + pl.d3
a1 = pl.d1; a2 = pl.d1 + pl.d2
pl['tp3'] = np.where(a1 > 0.03, a1, np.where(a2 > 0.03, a2, pl.three_day))
pl['tp3s'] = np.where(-a1 > 0.03, -a1, np.where(-a2 > 0.03, -a2, -pl.three_day))
pl['big_washout'] = ((pl.vs_nifty_1w <= -0.10) | (pl.vs_nifty_1m <= -0.20) | (pl.vs_ma50 <= -0.15)).astype(int)
pl.to_csv(os.path.join(HERE, 'placebo.csv.gz'), index=False)
print('placebo rows', len(pl), 'in_fo rows', int(pl.in_fo.sum()), 'stocks', pl.symbol.nunique(), 'qn range', pl.qn.min(), pl.qn.max())
