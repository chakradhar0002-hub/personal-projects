#!/usr/bin/env python3
"""Independent rebuild (verifier) of the trade-A past-performance features from events.csv / returns.csv /
index_close.csv (+ adjusted_ohlcv for the 52-week high; ev.pkl only for the split-adjusted volume ratio, which the
task allows to reuse). Does NOT import or read the authors' scripts; reads their panel / signals only at the end to
list mismatches.

Writes my_features.csv.gz and v1_features.log in this folder.
"""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
DATA = f'{SP}/sector_lab/data'
LOG = open(f'{HERE}/v1_features.log', 'w')


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    LOG.write(s + '\n')
    LOG.flush()


days = pd.read_csv(f'{DATA}/sessions.csv').day.tolist()
T = len(days)
ret = pd.read_csv(f'{DATA}/returns.csv', index_col=0)
assert ret.index.tolist() == days
SYM = {s: j for j, s in enumerate(ret.columns)}
R = ret.to_numpy(float)
ix = pd.read_csv(f'{DATA}/index_close.csv', index_col=0)
assert ix.index.tolist() == days
NIF = ix['Nifty 50'].to_numpy(float)
NR = np.r_[np.nan, NIF[1:] / NIF[:-1] - 1]
LOGP = np.cumsum(np.log1p(np.nan_to_num(R)), axis=0)      # log price, NaN return treated as 0
NVALID = np.cumsum(np.isfinite(R), axis=0)
FIRSTRET = np.array([np.argmax(np.isfinite(R[:, j])) if np.isfinite(R[:, j]).any() else T for j in range(R.shape[1])])

ev = pd.read_csv(f'{DATA}/events.csv')
for c in ('i_cut', 'i_m1', 'i_rd', 'i_p1', 'i_react'):
    ev[c] = ev[c].astype(int)
ev['fo'] = ev.in_fo.map({True: 1, False: 0, 'True': 1, 'False': 0})
P('events', len(ev), 'in_fo True', int((ev.fo == 1).sum()), 'NaN', int(ev.fo.isna().sum()))
ev['j'] = ev.symbol.map(SYM)
assert ev.j.notna().all()
ev['j'] = ev.j.astype(int)
ev['td'] = ev.three_day * 100
ev['xn'] = (R[ev.i_react, ev.j] - NR[ev.i_react]) * 100
# my own 3-day check: sum of daily returns i_cut+1..i_p1
s3 = np.array([np.nansum(R[a + 1:b + 1, j]) for a, b, j in zip(ev.i_cut, ev.i_p1, ev.j)]) * 100
d = np.abs(s3 - ev.td)
P(f'three_day = sum of daily returns i_cut+1..i_p1: max abs diff {np.nanmax(d):.2e}; i_p1 - i_cut values',
  sorted((ev.i_p1 - ev.i_cut).unique()))
# 20-session drift vs Nifty from reaction close, known at k+20
k = ev.i_react.to_numpy()
e = k + 20
okd = e <= T - 1
dr = np.full(len(ev), np.nan)
ee = np.minimum(e, T - 1)
dr[okd] = ((np.exp(LOGP[ee, ev.j] - LOGP[k, ev.j]) - 1) - (NIF[ee] / NIF[k] - 1))[okd] * 100
ev['dr'] = dr
ev['dr_end'] = e

# ---------------------------------------------------------------- universe
U = ev[ev.fo != 0].copy().reset_index(drop=True)
P('universe (in_fo True or blank):', len(U))

HIST = {s: g.sort_values('qn') for s, g in ev.groupby('symbol')}


