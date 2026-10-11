#!/usr/bin/env python3
"""Verifier v2 - recompute and stress A08 PRESS and A12 BIZ_UP from own features (work_v2/feat_results.csv).
usage: python3 v2_stats_A.py SCRATCH WORKDIR STUDY_DIR
STUDY_DIR is read only for the study's 27 luck p values (to redo Holm with my own A08 p) - no study code is imported."""
import sys
import numpy as np
import pandas as pd

SC, W, STUDY = sys.argv[1:4]
COST = 0.17
f = pd.read_csv(f'{W}/feat_results.csv')
ses = pd.read_csv(f'{SC}/sector_lab/data/sessions.csv')
sday = pd.to_datetime(ses.day).values
A = f[f.three_day.notna()].copy()
A['y'] = A.three_day
A['qmean'] = A.groupby('qn').y.transform('mean')
A['exc'] = A.y - A.qmean
A['cutday'] = pd.to_datetime(sday[A.i_cut.values])
A['year'] = A.cutday.dt.year
A['dmean'] = A.groupby('i_cut').y.transform('mean')
A['dn'] = A.groupby('i_cut').y.transform('size')
first_q = A.groupby('symbol').qn.transform('min')
A['early_member'] = first_q <= 1
A['lag'] = (A.in_fo_events == True) & (A.lag21 < -10) & (A.vol_ratio_5_60 >= 1.0)
A['auto'] = A.industry.fillna('').str.contains('Automobile')
print(f'A universe {len(A)}, mean three_day {A.y.mean():+.3f}; lag rule {A.lag.sum()} trades {A[A.lag].y.mean():+.3f}')
rng = np.random.default_rng(20261012)

# within-quarter permutation machinery
qs = sorted(A.qn.unique())
qy = {q: A.loc[A.qn == q, 'y'].values for q in qs}


def luck_p(mask, sign=1, B=20000):
    m = mask.values
    obs = (sign * A.y.values[m]).mean()
    tot = np.zeros(B); n = m.sum()
    for q in qs:
        k = int((m & (A.qn.values == q)).sum())
        if k == 0:
            continue
        v = sign * qy[q]
        # random k-subsets via argsort of random keys
        keys = rng.random((B, len(v)))
        idx = np.argpartition(keys, k - 1, axis=1)[:, :k]
        tot += v[idx].sum(1)
    perm = tot / n
    return (1 + (perm >= obs - 1e-12).sum()) / (1 + B)


def summarize(name, mask, sign=1, with_p=False):
    d = A[mask].copy()
    d['p'] = sign * d.y
    d['e'] = sign * d.y - sign * d.qmean
    o = {'name': name, 'n': len(d)}
    if len(d) == 0:
        return o
    o['gross'] = d.p.mean(); o['net'] = d.p.mean() - COST; o['excess'] = d.e.mean()
    pq = d.groupby('qn').p.mean() - COST
    o['q+'] = f'{(pq > 0).sum()}/{len(pq)}'
    h1, h2 = d[d.qn <= 13], d[d.qn >= 14]
    o['h1'] = f'{len(h1)}, {h1.p.mean() - COST:+.2f}, {h1.e.mean():+.2f}'
    o['h2'] = f'{len(h2)}, {h2.p.mean() - COST:+.2f}, {h2.e.mean():+.2f}'
    s = d.sort_values('p', ascending=False)
    o['net-5'] = s.p.iloc[5:].mean() - COST; o['exc-5'] = s.e.iloc[5:].mean()
    o['net-10'] = s.p.iloc[10:].mean() - COST; o['exc-10'] = s.e.iloc[10:].mean()
    # same-cutoff-day control: trade minus mean of the other results with the same cutoff session
    oth = (d.dmean * d.dn - d.y) / (d.dn - 1)
    o['exc_sameday'] = (sign * (d.y - oth)).replace([np.inf, -np.inf], np.nan).mean()
    o['median'] = d.p.median(); o['hit%'] = (d.p > 0).mean() * 100
    if with_p:
        o['luck_p'] = luck_p(mask, sign)
    return o


pd.set_option('display.width', 260); pd.set_option('display.max_columns', 40)
fmt = lambda df: df.to_string(index=False, float_format=lambda x: f'{x:+.3f}')

PR = A.PR30 >= 1
BIZUP = A.BIZ_RX > 0
print('\n=== RECOMPUTED (own features) vs study')
t = pd.DataFrame([summarize('A08 PR30>=1 (long)', PR, 1, True), summarize('complement PR30==0', ~PR),
                  summarize('A12 BIZ_RX>0 (long)', BIZUP, 1, True), summarize('A13 BIZ_RX<0 (short)', A.BIZ_RX < 0, -1, True),
                  summarize('any BIZ item in 45d, long (post hoc)', A.BIZ45 > 0)])
