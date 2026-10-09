"""Independent rebuild (verifier) of trade-B outcomes and the past-performance features behind the top candidates:
S1 (mean_drift_4 top quintile), S3 (3+ of last 4 drifts positive), W_NEAR52H (winner within 5% of 52-week high).
Own code from events.csv / returns.csv / index_close.csv / adjusted_ohlcv.csv.gz. Nothing imported from the authors.
Writes vb_panel.csv (one row per in_fo result) and vb_history.csv (one row per result, all 4,462)."""
import numpy as np, pandas as pd

SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
D = SP + '/sector_lab/data'
OUT = SP + '/perf/verify_B_post_results'

ses = pd.read_csv(f'{D}/sessions.csv')
ret = pd.read_csv(f'{D}/returns.csv', index_col=0)
ixc = pd.read_csv(f'{D}/index_close.csv', index_col=0)
assert list(ret.index) == list(ses.day) and list(ixc.index) == list(ses.day)
NS = len(ses)
DAYS = ses.day.to_numpy()
SYM = {s: j for j, s in enumerate(ret.columns)}
R = ret.to_numpy(float)
PX = np.cumprod(1 + np.nan_to_num(R), axis=0)          # blank return = flat day
VALID = ~np.isnan(R)
NIF = ixc['Nifty 50'].to_numpy(float)
print('Nifty NaN sessions:', int(np.isnan(NIF).sum()), 'last day', DAYS[-1], 'NS', NS)
NIFR = np.r_[np.nan, NIF[1:] / NIF[:-1] - 1]

ev = pd.read_csv(f'{D}/events.csv')
ev['fo_raw'] = ev.in_fo.astype(str)
print('events in_fo:', ev.fo_raw.value_counts().to_dict())
print('in_fo NaN rows:', ev.loc[~ev.fo_raw.isin(['True', 'False']), ['symbol', 'quarter']].values.tolist())
# universe: in_fo True, plus the 2 NaN rows (RELIANCE Q1 FY24, VEDL Q4 FY26) - both are F&O stocks; flagged separately
ev['in_fo_b'] = ev.fo_raw.eq('True') | (~ev.fo_raw.isin(['True', 'False']))
ev['j'] = ev.symbol.map(SYM)
assert ev.j.notna().all()
ev['j'] = ev.j.astype(int)


def fwd(j, k, H=20):
    """stock and Nifty return close k -> close k+H (percent) and tradability (k+21 exists, <=2 blanks in k+1..k+21)."""
    j = np.asarray(j, int); k = np.asarray(k, int)
    ok = k + 21 <= NS - 1
    kk = np.where(ok, k, 0)
    ii = np.minimum(kk + H, NS - 1)
    raw = (PX[ii, j] / PX[kk, j] - 1) * 100
    nif = (NIF[ii] / NIF[kk] - 1) * 100
    blanks = np.zeros(len(k), int)
    for t in range(1, 22):
        blanks += ~VALID[np.minimum(kk + t, NS - 1), j]
    ok &= blanks <= 2
    return raw, nif, ok


def drift_hist(j, k, H=20):
    """history drift: stock minus Nifty over k -> k+H, gross, percent; NaN if k+H beyond data."""
    j = np.asarray(j, int); k = np.asarray(k, int)
    ok = k + H <= NS - 1
    kk = np.where(ok, k, 0)
    d = ((PX[kk + np.where(ok, H, 0), j] / PX[kk, j]) - (NIF[kk + np.where(ok, H, 0)] / NIF[kk])) * 100
    return np.where(ok, d, np.nan)


k = ev.i_react.to_numpy(int)
j = ev.j.to_numpy(int)
ev['XN'] = (R[k, j] - NIFR[k]) * 100
ev['drift20'] = drift_hist(j, k)
ev['exit20'] = k + 20
raw, nif, ok = fwd(j, k)
ev['raw20'] = raw; ev['nif20'] = nif
ev['tradable'] = ok & ev.XN.notna().to_numpy()
ev['vsN_net'] = ev.raw20 - ev.nif20 - 0.19
ev.loc[~ev.tradable, 'vsN_net'] = np.nan

