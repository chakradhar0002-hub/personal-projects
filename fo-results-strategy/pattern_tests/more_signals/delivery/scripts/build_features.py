#!/usr/bin/env python3
"""DELIVERY % family - point-in-time features (no outcome of any trade is read here).

Inputs (read-only): downloads/delivery_eq.csv (parsed NSE sec_bhavdata_full / MTO, SERIES EQ), symbolchange.csv,
sector_lab/data/{sessions,returns,index_close,events}.csv, ta/build/adjusted_ohlcv.csv.gz (volume_factor and adjusted
volume, for split adjustment and validation), perf/features/panel.csv (features only), ta/build/placebo_ta.csv.gz
(stock-day keys only, no outcome columns), tafa/C_post_results/quiet_days.csv.gz (XN, W, m2_rsi14 at quiet day k).

POINT IN TIME: NSE publishes the delivery file for session t in the evening of t, after the close. At a decision taken at
the close of session d, delivery data is known up to session d-1 only. Every delivery feature "as of decision d" uses
sessions <= d-1 (index e = d-1). Price features use the same sessions.

Features (session grid; e = last delivery session used):
  DP[t]   delivery % (DELIV_PER) of session t; DQA[t] = DELIV_QTY x volume_factor (split/bonus adjusted)
  ACC(e)  mean DP over e-4..e (>= 4 values) minus mean DP over e-59..e (>= 40 values)    [percentage points]
  DQR(e)  mean DQA over e-4..e (>= 4) / mean DQA over e-59..e (>= 40)                       [ratio]
  DPL(e)  DP[e] minus mean DP over e-60..e-1 (>= 40)                                        [pp] (single day vs 60)
  DQL(e)  DQA[e] / mean DQA over e-60..e-1 (>= 40)                                          [ratio]
  DP60(e) mean DP over e-59..e (>= 40)                                                      [%] (level)
  PR5(e)  compounded stock return over sessions e-4..e (returns.csv, >= 4 traded)          [%]
  B, reaction day k:  DPK = DP[k] - mean DP over k-60..k-1 ; DQK = DQA[k] / mean DQA over k-60..k-1 ;
                      DPK1 = DP[k+1] - mean DP over k-60..k-1 (same base, before the results move)
  Quarter ranks (A): percentile rank (pandas pct, x100) among the same quarter's F&O results' symbols, all measured
  on the same session e as the row (results: e = i_cut-1; placebo day k: e = k-1, universe of quarter qn_next).
Outputs (this folder ../): feat_results.csv, feat_placeboA.csv.gz, feat_placeboB.csv.gz, build_features.log,
  delivery_panel.csv.gz (compact mapped matrix: day, symbol, DP, DQ, TQ, VF).
"""
import os
import sys

import numpy as np
import pandas as pd

OUT = sys.argv[1]            # .../more_signals/delivery
SP = sys.argv[2]             # scratchpad root (read-only inputs)
DATA = f'{SP}/sector_lab/data'
LOG = open(f'{OUT}/build_features.log', 'w')


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.write(s + '\n')
    LOG.flush()


ses = pd.read_csv(f'{DATA}/sessions.csv')
days = ses.day.tolist()
T = len(days)
DIX = {d: i for i, d in enumerate(days)}
ret = pd.read_csv(f'{DATA}/returns.csv', index_col=0)
assert ret.index.tolist() == days
SYMS = ret.columns.tolist()
S = len(SYMS)
SYM = {s: j for j, s in enumerate(SYMS)}
R = ret.to_numpy(float)

# ------------------------------------------------------------------ symbol mapping (dated ticker changes)
sc = pd.read_csv(f'{SP}/symbolchange.csv', header=None, names=['company', 'old', 'new', 'date'], dtype=str)
sc['old'] = sc.old.str.strip()
sc['new'] = sc.new.str.strip()
sc['d'] = pd.to_datetime(sc.date.str.strip(), format='%d-%b-%Y', errors='coerce').dt.strftime('%Y-%m-%d')
CH = {}
for o, n, d in zip(sc.old, sc.new, sc.d):
    if isinstance(d, str):
        CH.setdefault(o, []).append((d, n))