print(fmt(t))
print('study: A08 n 1023 gross +0.42 net +0.25 excess +0.36 q+ 15/22 h1 612,+0.29,+0.34 h2 411,+0.20,+0.40 w/o5 +0.17 luck 0.0043')
print('study: A12 n 170 gross +0.65 net +0.48 excess +0.60 q+ 14/22 h1 76,+0.80,+0.82 h2 94,+0.22,+0.42 w/o5 +0.05 luck 0.0575')

# my trade list vs study trade list
ta = pd.read_csv(f'{STUDY}/trades_A.csv')
for test, mask in [('A08', PR), ('A12', BIZUP)]:
    th = set(zip(ta[ta.test == test].symbol, ta[ta.test == test].qn)); mi = set(zip(A[mask].symbol, A[mask].qn))
    print(f'{test} trade list: study {len(th)}, mine {len(mi)}, common {len(th & mi)}')

# Holm with my p for A08
tests = pd.read_csv(f'{STUDY}/tests.csv')
p = tests.set_index('test').luck_p.copy()
myp = t.set_index('name').loc['A08 PR30>=1 (long)', 'luck_p']
p['A08'] = myp
ps = p.sort_values(); m = len(ps)
holm = np.maximum.accumulate(np.minimum(1, ps.values * (m - np.arange(m))))
print(f'\nHolm (27 tests, my A08 luck p {myp:.4f}): A08 Holm p {dict(zip(ps.index, holm))["A08"]:.3f}')

# cluster bootstraps of the A08 excess (one-sided P(<=0))
def clus_boot(d, col, key, B=10000):
    g = d.groupby(key)[col].agg(['sum', 'size'])
    s, n = g['sum'].values, g['size'].values
    idx = rng.integers(0, len(g), (B, len(g)))
    bs = s[idx].sum(1) / n[idx].sum(1)
    return np.percentile(bs, [5, 95]), (bs <= 0).mean()
d = A[PR]
for key in ['symbol', 'i_cut', 'qn']:
    ci, pz = clus_boot(d, 'exc', key)
    print(f'A08 excess cluster bootstrap by {key:6s}: 90% CI {ci[0]:+.3f} .. {ci[1]:+.3f}, P(<=0) {pz:.4f}')
# date-demeaned version: excess vs same-cutoff-day others
d2 = d.copy(); d2['sd'] = d2.y - (d2.dmean * d2.dn - d2.y) / (d2.dn - 1)
d2 = d2[np.isfinite(d2.sd)]
ci, pz = clus_boot(d2, 'sd', 'i_cut')
print(f'A08 same-day excess clustered by date: mean {d2.sd.mean():+.3f}, 90% CI {ci[0]:+.3f} .. {ci[1]:+.3f}, P(<=0) {pz:.4f}  (n {len(d2)})')
# regression with stock fixed effects: y on PR within stock, quarter-demeaned
A['yd'] = A.exc - A.groupby('symbol').exc.transform('mean')
A['prd'] = PR.astype(float) - PR.astype(float).groupby(A.symbol).transform('mean')
beta = (A.yd * A.prd).sum() / (A.prd ** 2).sum()
# symbol-cluster bootstrap of beta
syms = A.symbol.unique(); gi = {s: np.where(A.symbol.values == s)[0] for s in syms}
bb = []
for _ in range(3000):
    ss = rng.choice(syms, len(syms))
    ii = np.concatenate([gi[s] for s in ss])
    bb.append((A.yd.values[ii] * A.prd.values[ii]).sum() / (A.prd.values[ii] ** 2).sum())
bb = np.array(bb)
print(f'within-stock PR effect (stock FE, quarter-demeaned): {beta:+.3f} pp, symbol-cluster 90% CI {np.percentile(bb, 5):+.3f} .. {np.percentile(bb, 95):+.3f}, P(<=0) {(bb <= 0).mean():.4f}')
for h, mk in [('first14', A.qn <= 13), ('last8', A.qn >= 14)]:
    s_ = A[mk]; yd = s_.exc - s_.groupby('symbol').exc.transform('mean'); pr = (s_.PR30 >= 1).astype(float)
    prd = pr - pr.groupby(s_.symbol).transform('mean')
    print(f'   within-stock {h}: {(yd * prd).sum() / (prd ** 2).sum():+.3f}')

