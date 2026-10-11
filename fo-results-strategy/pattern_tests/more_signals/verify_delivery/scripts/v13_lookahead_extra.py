"""v13 - look-ahead checks (announcement timestamps vs decision sessions, publication timing of the delivery file,
rank universe) and extra A10 checks (Nifty-hedged, cutoff-day clustering, alternative rank universes).
usage: python3 -P v13_lookahead_extra.py <scratchpad> <out_dir>
"""
import sys
import numpy as np, pandas as pd

SP, OUT = sys.argv[1], sys.argv[2]
DATA = f'{SP}/sector_lab/data'
log = open(f'{OUT}/v13_lookahead_extra.log', 'w')
def P(*a):
    s = ' '.join(str(x) for x in a); print(s); log.write(s + '\n'); log.flush()

f = pd.read_csv(f'{OUT}/v11_feat.csv')
ses = pd.read_csv(f'{DATA}/sessions.csv'); DAYS = ses.day.tolist(); IDX = {d: i for i, d in enumerate(DAYS)}
ev = pd.read_csv(f'{DATA}/events.csv', usecols=['symbol', 'qn', 'results_date', 'results_time', 'timing', 'i_cut', 'i_rd', 'i_react', 'i_p1'])
m = f[['symbol', 'qn', 'i_cut', 'i_rd', 'i_react', 'i_p1']].merge(ev, on=['symbol', 'qn'], suffixes=('', '_ev'))
P(f'panel rows matched to events.csv: {len(m)} of {len(f)}')
for c in ['i_cut', 'i_rd', 'i_react', 'i_p1']:
    P(f'   {c} equal to events.csv: {int((m[c] == m[c + "_ev"]).sum())}')
m['cut_day'] = m.i_cut.map(lambda i: DAYS[i]); m['rd_day'] = m.i_rd.map(lambda i: DAYS[i])
m['rdate'] = pd.to_datetime(m.results_date)
P(f'results announced on/before the cutoff date (would be look-ahead for A): {int((m.rdate <= pd.to_datetime(m.cut_day)).sum())}')
P(f'results announced on the session after the cutoff (cutoff-day close still before it): {int((m.rdate == pd.to_datetime(m.i_cut.map(lambda i: DAYS[i + 1]))).sum())}')
P(f'i_rd - i_cut: {m.eval("i_rd - i_cut").value_counts().to_dict()}; i_react - i_rd by timing: '
  f'{m.groupby("timing").apply(lambda g: (g.i_react - g.i_rd).value_counts().to_dict()).to_dict()}')
P(f'announcement date vs result session: rd_day == results_date {int((pd.to_datetime(m.rd_day) == m.rdate).sum())}, '
  f'rd_day > results_date (non-trading-day announcement) {int((pd.to_datetime(m.rd_day) > m.rdate).sum())}, '
  f'rd_day < results_date {int((pd.to_datetime(m.rd_day) < m.rdate).sum())}')
# timing of results announced after close on the day before the cutoff+1 etc.
late = m[(m.timing == 'After close')]
P(f'after-close results: reaction day = next session after the announcement date: '
  f'{int((late.i_react == late.rd_day.map(IDX) + 1).sum())} of {len(late)}')
# Trade B: W_DQK_HI uses DQK at k (file published evening of k), entry close k+1: k+1 > k always
P('delivery data used: A features end at e = i_cut-1 (published evening of i_cut-1 < close i_cut); '
  'B DQK uses day k (published evening of k), entry close k+1')

# ----------------------------------------------------------------- A10 extras
R = pd.read_csv(f'{DATA}/returns.csv', index_col=0).to_numpy(float)
NC = pd.read_csv(f'{DATA}/index_close.csv', usecols=['day', 'Nifty 50']).set_index('day')['Nifty 50'].reindex(DAYS).to_numpy(float)
NR = np.r_[np.nan, NC[1:] / NC[:-1] - 1]
Y3 = f.three_day.to_numpy(float); QN = f.qn.to_numpy(int)
N3 = np.array([NR[a + 1:a + 4].sum() * 100 for a in f.i_cut])
A10 = (f.rank_DP60 > 80).to_numpy() & np.isfinite(Y3)
H = Y3 - N3
qmH = pd.Series(H).groupby(QN).transform('mean').to_numpy()
P(f'Nifty-hedged 3-day (stock - Nifty, sum convention): A10 n {A10.sum()} hedged gross {H[A10].mean():+.3f} net {H[A10].mean() - .17:+.3f}; '
  f'all results hedged gross {np.nanmean(H):+.3f}; A10 hedged excess quarter-matched {np.nanmean(H[A10] - qmH[A10]):+.3f}')
