#!/usr/bin/env python3
"""POST-HOC (not pre-registered; cannot change a verdict) robustness of the one WATCH signal, A08 PRESS
(press release(s) in the 30 days before the cutoff, long the 3-day window).
usage: python3 posthoc_A08.py OUT SP     writes OUT/posthoc_A08.csv and OUT/posthoc_A08.log"""
import sqlite3
import warnings
import sys

import numpy as np
import pandas as pd

OUT, SP = sys.argv[1], sys.argv[2]
warnings.filterwarnings('ignore', message='This pattern is interpreted')
LOG = open(f'{OUT}/posthoc_A08.log', 'w')


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.write(s + '\n')


CA = 0.17
r = pd.read_csv(f'{OUT}/work/feat_results.csv')
o = pd.read_csv(f'{SP}/perf/features/outcomes.csv', usecols=['symbol', 'qn', 'three_day'])
A = r.merge(o, on=['symbol', 'qn'], validate='1:1')
A = A[A.three_day.notna()].reset_index(drop=True)
y = A.three_day.to_numpy(float)
qn = A.qn.to_numpy(int)
QM = pd.Series(y).groupby(qn).mean()
base = QM.reindex(qn).to_numpy()
PR = (A.PR30 >= 1).to_numpy()
rows = []


def add(name, m, note=''):
    m = np.asarray(m, bool)
    n = int(m.sum())
    if n == 0:
        rows.append(dict(check=name, n=0, note=note))
        return
    ex = (y[m] - base[m])
    q = qn[m]
    rows.append(dict(check=name, n=n, avg=y[m].mean(), net=y[m].mean() - CA, excess=ex.mean(),
                     excess_h1=ex[q <= 13].mean() if (q <= 13).any() else np.nan,
                     excess_h2=ex[q >= 14].mean() if (q >= 14).any() else np.nan, note=note))


add('A08 as tested', PR)
add('complement: no press release in 30 days', ~PR)
# dose
add('PR30 == 1', A.PR30 == 1)
add('PR30 2-3', A.PR30.between(2, 3))
add('PR30 >= 4', A.PR30 >= 4)
# concentration
cnt = A[PR].symbol.value_counts()
top10 = cnt.index[:10].tolist()
P('symbols with the most A08 trades:', cnt.head(10).to_dict())
add('A08 without its 10 most frequent symbols', PR & ~A.symbol.isin(top10).to_numpy(), ','.join(top10))
# leave-one-symbol-out range of the excess
ex_all = y - base
loo = []
for s in cnt.index:
    m = PR & (A.symbol != s).to_numpy()
    loo.append(ex_all[m].mean())
P(f'leave-one-symbol-out excess: min {min(loo):+.3f}, max {max(loo):+.3f} (all {ex_all[PR].mean():+.3f})')

# within-stock: demean three_day by the stock's leave-one-out mean over its other F&O results
g = A.groupby('symbol').three_day
s_sum, s_n = g.transform('sum').to_numpy(), g.transform('count').to_numpy()
loo_mean = np.where(s_n > 1, (s_sum - y) / np.maximum(s_n - 1, 1), np.nan)
wd = y - loo_mean - (base - np.nanmean(base))
mixed = A.groupby('symbol').PR30.transform(lambda v: ((v >= 1).any() and (v < 1).any())).to_numpy(bool)
mk = mixed & np.isfinite(loo_mean)
d_obs = np.nanmean((y - loo_mean)[mk & PR]) - np.nanmean((y - loo_mean)[mk & ~PR])
# within-stock permutation of the PR flag (keeps each stock's PR frequency), 20,000
rng = np.random.default_rng(5)
yy = (y - base)[mk]
ss = A.symbol.to_numpy()[mk]
ff = PR[mk]
groups = [np.flatnonzero(ss == s) for s in np.unique(ss)]
dperm = np.empty(20000)
for b in range(20000):
    f2 = ff.copy()
    for gi in groups:
        f2[gi] = ff[gi][rng.permutation(len(gi))]
    dperm[b] = yy[f2].mean() - yy[~f2].mean()
d_q = yy[ff].mean() - yy[~ff].mean()
p_w = (1 + (dperm >= d_q - 1e-12).sum()) / 20001
P(f'within-stock (stocks with and without PR quarters: {len(groups)} stocks, {mk.sum()} results): '
  f'PR minus no-PR, quarter-adjusted {d_q:+.3f} pp, one-sided within-stock permutation p {p_w:.4f}; '
  f'stock-demeaned (leave-one-out) difference {d_obs:+.3f}')
rows.append(dict(check='within-stock PR minus no-PR (quarter-adjusted)', n=int(mk.sum()), excess=d_q,
                 note=f'within-stock permutation p {p_w:.4f}, {len(groups)} stocks'))
for hh, hm in (('first14', qn[mk] <= 13), ('last8', qn[mk] >= 14)):
    rows.append(dict(check=f'within-stock PR minus no-PR, {hh}', n=int(hm.sum()),
                     excess=yy[ff & hm].mean() - yy[~ff & hm].mean()))

# PR type: business-update or order-win press releases vs other press releases
con = sqlite3.connect(f'file:{SP}/report/nse_events.db?mode=ro', uri=True)
an = pd.read_sql("SELECT symbol, an_dt, descr, txt FROM an WHERE descr IN ('Press Release', 'Press Release (Revised)')",
                 con).drop_duplicates()