# STRESS
print('\n=== A08 STRESS')
rows = []
for q in qs:
    mk = PR & (A.qn != q)
    rows.append((q, A[mk].exc.mean(), A[mk].y.mean() - COST))
lo = pd.DataFrame(rows, columns=['drop_qn', 'exc', 'net'])
print(f'leave-one-quarter-out: excess {lo.exc.min():+.3f} .. {lo.exc.max():+.3f}; net {lo.net.min():+.3f} .. {lo.net.max():+.3f}')
pq = A[PR].groupby('qn').agg(n=('y', 'size'), net=('y', lambda s: s.mean() - COST), exc=('exc', 'mean'))
pq['compl_exc'] = A[~PR].groupby('qn').exc.mean()
print('per quarter (net, excess):'); print(pq.round(2).T.to_string())
print('by calendar year of entry:')
print(A[PR].groupby('year').agg(n=('y', 'size'), net=('y', lambda s: s.mean() - COST), exc=('exc', 'mean')).round(3).T.to_string())
var = [summarize(f'PR in {w}d >= 1', A[f'PR{w}'] >= 1) for w in (7, 14, 21, 30, 45, 60, 90)]
var += [summarize('PR30 == 1', A.PR30 == 1), summarize('PR30 >= 2', A.PR30 >= 2), summarize('PR30 >= 3', A.PR30 >= 3),
        summarize('PR30 to 15:30', A.PR30_1530 >= 1), summarize('PR30 as of previous close', A.PR30_prev >= 1),
        summarize('PR only 8-30d back (PR7==0)', (A.PR30 >= 1) & (A.PR7 == 0)), summarize('PR in last 7d', A.PR7 >= 1),
        summarize('PR30>=1 & PR above own norm', (A.PR30 >= 1) & (A.PR30 > A.PRnorm)),
        summarize('PR30>=1 & at/below own norm', (A.PR30 >= 1) & (A.PR30 <= A.PRnorm)),
        summarize('PR30==0 & habitual issuer (norm>=0.5)', (A.PR30 == 0) & (A.PRnorm >= 0.5)),
        summarize('PR30==0 & never/rare issuer (norm<0.5)', (A.PR30 == 0) & (A.PRnorm < 0.5))]
print('nearby cut-offs / definitions:'); print(fmt(pd.DataFrame(var)))
ov = [summarize('A08 & lag rule', PR & A.lag), summarize('lag rule, no PR', ~PR & A.lag),
      summarize('A08 without lag-rule trades', PR & ~A.lag),
      summarize('A08 & member by qn1', PR & A.early_member), summarize('A08 & later joiner', PR & ~A.early_member),
      summarize('no-PR & member by qn1', ~PR & A.early_member), summarize('no-PR & later joiner', ~PR & ~A.early_member),
      summarize('A08 non-auto', PR & ~A.auto), summarize('A08 auto', PR & A.auto), summarize('non-auto no-PR', ~PR & ~A.auto),
      summarize('A08 & RSI>50 at cutoff', PR & (A.cut_rsi14 > 50)), summarize('A08 & RSI<=50', PR & (A.cut_rsi14 <= 50))]
print('overlap / survivorship / industry:'); print(fmt(pd.DataFrame(ov)))
cs = A[PR].groupby('symbol').exc.agg(['size', 'sum', 'mean']).sort_values('sum', ascending=False)
print(f'A08 excess sum {cs["sum"].sum():+.1f} over {len(cs)} symbols; top 5 contribute {cs["sum"].head(5).sum():+.1f}, '
      f'top 10 {cs["sum"].head(10).sum():+.1f}; symbols with positive sum {(cs["sum"] > 0).sum()}')
print(cs.head(8).round(2).to_string())
for k in (5, 10):
    top = cs.index[:k]
    print(f'A08 without its top-{k} symbols: {summarize("x", PR & ~A.symbol.isin(top))["excess"]:+.3f} excess, net {summarize("x", PR & ~A.symbol.isin(top))["net"]:+.3f}')

# PLACEBO on my own ordinary days
pl = pd.read_csv(f'{W}/feat_placebo.csv.gz')
pl['PRf'] = pl.PR30 >= 1
pl['qmean'] = pl.groupby('qn_next').fwd3.transform('mean')
pl['exc'] = pl.fwd3 - pl.qmean
wq = A[PR].groupby('qn').size()
pe = pl[pl.PRf].groupby('qn_next').exc.mean().reindex(wq.index)
pl_exc = (pe * wq).sum() / wq[pe.notna()].sum()
res_exc = A[PR].exc.mean()
# placebo p: draw per-quarter counts of placebo PR days, mean excess >= results excess
B = 10000; tot = np.zeros(B)
for q, k in wq.items():
    v = pl.loc[pl.PRf & (pl.qn_next == q), 'exc'].values
    if len(v) == 0:
        continue
    tot += v[rng.integers(0, len(v), (B, k))].sum(1)
