#!/usr/bin/env python3
"""Skeptic checks of the two-down-days finding (written after seeing the main tables; not pre-registered).
1. Does the day-3 bounce reverse on day 4 (a closing-price artefact) or persist?
2. Is it the stocks or the market: big two-day falls, same-day peers.
3. Nifty 50 after two down days, by half and with a bootstrap.
4. Quarters on each side; leave-one-quarter-out.
Writes OUT/skeptic/checks.log."""
import os
import numpy as np
import pandas as pd
from scipy import stats

REPO = os.environ.get('REPO_ROOT', '.')
LAB = os.environ.get('LAB_ROOT', 'lab')
OUT = os.environ.get('OUT', os.path.join(REPO, 'results', 'two_down_days'))
os.makedirs(f'{OUT}/skeptic', exist_ok=True)
log = []
P = lambda *a: (log.append(' '.join(str(x) for x in a)), print(*a))
D = pd.read_csv(f'{OUT}/days.csv.gz')
M = D[D.main].copy()
M['down3'] = (M.r3 < 0).astype(float)
M['down4'] = (M.r4 < 0).astype(float)
M['two_down'] = (M.r1 < 0) & (M.r2 < 0)
M['r34'] = M.r3 + M.r4

def peer(X, sig, y):
    g = X.assign(s=sig.to_numpy()).dropna(subset=[y]).groupby(['day3', 's'])[y].mean().unstack('s').dropna()
    d = g[True] - g[False]
    return d.mean(), stats.ttest_1samp(d, 0).pvalue, len(d)

P('1. day 3 vs day 4 for two-down stocks, minus same-day peers (pts; share down x100)')
for y, lab in (('down3', 'share down day 3'), ('down4', 'share down day 4'), ('r3', 'mean day 3'), ('r4', 'mean day 4'), ('r34', 'mean day 3 + day 4'),
               ('gap3', 'day-3 opening gap'), ('intra3', 'day-3 open to close')):
    m, p, n = peer(M, M.two_down, y)
    k = 100 if y.startswith('down') else 1
    P(f'   {lab:22s} {m * k:+.3f}  p {p:.4f}  dates {n}')

P('\n2. market vs stock: raw share down after two down days, and minus same-day peers')
for lab, sig in (('two down', M.two_down), ('both < -1%', (M.r1 < -1) & (M.r2 < -1)), ('both < -2%', (M.r1 < -2) & (M.r2 < -2))):
    x = M[sig]
    m, p, n = peer(M, sig, 'down3')
    g = M.assign(s=sig.to_numpy()).groupby(['day3', 's']).down3.agg(['mean', 'size']).unstack('s').dropna()
    w = g[('size', True)]
    pw = (g[('mean', False)] * w).sum() / w.sum()
    P(f'   {lab:12s} n {len(x):6d}  raw down {x.down3.mean() * 100:5.1f}%  other stocks on the same days (weighted by signal count) '
      f'{pw * 100:5.1f}%  vs peers: equal-weight dates {m * 100:+.2f} (p {p:.3f}), signal-weighted {((g[("mean", True)] - g[("mean", False)]) * w).sum() / w.sum() * 100:+.2f}')

P('\n3. Nifty 50 after two down days (2016-01 .. 2026-09), by half; bootstrap of sessions by month')
ix = pd.read_csv(os.path.join(LAB, 'sector_lab', 'data', 'index_close.csv'), index_col=0)
r = ix['Nifty 50'].pct_change() * 100
r[r.index.isin(['2015-12-02', '2016-06-21'])] = np.nan
df = pd.DataFrame({'r1': r.shift(2), 'r2': r.shift(1), 'r3': r}).dropna()
df = df[df.index >= '2016-01-01']
df['dd'] = (df.r1 < 0) & (df.r2 < 0)
df['down'] = (df.r3 < 0).astype(float)
for lab, x in (('2016-2020', df[df.index < '2021-01-01']), ('2021-2026', df[df.index >= '2021-01-01']), ('all', df)):
    a_, b_ = x[x.dd].down.mean(), x[~x.dd].down.mean()
    P(f'   {lab:9s} after 2 down: {a_ * 100:5.1f}% down (n {int(x.dd.sum())}), other sessions {b_ * 100:5.1f}%  diff {(a_ - b_) * 100:+.1f}  '
      f'chi2 p {stats.chi2_contingency(pd.crosstab(x.dd, x.down))[1]:.3f}')
rng = np.random.default_rng(7)
mon = df.index.str[:7]
months = np.unique(mon)
grp = {m: df[mon == m] for m in months}
bs = []
for _ in range(5000):
    pick = rng.choice(months, len(months))
    x = pd.concat([grp[m] for m in pick])
    bs.append(x[x.dd].down.mean() - x[~x.dd].down.mean())
bs = np.array(bs)
P(f'   month bootstrap of the difference: 95% range {np.percentile(bs, 2.5) * 100:+.1f} .. {np.percentile(bs, 97.5) * 100:+.1f} pts, '
  f'p {min(1, 2 * min((bs <= 0).mean(), (bs >= 0).mean())):.3f}')

P('\n4. quarters: share-down difference vs same-day peers')
q = pd.read_csv(f'{OUT}/by_quarter.csv')
P(f'   negative (bounce) in {(q.peer_diff < 0).sum()} of {len(q)} quarters; sign test p {stats.binomtest(int((q.peer_diff < 0).sum()), len(q)).pvalue:.3f}')
M['quarter'] = M.day3.str[:4] + 'Q' + ((M.day3.str[5:7].astype(int) - 1) // 3 + 1).astype(str)
loo = []
for qq in M.quarter.unique():
    X = M[M.quarter != qq]
    loo.append(peer(X, X.two_down, 'down3')[0] * 100)
P(f'   leave-one-quarter-out: {min(loo):+.2f} .. {max(loo):+.2f} pts')
P('\n5. size of the effect in money: the extra share of up days is about 2.4 points, the extra mean return about +0.04 points;')
P('   costs are 0.17% a round trip, so the bounce is about a quarter of one trade\'s costs.')
open(f'{OUT}/skeptic/checks.log', 'w').write('\n'.join(log) + '\n')
