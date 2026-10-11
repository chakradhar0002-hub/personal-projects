#!/usr/bin/env python3
"""Verifier: recompute and stress A08 PRESS and A12 BIZ_UP (trade A) from the verifier's own features.
usage: python3 -P verify_A.py SP VDIR NEWSDIR
  SP = scratchpad root, VDIR = verify_news, NEWSDIR = more_signals/news (only its output CSVs are read, for the
  mismatch comparison; none of its code is imported)."""
import sys

import numpy as np
import pandas as pd

SP, V, NW = sys.argv[1:4]
D = f'{SP}/sector_lab/data'
LOG = open(f'{V}/verify_A.log', 'w')


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.write(s + '\n')


CA = 0.17
f = pd.read_csv(f'{V}/work/my_feat.csv')
out = pd.read_csv(f'{SP}/perf/features/outcomes.csv', usecols=['symbol', 'qn', 'three_day', 'vsN_net_H20',
                                                                  'tradable_B'])
pan = pd.read_csv(f'{SP}/perf/features/panel.csv', usecols=['symbol', 'qn', 'industry', 'mean_three_day_4_A',
                                                             'mean_drift_4_B', 'n_drift_4_B'])
f = f.merge(out, on=['symbol', 'qn']).merge(pan, on=['symbol', 'qn'])
ses = pd.read_csv(f'{D}/sessions.csv')
SD = pd.to_datetime(ses.day)
ret = pd.read_csv(f'{D}/returns.csv', index_col=0)
RC = {s: j for j, s in enumerate(ret.columns)}
R = ret.to_numpy(float)
nif = pd.read_csv(f'{D}/index_close.csv', index_col=0)['Nifty 50'].to_numpy(float)


def fwd(sym, i, h):
    j = RC[sym]
    r = R[i + 1:i + 1 + h, j]
    if len(r) < h or np.isnan(r).any():
        return np.nan
    return (np.prod(1 + r) - 1) * 100


# ---------------- outcome check: three_day = close i_cut -> close i_p1
f['td_mine'] = [fwd(s, ic, ip - ic) for s, ic, ip in zip(f.symbol, f.i_cut, f.i_p1)]
f['n3'] = f.i_p1 - f.i_cut
f['nifty3'] = (nif[f.i_p1.to_numpy(int)] / nif[f.i_cut.to_numpy(int)] - 1) * 100
dd = (f.td_mine - f.three_day).abs()
P(f'three_day recomputed from returns.csv: max |diff| {dd.max():.4f} (n {dd.notna().sum()}); window length sessions '
  f'{f.n3.value_counts().to_dict()}')
A = f[f.three_day.notna()].reset_index(drop=True)
P(f'A universe {len(A)}; mean three_day {A.three_day.mean():+.3f}')
lag = (A.in_fo_events == True) & (A.lag21 < -10) & (A.vol_ratio_5_60 >= 1.0)
P(f'lag rule {lag.sum()} trades, mean {A.three_day[lag].mean():+.3f}')
qm = A.groupby('qn').three_day.transform('mean')
A['exc'] = A.three_day - qm
A['exc_nifty'] = (A.three_day - A.nifty3) - (A.three_day - A.nifty3).groupby(A.qn).transform('mean')
dm = A.groupby('i_cut').three_day.transform('mean')
dn = A.groupby('i_cut').three_day.transform('size')
A['exc_date'] = np.where(dn > 1, (A.three_day - dm) * dn / (dn - 1), np.nan)  # vs other results with same entry
A['year'] = SD.iloc[A.i_cut.to_numpy(int)].dt.year.to_numpy()

# ---------------- mismatch vs the family's features
fr = pd.read_csv(f'{NW}/work/feat_results.csv', usecols=['symbol', 'qn', 'PR30', 'BIZ_RX', 'BIZ_N45', 'RDCHG'])
m = f.merge(fr, on=['symbol', 'qn'])
P(f'\nPR30 mine vs theirs: equal {np.mean(m.pr30 == m.PR30) * 100:.2f}%; IN mine {int((m.pr30 >= 1).sum())}, theirs '
  f'{int((m.PR30 >= 1).sum())}; flag disagreements {int(((m.pr30 >= 1) != (m.PR30 >= 1)).sum())}')
x = m[(m.pr30 >= 1) != (m.PR30 >= 1)]
if len(x):
    P(x[['symbol', 'qn', 'pr30', 'PR30']].to_string())