pp = (tot / wq.sum() >= res_exc).mean()
print(f'\nPLACEBO (own ordinary days: {len(pl)} days, {pl.PRf.sum()} with PR30>=1): placebo excess {pl_exc:+.3f}; '
      f'results excess {res_exc:+.3f}; DiD {res_exc - pl_exc:+.3f}; placebo p {pp:.4f}')
# same-stock-quarter placebo: ordinary days before the same result (qn_next) carry the result's PR flag
m = pl.merge(A[['symbol', 'qn', 'PR30']].rename(columns={'qn': 'qn_next', 'PR30': 'PRres'}), on=['symbol', 'qn_next'])
sq = m[m.PRres >= 1].groupby('qn_next').exc.mean().reindex(wq.index)
print(f'stock-quarter placebo (ordinary days of PR results\' stock-quarters): excess {(sq * wq).sum() / wq[sq.notna()].sum():+.3f}')
# placebo by half
for h, mk in [('first14', pl.qn_next <= 13), ('last8', pl.qn_next >= 14)]:
    print(f'  placebo PR-day excess {h}: {pl[mk & pl.PRf].exc.mean():+.3f}')

# empirical-Bayes shrink of the A08 excess using the 17 A tests (study numbers) + my SE
ta_ = tests[tests.trade == 'A'].copy()
from scipy.stats import norm
z = pd.Series(norm.isf(ta_.luck_p.clip(1e-6, 1 - 1e-6)), index=ta_.index)
se = (ta_.excess / z).abs().where(z.abs() > 0.3)
se = se.fillna(ta_.excess.std())
tau2 = max(0.0, np.var(ta_.excess, ddof=1) - np.mean(se ** 2))
a08se = float(se[ta_.test == 'A08'].iloc[0])
shr = tau2 / (tau2 + a08se ** 2)
shr_txt = None
print(f'\nEB shrinkage over the 17 A tests: tau^2 {tau2:.4f}, A08 SE {a08se:.3f} -> shrink factor {shr:.2f}; '
      f'shrunk excess {res_exc * shr:+.3f}')

# post hoc: business-update overlap, null for "drop the top-k contributing symbols"
print('\n=== POST HOC')
extra = [summarize('A08 & no BIZ item in 45d', PR & (A.BIZ45 == 0)), summarize('A08 & BIZ item', PR & (A.BIZ45 > 0)),
         summarize('A08 non-auto & no BIZ', PR & ~A.auto & (A.BIZ45 == 0)),
         summarize('BIZ item, no PR', ~PR & (A.BIZ45 > 0))]
print(fmt(pd.DataFrame(extra)))
def drop_topk_excess(mask, k):
    d = A[mask]; cs = d.groupby('symbol').exc.sum().sort_values(ascending=False)
    return d[~d.symbol.isin(cs.index[:k])].exc.mean()
null5, null10 = [], []
qidx = {q: np.where(A.qn.values == q)[0] for q in qs}
nq = A[PR].groupby('qn').size()
for b in range(400):
    m = np.zeros(len(A), bool)
    for q, k in nq.items():
        m[rng.choice(qidx[q], k, replace=False)] = True
    mm = pd.Series(m, index=A.index)
    null5.append(drop_topk_excess(mm, 5)); null10.append(drop_topk_excess(mm, 10))
print(f'null (random same-size within-quarter picks): excess after dropping top-5 symbols mean {np.mean(null5):+.3f} '
      f'(95th pct {np.percentile(null5, 95):+.3f}); top-10 mean {np.mean(null10):+.3f} (95th {np.percentile(null10, 95):+.3f})')
print(f'A08 actual: top-5 dropped {drop_topk_excess(PR, 5):+.3f}, top-10 dropped {drop_topk_excess(PR, 10):+.3f}')
from scipy.stats import binomtest
cs = A[PR].groupby('symbol').exc.mean()
print(f'symbols with positive mean excess {(cs > 0).sum()} of {len(cs)}; sign-test p {binomtest(int((cs > 0).sum()), len(cs), 0.5, alternative="greater").pvalue:.3f}')
