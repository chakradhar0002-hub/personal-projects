#!/usr/bin/env python3
"""ADDED AFTER the main run (run_tests.py) had been looked at. Diagnostics of the only WORKS test (S1_DRIFT4_Q5) and
the WATCH (S3_CONSIST_DRIFT), plus descriptive composites with the existing winner rule. No new p-value enters Holm;
nothing here can change a verdict. One extra luck p (S1 in the last 8 quarters alone) is a robustness read only."""
import numpy as np
import pandas as pd

SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
HERE = f'{SP}/perf/B_post_results'
F = f'{SP}/perf/features'
LOG = open(f'{HERE}/addendum.log', 'w')
rng = np.random.default_rng(11)


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    LOG.write(s + '\n')


o = pd.read_csv(f'{F}/outcomes.csv')
p = pd.read_csv(f'{F}/panel.csv').merge(o.drop(columns=['quarter', 'period']), on=['symbol', 'qn'], validate='1:1')
p = p[p.tradable_B].copy()
p['x'] = p.vsN_H20 - 0.19
for H in (5, 10):
    p[f'x{H}'] = p[f'raw_H{H}'] - p[f'nifty_H{H}'] - 0.19
p['label'] = 'Results for ' + p.period + ' (' + p.quarter + ')'
e4 = p.mean_drift_4_B.notna()
q80 = p.groupby('qn').mean_drift_4_B.transform(lambda s: s.quantile(0.8))
p['S1'] = e4 & (p.mean_drift_4_B >= q80)
p['S3'] = (p.n_drift_4_B == 4) & (p.n_pos_drift_4_B >= 3)
p['W_'] = p.W == True
p['WR_'] = p.W_ & (p.cut_rsi14 > 50)
E = p[e4].copy()


def gain(sub, par, cell, col='x'):
    pm = par.groupby(cell(par))[col].mean()
    dd = sub[col] - cell(sub).map(pm)
    return dd


def row(lab, sub, par, cell=lambda d: d.qn, col='x'):
    dd = gain(sub, par, cell, col)
    f, l = sub.qn <= 13, sub.qn >= 14
    P(f'  {lab:46s} n={len(sub):4d} mean {sub[col].mean():+.2f}  gain {dd.mean():+.2f}  '
      f'(first14 n={int(f.sum())} {sub[col][f].mean():+.2f} / {dd[f].mean():+.2f}; last8 n={int(l.sum())} '
      f'{sub[col][l].mean():+.2f} / {dd[l].mean():+.2f})')


P('X1  S1 (top quintile of mean_drift_4, any reaction) by the size of the current reaction; parent = eligible results '
  'of the same quarter AND same reaction bucket')
E['xb'] = pd.cut(E.XN, [-np.inf, 0, 4, np.inf], labels=['XN<=0', '0<XN<=4', 'XN>4 (winner)'])
for b in E.xb.cat.categories:
    row(f'S1 & {b}', E[E.S1 & (E.xb == b)], E[E.xb == b])
P('\nX2  S1 gain after controlling (parent cell = quarter x control bucket)')
row('plain (quarter)', E[E.S1], E)
for c in ('rank_vsN_252_B', 'rank_vsN_126_B', 'rank_vsN_63_B'):
    E['b_' + c] = pd.cut(E[c], [-1, 100 / 3, 200 / 3, 101], labels=False)
    row(f'quarter x {c} tercile', E[E.S1], E, cell=lambda d, c=c: d.qn * 10 + d['b_' + c])
E['b_mxn'] = E.groupby('qn').mean_xn_4_B.transform(lambda s: pd.qcut(s, 3, labels=False))
row('quarter x mean_xn_4 tercile (past reactions)', E[E.S1], E, cell=lambda d: d.qn * 10 + d.b_mxn)
E['b_xn'] = E.groupby('qn').XN.transform(lambda s: pd.qcut(s, 3, labels=False))
row('quarter x current XN tercile', E[E.S1], E, cell=lambda d: d.qn * 10 + d.b_xn)
row('quarter x sector_index', E[E.S1], E, cell=lambda d: d.qn.astype(str) + '|' + d.sector_index.astype(str))
row('quarter x fin_type', E[E.S1], E, cell=lambda d: d.qn.astype(str) + '|' + d.fin_type.astype(str))