P(f'BIZ: mine n45>0 {int((m.biz_n45 > 0).sum())}, theirs {int((m.BIZ_N45 > 0).sum())}; '
  f'rx>0 mine {int((m.biz_rx45 > 0).sum())}, theirs {int((m.BIZ_RX > 0).sum())}; both rx>0 '
  f'{int(((m.biz_rx45 > 0) & (m.BIZ_RX > 0)).sum())}')
both = m.RDCHG.notna() & m.rdchg_ok
P(f'RDCHG mine vs theirs (both known {both.sum()}): equal {np.mean(m.rdchg[both] == m.RDCHG[both]) * 100:.2f}%; '
  f'EARLY flag disagreements {int(((m.rdchg[both] < -7) != (m.RDCHG[both] < -7)).sum())}; '
  f'known only mine {int((m.rdchg_ok & m.RDCHG.isna()).sum())}, only theirs {int((~m.rdchg_ok & m.RDCHG.notna()).sum())}')
tA = pd.read_csv(f'{NW}/trades_A.csv', usecols=['test', 'symbol', 'qn', 'three_day', 'pnl_net'])
t8 = tA[tA.test == 'A08']
mine8 = set(zip(A.symbol[A.pr30 >= 1], A.qn[A.pr30 >= 1]))
P(f'A08 trade list: theirs {len(t8)}, mine {len(mine8)}, common {len(mine8 & set(zip(t8.symbol, t8.qn)))}')


# ---------------- stats helpers
def perm_p(mask, col='three_day', B=20000, seed=5):
    y = A[col].to_numpy(float)
    q = A.qn.to_numpy()
    ok = np.isfinite(y)
    obs = y[mask & ok].mean()
    rng = np.random.default_rng(seed)
    ge = 0
    cnts = {qq: int((mask & ok & (q == qq)).sum()) for qq in np.unique(q)}
    pools = {qq: y[ok & (q == qq)] for qq in cnts}
    tot = sum(cnts.values())
    sims = np.zeros(B)
    for qq, c in cnts.items():
        if c == 0:
            continue
        pool = pools[qq]
        idx = np.argsort(rng.random((B, len(pool))), axis=1)[:, :c]
        sims += pool[idx].sum(1)
    sims /= tot
    return (1 + (sims >= obs - 1e-12).sum()) / (B + 1)


def stats(mask, name, sign=1):
    s = A[mask]
    p = sign * s.three_day
    e = sign * s.exc
    r = {'name': name, 'n': len(s), 'gross': p.mean(), 'net': p.mean() - CA, 'excess': e.mean()}
    pq = (p - CA).groupby(s.qn).mean()
    r['q+'] = f'{int((pq > 0).sum())}/{len(pq)}'
    h1, h2 = s.qn <= 13, s.qn >= 14
    r['h1 n/net/exc'] = f'{h1.sum()}, {p[h1].mean() - CA:+.2f}, {e[h1].mean():+.2f}'
    r['h2 n/net/exc'] = f'{h2.sum()}, {p[h2].mean() - CA:+.2f}, {e[h2].mean():+.2f}'
    o = np.argsort(-p.to_numpy())
    r['net-5'] = np.delete(p.to_numpy(), o[:5]).mean() - CA
    r['exc-5'] = np.delete(e.to_numpy(), o[:5]).mean()
    r['net-10'] = np.delete(p.to_numpy(), o[:10]).mean() - CA
    r['exc-10'] = np.delete(e.to_numpy(), o[:10]).mean()
    r['exc_vsNifty'] = sign * s.exc_nifty.mean()
    r['exc_sameday'] = sign * np.nanmean(s.exc_date)
    r['median'] = p.median()
    r['hit%'] = (p > 0).mean() * 100
    return r


def tab(rows):
    t = pd.DataFrame(rows)
    return t.to_string(index=False, float_format=lambda v: f'{v:+.3f}')


pr = (A.pr30 >= 1).to_numpy()
P('\n=== A08 PRESS recomputed from my features')
r0 = stats(pr, 'A08 PR30>=1')
r0['luck_p'] = perm_p(pr)
P(tab([r0, stats(~pr, 'complement PR30==0')]))
P(f'luck p vs-Nifty excess version: {perm_p(pr, "exc_nifty"):.4f}')