def map_sym(s, day):
    for _ in range(10):
        nxt = [(d, n) for d, n in CH.get(s, []) if d > day]
        if not nxt:
            break
        s = min(nxt)[1]
    return s


dl = pd.read_csv(f'{OUT}/downloads/delivery_eq.csv', dtype={'symbol': str})
st = pd.read_csv(f'{OUT}/downloads/fetch_status.csv')
P(f'delivery rows {len(dl)}; sessions fetched {len(st)}: status {st.status.value_counts().to_dict()}, '
  f'source {st.src.value_counts().to_dict()}')
pairs = dl[['symbol', 'day']].drop_duplicates()
mp = {(s, d): map_sym(s, d) for s, d in zip(pairs.symbol, pairs.day)}
dl['sym'] = [mp[(s, d)] for s, d in zip(dl.symbol, dl.day)]
n_ren = int((dl.sym != dl.symbol).sum())
dl = dl[dl.sym.isin(SYM) & dl.day.isin(DIX)].copy()
dup = dl.duplicated(['day', 'sym'], keep=False)
P(f'rows mapped to an earlier ticker: {n_ren}; rows in universe: {len(dl)}; duplicate day-symbol after mapping: '
  f'{int(dup.sum())}')
if dup.any():
    P(dl[dup].head(20).to_string())
    dl = dl.sort_values(['day', 'sym', 'deliv_qty'], na_position='first').drop_duplicates(['day', 'sym'], keep='last')
ii = dl.day.map(DIX).to_numpy(int)
jj = dl.sym.map(SYM).to_numpy(int)


def mat(col):
    M = np.full((T, S), np.nan)
    M[ii, jj] = dl[col].to_numpy(float)
    return M


DP, DQ, TQ, CL, PC = mat('deliv_per'), mat('deliv_qty'), mat('ttl_trd_qnty'), mat('close'), mat('prev_close')
i_lo, i_hi = int(st.i.min()), int(st.i.max())
P(f'session range with delivery files: i {i_lo}..{i_hi} ({days[i_lo]} .. {days[i_hi]})')

# ------------------------------------------------------------------ validation
adj = pd.read_csv(f'{SP}/ta/build/adjusted_ohlcv.csv.gz', usecols=['day', 'symbol', 'volume', 'volume_factor'])
adj = adj[adj.symbol.isin(SYM) & adj.day.isin(DIX)]
VF = np.full((T, S), np.nan)
AV = np.full((T, S), np.nan)
ai, aj = adj.day.map(DIX).to_numpy(int), adj.symbol.map(SYM).to_numpy(int)
VF[ai, aj] = adj.volume_factor.to_numpy(float)
AV[ai, aj] = adj.volume.to_numpy(float)
W = slice(i_lo, i_hi + 1)
rr = R[W]
rn = CL[W] / PC[W] - 1
both = np.isfinite(rr) & np.isfinite(rn)
dif = np.abs(rr - rn)[both]
P(f'V1 close/prev_close vs returns.csv: {both.sum()} stock-days, |diff| < 0.05pp on {np.mean(dif < 5e-4) * 100:.2f}%, '
  f'< 0.5pp on {np.mean(dif < 5e-3) * 100:.2f}%')
traded = np.isfinite(rr)
have = np.isfinite(DP[W]) | np.isfinite(TQ[W])
P(f'V1b traded stock-days (returns.csv non-NaN) in range: {traded.sum()}; with a delivery-file row: '
  f'{(traded & have).sum()} ({(traded & have).sum() / traded.sum() * 100:.2f}%); with DELIV_PER: '
  f'{(traded & np.isfinite(DP[W])).sum() / traded.sum() * 100:.2f}%')
