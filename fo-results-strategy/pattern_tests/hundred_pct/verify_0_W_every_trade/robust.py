import os  # LAB_ROOT: folder holding search22/, sector/, sector_lab/data/ and five_pct/
import pandas as pd, numpy as np
SP = os.environ.get('LAB_ROOT', 'lab') + ''
d = pd.read_csv(f'{SP}/five_pct/A_rule_search/features_all.csv')
fo = d[d.in_fo].copy()
fo['r'] = fo.three_day * 100
fo['yr'] = pd.to_datetime(fo.cutoff).dt.year


def sel(x, a=154, b=-0.01678, c=0.003908):
    return x[(x.days_since_dividend >= a) & (x.gap5 <= b) & (x.own_dm1 <= c)]


def st(p, col='r'):
    if len(p) == 0:
        return 'n=0'
    q = p.groupby('qn')[col].mean()
    return 'n=%3d win=%5.1f%% net>0.17=%5.1f%% avg=%+.2f worst=%+.1f qpos=%d/%d' % (
        len(p), (p[col] > 0).mean() * 100, (p[col] > 0.17).mean() * 100, p[col].mean(), p[col].min(), (q > 0).sum(), len(q))


print('BASE all22 :', st(sel(fo)))
print('BASE first14:', st(sel(fo[fo.qn < 14])))
print('BASE last8  :', st(sel(fo[fo.qn >= 14])))
fo['tp'] = fo.tp3 * 100
print('tp3 exit last8:', st(sel(fo[fo.qn >= 14]), 'tp'), ' all22:', st(sel(fo), 'tp'))
print('\nBy year:')
for y, g in sel(fo).groupby('yr'):
    print(' ', y, st(g))
print('\nBy quarter (last 8):')
for q, g in sel(fo[fo.qn >= 14]).groupby('qn'):
    print('  qn', q, 'n', len(g), 'wins', (g.r > 0).sum(), 'avg %+.2f' % g.r.mean())
print('\nLast 4 quarters (qn 18-21):', st(sel(fo[fo.qn >= 18])))
print('\nNeighbouring thresholds (first14 | last8):')
for a in [120, 140, 154, 170, 200]:
    for b in [-0.012, -0.015, -0.01678, -0.019, -0.022]:
        for c in [0.0, 0.002, 0.003908, 0.006, 1]:
            p1 = sel(fo[fo.qn < 14], a, b, c); p2 = sel(fo[fo.qn >= 14], a, b, c)
            if (a, b, c) in [(154, -0.01678, 0.003908)] or (a == 154 and c == 0.003908) or (b == -0.01678 and c == 0.003908) or (a == 154 and b == -0.01678):
                print('  dsd>=%d gap5<=%.4f own_dm1<=%s | IS n=%d win=%.1f%% | OOS n=%d win=%.1f%% avg=%+.2f' % (
                    a, b, c, len(p1), (p1.r > 0).mean() * 100, len(p2), (p2.r > 0).mean() * 100 if len(p2) else np.nan, p2.r.mean() if len(p2) else np.nan))
# grid summary: share of neighbouring cells with 100% IS
res = []
for a in np.arange(100, 260, 10):
    for b in np.arange(-0.025, -0.0099, 0.001):
        for c in np.arange(-0.002, 0.0081, 0.001):
            p1 = sel(fo[fo.qn < 14], a, b, c); p2 = sel(fo[fo.qn >= 14], a, b, c)
            res.append(dict(a=a, b=b, c=c, n_is=len(p1), wr_is=(p1.r > 0).mean() * 100 if len(p1) else np.nan,
                            n_oos=len(p2), wr_oos=(p2.r > 0).mean() * 100 if len(p2) else np.nan, avg_oos=p2.r.mean() if len(p2) else np.nan))
