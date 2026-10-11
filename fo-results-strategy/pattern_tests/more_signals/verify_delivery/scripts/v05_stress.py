#!/usr/bin/env python3
"""Verifier stress tests for the delivery-family candidates (A10, A06, RA1, W_DQK_HI, WR_DQK_HI), own code.
usage: python3 -P v05_stress.py SCRATCH OUTDIR"""
import sys

import numpy as np
import pandas as pd

SP, OUT = sys.argv[1], sys.argv[2]
DATA = f'{SP}/sector_lab/data'
LOG = open(f'{OUT}/v05_stress.log', 'w')
pd.set_option('display.width', 250)


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.write(s + '\n')


ses = pd.read_csv(f'{DATA}/sessions.csv')
days = ses.day.to_numpy()
T = len(days)
ret = pd.read_csv(f'{DATA}/returns.csv', index_col=0)
SY = ret.columns.tolist()
SJ = {s: j for j, s in enumerate(SY)}
S = len(SY)
R = ret.to_numpy(float) * 100                          # % daily
NC = pd.read_csv(f'{DATA}/index_close.csv', usecols=['day', 'Nifty 50']).set_index('day')['Nifty 50'].reindex(days).to_numpy(float)
NR = np.r_[np.nan, (NC[1:] / NC[:-1] - 1) * 100]
Mz = np.load(f'{OUT}/own_mats.npz')
DP, DP60, DQR, DQL, DPL, DQA = Mz['DP'], Mz['DP60'], Mz['DQR'], Mz['DQL'], Mz['DPL'], Mz['DQA']
f = pd.read_csv(f'{OUT}/own_feat.csv')
pan = pd.read_csv(f'{SP}/perf/features/panel.csv', usecols=['symbol', 'qn', 'cutoff', 'industry', 'sector_index',
                                                              'mean_drift_4_B'])
f = f.merge(pan[['symbol', 'qn', 'cutoff', 'sector_index']], on=['symbol', 'qn'])
QN = f.qn.to_numpy(int)
H1 = QN <= 13
j = f.symbol.map(SJ).to_numpy(int)
ic = f.i_cut.to_numpy(int)
e = ic - 1
y3 = f.three_day.to_numpy(float)
qmean = pd.Series(y3).groupby(QN).transform('mean').to_numpy()
f['year'] = f.cutoff.str[:4].astype(int)
U = {q: g.symbol.map(SJ).to_numpy(int) for q, g in f.groupby('qn')}
first_q = f.groupby('symbol').qn.min()
early = f.symbol.map(first_q).to_numpy() <= 1                     # in F&O by qn 1
lag_rule = (f.in_fo_events == True).to_numpy() & (f.lag21.to_numpy() < -10) & (f.vol_ratio_5_60.to_numpy() >= 1.0)
Wm = f.XN.to_numpy() > 4
WRm = Wm & (f.cut_rsi14.to_numpy() > 50)
btr = pd.read_csv(f'{SP}/perf/B_post_results/trades.csv')
hab = set(zip(btr[btr.test == 'S1_DRIFT4_Q5'].symbol, btr[btr.test == 'S1_DRIFT4_Q5'].qn))
HAB = np.array([(s, q) in hab for s, q in zip(f.symbol, f.qn)])
rng = np.random.default_rng(5)

# -------- same-window market controls for trade A
CRs = np.vstack([np.zeros((1, S)), np.cumsum(np.nan_to_num(R), 0)])     # cumulative sum of daily % returns
CNT = np.vstack([np.zeros((1, S)), np.cumsum(np.isfinite(R), 0)])
ip1 = f.i_p1.to_numpy(int)
ew = np.full(len(f), np.nan)
for n_, (q, a, b) in enumerate(zip(QN, ic, ip1)):
    js = U[q]
    s_ = CRs[b + 1, js] - CRs[a + 1, js]
    ok = (CNT[b + 1, js] - CNT[a + 1, js]) == (b - a)
    ew[n_] = s_[ok].mean()
f['ew3'] = ew                                                             # equal-weight F&O universe, same 3 sessions
CN = np.r_[0, np.cumsum(np.nan_to_num(NR))]
f['n3'] = CN[ip1 + 1] - CN[ic + 1]
# 250-session beta and 60-session volatility before the cutoff
beta = np.full(len(f), np.nan)
vol60 = np.full(len(f), np.nan)
for n_, (a, jj) in enumerate(zip(ic, j)):
    x = NR[a - 249:a + 1]
    yv = R[a - 249:a + 1, jj]
    ok = np.isfinite(x) & np.isfinite(yv)
    if ok.sum() > 150:
        beta[n_] = np.cov(x[ok], yv[ok])[0, 1] / np.var(x[ok], ddof=1)
    v = R[a - 59:a + 1, jj]
    vol60[n_] = np.nanstd(v)