miss = traded & ~have
if miss.any():
    ms = pd.Series(miss.sum(0), index=SYMS)
    P('    symbols with traded days but no delivery row (top 15):', ms[ms > 0].sort_values(ascending=False).head(15).to_dict())
    md = pd.Series(miss.sum(1), index=days[i_lo:i_hi + 1])
    P('    days with most missing (top 10):', md[md > 0].sort_values(ascending=False).head(10).to_dict())
tv = TQ[W] * VF[W]
ok = np.isfinite(tv) & np.isfinite(AV[W]) & (AV[W] > 0)
rat = tv[ok] / AV[W][ok]
P(f'V2 TTL_TRD_QNTY x volume_factor vs adjusted volume: {ok.sum()} stock-days, within 1% on '
  f'{np.mean(np.abs(rat - 1) < 0.01) * 100:.2f}%, median ratio {np.median(rat):.4f}')
okp = np.isfinite(DP[W]) & np.isfinite(DQ[W]) & (TQ[W] > 0)
rp = np.abs(DP[W][okp] - 100 * DQ[W][okp] / TQ[W][okp])
P(f'V3 DELIV_PER vs 100 x DELIV_QTY / TTL_TRD_QNTY: within 0.01pp on {np.mean(rp < 0.011) * 100:.2f}% of {okp.sum()}')
P(f'    DELIV_PER distribution (all stock-days): p5 {np.nanpercentile(DP[W], 5):.1f} median '
  f'{np.nanpercentile(DP[W], 50):.1f} p95 {np.nanpercentile(DP[W], 95):.1f}; values > 100: {(DP[W] > 100.0001).sum()}')

DQA = DQ * VF


# ------------------------------------------------------------------ feature matrices (index = last session used, e)
def roll(M, w, mp):
    return pd.DataFrame(M).rolling(w, min_periods=mp).mean().to_numpy()


DP5 = roll(DP, 5, 4)
DP60 = roll(DP, 60, 40)
ACC = DP5 - DP60
DQ5 = roll(DQA, 5, 4)
DQ60 = roll(DQA, 60, 40)
with np.errstate(divide='ignore', invalid='ignore'):
    DQR = np.where(DQ60 > 0, DQ5 / DQ60, np.nan)
DP60p = np.vstack([np.full((1, S), np.nan), DP60[:-1]])        # mean over e-60..e-1
DQ60p = np.vstack([np.full((1, S), np.nan), DQ60[:-1]])
DPL = DP - DP60p
with np.errstate(divide='ignore', invalid='ignore'):
    DQL = np.where(DQ60p > 0, DQA / DQ60p, np.nan)
LR = np.log1p(R)
cnt5 = pd.DataFrame(np.isfinite(R).astype(float)).rolling(5, min_periods=1).sum().to_numpy()
PR5 = np.where(cnt5 >= 4, (np.exp(pd.DataFrame(np.nan_to_num(LR)).rolling(5, min_periods=1).sum().to_numpy()) - 1) * 100,
               np.nan)

# V4: reproduce panel vol_ratio_5_60 with our traded quantity (validates the session alignment and the adjustment)
panel = pd.read_csv(f'{SP}/perf/features/panel.csv')
assert len(panel) == 3280
Vg = TQ * VF
VR = (pd.DataFrame(Vg).rolling(5, min_periods=1).mean() / pd.DataFrame(Vg).rolling(60, min_periods=1).mean()).to_numpy()
pj = panel.symbol.map(SYM).to_numpy(int)
pc = panel.i_cut.to_numpy(int)
mine = VR[pc, pj]
okv = np.isfinite(mine) & panel.vol_ratio_5_60.notna().to_numpy()
rv = mine[okv] / panel.vol_ratio_5_60.to_numpy()[okv]
P(f'V4 vol_ratio_5_60 recomputed from NSE traded qty vs panel: {okv.sum()} rows, within 1% on '
  f'{np.mean(np.abs(rv - 1) < 0.01) * 100:.2f}%, within 5% on {np.mean(np.abs(rv - 1) < 0.05) * 100:.2f}%')