# ---------------- stress: LOQO, by year, nearby cutoffs
P('\n--- leave-one-quarter-out (excess, net)')
lo = []
for q in sorted(A.qn.unique()):
    mm = pr & (A.qn != q).to_numpy()
    lo.append((q, A.exc[mm].mean(), A.three_day[mm].mean() - CA))
lo = pd.DataFrame(lo, columns=['dropped_qn', 'excess', 'net'])
P(f'excess range {lo.excess.min():+.3f} .. {lo.excess.max():+.3f}; net range {lo.net.min():+.3f} .. {lo.net.max():+.3f}')
P('\n--- per quarter')
pq = A[pr].groupby('qn').agg(n=('exc', 'size'), net=('three_day', lambda v: v.mean() - CA), excess=('exc', 'mean'))
pq['compl_exc'] = A[~pr].groupby('qn').exc.mean()
pq['all_mean'] = A.groupby('qn').three_day.mean()
P(pq.round(2).to_string())
P('\n--- by calendar year of entry')
P(A[pr].groupby('year').agg(n=('exc', 'size'), net=('three_day', lambda v: v.mean() - CA),
                             excess=('exc', 'mean')).round(3).to_string())
P('\n--- nearby cut-offs / definitions')
rows = []
for w in (14, 21, 30, 45, 60):
    rows.append(stats((A[f'pr{w}'] >= 1).to_numpy(), f'PR in {w}d >= 1'))
rows.append(stats((A.pr30 >= 2).to_numpy(), 'PR30 >= 2'))
rows.append(stats((A.pr30 == 1).to_numpy(), 'PR30 == 1'))
rows.append(stats((A.pr30_incl_own >= 1).to_numpy(), 'PR30 incl own results days'))
rows.append(stats((A.pr30_1530 >= 1).to_numpy(), 'PR30 to 15:30'))
rows.append(stats((A.pr30_prevclose >= 1).to_numpy(), 'PR30 as of previous close'))
rows.append(stats((A.pr30 >= 1).to_numpy() & (A.pr_norm.fillna(0) > 0).to_numpy(), 'PR30>=1 & habitual issuer'))
rows.append(stats((A.pr30 == 0).to_numpy() & (A.pr_norm.fillna(0) > 0.33).to_numpy(), 'PR30==0 & PR norm>0.33 (quiet)'))
rows.append(stats((A.all30 >= A.all30.median()).to_numpy(), f'all announcements30 >= median {A.all30.median():.0f}'))
rows.append(stats((A.newsver30 >= 1).to_numpy(), 'News Verification in 30d'))
P(tab(rows))

# ---------------- confounders: industry, size proxy, market timing
P('\n--- by industry (A08 trades, top 12 industries by count)')
g = A[pr].groupby('industry').agg(n=('exc', 'size'), excess=('exc', 'mean'))
P(g.sort_values('n', ascending=False).head(12).round(2).to_string())
auto = A.industry.fillna('').str.contains('Automobile|Auto')
P(tab([stats(pr & ~auto.to_numpy(), 'A08 without Automobile industries'),
       stats(pr & auto.to_numpy(), 'A08 Automobile only')]))
top = A[pr].symbol.value_counts()
P(f'A08 symbols {len(top)}; top 10 {top.head(10).to_dict()}')
P(tab([stats(pr & ~A.symbol.isin(top.head(10).index).to_numpy(), 'A08 w/o top10 symbols'),
       stats(pr & ~A.symbol.isin(top.head(20).index).to_numpy(), 'A08 w/o top20 symbols')]))
# within-stock: stock fixed effect via demeaning the quarter excess
ws = A.groupby('symbol').filter(lambda g: (g.pr30 >= 1).any() and (g.pr30 == 0).any())
ws = ws.assign(dm=ws.exc - ws.groupby('symbol').exc.transform('mean'))
P(f'within-stock (stocks with both): n {len(ws)}, stocks {ws.symbol.nunique()}, PR quarters demeaned excess '
  f'{ws.dm[ws.pr30 >= 1].mean():+.3f}, no-PR {ws.dm[ws.pr30 == 0].mean():+.3f}')
# stock-level: symbols that ALWAYS have PR vs never
share = A.groupby('symbol').pr30.apply(lambda v: (v >= 1).mean())
A['pr_share'] = A.symbol.map(share)
P(A.groupby(pd.cut(A.pr_share, [-0.01, 0.0, 0.25, 0.5, 0.75, 0.99, 1.0])).agg(
    n=('exc', 'size'), exc=('exc', 'mean'), exc_PR=('exc', lambda v: v[A.loc[v.index, 'pr30'] >= 1].mean()),
    exc_noPR=('exc', lambda v: v[A.loc[v.index, 'pr30'] == 0].mean())).round(3).to_string())

