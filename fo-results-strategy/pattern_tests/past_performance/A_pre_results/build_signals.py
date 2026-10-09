#!/usr/bin/env python3
"""Signals for the trade-A performance tests (features only; no results outcome is read here).

1. Point-in-time percentile ranks at the cutoff (rank among the same quarter's F&O stocks, all measured on this row's
   cutoff session; same method as perf/features/build_panel.py): rank_vsN_21, rank_vsSec_63, rank_vsSec_252.
   Validation: the same code reproduces panel rank_vsN_63/126/252_A, vsN_*_A and vsSec_*_A.
2. Placebo stock-days (ta/build/placebo_ta.csv.gz, in_fo True, next result in the panel): price-performance features at
   day k, ranks among the F&O stocks of quarter qn_next measured at k, and the track-record flags of (symbol, qn_next).
3. Signal masks for every pre-registered test (prereg.txt) on results rows and on placebo days.
Writes signals_results.csv.gz, signals_placebo.csv.gz, build_signals.log.
"""
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
DATA = f'{SP}/sector_lab/data'
FEAT = f'{SP}/perf/features'
LOG = open(f'{HERE}/build_signals.log', 'w')


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    LOG.write(s + '\n')
    LOG.flush()


ses = pd.read_csv(f'{DATA}/sessions.csv')
days = ses.day.tolist()
T = len(days)
ret = pd.read_csv(f'{DATA}/returns.csv', index_col=0)
assert ret.index.tolist() == days
SYMS = ret.columns.tolist()
SYM = {s: j for j, s in enumerate(SYMS)}
R = ret.to_numpy(float)
S = R.shape[1]
PX = np.cumprod(1.0 + np.nan_to_num(R), axis=0)
CVALID = np.cumsum(~np.isnan(R), axis=0)
FIRST = np.array([np.argmax(np.isfinite(R[:, j])) for j in range(S)])
ixc = pd.read_csv(f'{DATA}/index_close.csv', index_col=0)
assert ixc.index.tolist() == days
NIFTY = ixc['Nifty 50'].to_numpy(float)
MAXBLANK = {21: 2, 63: 3, 126: 6, 252: 12}


def stock_ret_matrix(L):
    """(T x S) % return over (i-L, i]; NaN when the window starts before the listing-day return or has too many
    no-trade sessions (identical rule to build_panel.stock_ret)."""
    out = np.full((T, S), np.nan)
    i = np.arange(L, T)
    r = (PX[i] / PX[i - L] - 1) * 100
    blanks = L - (CVALID[i] - CVALID[i - L])
    ok = (i[:, None] - L >= FIRST[None, :]) & (blanks <= MAXBLANK[L])
    out[i] = np.where(ok, r, np.nan)
    return out


def index_ret_vec(arr, L):
    out = np.full(T, np.nan)
    out[L:] = (arr[L:] / arr[:-L] - 1) * 100
    return out


SR = {L: stock_ret_matrix(L) for L in (21, 63, 126, 252)}
NR = {L: index_ret_vec(NIFTY, L) for L in (21, 63, 126, 252)}
IXR = {}
for sx in ixc.columns:
    a = ixc[sx].to_numpy(float)
    IXR[sx] = {L: index_ret_vec(a, L) for L in (63, 252)}

panel = pd.read_csv(f'{FEAT}/panel.csv')
assert len(panel) == 3280
UJ = panel.symbol.map(SYM).to_numpy(int)


def vssec_matrix_for(q_rows, L):
    """(T x len(q_rows)) stock minus sector index L-session return for the quarter's universe (each stock with its own
    sector_index of that quarter)."""
    cols = []
    for sym, sx in zip(q_rows.symbol, q_rows.sector_index):
        j = SYM[sym]
        if isinstance(sx, str) and sx in IXR:
            cols.append(SR[L][:, j] - IXR[sx][L])
        else:
            cols.append(np.full(T, np.nan))
    return np.column_stack(cols)


def pct_rank_rows(M):
    """Row-wise percentile rank (pandas rank pct, average ties) x 100; NaN stays NaN."""
    return pd.DataFrame(M).rank(axis=1, pct=True).to_numpy() * 100


# ------------------------------------------------------------------ placebo days
pl = pd.read_csv(f'{SP}/ta/build/placebo_ta.csv.gz',
                 usecols=['symbol', 'day', 'i', 'in_fo', 'qn_prev', 'qn_next', 'since_prev_result', 'to_next_result',
                          'dist_52w_high_pct', 'lag_pct', 'vol_ratio_5_60', 'three_day'])