def hist_feats(sym, q, dec):
    """track record known at session dec, built only from results of EARLIER quarters whose 3-day window AND
    reaction day ended strictly before dec; drift only when its exit k+20 < dec."""
    g = HIST[sym]
    h = g[(g.qn < q) & (g.i_p1 < dec) & (g.i_react < dec)].sort_values('qn', ascending=False)
    o = {'n_prev': len(h), 'h_used_max': -1}
    if len(h) == 0:
        return o
    o['prev1_qn'] = h.qn.iloc[0]
    o['prev1_td'] = h.td.iloc[0]
    o['prev1_xn'] = h.xn.iloc[0]
    o['h_used_max'] = max(h.i_p1.max(), h.i_react.max())
    for K in (3, 4, 5, 6):
        if len(h) >= K:
            hk = h.iloc[:K]
            td = hk.td.dropna()
            o[f'n_pos_td{K}'] = float((td > 0).sum())
            o[f'mean_td{K}'] = td.mean()
            o[f'mean_xn{K}'] = hk.xn.mean()
            o[f'n_win{K}'] = float((hk.xn > 4).sum())
            dk = hk.dr.where(hk.dr_end < dec)
            o[f'mean_dr{K}'] = dk.mean()
            if K == 4 and dk.notna().any():
                o['h_used_max'] = max(o['h_used_max'], hk.dr_end[dk.notna()].max())
    o['mean_td_all'] = h.td.mean()
    o['share_pos_td_all'] = (h.td.dropna() > 0).mean() if h.td.notna().any() else np.nan
    o['mean_xn_all'] = h.xn.mean()
    return o


rows = []
for r in U.itertuples():
    o = hist_feats(r.symbol, r.qn, r.i_cut)
    assert o['h_used_max'] < r.i_cut
    rows.append(o)
F = pd.concat([U[['symbol', 'qn', 'quarter', 'period', 'results_date', 'cutoff', 'i_cut', 'i_rd', 'i_p1', 'i_react',
                  'fo', 'sector_index', 'td', 'j']].reset_index(drop=True), pd.DataFrame(rows)], axis=1)
P('look-ahead assert (own cutoff): every history item ended before i_cut: OK')
# "current result" never included
assert (F.prev1_qn.isna() | (F.prev1_qn < F.qn)).all()

# ---------------------------------------------------------------- price performance at i_cut
def sret(j, i, L):
    """L-session % return (compounded) over (i-L, i]; NaN if i-L before the first return (listing) or > 10% blanks"""
    if i - L < FIRSTRET[j]:
        return np.nan
    if L - (NVALID[i, j] - NVALID[i - L, j]) > max(2, int(0.05 * L)):
        return np.nan
    return (np.exp(LOGP[i, j] - LOGP[i - L, j]) - 1) * 100


for L in (21, 63, 126, 252):
    F[f'vsN{L}'] = [sret(j, i, L) - (NIF[i] / NIF[i - L] - 1) * 100 for j, i in zip(F.j, F.i_cut)]
# rank of 63/252-session return among the same quarter's universe stocks, all measured at THIS row's cutoff
for L in (21, 63, 126, 252):
    rk = np.full(len(F), np.nan)
    for q, g in F.groupby('qn'):
        js = g.j.to_numpy()
        for i in g.i_cut.unique():
            x = np.array([sret(j, i, L) for j in js])
            pr = pd.Series(x).rank(pct=True).to_numpy() * 100
            sel = (g.i_cut == i).to_numpy()
            rk[g.index[sel]] = pr[sel]
    F[f'rk{L}'] = rk

# 52-week high distance from adjusted OHLCV (max high over last 250 traded sessions incl. today)
oh = pd.read_csv(f'{SP}/ta/build/adjusted_ohlcv.csv.gz', usecols=['day', 'symbol', 'high', 'close', 'volume'])
DIX = {d_: i for i, d_ in enumerate(days)}
oh = oh[oh.symbol.isin(SYM)].copy()
oh['i'] = oh.day.map(DIX)
oh = oh.sort_values(['symbol', 'i'])
oh['hh'] = oh.groupby('symbol').high.transform(lambda s: s.rolling(250, min_periods=250).max())
oh['d52'] = (oh.close / oh.hh - 1) * 100
# volume ratio: mean volume of last 5 traded sessions / last 60 traded sessions, ending at the cutoff
oh['v5'] = oh.groupby('symbol').volume.transform(lambda s: s.rolling(5, min_periods=5).mean())
oh['v60'] = oh.groupby('symbol').volume.transform(lambda s: s.rolling(60, min_periods=60).mean())
oh['vr'] = oh.v5 / oh.v60
key = oh.set_index(['symbol', 'i'])
F = F.merge(oh[['symbol', 'i', 'd52', 'vr']].rename(columns={'i': 'i_cut', 'vr': 'my_vr'}), on=['symbol', 'i_cut'],
            how='left', validate='1:1')