# ---------------- overlap with existing rules, survivorship
first_fo = A.groupby('symbol').qn.min()
A['early_member'] = A.symbol.map(first_fo) <= 1
tr05 = pd.read_csv(__import__('os').environ.get('REPO_ROOT', '.') + '/results/past_performance/A_pre_results/'
                   'trades_TR05.csv', usecols=['symbol', 'qn'])
A['tr05'] = [k in set(zip(tr05.symbol, tr05.qn)) for k in zip(A.symbol, A.qn)]
P('\n--- overlap / survivorship')
P(tab([stats(pr & lag.to_numpy(), 'A08 & lag rule'), stats(~pr & lag.to_numpy(), 'not A08 & lag rule'),
       stats(pr & ~lag.to_numpy(), 'A08 outside lag rule'),
       stats(pr & A.tr05.to_numpy(), 'A08 & habitual risers TR05'),
       stats(pr & ~A.tr05.to_numpy(), 'A08 not TR05'),
       stats(pr & A.early_member.to_numpy(), 'A08, in F&O by qn<=1'),
       stats(pr & ~A.early_member.to_numpy(), 'A08, later joiners')]))
P(f'A08 share in TR05 {A.tr05[pr].mean() * 100:.1f}% vs all {A.tr05.mean() * 100:.1f}%')

# ---------------- my placebo: ordinary F&O stock-days, no result session within 10 before / 13 after
ev = pd.read_csv(f'{D}/events.csv', usecols=['symbol', 'qn', 'i_rd', 'i_react', 'in_fo'])
f30 = pd.read_csv(f'{V}/work/my_pr_biz_rows.csv')
f30 = f30[f30.is_pr & ~f30.own_rd]
f30['t'] = pd.to_datetime(f30.an_dt, format='%d-%b-%Y %H:%M:%S')
PRS = {s: np.sort(g.t.to_numpy('datetime64[ns]')) for s, g in f30.groupby('symbol')}
SDn = SD.to_numpy('datetime64[ns]')
keys = set(zip(A.symbol, A.qn))
rows = []
for s, g in ev.groupby('symbol'):
    if s not in RC:
        continue
    g = g.sort_values('i_rd')
    rs = np.unique(np.r_[g.i_rd.to_numpy(int), g.i_react.to_numpy(int)])
    for _, e in g.iterrows():
        if (s, e.qn) not in keys:
            continue
        prev = g.i_react[g.i_rd < e.i_rd]
        lo_i = int(prev.max()) + 10 if len(prev) else int(e.i_rd) - 70
        for i in range(lo_i, int(e.i_rd) - 13):
            if np.any(np.abs(rs - i) <= 10) or np.any((rs - i > 0) & (rs - i <= 13)):
                continue
            rows.append((s, e.qn, i))
pl = pd.DataFrame(rows, columns=['symbol', 'qn', 'i'])
pl['y'] = [fwd(s, i, 3) for s, i in zip(pl.symbol, pl.i)]
pl['n3'] = (nif[pl.i.to_numpy(int) + 3] / nif[pl.i.to_numpy(int)] - 1) * 100
pl = pl[pl.y.notna()].reset_index(drop=True)
T = SDn[pl.i.to_numpy(int)] + np.timedelta64(15, 'h')
c = np.zeros(len(pl), int)
for j, (s, t) in enumerate(zip(pl.symbol, T)):
    a = PRS.get(s)
    if a is not None:
        c[j] = np.searchsorted(a, t, 'left') - np.searchsorted(a, t - np.timedelta64(30, 'D'), 'left')
pl['pr30'] = c
pl['exc'] = pl.y - pl.groupby('qn').y.transform('mean')
P(f'\n--- my placebo: {len(pl)} ordinary days, mean 3-day {pl.y.mean():+.3f}; PR30>=1 share {np.mean(c >= 1) * 100:.1f}%')
# weight placebo by the trade's per-quarter counts
w = A[pr].qn.value_counts()
pe = pl[pl.pr30 >= 1].groupby('qn').exc.mean()
pexc = (pe.reindex(w.index) * w).sum() / w.sum()
P(f'placebo PR days excess (trade-quarter weighted) {pexc:+.3f}; results A08 excess {r0["excess"]:+.3f}; DiD '
  f'{r0["excess"] - pexc:+.3f}')