f['beta'] = beta
f['vol60'] = vol60
f['rank_vol60'] = f.groupby('qn').vol60.rank(pct=True) * 100


def stats_A(mask, y=None, base=None, cost=0.17):
    y = y3 if y is None else y
    base = qmean if base is None else base
    m = mask & np.isfinite(y) & np.isfinite(base)
    ex = y[m] - base[m]
    net = y[m] - cost
    srt = np.argsort(-y[m])
    return dict(n=int(m.sum()), net=net.mean(), ex=ex.mean(), ex_h1=ex[H1[m]].mean(), ex_h2=ex[~H1[m]].mean(),
                net_wo5=np.delete(net, srt[:5]).mean(), ex_wo5=np.delete(ex, srt[:5]).mean(),
                net_wo10=np.delete(net, srt[:10]).mean(), ex_wo10=np.delete(ex, srt[:10]).mean())


def fmt(d):
    return ' '.join(f'{k} {v:+.3f}' if isinstance(v, float) else f'{k} {v}' for k, v in d.items())


def loqo(mask, y=None, base=None):
    y = y3 if y is None else y
    base = qmean if base is None else base
    out = []
    for q in range(22):
        m = mask & (QN != q) & np.isfinite(y) & np.isfinite(base)
        out.append((y[m] - base[m]).mean())
    return np.min(out), np.max(out), int(np.argmin(out)), int(np.argmax(out))


def by_year(mask, y=None, base=None):
    y = y3 if y is None else y
    base = qmean if base is None else base
    m = mask & np.isfinite(y)
    g = pd.DataFrame({'yr': f.year[m], 'ex': y[m] - base[m]}).groupby('yr').ex.agg(['size', 'mean'])
    return ', '.join(f'{yr}: {int(r_["size"])} {r_["mean"]:+.2f}' for yr, r_ in g.iterrows())


def cluster_boot(mask, y=None, base=None, B=5000):
    """symbol-cluster bootstrap of the mean excess (resample symbols with replacement)"""
    y = y3 if y is None else y
    base = qmean if base is None else base
    m = mask & np.isfinite(y)
    d = pd.DataFrame({'s': f.symbol[m], 'ex': y[m] - base[m]})
    g = d.groupby('s').ex.agg(['sum', 'size'])
    sm, sz = g['sum'].to_numpy(), g['size'].to_numpy()
    idx = rng.integers(0, len(g), (B, len(g)))
    bm = sm[idx].sum(1) / sz[idx].sum(1)
    return len(g), float(np.mean(bm <= 0)), np.percentile(bm, [5, 95])


A10 = (f.rank_DP60 > 80).to_numpy()
A06 = (f.rank_DPL > 80).to_numpy()
RA1 = (f.in_fo_events == True).to_numpy() & (f.lag21.to_numpy() < -10) & (f.DQR.to_numpy() >= 1.0)

P('=' * 100)
P('A10  (60-day delivery % level, top quintile of the quarter, long the 3-day window)')
P('=' * 100)
P('base (quarter-matched excess):', fmt(stats_A(A10)))
P('LOQO excess min/max (dropped quarter):', loqo(A10))
P('by calendar year (n, excess):', by_year(A10))
nsym, pneg, ci = cluster_boot(A10)
P(f'symbol-cluster bootstrap: {nsym} distinct symbols, P(mean excess <= 0) = {pneg:.3f}, 90% CI {ci.round(3)}')
vc = f[A10].symbol.value_counts()
P('most frequent symbols:', vc.head(12).to_dict())
P('industry mix (A10 share vs all):')
mix = pd.DataFrame({'A10': f[A10].industry.value_counts(normalize=True), 'all': f.industry.value_counts(normalize=True)}).fillna(0)
mix['lift'] = mix.A10 / mix['all']
P(mix.sort_values('A10', ascending=False).head(12).round(3).to_string())
# controls
base_ew = f.ew3.to_numpy()
P('date-matched control (minus equal-weight F&O universe over the same 3 sessions):')
P('   A10   ', fmt(stats_A(A10, base=base_ew)))
P('   all   ', fmt(stats_A(np.ones(len(f), bool), base=base_ew)))
P('   A10 minus all (date-matched):', round(stats_A(A10, base=base_ew)['ex'] - stats_A(np.ones(len(f), bool), base=base_ew)['ex'], 3))
yb = y3 - f.beta.to_numpy() * f.n3.to_numpy()
qb = pd.Series(yb).groupby(QN).transform('mean').to_numpy()
P('beta-adjusted (three_day - beta x Nifty 3d; quarter-matched):', fmt(stats_A(A10, y=yb, base=qb)))
ind_q = f.groupby(['qn', 'industry']).three_day.transform('mean').to_numpy()
ind_n = f.groupby(['qn', 'industry']).three_day.transform('size').to_numpy()
okind = ind_n >= 3
P('industry x quarter matched excess (industries with >= 3 results that quarter):',
  fmt(stats_A(A10 & okind, base=np.where(okind, ind_q, np.nan))))
