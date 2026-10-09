#!/usr/bin/env python3
"""Verifier placebo (own construction): the same signals on ordinary F&O stock-days.

Ordinary day k for symbol s: s is in F&O for its next result (events in_fo of the first result with i_p1 >= k), no
result session (i_rd) of s within [k-9, k+13], k+3 within the data, three forward returns k+1..k+3 present.
Outcome: fwd3 = sum of daily returns k+1..k+3 (%), same construction as three_day (cutoff close -> Day+1 close).
Signals on day k use only information known at the close of k:
  track record: results whose 3-day window ended before k (i_p1 < k); drift only if i_react+20 < k;
  ranks: cross-sectional percentile among ALL F&O stocks on day k that have the feature (not only ordinary days).
Excess (placebo) = fwd3 minus the same-day mean of all ordinary days; results excess = three_day minus the quarter
mean of all F&O results. DiD = results excess - placebo excess (placebo weighted to the results trades' quarters,
quarter = qn of the stock's next result). Placebo p = share of 10,000 quarter-matched draws of placebo signal days
whose mean excess >= results excess.
Writes v3_placebo.log, placebo_summary.csv.
"""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
DATA = f'{SP}/sector_lab/data'
LOG = open(f'{HERE}/v3_placebo.log', 'w')
rng = np.random.default_rng(777)


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    LOG.write(s + '\n')
    LOG.flush()


days = pd.read_csv(f'{DATA}/sessions.csv').day.tolist()
T = len(days)
ret = pd.read_csv(f'{DATA}/returns.csv', index_col=0)
SYMS = ret.columns.tolist()
SYM = {s: j for j, s in enumerate(SYMS)}
S = len(SYMS)
R = ret.to_numpy(float)
ix = pd.read_csv(f'{DATA}/index_close.csv', index_col=0)
NIF = ix['Nifty 50'].to_numpy(float)
NR = np.r_[np.nan, NIF[1:] / NIF[:-1] - 1]
LOGP = np.cumsum(np.log1p(np.nan_to_num(R)), axis=0)
NVALID = np.cumsum(np.isfinite(R), axis=0)
FIRSTRET = np.array([np.argmax(np.isfinite(R[:, j])) if np.isfinite(R[:, j]).any() else T for j in range(S)])

ev = pd.read_csv(f'{DATA}/events.csv')
for c in ('i_cut', 'i_rd', 'i_p1', 'i_react'):
    ev[c] = ev[c].astype(int)
ev['fo'] = ev.in_fo.map({True: 1.0, False: 0.0, 'True': 1.0, 'False': 0.0})
ev.loc[ev.fo.isna(), 'fo'] = 1.0           # the 2 blank rows are in the 3,280 universe
ev['j'] = ev.symbol.map(SYM).astype(int)
ev['td'] = ev.three_day * 100
ev['xn'] = (R[ev.i_react, ev.j] - NR[ev.i_react]) * 100
k_ = ev.i_react.to_numpy()
ee = np.minimum(k_ + 20, T - 1)
ev['dr'] = np.where(k_ + 20 <= T - 1, ((np.exp(LOGP[ee, ev.j] - LOGP[k_, ev.j]) - 1) - (NIF[ee] / NIF[k_] - 1)) * 100,
                    np.nan)
ev['dr_end'] = k_ + 20

# ---------------------------------------------------------------- day x symbol matrices
FO = np.full((T, S), np.nan)
QNEXT = np.full((T, S), np.nan)
NEAR = np.zeros((T, S), bool)
TD4 = np.full((T, S), np.nan)
XN4 = np.full((T, S), np.nan)
NPOS4 = np.full((T, S), np.nan)
DR4 = np.full((T, S), np.nan)
for s, g in ev.groupby('symbol'):
    g = g.sort_values('i_p1').reset_index(drop=True)
    assert (np.diff(g.qn) > 0).all()
    j = SYM[s]
    prev_end = -1
    for r in g.itertuples():
        FO[prev_end + 1:r.i_p1 + 1, j] = r.fo         # days k with this result as the next one (i_p1 >= k)
        QNEXT[prev_end + 1:r.i_p1 + 1, j] = r.qn
        prev_end = r.i_p1
        NEAR[max(0, r.i_rd - 13):r.i_rd + 10, j] = True   # k with i_rd in [k-9, k+13]
    # track record change points
    cps = sorted(set([int(x) + 1 for x in g.i_p1] + [int(x) + 1 for x in g.dr_end if x + 1 < T]))
    cps = [c for c in cps if c < T]
    for a, c in enumerate(cps):
        b = cps[a + 1] if a + 1 < len(cps) else T
        h = g[g.i_p1 < c].iloc[::-1]
        if len(h) >= 4:
            h4 = h.iloc[:4]
            TD4[c:b, j] = h4.td.mean()
            XN4[c:b, j] = h4.xn.mean()
            NPOS4[c:b, j] = (h4.td.dropna() > 0).sum()
            d4 = h4.dr.where(h4.dr_end < c)
            DR4[c:b, j] = d4.mean()