n0 = len(pl)
pl = pl[(pl.in_fo == True) & pl.qn_next.notna()].copy()
pl['qn_next'] = pl.qn_next.astype(int)
keys = set(zip(panel.symbol, panel.qn))
pl = pl[[(s, q) in keys for s, q in zip(pl.symbol, pl.qn_next)]].copy()
pl = pl[pl.symbol.isin(SYM)].reset_index(drop=True)
P(f'placebo_ta rows {n0}; in_fo True with next result in the panel: {len(pl)} stock-days, {pl.symbol.nunique()} symbols, '
  f'qn_next {pl.qn_next.min()}..{pl.qn_next.max()}; min since_prev {pl.since_prev_result.min()}, '
  f'min to_next {pl.to_next_result.min()}')
assert (pl.since_prev_result >= 10).all() and (pl.to_next_result >= 14).all()
PJ = pl.symbol.map(SYM).to_numpy(int)
PI = pl.i.to_numpy(int)

# ------------------------------------------------------------------ results rows: values and point-in-time ranks
res = panel[['symbol', 'qn', 'i_cut']].copy()
pla = pl[['symbol', 'qn_next', 'i']].copy()
for L in (21, 63, 126, 252):
    res[f'my_vsN_{L}'] = SR[L][panel.i_cut.to_numpy(int), UJ] - NR[L][panel.i_cut.to_numpy(int)]
    pla[f'vsN_{L}'] = SR[L][PI, PJ] - NR[L][PI]
for c in ['rank_vsN_21', 'rank_vsN_63', 'rank_vsN_126', 'rank_vsN_252', 'rank_vsSec_63', 'rank_vsSec_252',
          'vsSec_63', 'vsSec_252']:
    res['my_' + c] = np.nan
    pla[c] = np.nan
for q, gq in panel.groupby('qn'):
    gq = gq.reset_index()          # 'index' = panel row
    jq = gq.symbol.map(SYM).to_numpy(int)
    col_of = {s: n for n, s in enumerate(gq.symbol)}
    mats = {f'rank_vsN_{L}': pct_rank_rows(SR[L][:, jq]) for L in (21, 63, 126, 252)}
    secv = {L: vssec_matrix_for(gq, L) for L in (63, 252)}
    for L in (63, 252):
        mats[f'rank_vsSec_{L}'] = pct_rank_rows(secv[L])
    ic = gq.i_cut.to_numpy(int)
    cc = np.arange(len(gq))
    for name, M in mats.items():
        res.loc[gq['index'].to_numpy(), 'my_' + name] = M[ic, cc]
    for L in (63, 252):
        res.loc[gq['index'].to_numpy(), f'my_vsSec_{L}'] = secv[L][ic, cc]
    # placebo days whose next result is in quarter q
    sel = np.flatnonzero(pla.qn_next.to_numpy() == q)
    if len(sel) == 0:
        continue
    pc = np.array([col_of[s] for s in pla.symbol.to_numpy()[sel]])
    pi = PI[sel]
    for name, M in mats.items():
        pla.loc[sel, name] = M[pi, pc]
    for L in (63, 252):
        pla.loc[sel, f'vsSec_{L}'] = secv[L][pi, pc]

# validation against the panel
for L in (21, 63, 126, 252):
    d = (res[f'my_vsN_{L}'] - panel[f'vsN_{L}_A']).abs()
    P(f'check vsN_{L}: max abs diff {d.max():.2e}, NaN mine {res[f"my_vsN_{L}"].isna().sum()} panel {panel[f"vsN_{L}_A"].isna().sum()}')
    assert d.max() < 1e-3
for L in (63, 126, 252):
    d = (res[f'my_rank_vsN_{L}'] - panel[f'rank_vsN_{L}_A']).abs()
    P(f'check rank_vsN_{L}: max abs diff {d.max():.2e} (method validation)')
    assert d.max() < 1e-3 and (res[f'my_rank_vsN_{L}'].isna() == panel[f'rank_vsN_{L}_A'].isna()).all()
for L in (63, 252):
    d = (res[f'my_vsSec_{L}'] - panel[f'vsSec_{L}_A']).abs()
    P(f'check vsSec_{L}: max abs diff {d.max():.2e}, NaN mine {res[f"my_vsSec_{L}"].isna().sum()} panel {panel[f"vsSec_{L}_A"].isna().sum()}')
    assert d.max() < 1e-3 and (res[f'my_vsSec_{L}'].isna() == panel[f'vsSec_{L}_A'].isna()).all()
