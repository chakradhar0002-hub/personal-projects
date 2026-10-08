"""
06_placebo_panel.py -- price features for every (session, stock) so a rule can be applied on dates WITHOUT results.
Definitions copied from pattern_tests/features22.py and five_pct/A_rule_search/01_build_features.py (checked against
features_all.csv at the real cutoffs, printed below).  Placebo rows: sessions from 2021-03-01 to the last event,
stock inside its F&O period (between its first and last in_fo result cutoff), no result session of that stock within
10 sessions either side.  Forward return = sum of the next 3 daily returns (same as three_day).
As-of results features for placebo dates: own_rd / own_pre5 = averages over the stock's results completed before the
date (>= 2), season_so_far_3d = average three_day of the latest season's results completed by the date (>= 5).
Output: placebo_panel.pkl (long table of placebo rows) and event_check.csv
"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gsearch as G
D = os.environ.get('LAB_ROOT', 'lab') + '/sector_lab/data/'
R = pd.read_csv(D + 'returns.csv')
I = pd.read_csv(D + 'intraday.csv')
IX = pd.read_csv(D + 'index_close.csv')
E = pd.read_csv(D + 'events.csv')
F = pd.read_csv(f'{G.RL.HERE}/features_all.csv')
days = R.day.values
syms = list(R.columns[1:])
RA = R[syms].values.astype(float)
IA = I[syms].values.astype(float)
T, NS = RA.shape
nifty = IX['Nifty 50'].values.astype(float)
valid = np.isfinite(RA)
started = np.maximum.accumulate(valid, axis=0)
lv = np.cumprod(1 + np.nan_to_num(RA), axis=0)
lv[~started] = np.nan


def shift(a, k):
    out = np.full_like(a, np.nan)
    out[k:] = a[:-k]
    return out


def roll(a, n, fn, minp):
    return getattr(pd.DataFrame(a).rolling(n, min_periods=minp), fn)().values


P = {}
P['d0'] = RA
P['r2d'] = lv / shift(lv, 2) - 1
P['r3d'] = lv / shift(lv, 3) - 1
P['pre5'] = lv / shift(lv, 5) - 1
P['r20d'] = lv / shift(lv, 20) - 1
P['r6m'] = lv / shift(lv, 126) - 1
P['r3m'] = lv / shift(lv, 63) - 1
st1m = np.exp(roll(np.log1p(np.nan_to_num(RA)), 21, 'sum', 21)) - 1
st1m[~shift(started.astype(float), 21).astype(bool) if False else np.isnan(shift(np.where(started, 1.0, np.nan), 21))] = np.nan
n1m = nifty / np.r_[np.full(21, np.nan), nifty[:-21]] - 1
P['vs_nifty_1m'] = st1m - n1m[:, None]
n3 = nifty / np.r_[np.full(3, np.nan), nifty[:-3]] - 1
P['nifty_3d'] = np.repeat(n3[:, None], NS, 1)
cnt250 = roll(np.where(np.isfinite(lv), 1.0, 0.0), 250, 'sum', 1)
ma200 = roll(lv, 200, 'mean', 1); ma50 = roll(lv, 50, 'mean', 1)
P['vs_ma200'] = np.where(cnt250 > 200, lv / ma200 - 1, np.nan)
P['vs_ma50'] = np.where(cnt250 > 200, lv / ma50 - 1, np.nan)
cnt60 = roll(valid.astype(float), 60, 'sum', 1)
absr = np.abs(RA)
P['maxabs5'] = np.where(cnt60 >= 45, roll(absr, 5, 'max', 1), np.nan)
pp = np.cumprod(1 + np.nan_to_num(RA), axis=0)
P['dist_20h'] = np.where(cnt60 >= 45, pp / roll(pp, 20, 'max', 1) - 1, np.nan)
sd60 = roll(RA, 60, 'std', 2)  # pandas std ddof=1; 01_build uses np.nanstd ddof=0 -> rescale below
sd60 = sd60 * np.sqrt((cnt60 - 1) / np.maximum(cnt60, 1))
P['z20'] = np.where(cnt60 >= 45, P['r20d'] / (sd60 * np.sqrt(20)), np.nan)
P['vol60'] = np.where(cnt60 > 40, roll(RA, 60, 'std', 2) * np.sqrt(252), np.nan)
gap = (1 + RA) / (1 + IA) - 1
P['gap0'] = gap; P['intra0'] = IA
gcnt = roll(np.isfinite(gap).astype(float), 5, 'sum', 1)
P['gap5'] = np.where(gcnt >= 3, roll(np.nan_to_num(gap), 5, 'sum', 1), np.nan)
fwd = np.full_like(RA, np.nan)
z = np.nan_to_num(RA)
fwd[:-3] = z[1:-2] + z[2:-1] + z[3:]
fwd[~started] = np.nan

# ---- check against features_all at real cutoffs
col = {s: j for j, s in enumerate(syms)}
chk = []
Fi = F[F.symbol.isin(col)]
for f in ['d0', 'r2d', 'r3d', 'pre5', 'r20d', 'r6m', 'r3m', 'vs_nifty_1m', 'nifty_3d', 'vs_ma200', 'vs_ma50', 'maxabs5',
          'dist_20h', 'z20', 'vol60', 'gap0', 'intra0', 'gap5']:
    a = P[f][Fi.i_cut.values, [col[s] for s in Fi.symbol]]
    b = Fi[f].values
    ok = np.isfinite(a) & np.isfinite(b)
    chk.append({'feature': f, 'n_both': int(ok.sum()), 'n_feat': int(np.isfinite(b).sum()),
                'max_abs_diff': float(np.abs(a[ok] - b[ok]).max()), 'share_close': float((np.abs(a[ok] - b[ok]) < 1e-4).mean())})
C = pd.DataFrame(chk); C.to_csv(f'{G.HERE}/event_check.csv', index=False)
print(C.to_string())

# ---- placebo rows
E = E.sort_values(['symbol', 'i_cut'])
near = np.zeros((T, NS), bool)
for s, ird in zip(E.symbol, E.i_rd):
    if s in col:
        near[max(0, ird - 10):ird + 11, col[s]] = True
fo_span = np.zeros((T, NS), bool)
for s, g in E[E.in_fo == True].groupby('symbol'):
    if s in col:
        fo_span[g.i_cut.min():g.i_cut.max() + 1, col[s]] = True
t0 = int(np.searchsorted(days, '2021-03-01'))
t1 = int(E.i_p1.max())
mask = np.zeros((T, NS), bool)
mask[t0:t1 + 1] = True
mask &= fo_span & ~near & np.isfinite(fwd) & np.isfinite(P['vs_nifty_1m'])
ii, jj = np.nonzero(mask)
L = pd.DataFrame({'i': ii, 'symbol': np.array(syms)[jj], 'day': days[ii], 'fwd3': fwd[ii, jj]})
for f, a in P.items():
    L[f] = a[ii, jj]
# as-of results features
E['abs3'] = E.three_day.abs()
own = []
for s, g in E.groupby('symbol'):
    g = g.sort_values('i_cut')
    pre5_ev = F.set_index(['symbol', 'qn'])['pre5']
    p5 = np.array([pre5_ev.get((s, q), np.nan) for q in g.qn])
    rd = g.ret_rd.values
    for k in range(len(g)):
        own.append({'symbol': s, 'i_from': g.i_p1.values[k] + 1, 'n_done': k + 1,
                    'own_rd_asof': np.nanmean(rd[:k + 1]) if k + 1 >= 2 else np.nan,
                    'own_pre5_asof': np.nanmean(p5[:k + 1]) if k + 1 >= 2 else np.nan})
O = pd.DataFrame(own).sort_values('i_from')
L = L.sort_values('i')
L = pd.merge_asof(L, O, left_on='i', right_on='i_from', by='symbol', direction='backward')
L['pre5_vs_own'] = L.pre5 - L.own_pre5_asof
# season so far: latest quarter with a completed result by day i; mean three_day of that quarter's completed results
Fe = F.merge(E[['symbol', 'qn', 'i_p1']], on=['symbol', 'qn'])
ssf = np.full(T, np.nan)
for i in range(t0, t1 + 1):
    done = Fe[Fe.i_p1 <= i - 0]
    if not len(done):
        continue
    q = done.qn.max()
    x = done[done.qn == q].three_day
    ssf[i] = x.mean() if len(x) >= 5 else np.nan
L['season_so_far_3d'] = ssf[L.i.values]
L.to_pickle(f'{G.HERE}/placebo_panel.pkl')
print('placebo rows', len(L), 'with vs_nifty_1m < -5%:', int((L.vs_nifty_1m < -0.05).sum()),
      'avg fwd3 all %.3f%%, lag>5%% %.3f%%' % (100 * L.fwd3.mean(), 100 * L[L.vs_nifty_1m < -0.05].fwd3.mean()))
