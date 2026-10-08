"""
01_build.py -- build the group tables and the non-results placebo panel for the pre-registered splits.

Outputs (this folder):
  group_fo.csv   the 679 in_fo results with vs_nifty_1m < -5% (+ features_all columns + derived features)
  group_all.csv  all results with vs_nifty_1m < -5% (secondary universe)
  placebo.csv    stock-sessions with NO result session of that stock in [c-10, c+13], lag < -5%,
                 price features recomputed from the adjusted daily returns with the same definitions as
                 features22.py / 01_build_features.py, slow-moving features carried from the stock's NEXT
                 result row (its "prev_*" values are already public at the placebo date), 3-day forward return.
  feature_check.csv  agreement of the recomputed price features with features_all at the real cutoffs.
No outcome is summarised here.
"""
import os
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.path.abspath(os.path.join(HERE, '..', '..'))
FA = pd.read_csv(f'{SP}/five_pct/A_rule_search/features_all.csv')
TR = pd.read_csv(os.environ.get('REPO_ROOT', '.') + '/results/lagged_nifty/trades_lag5.csv')
EV = pd.read_csv(f'{SP}/sector_lab/data/events.csv')
R = pd.read_csv(f'{SP}/sector_lab/data/returns.csv')
IX = pd.read_csv(f'{SP}/sector_lab/data/index_close.csv')
assert (R.day.values == IX.day.values).all()
days = R.day.values
Rv = R.drop(columns='day').astype(float)
syms = list(Rv.columns)
NS = len(days)

# ---------------------------------------------------------------- price features on the full panel
r = Rv.values
valid = np.isfinite(r)
first = np.where(valid.any(0), valid.argmax(0), NS)
r0 = np.nan_to_num(r)
logp = np.cumsum(np.log1p(r0), axis=0)
L = np.exp(logp)
for j in range(r.shape[1]):
    L[:first[j], j] = np.nan
Ld = pd.DataFrame(L)
Rd = pd.DataFrame(r)


def shift_ret(n):
    return (Ld / Ld.shift(n) - 1).values


P = {}
P['r1w'] = shift_ret(5); P['r1m'] = shift_ret(21); P['r3m'] = shift_ret(63); P['r1y'] = shift_ret(250)
P['r3d'] = shift_ret(3)
P['d0'] = r
P['from_52w_high'] = (Ld / Ld.rolling(250, min_periods=201).max() - 1).values
P['from_52w_low'] = (Ld / Ld.rolling(250, min_periods=201).min() - 1).values
P['vs_ma200'] = (Ld / Ld.rolling(200, min_periods=200).mean() - 1).values
P['vol60'] = (Rd.rolling(60, min_periods=41).std() * np.sqrt(252)).values
sd60 = Rd.rolling(60, min_periods=45).std(ddof=0)
P['vol5_60'] = (Rd.rolling(5, min_periods=3).std(ddof=0) / sd60).values
P['dist_20l'] = (Ld / Ld.rolling(20, min_periods=20).min() - 1).values
P['worst1m'] = Rd.rolling(21, min_periods=15).min().values
# streak: signed run of consecutive up / down days ending at the session (0 / NaN breaks)
st = np.zeros_like(r)
for j in range(r.shape[1]):
    s = 0
    col = r[:, j]
    for i in range(NS):
        x = col[i]
        if not np.isfinite(x) or x == 0:
            s = 0
        elif s > 0 and x > 0:
            s += 1
        elif s < 0 and x < 0:
            s -= 1
        else:
            s = 1 if x > 0 else -1
        st[i, j] = s
P['streak'] = st
nifty = IX['Nifty 50'].values.astype(float)
nifty_1m = np.r_[np.full(21, np.nan), nifty[21:] / nifty[:-21] - 1]
nifty_1w = np.r_[np.full(5, np.nan), nifty[5:] / nifty[:-5] - 1]
vix = IX['India VIX'].values.astype(float)


def idx_1m(name):
    x = IX[name].values.astype(float)
    return np.r_[np.full(21, np.nan), x[21:] / x[:-21] - 1]


SEC1M = {s: idx_1m(s) for s in IX.columns if s != 'day'}
col = {s: k for k, s in enumerate(syms)}


def price_feats(j, c, sector):
    o = {k: P[k][c, j] for k in P}
    o['nifty_1m'] = nifty_1m[c]
    o['vs_nifty_1m'] = o['r1m'] - nifty_1m[c]
    o['vs_nifty_1w'] = o['r1w'] - nifty_1w[c]
    o['india_vix'] = vix[c]
    if isinstance(sector, str) and sector in SEC1M:
        s1 = SEC1M[sector][c]
        o['sector_1m'] = s1
        o['vs_sector_1m'] = o['r1m'] - s1
        o['sec_vs_nifty_1m'] = s1 - nifty_1m[c]
    return o


# ---------------------------------------------------------------- group tables (results)
def derive(df):
    df = df.copy()
    df['lag'] = df['vs_nifty_1m']
    df['ratio_1w'] = df['vs_nifty_1w'] / df['vs_nifty_1m']
    df['fin'] = df['fin_type'].isin(['Bank', 'NBFC / financial']).astype(int)
    return df