P('\nX3  S1 robustness')
s1 = E[E.S1]
pq = s1.groupby(['qn', 'label']).x.mean()
dq = gain(s1, E, lambda d: d.qn).groupby(s1.qn).mean()
best_q = dq.idxmax()
row(f'without its best quarter (qn {best_q})', s1[s1.qn != best_q], E[E.qn != best_q])
P(f'  unique stocks {s1.symbol.nunique()}; trades per stock max {s1.symbol.value_counts().max()}; '
  f'top-10 stocks hold {s1.symbol.value_counts().head(10).sum()} of {len(s1)} trades')
top10 = s1.symbol.value_counts().head(10).index
row('without its 10 most frequent stocks', s1[~s1.symbol.isin(top10)], E)
gs = s1.groupby('symbol').x.sum().sort_values(ascending=False)
row('without the 10 stocks contributing most', s1[~s1.symbol.isin(gs.index[:10])], E)
for ft in sorted(E.fin_type.dropna().unique()):
    row(f'fin_type {ft}', s1[s1.fin_type == ft], E[E.fin_type == ft])
# last 8 alone: luck p
l8 = s1[s1.qn >= 14]
cnt = l8.groupby('qn').size()
pools = {q: E[E.qn == q].x.to_numpy() for q in cnt.index}
dr = np.array([np.concatenate([rng.choice(pools[q], k, replace=False) for q, k in cnt.items()]).mean()
               for _ in range(5000)])
P(f'  last 8 alone: obs {l8.x.mean():+.3f}, random {dr.mean():+.3f} (sd {dr.std():.3f}), luck p {(1 + (dr >= l8.x.mean()).sum()) / 5001:.4f}')
f14 = s1[s1.qn <= 13]
cnt = f14.groupby('qn').size()
pools = {q: E[E.qn == q].x.to_numpy() for q in cnt.index}
dr = np.array([np.concatenate([rng.choice(pools[q], k, replace=False) for q, k in cnt.items()]).mean()
               for _ in range(5000)])
P(f'  first 14 alone: obs {f14.x.mean():+.3f}, random {dr.mean():+.3f} (sd {dr.std():.3f}), luck p {(1 + (dr >= f14.x.mean()).sum()) / 5001:.4f}')
P('  horizons (same trades, exit k+5 / k+10 / k+20; net -0.19):')
for c in ('x5', 'x10', 'x'):
    row(f'   S1 {c}', s1, E, col=c)
# concurrency
srt = s1.sort_values('i_react')
ii = srt.i_react.to_numpy()
conc = max(int(((ii <= t) & (ii + 20 > t)).sum()) for t in range(ii.min(), ii.max() + 21))
P(f'  max positions open at once (20-session holds): {conc}')
P('  per quarter (S1 trades, mean vsN_net, all eligible results mean, gain):')
for (q, lab), v in pq.items():
    P(f'    qn {q:2d} {lab:38s} n={int((s1.qn == q).sum()):3d} S1 {v:+6.2f}  all {E[E.qn == q].x.mean():+6.2f}  gain {dq[q]:+6.2f}')

P('\nX4  mean_drift_4 quintile (within quarter, all F&O results) -> 20-session vsN_net (mean / gain vs quarter)')
E['qq'] = E.groupby('qn').mean_drift_4_B.transform(lambda s: pd.qcut(s.rank(method='first'), 5, labels=False) + 1)
for k in range(1, 6):
    row(f'Q{k}', E[E.qq == k], E)