def ret_L(L):
    out = np.full((T, S), np.nan)
    i = np.arange(L, T)
    r = (np.exp(LOGP[i] - LOGP[i - L]) - 1) * 100
    blanks = L - (NVALID[i] - NVALID[i - L])
    ok = (i[:, None] - L >= FIRSTRET[None, :]) & (blanks <= max(2, int(0.05 * L)))
    out[i] = np.where(ok, r, np.nan)
    return out


R21 = ret_L(21)
R63 = ret_L(63)
NR21 = np.full(T, np.nan)
NR21[21:] = (NIF[21:] / NIF[:-21] - 1) * 100
LAG21 = R21 - NR21[:, None]

oh = pd.read_csv(f'{SP}/ta/build/adjusted_ohlcv.csv.gz', usecols=['day', 'symbol', 'high', 'close', 'volume'])
DIX = {d_: i for i, d_ in enumerate(days)}
oh = oh[oh.symbol.isin(SYM)].copy()
oh['i'] = oh.day.map(DIX)
oh = oh.sort_values(['symbol', 'i'])
oh['vr'] = oh.groupby('symbol').volume.transform(lambda s_: s_.rolling(5, min_periods=5).mean()) / \
    oh.groupby('symbol').volume.transform(lambda s_: s_.rolling(60, min_periods=60).mean())
oh['hh'] = oh.groupby('symbol').high.transform(lambda s_: s_.rolling(250, min_periods=250).max())
oh['d52'] = (oh.close / oh.hh - 1) * 100
VR = np.full((T, S), np.nan)
D52 = np.full((T, S), np.nan)
VR[oh.i.to_numpy(), oh.symbol.map(SYM).to_numpy()] = oh.vr.to_numpy()
D52[oh.i.to_numpy(), oh.symbol.map(SYM).to_numpy()] = oh.d52.to_numpy()

FW = np.full((T, S), np.nan)
for k in range(T - 3):
    FW[k] = R[k + 1:k + 4].sum(0) * 100
    FW[k][~np.isfinite(R[k + 1:k + 4]).all(0)] = np.nan

isfo = FO == 1


def xrank(M):
    X = np.where(isfo, M, np.nan)
    return pd.DataFrame(X).rank(axis=1, pct=True).to_numpy()


PK_TD4, PK_XN4, PK_DR4 = xrank(TD4), xrank(XN4), xrank(DR4)
RK63 = xrank(R63) * 100

first_cut = int(ev[ev.qn == 0].i_cut.min())
ELIG = isfo & ~NEAR & np.isfinite(FW) & (np.arange(T)[:, None] >= first_cut) & np.isfinite(QNEXT)
kk, jj = np.nonzero(ELIG)
pl = pd.DataFrame({'k': kk, 'j': jj, 'qn_next': QNEXT[kk, jj].astype(int), 'fw': FW[kk, jj]})
pl['dm'] = pl.fw - pl.groupby('k').fw.transform('mean')
P(f'ordinary F&O stock-days: {len(pl)}, symbols {pl.j.nunique()}, mean fwd3 {pl.fw.mean():+.3f}%, qn_next '
  f'{pl.qn_next.min()}..{pl.qn_next.max()}')
P(pl.groupby('qn_next').fw.agg(['size', 'mean']).round(3).T.to_string())
for nm, M in [('pk_td4', PK_TD4), ('pk_xn4', PK_XN4), ('pk_dr4', PK_DR4), ('npos4', NPOS4), ('rk63', RK63),
              ('vr', VR), ('lag21', LAG21), ('d52', D52), ('td4', TD4)]:
    pl[nm] = M[kk, jj]

PSIG = {
    'TR05 (top quintile mean 3-day window)': pl.pk_td4 > 0.8,
    'TR05 top decile (post-hoc)': pl.pk_td4 > 0.9,
    'TR12 (top quintile mean reaction)': pl.pk_xn4 > 0.8,
    'TR12 top decile (post-hoc)': pl.pk_xn4 > 0.9,
    'TR03 (>=3 of last 4 positive)': pl.npos4 >= 3,
    'TR03 4 of 4 (post-hoc)': pl.npos4 == 4,
    'RP1 (vol>=1 & 3m bottom quintile)': (pl.vr >= 1.0) & (pl.rk63 <= 20),
    'RP1 without lag21<-10': (pl.vr >= 1.0) & (pl.rk63 <= 20) & (pl.lag21 >= -10),
    'LAGRULE (lag<-10 & vol>=1)': (pl.lag21 < -10) & (pl.vr >= 1.0),
    'LAGRULE & d52<=-30 (PP12 split)': (pl.lag21 < -10) & (pl.vr >= 1.0) & (pl.d52 <= -30),
    'LAGRULE & d52>-30': (pl.lag21 < -10) & (pl.vr >= 1.0) & (pl.d52 > -30),
    'LAGRULE & drift top quintile (TR15 split)': (pl.lag21 < -10) & (pl.vr >= 1.0) & (pl.pk_dr4 > 0.8),
    'LAGRULE & drift not top quintile': (pl.lag21 < -10) & (pl.vr >= 1.0) & (pl.pk_dr4 <= 0.8),
}