R = pd.DataFrame(res)
R.to_csv(os.environ.get('LAB_ROOT', 'lab') + '/hundred_pct/verify_0_W_every_trade/threshold_grid.csv', index=False)
print('\nGrid of %d threshold combos (dsd 100..250, gap5 -2.5%%..-1.0%%, own_dm1 -0.2%%..+0.8%%):' % len(R))
print('  IS win rate: median %.1f%%, share 100%% = %.1f%%' % (R.wr_is.median(), (R.wr_is == 100).mean() * 100))
print('  OOS win rate: median %.1f%%, 10-90%%: %.1f..%.1f; OOS avg median %+.2f' % (R.wr_oos.median(), R.wr_oos.quantile(.1), R.wr_oos.quantile(.9), R.avg_oos.median()))
print('\nSingle and double conditions (first14 | last8):')
for nm, f in [('gap5<=-1.678%', lambda x: x.gap5 <= -0.01678), ('dsd>=154', lambda x: x.days_since_dividend >= 154),
              ('own_dm1<=0.39%', lambda x: x.own_dm1 <= 0.003908),
              ('gap5 & dsd', lambda x: (x.gap5 <= -0.01678) & (x.days_since_dividend >= 154)),
              ('gap5 & own_dm1', lambda x: (x.gap5 <= -0.01678) & (x.own_dm1 <= 0.003908)),
              ('dsd & own_dm1', lambda x: (x.days_since_dividend >= 154) & (x.own_dm1 <= 0.003908)),
              ('all F&O', lambda x: x.gap5 == x.gap5)]:
    a1 = fo[(fo.qn < 14) & f(fo)]; a2 = fo[(fo.qn >= 14) & f(fo)]
    print('  %-16s IS n=%4d win=%.1f%% avg=%+.2f | OOS n=%4d win=%.1f%% avg=%+.2f' % (nm, len(a1), (a1.r > 0).mean() * 100, a1.r.mean(), len(a2), (a2.r > 0).mean() * 100, a2.r.mean()))
p = sel(fo).sort_values('r')
print('\nWithout best trades (all 22):')
for k in [1, 3, 5]:
    q = p.iloc[:-k]
    print('  drop top %d: avg %+.2f win %.1f%%' % (k, q.r.mean(), (q.r > 0).mean() * 100))
po = sel(fo[fo.qn >= 14]).sort_values('r')
for k in [1, 3]:
    q = po.iloc[:-k]
    print('  OOS drop top %d: avg %+.2f' % (k, q.r.mean()))
print('  OOS drop worst 1: avg %+.2f' % po.iloc[1:].r.mean())
print('\nLeave-one-quarter-out (all 22) avg / win:')
P = sel(fo)
lo = [(q, P[P.qn != q].r.mean(), (P[P.qn != q].r > 0).mean() * 100) for q in sorted(P.qn.unique())]
print('  avg range %+.2f..%+.2f, win range %.1f..%.1f' % (min(x[1] for x in lo), max(x[1] for x in lo), min(x[2] for x in lo), max(x[2] for x in lo)))
# clustering: trades per day
print('\nTrades sharing a cutoff date (all 22):', P.groupby('cutoff').size().value_counts().sort_index().to_dict())
print('distinct cutoff dates IS:', P[P.qn < 14].cutoff.nunique(), ' OOS:', P[P.qn >= 14].cutoff.nunique())
# all stocks / survivors
A = d.copy(); A['r'] = A.three_day * 100
pa = sel(A)
print('\nAll stocks:', st(pa), ' | pre-F&O rows:', st(pa[~pa.in_fo]))
print('All stocks first14:', st(pa[pa.qn < 14]), ' pre-F&O first14:', st(pa[(~pa.in_fo) & (pa.qn < 14)]))
# binomial
from scipy.stats import binomtest
base = (fo[fo.qn >= 14].r > 0).mean()
print('\nOOS 23/33 vs 50%%: p=%.4f ; vs F&O last-8 base rate %.1f%%: p=%.4f' % (binomtest(23, 33, 0.5).pvalue, base * 100, binomtest(23, 33, base).pvalue))
g = fo[(fo.qn >= 14) & (fo.gap5 <= -0.01678)]
print('OOS vs gap5-only base rate %.1f%%: p=%.4f' % ((g.r > 0).mean() * 100, binomtest(23, 33, (g.r > 0).mean()).pvalue))
# effective sample size: cluster by cutoff date
c = sel(fo[fo.qn >= 14]).groupby('cutoff').r.apply(lambda s: (s > 0).mean())
print('OOS by distinct cutoff date: %d dates, share of dates with >50%% winners %.1f%%' % (len(c), (c > 0.5).mean() * 100))