P('\nX5  composites with the existing winner rule (descriptive; parent = all winners / RSI winners of the quarter)')
W4 = p[p.W_]
WR4 = p[p.WR_]
row('W (all plain winners)', W4, W4)
row('W & S1 (winner + top-quintile drift record)', W4[W4.S1], W4)
row('W & not S1 (record known)', W4[~W4.S1 & W4.mean_drift_4_B.notna()], W4)
row('WR (winners RSI>50)', WR4, WR4)
row('WR & S1', WR4[WR4.S1], WR4)
row('WR & not S1 (record known)', WR4[~WR4.S1 & WR4.mean_drift_4_B.notna()], WR4)
row('S1 & XN>0 (any positive reaction)', E[E.S1 & (E.XN > 0)], E)
row('S1 & XN<=0', E[E.S1 & (E.XN <= 0)], E)
qf = pd.read_csv(f'{HERE}/quiet_features.csv.gz')
ses = pd.read_csv(f'{SP}/sector_lab/data/sessions.csv')
ret = pd.read_csv(f'{SP}/sector_lab/data/returns.csv', index_col=0)
nif = pd.read_csv(f'{SP}/sector_lab/data/index_close.csv', index_col=0)['Nifty 50'].to_numpy()
PX = np.cumprod(1 + np.nan_to_num(ret.to_numpy(float)), axis=0)
SYM = {s: j for j, s in enumerate(ret.columns)}
j = qf.symbol.map(SYM).to_numpy(int)
i = qf.i.to_numpy(int)
qf['x'] = ((PX[i + 20, j] / PX[i, j] - 1) - (nif[i + 20] / nif[i] - 1)) * 100 - 0.19
qf['month'] = qf.day.str[:7]
qe = qf.mean_drift_4.notna()
qtop = qe & (qf.mean_drift_4 >= qf.p80)
for lab, m in (('quiet winners & top-quintile record', qf.W & qtop), ('quiet winners, record known', qf.W & qe)):
    P(f'  placebo {lab:40s} n={int(m.sum()):5d} mean {qf.x[m].mean():+.2f}')
qw = qf[qf.W & qe]
pm = qw.groupby('month').x.mean()
P(f'  placebo gain of top-quintile record among quiet winners (same month): '
  f'{(qw[qw.mean_drift_4 >= qw.p80].x - qw[qw.mean_drift_4 >= qw.p80].month.map(pm)).mean():+.2f}')
LOG.close()

# ---- X6 (ADDED AFTER X3 was seen): calibrate the stock-concentration cuts against random same-size picks
LOG = open(f'{HERE}/addendum.log', 'a')
P('\nX6  stock concentration calibrated: same cuts applied to 1,000 random same-size per-quarter picks of eligible results')
qm = E.groupby('qn').x.mean()
E['g'] = E.x - E.qn.map(qm)
cnt = s1.groupby('qn').size()
idx_by_q = {q: np.flatnonzero((E.qn == q).to_numpy()) for q in cnt.index}
res_top, res_freq = [], []
for _ in range(1000):
    pick = E.iloc[np.concatenate([rng.choice(idx_by_q[q], k, replace=False) for q, k in cnt.items()])]
    gs_ = pick.groupby('symbol').g.sum().sort_values(ascending=False)
    res_top.append(pick[~pick.symbol.isin(gs_.index[:10])].g.mean())
    fr = pick.symbol.value_counts().head(10).index
    res_freq.append(pick[~pick.symbol.isin(fr)].g.mean())
res_top, res_freq = np.array(res_top), np.array(res_freq)
s1g = E[E.S1]
gs = s1g.groupby('symbol').g.sum().sort_values(ascending=False)
obs_top = s1g[~s1g.symbol.isin(gs.index[:10])].g.mean()
obs_fr = s1g[~s1g.symbol.isin(s1g.symbol.value_counts().head(10).index)].g.mean()
P(f'  without the 10 stocks contributing most: S1 {obs_top:+.2f}; random picks mean {res_top.mean():+.2f}, '
  f'95th pct {np.percentile(res_top, 95):+.2f}; share of random >= S1: {(res_top >= obs_top).mean():.3f}')
P(f'  without the 10 most frequent stocks:     S1 {obs_fr:+.2f}; random picks mean {res_freq.mean():+.2f}, '
  f'95th pct {np.percentile(res_freq, 95):+.2f}; share of random >= S1: {(res_freq >= obs_fr).mean():.3f}')
P('  S1 top-10 contributing stocks:', ', '.join(f'{s} ({int((s1g.symbol == s).sum())} trades, gain sum {v:+.1f})'
                                            for s, v in gs.head(10).items()))
LOG.close()