an['t'] = pd.to_datetime(an.an_dt, format='%d-%b-%Y %H:%M:%S')
ses = pd.read_csv(f'{SP}/sector_lab/data/sessions.csv')
SDEC = pd.to_datetime(ses.day) + pd.Timedelta(hours=15)
A['TDEC'] = SDEC.reindex(A.i_cut).to_numpy()
tx = an.txt.fillna('').str.lower()
an['biz'] = tx.str.contains(r'(sales|business update|quarterly update|provisional|production|volumes?|deliver)')
an['res'] = tx.str.contains(r'(result|earnings|financial performance|quarter ended|q[1-4] ?fy)')
ev = pd.read_csv(f'{SP}/sector_lab/data/events.csv', usecols=['symbol', 'results_date'])
ev['rd'] = pd.to_datetime(ev.results_date)
RD = {s: set(g.rd) | set(g.rd + pd.Timedelta(days=1)) for s, g in ev.groupby('symbol')}
an = an[[t.normalize() not in RD.get(s, ()) for s, t in zip(an.symbol, an.t)]]
by = {s: g for s, g in an.groupby('symbol')}
n_biz, n_res, n_oth, last7 = (np.zeros(len(A), int) for _ in range(4))
for i, (s, T) in enumerate(zip(A.symbol, A.TDEC)):
    g = by.get(s)
    if g is None:
        continue
    w = g[(g.t >= T - pd.Timedelta(days=30)) & (g.t < T)]
    n_biz[i] = w.biz.sum()
    n_res[i] = (w.res & ~w.biz).sum()
    n_oth[i] = (~w.res & ~w.biz).sum()
    last7[i] = (w.t >= T - pd.Timedelta(days=7)).sum()
chk = (n_biz + n_res + n_oth) == A.PR30.to_numpy()
P(f'PR re-count matches PR30 on {chk.mean() * 100:.2f}% of results')
add('A08: only "other" press releases (no business-update / results wording)', PR & (n_biz == 0) & (n_res == 0))
add('A08: some business-update wording (sales / volumes / provisional ...)', PR & (n_biz > 0))
add('A08: some results / earnings wording (previews, dates)', PR & (n_res > 0))
add('A08: a press release in the last 7 days before the cutoff', PR & (last7 > 0))
add('A08: press releases only 8-30 days before', PR & (last7 == 0))
# habitual issuers: stock's press releases in the 365 days before the 30-day window (per 30 days)
hab = np.full(len(A), np.nan)
for i, (s, T) in enumerate(zip(A.symbol, A.TDEC)):
    g = by.get(s)
    w0 = max(T - pd.Timedelta(days=395), pd.Timestamp('2021-03-01'))
    days_ = (T - pd.Timedelta(days=30) - w0).days
    if days_ >= 90:
        hab[i] = (0 if g is None else ((g.t >= w0) & (g.t < T - pd.Timedelta(days=30))).sum()) / days_ * 30
A['PR_HAB'] = hab
med = np.nanmedian(hab)
add(f'A08 in habitual issuers (PR norm >= median {med:.2f}/30d)', PR & (hab >= med))
add('A08 in rare issuers (PR norm < median)', PR & (hab < med))
add('no PR, habitual issuers', ~PR & (hab >= med))
add('no PR, rare issuers', ~PR & (hab < med))

# stock-quarter placebo: ordinary days before the same result carry the result's PR30 flag
pl = pd.read_csv(f'{OUT}/work/feat_placeboA.csv.gz', usecols=['symbol', 'i', 'qn_next', 'PR30'])
plo = pd.read_csv(f'{SP}/ta/build/placebo_ta.csv.gz', usecols=['symbol', 'i', 'in_fo', 'qn_next', 'three_day'])
plo = plo[(plo.in_fo == True) & plo.qn_next.notna()][['symbol', 'i', 'three_day']]
pl = pl.merge(plo, on=['symbol', 'i'], validate='1:1')
pl = pl[pl.three_day.notna()]
flag = A.set_index(['symbol', 'qn']).PR30.ge(1)
pl['res_PR'] = flag.reindex(list(zip(pl.symbol, pl.qn_next.astype(int)))).to_numpy()
pqm = pl.groupby('qn_next').three_day.transform('mean')
pl['ex'] = pl.three_day - pqm
sq = pl[pl.res_PR == True]
rows.append(dict(check='stock-quarter placebo: ordinary days of A08 stock-quarters', n=len(sq), excess=sq.ex.mean(),
                 note='ordinary 3-day returns before the same result, quarter-adjusted'))
rows.append(dict(check='placebo: ordinary days with a press release in their own 30 days', n=int((pl.PR30 >= 1).sum()),
                 excess=pl.ex[pl.PR30 >= 1].mean()))
R = pd.DataFrame(rows)
R.to_csv(f'{OUT}/posthoc_A08.csv', index=False, float_format='%.4f')
pd.set_option('display.width', 250)
P(R.round(3).to_string(index=False))
# per quarter
pq = pd.DataFrame({'qn': qn[PR], 'pnl': y[PR] - CA, 'ex': (y - base)[PR]}).groupby('qn').agg(
    n=('pnl', 'size'), net=('pnl', 'mean'), excess=('ex', 'mean'))
pq.insert(0, 'results_for', A.groupby('qn').results_for.first().reindex(pq.index))
pq.to_csv(f'{OUT}/posthoc_A08_per_quarter.csv', float_format='%.4f')
P(pq.round(2).to_string())
LOG.close()