# ------------------------------------------------------------------ quarter ranks (A)
def pct_rank_rows(M):
    return pd.DataFrame(M).rank(axis=1, pct=True).to_numpy() * 100


RANKED = {'ACC': ACC, 'DQR': DQR, 'DPL': DPL, 'DP60': DP60}
UNIV = {q: g.symbol.map(SYM).to_numpy(int) for q, g in panel.groupby('qn')}
RANKM = {q: {k: pct_rank_rows(M[:, js]) for k, M in RANKED.items()} for q, js in UNIV.items()}
COLQ = {q: {j: c for c, j in enumerate(js)} for q, js in UNIV.items()}


def take(M, e, j):
    e = np.asarray(e, int)
    j = np.asarray(j, int)
    out = np.full(len(e), np.nan)
    ok_ = (e >= 0) & (e < T)
    out[ok_] = M[e[ok_], j[ok_]]
    return out


def add_a_features(df, e, j, q):
    df['e_A'] = e
    df['ACC'] = take(ACC, e, j)
    df['DQR'] = take(DQR, e, j)
    df['DPL'] = take(DPL, e, j)
    df['DQL'] = take(DQL, e, j)
    df['DP60'] = take(DP60, e, j)
    df['DP5'] = take(DP5, e, j)
    df['PR5'] = take(PR5, e, j)
    for k in RANKED:
        v = np.full(len(df), np.nan)
        for n, (ee, jj_, qq) in enumerate(zip(e, j, q)):
            if qq in RANKM and jj_ in COLQ[qq] and 0 <= ee < T:
                v[n] = RANKM[qq][k][ee, COLQ[qq][jj_]]
        df[f'rank_{k}'] = v
    return df


def add_b_features(df, k, j):
    df['ACC_pre'] = take(ACC, k - 1, j)              # entry k: data through k-1
    df['DQR_pre'] = take(DQR, k - 1, j)
    df['DPK'] = take(DPL, k, j)                      # entry k+1: data through k
    df['DQK'] = take(DQL, k, j)
    df['DPK1'] = take(DP, k + 1, j) - take(DP60p, k, j)   # entry k+2: DP[k+1] - mean DP k-60..k-1
    df['DP_k'] = take(DP, k, j)
    df['DP_k1'] = take(DP, k + 1, j)
    df['base60_k'] = take(DP60p, k, j)
    return df


# ------------------------------------------------------------------ results rows
res = panel[['symbol', 'qn', 'quarter', 'period', 'i_cut', 'i_rd', 'i_p1', 'i_react', 'in_fo_events', 'lag21',
             'vol_ratio_5_60', 'cut_rsi14', 'XN', 'W']].copy()
res = add_a_features(res, res.i_cut.to_numpy(int) - 1, pj, res.qn.to_numpy(int))
res = add_b_features(res, res.i_react.to_numpy(int), pj)
# diagnostic only (NOT point in time for a cutoff-close entry): the cutoff day's own delivery file (e = i_cut),
# published in the evening after the cutoff close
c0 = add_a_features(res[['symbol', 'qn']].copy(), res.i_cut.to_numpy(int), pj, res.qn.to_numpy(int))
for c in ['ACC', 'DQR', 'DPL', 'PR5', 'rank_ACC', 'rank_DQR', 'rank_DPL']:
    res[c + '_c0'] = c0[c].to_numpy()
res.to_csv(f'{OUT}/feat_results.csv', index=False, float_format='%.6g')
P(f'\nresults rows {len(res)}; A features at e = i_cut-1; B at k-1 / k / k+1')
cov = res.groupby('qn').agg(n=('symbol', 'size'), ACC=('ACC', lambda s: s.notna().mean() * 100),
                            DQR=('DQR', lambda s: s.notna().mean() * 100), DPL=('DPL', lambda s: s.notna().mean() * 100),
                            DPK=('DPK', lambda s: s.notna().mean() * 100), DPK1=('DPK1', lambda s: s.notna().mean() * 100))