FA = FA.copy()
FA['worst1m'] = [P['worst1m'][c, col[s]] for s, c in zip(FA.symbol, FA.i_cut)]
FA = derive(FA)
FA['three_day_pct'] = 100 * FA.three_day
FA['tp_pct'] = 100 * FA.tp3
grp_all = FA[FA.vs_nifty_1m < -0.05].copy()
grp_fo = grp_all[grp_all.in_fo == True].copy()
# must be the same 679 trades as the project's trades_lag5.csv
k1 = set(zip(grp_fo.symbol, grp_fo.quarter)); k2 = set(zip(TR.symbol, TR.quarter))
print('group fo', len(grp_fo), 'trades file', len(TR), 'same keys', k1 == k2, 'all-results group', len(grp_all))
chk = grp_fo.merge(TR[['symbol', 'quarter', 'three_day', 'take_profit']], on=['symbol', 'quarter'], suffixes=('', '_t'))
print('max |three_day diff|', np.abs(chk.three_day - chk.three_day_t).max(), ' max |tp diff|', np.abs(chk.tp3 - chk.take_profit).max())
grp_fo.to_csv(f'{HERE}/group_fo.csv', index=False)
grp_all.to_csv(f'{HERE}/group_all.csv', index=False)

# agreement of recomputed price features with features_all at the real cutoffs (all 4,460 rows)
rec = pd.DataFrame([price_feats(col[s], c, si) for s, c, si in zip(FA.symbol, FA.i_cut, FA.sector_index)])
rows = []
for k in ['r1w', 'r1m', 'r3m', 'r1y', 'r3d', 'd0', 'from_52w_high', 'from_52w_low', 'vs_ma200', 'vol60', 'vol5_60',
          'dist_20l', 'streak', 'nifty_1m', 'vs_nifty_1m', 'vs_nifty_1w', 'india_vix', 'sector_1m', 'vs_sector_1m',
          'sec_vs_nifty_1m']:
    a, b = FA[k].values.astype(float), rec[k].values.astype(float)
    ok = np.isfinite(a) & np.isfinite(b)
    rows.append({'feature': k, 'n_both': int(ok.sum()), 'n_fa': int(np.isfinite(a).sum()), 'n_rec': int(np.isfinite(b).sum()),
                 'corr': np.corrcoef(a[ok], b[ok])[0, 1], 'median_abs_diff': np.median(np.abs(a[ok] - b[ok])),
                 'p95_abs_diff': np.percentile(np.abs(a[ok] - b[ok]), 95)})
fc = pd.DataFrame(rows)
fc.to_csv(f'{HERE}/feature_check.csv', index=False)
print(fc.round(4).to_string())

# ---------------------------------------------------------------- placebo panel
carry = ['past_avg_3d', 'past_pct_up', 'prev1_3d', 'prev1_next20', 'prev_pat_yoy', 'prev_sales_yoy', 'profit_rising_4q',
         'sales_rising_4q', 'roe', 'pe', 'pe_vs_peers', 'debt_equity', 'log_mcap', 'fin', 'in_fo', 'sector_index', 'qn']
rd_by_sym = EV.groupby('symbol').i_rd.apply(lambda s: np.sort(s.dropna().astype(int).values)).to_dict()
fa_by_sym = {s: g.sort_values('i_cut') for s, g in FA.groupby('symbol')}
qcut = FA.groupby('qn').i_cut.median()
lo = int(FA[FA.qn == 0].i_cut.min()) - 30
hi = min(int(FA[FA.qn == FA.qn.max()].i_cut.max()) + 30, NS - 4)
lagmat = P['r1m'] - nifty_1m[:, None]
out = []
for s, g in fa_by_sym.items():
    if s not in col:
        continue
    j = col[s]
    rds = rd_by_sym.get(s, np.array([], int))
    cuts = g.i_cut.values
    for c in range(max(lo, first[j] + 21), hi + 1):
        lg = lagmat[c, j]
        if not (lg < -0.05):
            continue
        if len(rds) and ((rds >= c - 10) & (rds <= c + 13)).any():
            continue
        k = np.searchsorted(cuts, c, side='right')       # next result row of this stock
        if k >= len(cuts):
            k = len(cuts) - 1                             # after the last one: carry the last
        nx = g.iloc[k]
        o = {'symbol': s, 'c': c, 'day': days[c]}
        o.update(price_feats(j, c, nx.sector_index))
        for kk in carry:
            o['next_' + kk if kk == 'qn' else kk] = nx[kk]
        y = np.nan_to_num(r[c + 1:c + 4, j])
        o['three_day_pct'] = 100 * y.sum()
        o['tp_pct'] = 100 * (y[0] if y[0] > 0.03 else (y[0] + y[1] if y[0] + y[1] > 0.03 else y.sum()))
        out.append(o)
pl = pd.DataFrame(out)
# season (qn) of a placebo date = the results season whose median cutoff is nearest
qv, qc = qcut.index.values, qcut.values
pl['qn'] = qv[np.abs(pl.c.values[:, None] - qc[None, :]).argmin(1)]
pl['lag'] = pl['vs_nifty_1m']
pl['ratio_1w'] = pl['vs_nifty_1w'] / pl['vs_nifty_1m']
pl.to_csv(f'{HERE}/placebo.csv', index=False)
print('placebo rows', len(pl), 'in_fo', int((pl.in_fo == True).sum()), 'stocks', pl.symbol.nunique(),
      'days', pl.day.min(), pl.day.max())
print(pl.groupby('qn').size().to_string())