P('A10 median beta', round(np.nanmedian(f.beta[A10]), 2), 'vs others', round(np.nanmedian(f.beta[~A10]), 2),
  '; median 60d vol', round(np.nanmedian(f.vol60[A10]), 2), 'vs', round(np.nanmedian(f.vol60[~A10]), 2))
LV = (f.rank_vol60 <= 20).to_numpy()
P('comparator: lowest-volatility quintile (60d) of the quarter:', fmt(stats_A(LV)), '| overlap with A10', int((LV & A10).sum()))
P('A10 outside the low-vol quintile:', fmt(stats_A(A10 & ~LV)))
# OLS with quarter FE: three_day ~ A10 + beta + vol60 (+ industry FE)
d = f[['three_day', 'qn', 'industry', 'beta', 'vol60']].copy()
d['A10'] = A10.astype(float)
d = d.dropna()
X = pd.get_dummies(d[['qn', 'industry']].astype(str), drop_first=True).astype(float)
X['A10'] = d.A10
X['beta'] = d.beta
X['vol60'] = d.vol60
X['const'] = 1.0
Xv = X.to_numpy(float)
yv = d.three_day.to_numpy(float)
bhat, *_ = np.linalg.lstsq(Xv, yv, rcond=None)
res = yv - Xv @ bhat
XtXi = np.linalg.pinv(Xv.T @ Xv)
# cluster-robust (symbol) SE
sy = f.loc[d.index, 'symbol'].to_numpy()
meat = np.zeros((Xv.shape[1], Xv.shape[1]))
for s_ in np.unique(sy):
    mm = sy == s_
    g_ = Xv[mm].T @ res[mm]
    meat += np.outer(g_, g_)
V = XtXi @ meat @ XtXi
ia = list(X.columns).index('A10')
P(f'OLS three_day ~ A10 + beta + vol60 + quarter FE + industry FE: A10 coef {bhat[ia]:+.3f}, symbol-clustered t {bhat[ia] / np.sqrt(V[ia, ia]):.2f}')
P('nearby cut-offs (quarter-matched excess):')
for lab, m in [('rank>60', f.rank_DP60 > 60), ('rank>70', f.rank_DP60 > 70), ('rank>75', f.rank_DP60 > 75),
               ('rank>80', f.rank_DP60 > 80), ('rank>85', f.rank_DP60 > 85), ('rank>90', f.rank_DP60 > 90),
               ('DP60>=55', f.DP60 >= 55), ('DP60>=60', f.DP60 >= 60), ('DP60>=65', f.DP60 >= 65),
               ('rank<=20 (low delivery)', f.rank_DP60 <= 20)]:
    P(f'   {lab:24s}', fmt(stats_A(m.to_numpy(bool))))
# other window lengths for the level
for w in (20, 120, 250):
    v = np.full(len(f), np.nan)
    for n_, (ee, jj) in enumerate(zip(e, j)):
        x = DP[ee - w + 1:ee + 1, jj]
        if np.isfinite(x).sum() >= 0.66 * w:
            v[n_] = np.nanmean(x)
    rk = pd.Series(v).groupby(QN).rank(pct=True).to_numpy() * 100
    P(f'   {w}-day level rank>80          ', fmt(stats_A(rk > 80)))
P('overlap with the lag rule:', int((A10 & lag_rule).sum()), 'of 85; A10 without lag-rule trades:',
  fmt(stats_A(A10 & ~lag_rule)))