cov.insert(0, 'results_for', res.groupby('qn').apply(lambda g: f"Results for {g.period.iloc[0]} ({g.quarter.iloc[0]})"))
P('coverage by quarter (% of F&O results with the feature):')
P(cov.round(1).to_string())

# ------------------------------------------------------------------ placebo A (ordinary stock-days)
pl = pd.read_csv(f'{SP}/ta/build/placebo_ta.csv.gz',
                 usecols=['symbol', 'day', 'i', 'in_fo', 'qn_next', 'since_prev_result', 'to_next_result', 'lag_pct',
                          'vol_ratio_5_60'])
pl = pl[(pl.in_fo == True) & pl.qn_next.notna()].copy()
pl['qn_next'] = pl.qn_next.astype(int)
keys = set(zip(panel.symbol, panel.qn))
pl = pl[np.array([(s, q) in keys for s, q in zip(pl.symbol, pl.qn_next)]) & pl.symbol.isin(SYM).to_numpy()].reset_index(drop=True)
assert (pl.since_prev_result >= 10).all() and (pl.to_next_result >= 14).all()
plj = pl.symbol.map(SYM).to_numpy(int)
pl = add_a_features(pl, pl.i.to_numpy(int) - 1, plj, pl.qn_next.to_numpy(int))
pl.to_csv(f'{OUT}/feat_placeboA.csv.gz', index=False, float_format='%.6g', compression='gzip')
P(f'\nplacebo A stock-days {len(pl)} (no result session within 9 before / 13 after); with ACC {pl.ACC.notna().sum()}, '
  f'rank_ACC {pl.rank_ACC.notna().sum()}')

# ------------------------------------------------------------------ placebo B (quiet days)
qd = pd.read_csv(f'{SP}/tafa/C_post_results/quiet_days.csv.gz', usecols=['symbol', 'i', 'day', 'qn_prev', 'XN',
                                                                          'm2_rsi14', 'W'])
qd = qd[qd.symbol.isin(SYM)].reset_index(drop=True)
ev = pd.read_csv(f'{DATA}/events.csv', usecols=['symbol', 'i_rd', 'i_react'])
RS = {}
for s, g in ev.groupby('symbol'):
    RS[s] = np.unique(np.r_[g.i_rd.dropna().to_numpy(int), g.i_react.dropna().to_numpy(int)])
k = qd.i.to_numpy(int)
far = np.ones(len(qd), bool)
for n, (s, kk) in enumerate(zip(qd.symbol, k)):
    r_ = RS.get(s)
    if r_ is not None and np.any((r_ >= kk - 10) & (r_ <= kk + 22)):
        far[n] = False
P(f'\nquiet days {len(qd)}; with no result session of the stock in [k-10, k+22] (covers entry k+2 + 20): {far.sum()}')
qd['no_result_k22'] = far
qd = add_b_features(qd, k, qd.symbol.map(SYM).to_numpy(int))
qd.to_csv(f'{OUT}/feat_placeboB.csv.gz', index=False, float_format='%.6g', compression='gzip')

# compact mapped delivery panel (for re-use / audit)
rows_i, rows_j = np.nonzero(np.isfinite(DP) | np.isfinite(TQ))
cp = pd.DataFrame({'day': np.array(days)[rows_i], 'symbol': np.array(SYMS)[rows_j], 'deliv_per': DP[rows_i, rows_j],
                   'deliv_qty': DQ[rows_i, rows_j], 'ttl_trd_qnty': TQ[rows_i, rows_j],
                   'volume_factor': VF[rows_i, rows_j]})
cp.to_csv(f'{OUT}/delivery_panel.csv.gz', index=False, float_format='%.6g', compression='gzip')
P(f'delivery_panel.csv.gz rows {len(cp)}')
LOG.close()