# ---------------------------------------------------------------- track record (point in time at decision k)
ev = ev.sort_values(['symbol', 'qn']).reset_index(drop=True)
rows = []
for s, g in ev.groupby('symbol', sort=False):
    g = g.sort_values('i_react')
    gi = g.index.to_numpy()
    for a in range(len(g)):
        kdec = int(g.i_react.iloc[a])
        prior = g[(g.i_p1 < kdec) & (g.i_react < kdec) & (g.qn < g.qn.iloc[a])]
        # also guard: no earlier result counted whose qn >= current
        last4 = prior.tail(4)
        known = last4[last4.exit20 < kdec]
        last4_all_known = len(known) == len(last4)
        last3 = prior.tail(3); k3 = last3[last3.exit20 < kdec]
        last6 = prior.tail(6); k6 = last6[last6.exit20 < kdec]
        last8 = prior.tail(8); k8 = last8[last8.exit20 < kdec]
        allk = prior[prior.exit20 < kdec]
        rows.append(dict(
            idx=gi[a], n_prev=len(prior),
            n_drift_4=len(known), mean_drift_4=known.drift20.mean() if len(prior) >= 4 else np.nan,
            n_pos_drift_4=int((known.drift20 > 0).sum()) if len(prior) >= 4 else np.nan,
            all4_known=last4_all_known if len(prior) >= 4 else np.nan,
            max_exit_used=known.exit20.max() if len(known) else np.nan,
            mean_drift_3=k3.drift20.mean() if len(prior) >= 3 else np.nan,
            mean_drift_6=k6.drift20.mean() if len(prior) >= 6 else np.nan,
            mean_drift_8=k8.drift20.mean() if len(prior) >= 8 else np.nan,
            mean_drift_all=allk.drift20.mean() if len(allk) else np.nan, n_drift_all=len(allk),
            median_drift_4=known.drift20.median() if len(prior) >= 4 else np.nan,
            prev1_xn=prior.XN.iloc[-1] if len(prior) else np.nan,
            prev1_drift=prior.drift20.iloc[-1] if len(prior) and prior.exit20.iloc[-1] < kdec else np.nan,
            n_win_4=int((last4.XN > 4).sum()) if len(prior) >= 4 else np.nan,
        ))
tr = pd.DataFrame(rows).set_index('idx').sort_index()
ev = ev.join(tr)

# ---------------------------------------------------------------- 52-week high at k (own definition, adjusted OHLCV)
ohl = pd.read_csv(f'{SP}/ta/build/adjusted_ohlcv.csv.gz', usecols=['day', 'symbol', 'high', 'close'])
ohl = ohl.sort_values(['symbol', 'day'])
ohl['hmax250'] = ohl.groupby('symbol').high.transform(lambda x: x.rolling(250, min_periods=250).max())
ohl['dist_52wh'] = (ohl.close / ohl.hmax250 - 1) * 100
ev['reaction_day_s'] = DAYS[ev.i_react.to_numpy(int)]
ev = ev.merge(ohl[['symbol', 'day', 'dist_52wh']].rename(columns={'day': 'reaction_day_s'}),
              on=['symbol', 'reaction_day_s'], how='left')

# ---------------------------------------------------------------- momentum (for controls): 252-session vs Nifty at k
def vsN(j, k, L):
    j = np.asarray(j, int); k = np.asarray(k, int)
    ok = k - L >= 0
    k0 = np.where(ok, k - L, 0)
    nblank = np.array([(~VALID[a + 1:b + 1, c]).sum() for a, b, c in zip(k0, k, j)])
    r = ((PX[k, j] / PX[k0, j]) - (NIF[k] / NIF[k0])) * 100
    return np.where(ok & (nblank <= 0.05 * L), r, np.nan)


ev['vsN_252'] = vsN(ev.j, ev.i_react, 252)
ev['vsN_63'] = vsN(ev.j, ev.i_react, 63)

# first in_fo quarter per symbol (survivorship split)
first_fo = ev[ev.in_fo_b].groupby('symbol').qn.min()
ev['first_fo_qn'] = ev.symbol.map(first_fo)
ev['results_for'] = 'Results for ' + ev.period + ' (' + ev.quarter + ')'

hist = ev[['symbol', 'qn', 'quarter', 'period', 'i_p1', 'i_react', 'XN', 'drift20', 'exit20']]
hist.to_csv(f'{OUT}/vb_history.csv', index=False, float_format='%.6g')
cols = ['symbol', 'qn', 'quarter', 'period', 'results_for', 'industry', 'sector_index', 'fin_type', 'fo_raw', 'in_fo_b',
        'i_cut', 'i_p1', 'i_react', 'reaction_day_s', 'XN', 'raw20', 'nif20', 'tradable', 'vsN_net', 'n_prev',
        'n_drift_4', 'mean_drift_4', 'n_pos_drift_4', 'all4_known', 'max_exit_used', 'mean_drift_3', 'mean_drift_6',
        'mean_drift_8', 'mean_drift_all', 'n_drift_all', 'median_drift_4', 'prev1_xn', 'prev1_drift', 'n_win_4',
        'dist_52wh', 'vsN_252', 'vsN_63', 'first_fo_qn', 'mcap']
p = ev[ev.in_fo_b][cols].reset_index(drop=True)
p.to_csv(f'{OUT}/vb_panel.csv', index=False, float_format='%.6g')
print('panel rows', len(p), 'tradable', int(p.tradable.sum()))
W = p.tradable & (p.XN > 4)
print('W n', int(W.sum()), 'mean', round(p.vsN_net[W].mean(), 3), '| all tradable mean', round(p.vsN_net[p.tradable].mean(), 3))