P('survivorship: in F&O by qn 1:', fmt(stats_A(A10 & early)), '| later joiners:', fmt(stats_A(A10 & ~early)))
P('compounded 3-day return instead of the sum convention:', fmt(stats_A(A10, y=f.own_three_day.to_numpy(),
                                                                        base=pd.Series(f.own_three_day).groupby(QN).transform('mean').to_numpy())))
f['A10'] = A10

# -------- own placebo for trade A: ordinary stock-days
P('\nOWN PLACEBO A: ordinary F&O stock-days (no result session of the stock in [d-10, d+13]); signal at e = d-1;')
P('               outcome = sum of daily returns d+1..d+3 (same convention); ranks among the quarter universe that day')
ev = pd.read_csv(f'{DATA}/events.csv', usecols=['symbol', 'i_rd', 'i_react'])
RES = np.zeros((T, S), bool)
for s_, a, b in zip(ev.symbol, ev.i_rd, ev.i_react):
    if s_ in SJ:
        for x in (a, b):
            if np.isfinite(x):
                RES[int(x), SJ[s_]] = True
# blocked days
BL = np.zeros((T, S), bool)
for t_, jj in zip(*np.where(RES)):
    BL[max(0, t_ - 13):t_ + 11, jj] = True                         # d in [r-13, r+10]  <=> r in [d-10, d+13]
# qn_next for each (day, symbol): next panel result with i_rd >= d+1, within 70 sessions
NXT = np.full((T, S), -1)
for (s_, q), g in f.groupby(['symbol', 'qn']):
    jj = SJ[s_]
    rd = int(g.i_rd.iloc[0])
    lo = max(0, rd - 70)
    seg = NXT[lo:rd, jj]
    NXT[lo:rd, jj] = np.where(seg == -1, q, seg)
pl = []
i_lo = int(f.i_cut.min()) - 70
i_hi = T - 5
for d_ in range(i_lo, i_hi):
    js = np.where((NXT[d_] >= 0) & ~BL[d_] & np.isfinite(R[d_ + 1:d_ + 4]).all(0))[0]
    if len(js) == 0:
        continue
    for jj in js:
        q = NXT[d_, jj]
        uni = U[q]
        vals = DP60[d_ - 1, uni]
        vals = vals[np.isfinite(vals)]
        x = DP60[d_ - 1, jj]
        if not np.isfinite(x) or len(vals) < 20:
            continue
        rk = (np.sum(vals < x) + (np.sum(vals == x) + 1) / 2) / len(vals) * 100
        pl.append((d_, jj, q, rk, R[d_ + 1:d_ + 4, jj].sum()))
pl = pd.DataFrame(pl, columns=['d', 'j', 'qn', 'rank_DP60', 'fwd3'])
pl['date_mean'] = pl.groupby('d').fwd3.transform('mean')
pl['q_mean'] = pl.groupby('qn').fwd3.transform('mean')
sig = pl.rank_DP60 > 80
ex_q = (pl.fwd3 - pl.q_mean)[sig]
ex_d = (pl.fwd3 - pl.date_mean)[sig]
P(f'placebo stock-days {len(pl)}, signal days {int(sig.sum())}; excess (quarter-matched) {ex_q.mean():+.3f}; '
  f'excess (date-matched) {ex_d.mean():+.3f}')
# weight placebo quarters like the results
wq = f[A10].qn.value_counts(normalize=True)
exq_w = (pl[sig].assign(ex=ex_d).groupby('qn').ex.mean().reindex(wq.index) * wq).sum()
P(f'placebo date-matched excess re-weighted to the results quarter mix {exq_w:+.3f}')
res_ex_d = stats_A(A10, base=base_ew)['ex'] - stats_A(np.ones(len(f), bool), base=base_ew)['ex']
P(f'results A10 date-matched excess vs all results {res_ex_d:+.3f} (quarter-matched {stats_A(A10)["ex"]:+.3f})')
P(f'DiD (quarter-matched) {stats_A(A10)["ex"] - ex_q.mean():+.3f}; DiD (date-matched) {stats_A(A10, base=base_ew)["ex"] - ex_d.mean():+.3f}')
# placebo p: draws of 681 placebo signal days (date-matched excess) vs results date-matched excess of A10
obs = stats_A(A10, base=base_ew)['ex']
dr = rng.choice(ex_d.to_numpy(), (10000, int(A10.sum())), replace=True).mean(1)
P(f'placebo p (date-matched: results A10 minus EW universe {obs:+.3f} vs draws of placebo signal days): {np.mean(dr >= obs):.4f}')
# placebo by sub-period
for lab, mm in [('first 14', pl.qn <= 13), ('last 8', pl.qn >= 14)]:
    P(f'   placebo {lab}: signal days {int((sig & mm).sum())}, date-matched excess {(pl.fwd3 - pl.date_mean)[sig & mm].mean():+.3f}')