# ---------------------------------------------------------------- results side (my own features)
F = pd.read_csv(f'{HERE}/my_features.csv.gz')
F = F[F.td.notna()].reset_index(drop=True)
y = F.td.to_numpy()
qn = F.qn.to_numpy()
QMEAN = pd.Series(y).groupby(qn).mean()
fo = (F.fo == 1).to_numpy()
LAG = fo & (F.vsN21 < -10).to_numpy() & (F.vr >= 1.0).to_numpy()
RSIG = {
    'TR05 (top quintile mean 3-day window)': F.pq_mean_td4 > 0.8,
    'TR05 top decile (post-hoc)': F.pq_mean_td4 > 0.9,
    'TR12 (top quintile mean reaction)': F.pq_mean_xn4 > 0.8,
    'TR12 top decile (post-hoc)': F.pq_mean_xn4 > 0.9,
    'TR03 (>=3 of last 4 positive)': F.n_pos_td4 >= 3,
    'TR03 4 of 4 (post-hoc)': F.n_pos_td4 == 4,
    'RP1 (vol>=1 & 3m bottom quintile)': pd.Series(fo & (F.vr >= 1.0).to_numpy() & (F.rk63 <= 20).to_numpy()),
    'RP1 without lag21<-10': pd.Series(fo & (F.vr >= 1.0).to_numpy() & (F.rk63 <= 20).to_numpy() & (F.vsN21 >= -10).to_numpy()),
    'LAGRULE (lag<-10 & vol>=1)': pd.Series(LAG),
    'LAGRULE & d52<=-30 (PP12 split)': pd.Series(LAG & (F.d52 <= -30).to_numpy()),
    'LAGRULE & d52>-30': pd.Series(LAG & (F.d52 > -30).to_numpy()),
    'LAGRULE & drift top quintile (TR15 split)': pd.Series(LAG & (F.pq_mean_dr4 > 0.8).to_numpy()),
    'LAGRULE & drift not top quintile': pd.Series(LAG & (F.pq_mean_dr4 <= 0.8).to_numpy()),
}

rows = []
pdm = pl.dm.to_numpy()
pq = pl.qn_next.to_numpy()
for name, ps in PSIG.items():
    pm = ps.fillna(False).to_numpy(bool)
    rm = RSIG[name].fillna(False).to_numpy(bool)
    pools = {q: pdm[pm & (pq == q)] for q in np.unique(pq[pm])}
    keep = rm & np.isin(qn, list(pools))
    res_exc = (y[keep] - QMEAN.reindex(qn[keep]).to_numpy()).mean()
    nq = pd.Series(qn[keep]).value_counts()
    n = int(keep.sum())
    pl_exc = sum(k * pools[q].mean() for q, k in nq.items()) / n
    tot = np.zeros(10000)
    for q, k in nq.items():
        pool = pools[q]
        tot += pool[rng.integers(0, len(pool), size=(10000, k))].sum(1)
    draws = tot / n
    p = (1 + (draws >= res_exc).sum()) / 10001
    # placebo: signal days vs other ordinary days, raw (unweighted) and its own day-clustered t
    sig_dm = pdm[pm]
    by_day = pd.Series(sig_dm).groupby(pl.k.to_numpy()[pm]).mean()
    t_day = by_day.mean() / (by_day.std(ddof=1) / np.sqrt(len(by_day)))
    # halves on placebo
    h1 = pm & (pq <= 13)
    h2 = pm & (pq >= 14)
    r = dict(signal=name, res_n=int(rm.sum()), res_n_cmp=n, res_avg=y[rm].mean(), res_excess=res_exc,
             pl_days=int(pm.sum()), pl_raw_avg=pl.fw.to_numpy()[pm].mean(), pl_excess_qw=pl_exc,
             pl_excess_unw=sig_dm.mean(), pl_t_day=t_day, pl_exc_h1=pdm[h1].mean(), pl_exc_h2=pdm[h2].mean(),
             DiD=res_exc - pl_exc, placebo_p=p)
    rows.append(r)
    P(f"{name:42s} results n={r['res_n']:4d} excess {res_exc:+.2f} | placebo days {r['pl_days']:6d} "
      f"excess {pl_exc:+.3f} (unweighted {sig_dm.mean():+.3f}, day-t {t_day:.1f}; h1 {r['pl_exc_h1']:+.3f} "
      f"h2 {r['pl_exc_h2']:+.3f}) | DiD {r['DiD']:+.2f} | placebo p {p:.4f}")
pd.DataFrame(rows).to_csv(f'{HERE}/placebo_summary.csv', index=False, float_format='%.4f')