# beta-adjusted: rolling 120-session beta at the cutoff
SY = pd.read_csv(f'{DATA}/returns.csv', index_col=0, nrows=1).columns.tolist(); SJ = {s: j for j, s in enumerate(SY)}
j = f.symbol.map(SJ).to_numpy(int)
beta = np.full(len(f), np.nan)
for n_, (ic, jj) in enumerate(zip(f.i_cut, j)):
    x = NR[ic - 119:ic + 1]; y = R[ic - 119:ic + 1, jj]; ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() > 60: beta[n_] = np.cov(x[ok], y[ok])[0, 1] / np.var(x[ok], ddof=1)
BH = Y3 - beta * N3
qmB = pd.Series(BH).groupby(QN).transform('mean').to_numpy()
P(f'beta-hedged (120-session beta at the cutoff): A10 median beta {np.nanmedian(beta[A10]):.2f} vs others {np.nanmedian(beta[~A10]):.2f}; '
  f'A10 beta-hedged gross {np.nanmean(BH[A10]):+.3f} net {np.nanmean(BH[A10]) - .17:+.3f}; excess quarter-matched {np.nanmean(BH[A10] - qmB[A10]):+.3f}')
# cutoff-day clustering: many A10 trades share the same 3-day window
ex = Y3 - pd.Series(Y3).groupby(QN).transform('mean').to_numpy()
g = pd.Series(ex[A10]).groupby(f.i_cut.to_numpy()[A10]).mean()
t = g.mean() / (g.std(ddof=1) / np.sqrt(len(g)))
P(f'A10 excess clustered by cutoff session: {len(g)} distinct cutoff sessions for {A10.sum()} trades; mean of session means {g.mean():+.3f}, t {t:.2f}')
gs = pd.Series(ex[A10]).groupby(f.symbol.to_numpy()[A10]).mean()
P(f'A10 by symbol: {len(gs)} symbols; mean of symbol means {gs.mean():+.3f}; share of symbols with positive mean excess {np.mean(gs > 0):.2f}; '
  f'top-5 symbol contributions {gs.sort_values().tail(5).round(2).to_dict()}')
# alternative rank universes for A10 (point-in-time robustness)
M = np.load(f'{OUT}/v11_mats.npz'); DP60 = M['DP60']
UQ = {q: np.array(sorted(g.symbol.map(SJ))) for q, g in f.groupby('qn')}
def alt_rank(univ_fn):
    rk = np.full(len(f), np.nan)
    for n_, (e, jj, q) in enumerate(zip(f.e, j, QN)):
        u = univ_fn(q, e)
        v = DP60[e, u]; v = v[np.isfinite(v)]
        rk[n_] = 100 * (np.sum(v < DP60[e, jj]) + 0.5 * (np.sum(v == DP60[e, jj]) - 1) + 1) / len(v)
    return rk
allsym = np.arange(len(SY))
for lab, fn in [('previous quarter F&O list (known in advance)', lambda q, e: UQ[max(q - 1, 0)] if q > 0 else UQ[0]),
                ('all 213 symbols with delivery data', lambda q, e: allsym)]:
    rk = alt_rank(fn); mm = (rk > 80) & np.isfinite(Y3)
    ex_ = (Y3 - pd.Series(Y3).groupby(QN).transform('mean').to_numpy())[mm]
    P(f'A10 with rank universe = {lab}: n {mm.sum()} net {Y3[mm].mean() - .17:+.3f} excess {ex_.mean():+.3f} '
      f'h1 {ex_[QN[mm] <= 13].mean():+.3f} h2 {ex_[QN[mm] > 13].mean():+.3f}; same trades as A10 {int((mm & A10).sum())}')
# a fixed absolute threshold chosen from qn 0-13 only (point in time), applied to qn 14-21
thr = np.nanpercentile(f.DP60[QN <= 13], 80)
mm = (f.DP60.to_numpy() > thr) & np.isfinite(Y3) & (QN > 13)
ex_ = (Y3 - pd.Series(Y3).groupby(QN).transform('mean').to_numpy())[mm]
P(f'A10 out-of-sample with a fixed DP60 threshold from qn 0-13 ({thr:.1f}%): last 8 n {mm.sum()} net {Y3[mm].mean() - .17:+.3f} excess {ex_.mean():+.3f}')