evp = pd.read_pickle(f'{SP}/lag15_vol15_verify/ev.pkl')[['symbol', 'qn', 'lag', 'vr']]
F = F.merge(evp, on=['symbol', 'qn'], how='left', validate='1:1')
d = (F.vsN21 - F.lag * 100).abs()
P(f'my lag21 (vsN21) vs ev.pkl lag: max abs diff {d.max():.2e}, NaN mine {F.vsN21.isna().sum()}')
d = (F.my_vr - F.vr).abs()
P(f'my 5/60 volume ratio vs ev.pkl vr: n={d.notna().sum()} median abs diff {d.median():.3f}, share within 0.01: '
  f'{(d < 0.01).mean():.3f}; (ev.pkl vr is used for the rule; mine only as a cross-check)')

# ---------------------------------------------------------------- within-quarter quintiles (authors' convention)
for c in ['mean_td4', 'mean_xn4', 'mean_dr4', 'mean_td3', 'mean_td5', 'mean_xn3', 'mean_xn5', 'mean_td_all',
          'mean_xn_all']:
    F['pq_' + c] = F.groupby('qn')[c].rank(pct=True)

# ---------------------------------------------------------------- look-ahead check of the CROSS-SECTIONAL rank
# For each quarter: does any stock's feature use a history item that ended AFTER the earliest cutoff of the quarter?
F['first_cut_q'] = F.groupby('qn').i_cut.transform('min')
late = F[F.h_used_max >= F.first_cut_q]
P(f'rows whose own feature uses an item ending on/after the quarter\'s first cutoff: {len(late)} '
  f'(these leak into earlier stocks\' within-quarter ranks)')
if len(late):
    P(late.groupby('qn').size().to_string())

# Strict point-in-time rank: for row r, rank its feature among quarter-q stocks' features as known at r's cutoff,
# using for every stock only results of quarters < q that ended before r's cutoff.
def strict_rank(col_fn, name):
    out = np.full(len(F), np.nan)
    for q, g in F.groupby('qn'):
        syms = g.symbol.tolist()
        for i in g.i_cut.unique():
            vals = np.array([col_fn(s, q, i) for s in syms], float)
            pr = pd.Series(vals).rank(pct=True).to_numpy()
            sel = (g.i_cut == i).to_numpy()
            out[g.index[sel]] = pr[sel]
    F['sp_' + name] = out


CACHE = {}


def hf(s, q, i):
    kk = (s, q, i)
    if kk not in CACHE:
        CACHE[kk] = hist_feats(s, q, i)
    return CACHE[kk]


strict_rank(lambda s, q, i: hf(s, q, i).get('mean_td4', np.nan), 'mean_td4')
strict_rank(lambda s, q, i: hf(s, q, i).get('mean_xn4', np.nan), 'mean_xn4')
strict_rank(lambda s, q, i: hf(s, q, i).get('mean_dr4', np.nan), 'mean_dr4')
for c in ['mean_td4', 'mean_xn4', 'mean_dr4']:
    a = F['pq_' + c] > 0.8
    b = F['sp_' + c] > 0.8
    P(f'top quintile {c}: within-quarter rank {int(a.sum())} vs strict point-in-time rank {int(b.sum())}; '
      f'differ on {int((a != b).sum())} rows')

# ex-ante breakpoint: previous quarter's 80th percentile of the same feature (fully known before the season)
for c in ['mean_td4', 'mean_xn4']:
    bp = F.groupby('qn')[c].quantile(0.8).shift(1)
    v = (F[c] > F.qn.map(bp)).astype(float)
    v[F.qn.map(bp).isna()] = np.nan
    F['exante_top_' + c] = v

# survivorship: first quarter the symbol was in the universe
fq = F.groupby('symbol').qn.min()
F['first_fo_qn'] = F.symbol.map(fq)
F['early'] = F.first_fo_qn <= 1

F.drop(columns=['j']).to_csv(f'{HERE}/my_features.csv.gz', index=False, compression='gzip', float_format='%.6g')
P('wrote my_features.csv.gz', F.shape)