# Same-date comparison on results: high-DP60 results vs high-DP60 non-results the same days (paired by date)
pl['A10'] = sig
pd.DataFrame(pl).to_csv(f'{OUT}/own_placebo_A.csv.gz', index=False, compression='gzip', float_format='%.5g')

# -------- A06 quick
P('\n' + '=' * 100)
P('A06 (last published day delivery % spike, top quintile)')
P('=' * 100)
P('base:', fmt(stats_A(A06)))
P('LOQO:', loqo(A06), '| by year:', by_year(A06))
nsym, pneg, ci = cluster_boot(A06)
P(f'symbol-cluster bootstrap: {nsym} symbols, P(mean excess <= 0) {pneg:.3f}')
P('date-matched:', fmt(stats_A(A06, base=base_ew)), '| all:', round(stats_A(np.ones(len(f), bool), base=base_ew)['ex'], 3))
for lab, m in [('rank>70', f.rank_DPL > 70), ('rank>75', f.rank_DPL > 75), ('rank>85', f.rank_DPL > 85),
               ('rank>90', f.rank_DPL > 90), ('DPL>5', f.DPL > 5), ('DPL>10', f.DPL > 10)]:
    P(f'   {lab:10s}', fmt(stats_A(m.to_numpy(bool))))
P('overlap with A10:', int((A06 & A10).sum()), '; A06 without A10:', fmt(stats_A(A06 & ~A10)))

# -------- RA1
P('\n' + '=' * 100)
P('RA1 (lag21 < -10 AND delivery qty 5/60 >= 1.0)')
P('=' * 100)
P('base:', fmt(stats_A(RA1)))
P('lag rule:', fmt(stats_A(lag_rule)))
P('LOQO RA1:', loqo(RA1), '| by year:', by_year(RA1))
P('union RA1 or lag rule:', fmt(stats_A(RA1 | lag_rule)), '| RA1 only:', fmt(stats_A(RA1 & ~lag_rule)),
  '| lag only:', fmt(stats_A(lag_rule & ~RA1)))
P('lag rule AND RA1 (both volume and delivery up):', fmt(stats_A(RA1 & lag_rule)))
lag10 = (f.in_fo_events == True).to_numpy() & (f.lag21.to_numpy() < -10)
for c in (0.8, 0.9, 1.0, 1.1, 1.2, 1.5):
    P(f'   lag<-10 & DQR>={c}:', fmt(stats_A(lag10 & (f.DQR.to_numpy() >= c))), '| lag rule with vol>=', c, ':',
      fmt(stats_A(lag10 & (f.vol_ratio_5_60.to_numpy() >= c))))
for L in (-8, -12, -15):
    lm = (f.in_fo_events == True).to_numpy() & (f.lag21.to_numpy() < L)
    P(f'   lag<{L} & DQR>=1:', fmt(stats_A(lm & (f.DQR.to_numpy() >= 1))), '| vol>=1:', fmt(stats_A(lm & (f.vol_ratio_5_60.to_numpy() >= 1))))
P('survivorship RA1: early', fmt(stats_A(RA1 & early)), '| later', fmt(stats_A(RA1 & ~early)))
nsym, pneg, ci = cluster_boot(RA1)
P(f'symbol-cluster bootstrap RA1: {nsym} symbols, P(mean excess <= 0) {pneg:.4f}')
P('date-matched RA1:', fmt(stats_A(RA1, base=base_ew)))
# within lag<-10: does DQR add to volume? 2x2
for a_lab, am in [('vol>=1', f.vol_ratio_5_60 >= 1), ('vol<1', f.vol_ratio_5_60 < 1)]:
    for b_lab, bm in [('DQR>=1', f.DQR >= 1), ('DQR<1', f.DQR < 1)]:
        P(f'   lag<-10 & {a_lab} & {b_lab}:', fmt(stats_A(lag10 & am.to_numpy() & bm.to_numpy())))

f.to_csv(f'{OUT}/own_feat_stress.csv', index=False, float_format='%.6g')
LOG.close()