d = (pla.vsN_21 - pl.lag_pct).abs()
P(f'check placebo vsN_21 vs placebo_ta lag_pct: max abs diff {d.max():.2e}, n {d.notna().sum()}, NaN mine {pla.vsN_21.isna().sum()} ta {pl.lag_pct.isna().sum()}')
P('rank_vsN_21 results: NaN', res.my_rank_vsN_21.isna().sum(), '; rank_vsSec_63 NaN', res.my_rank_vsSec_63.isna().sum(),
  '; rank_vsSec_252 NaN', res.my_rank_vsSec_252.isna().sum())

# ------------------------------------------------------------------ feature frames for the two worlds
F = panel.copy()
F['rank_vsN_21'] = res.my_rank_vsN_21
F['rank_vsSec_63'] = res.my_rank_vsSec_63
F['rank_vsSec_252'] = res.my_rank_vsSec_252
for L in (63, 126, 252):
    F[f'rank_vsN_{L}'] = F[f'rank_vsN_{L}_A']
F['vsN_21'] = F.vsN_21_A
F['dist_52wh'] = F.dist_52wh_A
F['vol'] = F.vol_ratio_5_60
F['lag'] = F.lag21
F['ok_drift'] = True

# track-record within-quarter quintiles (on the results rows; placebo days inherit the flag of symbol + qn_next)
TRQ = ['mean_three_day_4_A', 'mean_xn_4_A', 'mean_abs_xn_4_A', 'mean_drift_4_A']
for c in TRQ:
    F['pct_' + c] = F.groupby('qn')[c].rank(pct=True)

TRCOLS = ['prev1_three_day_A', 'n_pos_three_day_4_A', 'prev1_xn_A', 'n_winner_4_A', 'mean_three_day_4_A'] + \
         ['pct_' + c for c in TRQ]
G = pla.merge(F[['symbol', 'qn', 'sector_index', 'in_fo_events'] + TRCOLS].rename(columns={'qn': 'qn_next'}),
              on=['symbol', 'qn_next'], how='left', validate='m:1')
assert len(G) == len(pla)
G['dist_52wh'] = pl.dist_52w_high_pct.to_numpy()
G['vol'] = pl.vol_ratio_5_60.to_numpy()
G['lag'] = pla.vsN_21.to_numpy()
# drift items: placebo day must be after the previous result's drift exit (i_react + 20)
hist = pd.read_csv(f'{FEAT}/history.csv', usecols=['symbol', 'qn', 'h_dr_end', 'h_td_end', 'h_xn_end'])
G['qn_prev'] = pl.qn_prev.astype(int).to_numpy()
G = G.merge(hist.rename(columns={'qn': 'qn_prev'}), on=['symbol', 'qn_prev'], how='left', validate='m:1')
assert G.h_dr_end.notna().all()
assert (G.h_td_end < G.i).all() and (G.h_xn_end < G.i).all()   # last result's window / reaction known at k
G['ok_drift'] = G.i > G.h_dr_end
assert ((pl.qn_next - pl.qn_prev) == 1).all()
P(f'placebo days after the previous drift exit: {int(G.ok_drift.sum())} of {len(G)}')