pl['exc_n'] = (pl.y - pl.n3) - (pl.y - pl.n3).groupby(pl.qn).transform('mean')
pen = pl[pl.pr30 >= 1].groupby('qn').exc_n.mean()
P(f'placebo vs-Nifty excess {(pen.reindex(w.index) * w).sum() / w.sum():+.3f}; results vs-Nifty excess '
  f'{r0["exc_vsNifty"]:+.3f}')
# within-stock placebo: same stock-quarters, ordinary days, PR vs not
pl['stock_q_pr'] = [(s, q) in set(zip(A.symbol[pr], A.qn[pr])) for s, q in zip(pl.symbol, pl.qn)]
P(f'placebo days of A08 stock-quarters: excess {pl.exc[pl.stock_q_pr].mean():+.3f} (n {pl.stock_q_pr.sum()}); '
  f'other stock-quarters {pl.exc[~pl.stock_q_pr].mean():+.3f}')
# bootstrap placebo p: draws of placebo PR days with trade per-quarter counts
rng = np.random.default_rng(9)
pools = {q: pl.exc[(pl.pr30 >= 1) & (pl.qn == q)].to_numpy() for q in w.index}
sims = np.zeros(5000)
for q, k in w.items():
    if len(pools[q]):
        sims += pools[q][rng.integers(0, len(pools[q]), (5000, k))].sum(1)
sims /= w.sum()
P(f'placebo p (P(placebo draw excess >= results excess)) {np.mean(sims >= r0["excess"]):.4f}')
# DiD within results vs within placebo: PR - noPR difference in both
res_diff = A.exc[pr].mean() - A.exc[~pr].mean()
pl_diff = pl.exc[pl.pr30 >= 1].mean() - pl.exc[pl.pr30 == 0].mean()
P(f'PR minus no-PR: results {res_diff:+.3f}, placebo {pl_diff:+.3f}, DiD {res_diff - pl_diff:+.3f}')
pl.to_csv(f'{V}/work/my_placeboA.csv.gz', index=False, compression='gzip')

# ---------------- A12 BIZ_UP
P('\n=== A12 BIZ_UP (business update in 45 days, sum of reactions > 0) with my broader BIZ definition')
fb = A.merge(fr[['symbol', 'qn', 'BIZ_RX', 'BIZ_N45']], on=['symbol', 'qn'], how='left')
mb_theirs = (fb.BIZ_RX > 0).to_numpy()
mb_mine = (A.biz_rx45 > 0).to_numpy()
mb_last = (A.biz_rxlast > 0).to_numpy()
mb_any = (A.biz_n45 > 0).to_numpy()
rows = [stats(mb_theirs, 'their BIZ_RX>0 flag'), stats(mb_mine, 'mine biz_rx45>0'),
        stats(mb_last, 'mine last update rx>0'), stats(mb_any, 'mine any business update'),
        stats(mb_any & ~mb_mine, 'mine update with rx<=0'), stats(mb_theirs & ~pr, 'their BIZ_UP & no PR30'),
        stats(mb_mine & ~pr, 'mine BIZ_UP & no PR30')]
for r_ in rows[:2]:
    pass
rows[0]['luck_p'] = perm_p(mb_theirs)
rows[1]['luck_p'] = perm_p(mb_mine)
P(tab(rows))
P(f'their BIZ_UP overlap with A08: {np.mean(pr[mb_theirs]) * 100:.0f}% of BIZ_UP trades have PR30>=1')
lo = [A.exc[mb_theirs & (A.qn != q).to_numpy()].mean() for q in sorted(A.qn.unique())]
P(f'their BIZ_UP LOQO excess range {min(lo):+.3f} .. {max(lo):+.3f}')
P(tab([stats(mb_theirs & lag.to_numpy(), 'BIZ_UP & lag'), stats(mb_theirs & A.early_member.to_numpy(), 'BIZ_UP early members'),
       stats(mb_theirs & ~A.early_member.to_numpy(), 'BIZ_UP later joiners')]))
P(A[mb_theirs].symbol.value_counts().head(10).to_dict())
A[['symbol', 'qn', 'i_cut', 'three_day', 'exc', 'exc_nifty', 'exc_date', 'pr30', 'biz_rx45']].to_csv(
    f'{V}/work/my_A.csv', index=False)
LOG.close()