# ------------------------------------------------------------------ pre-registered signals
def masks(X):
    top = lambda c: X[c] > 80
    bot = lambda c: X[c] <= 20
    tq = lambda c: X['pct_' + c] > 0.8
    bq = lambda c: X['pct_' + c] <= 0.2
    m = {
        'TR01': X.prev1_three_day_A > 0,
        'TR02': X.prev1_three_day_A < 0,
        'TR03': X.n_pos_three_day_4_A >= 3,
        'TR04': X.n_pos_three_day_4_A <= 1,
        'TR05': tq('mean_three_day_4_A'),
        'TR06': bq('mean_three_day_4_A'),
        'TR07': X.prev1_xn_A > 4,
        'TR08': X.prev1_xn_A > 4,
        'TR09': X.prev1_xn_A < -4,
        'TR10': X.prev1_xn_A < -4,
        'TR11': X.n_winner_4_A >= 2,
        'TR12': tq('mean_xn_4_A'),
        'TR13': bq('mean_xn_4_A'),
        'TR14': tq('mean_abs_xn_4_A'),
        'TR15': tq('mean_drift_4_A') & X.ok_drift,
        'TR16': bq('mean_drift_4_A') & X.ok_drift,
        'PP01': bot('rank_vsN_21'),
        'PP02': top('rank_vsN_21'),
        'PP03': top('rank_vsN_63'),
        'PP04': bot('rank_vsN_63'),
        'PP05': top('rank_vsN_126'),
        'PP06': bot('rank_vsN_126'),
        'PP07': top('rank_vsN_252'),
        'PP08': bot('rank_vsN_252'),
        'PP09': top('rank_vsN_252') & (X.vsN_21 < 0),
        'PP10': (X.rank_vsN_252 > 50) & bot('rank_vsN_21'),
        'PP11': X.dist_52wh >= -5,
        'PP12': X.dist_52wh <= -30,
        'PP13': top('rank_vsSec_63'),
        'PP14': bot('rank_vsSec_63'),
        'PP15': top('rank_vsSec_252'),
        'PP16': bot('rank_vsSec_252'),
        'PP17': bot('rank_vsN_252') & bot('rank_vsN_21'),
        # replacement tests (in_fo_events True applied on results rows below)
        'RP1': (X.vol >= 1.0) & bot('rank_vsN_63'),
        'RP2': (X.lag < -10) & (X.mean_three_day_4_A > 0),
        'RP3': (X.lag < -10) & (X.rank_vsN_252 > 50),
        # reference sets
        'LAGRULE': (X.lag < -10) & (X.vol >= 1.0),
        'VOL_ALONE': X.vol >= 1.0,
        'LAG_ALONE': X.lag < -10,
    }
    return pd.DataFrame({k: v.fillna(False).astype(bool).to_numpy() for k, v in m.items()})


# placebo frame needs the rank columns
for c in ['rank_vsN_21', 'rank_vsN_63', 'rank_vsN_126', 'rank_vsN_252', 'rank_vsSec_63', 'rank_vsSec_252', 'vsN_21']:
    G[c] = pla[c].to_numpy()
MR = masks(F)
MP = masks(G)
fo_ev = (F.in_fo_events == True).to_numpy()
for k in ['RP1', 'RP2', 'RP3', 'LAGRULE', 'VOL_ALONE', 'LAG_ALONE']:
    MR[k] = MR[k].to_numpy() & fo_ev
P('LAGRULE results rows:', int(MR.LAGRULE.sum()), '(expect 85)')
assert MR.LAGRULE.sum() == 85
rep = pd.read_csv(__import__('os').environ.get('REPO_ROOT', '.') + '/results/lag10_volume/trades.csv')
s1 = set(zip(F.symbol[MR.LAGRULE], F.qn[MR.LAGRULE]))
s2 = set(zip(rep.symbol, rep.qn))
P('LAGRULE same set as repo results/lag10_volume/trades.csv:', s1 == s2)
assert s1 == s2

P('\nsignal counts (results rows / placebo days):')
for k in MR.columns:
    P(f'  {k:10s} {int(MR[k].sum()):5d} / {int(MP[k].sum()):7d}')

keep_res = F[['symbol', 'qn', 'quarter', 'period', 'i_cut', 'in_fo_events', 'lag21', 'vol_ratio_5_60',
              'rank_vsN_21', 'rank_vsN_63', 'rank_vsN_126', 'rank_vsN_252', 'rank_vsSec_63', 'rank_vsSec_252',
              'vsN_21', 'dist_52wh'] + TRCOLS].reset_index(drop=True)
pd.concat([keep_res, MR], axis=1).to_csv(f'{HERE}/signals_results.csv.gz', index=False, float_format='%.6g',
                                         compression='gzip')
keep_pl = G[['symbol', 'qn_prev', 'qn_next', 'i', 'ok_drift', 'lag', 'vol', 'rank_vsN_21', 'rank_vsN_63',
             'rank_vsN_126', 'rank_vsN_252', 'rank_vsSec_63', 'rank_vsSec_252', 'vsN_21', 'dist_52wh']].copy()
keep_pl['three_day'] = pl.three_day.to_numpy()
pd.concat([keep_pl.reset_index(drop=True), MP], axis=1).to_csv(f'{HERE}/signals_placebo.csv.gz', index=False,
                                                                float_format='%.6g', compression='gzip')
P('wrote signals_results.csv.gz', MR.shape, 'signals_placebo.csv.gz', MP.shape)
