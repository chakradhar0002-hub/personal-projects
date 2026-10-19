"""Skeptic 2: is the link for the strongest features driven by a few quarters / results / subgroups / lag trades /
plain past return / market timing?"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
from scipy import stats
from common import *

df = load_events()
TOP = ['slope_sma_50', 'slope_ema_20', 'dist_sma_100', 'slope_ema_50', 'dist_ema_50', 'dist_sma_50']


def line(name, d, f, y='three_day', B=4000):
    ics = ic_by_q(d, f, y)
    m, t, pos, n = summ(ics)
    _, p, _ = perm_ic(d, f, y, B=B)
    return f'{name:44s} n={len(d):5d} meanIC {m:+.3f} t {t:+.2f} pos {pos}/{n} p {fpv(p)}'


print('== leave-one-quarter-out and drop-the-worst-quarters')
for f in TOP:
    ics = ic_by_q(df, f)
    loo = [(q, ics.drop(q).mean(), summ(ics.drop(q))[1]) for q in ics.index]
    lo = min(loo, key=lambda x: abs(x[1])); hi = max(loo, key=lambda x: abs(x[1]))
    srt = ics.sort_values()
    d3 = ics.drop(srt.index[:3])
    print(f'  {f:14s} all {ics.mean():+.3f} (t {summ(ics)[1]:+.2f}); LOO range {lo[1]:+.3f} (drop q{lo[0]}, t {lo[2]:+.2f}) .. '
          f'{hi[1]:+.3f}; drop 3 most negative quarters {list(srt.index[:3])}: {d3.mean():+.3f} t {summ(d3)[1]:+.2f} pos {summ(d3)[2]}/19; '
          f'median quarterly IC {ics.median():+.3f}')
    # sign test on quarters
    k = (ics > 0).sum()
    print(f'      sign test {k}/22 positive: two-sided binomial p {stats.binomtest(int(k), 22).pvalue:.3f}')

print('\n== drop the most extreme results (pooled excess) / bottom-fifth average without them')
for f in TOP:
    out = []
    for k in [5, 10]:
        d = df.copy()
        top = d.three_day.nlargest(k).index; bot = d.three_day.nsmallest(k).index
        a = line(f'{f} drop {k} best', d.drop(top), f, B=2000)
        b = line(f'{f} drop {k} worst', d.drop(bot), f, B=2000)
        c = line(f'{f} drop {k} best+{k} worst', d.drop(top.union(bot)), f, B=2000)
        out += [a, b, c]
    print('\n'.join('  ' + o for o in out))

print('\n== bottom fifth (favourable side) average gross, with / without big winners')
for f in TOP:
    fi = fifth(df, f)
    b = df[fi == 1].three_day
    t5 = df[fi == 5].three_day
    print(f'  {f:14s} bottom {b.mean():+.2f} (n {len(b)}), median {b.median():+.2f}; minus 5 best {b.drop(b.nlargest(5).index).mean():+.2f}; '
          f'minus 10 best {b.drop(b.nlargest(10).index).mean():+.2f}; winsorised 1%/99% {b.clip(df.three_day.quantile(.01), df.three_day.quantile(.99)).mean():+.2f} | '
          f'top {t5.mean():+.2f} median {t5.median():+.2f}')

print('\n== subgroups')
df['big'] = df.groupby('qn').mcap.transform(lambda s: s >= s.median())
for f in TOP[:4]:
    print(f'  {f}')
    print('   ', line('mcap >= quarter median', df[df.big & df.mcap.notna()], f))
    print('   ', line('mcap < quarter median', df[~df.big & df.mcap.notna()], f))
    print('   ', line('mcap missing', df[df.mcap.isna()], f) if df.mcap.isna().sum() > 50 else '')
    print('   ', line('in F&O since qn 0', df[df.first_qn == 0], f))
    print('   ', line('joined F&O later (first qn >= 1)', df[df.first_qn >= 1], f))
    print('   ', line('joined F&O qn >= 14', df[df.first_qn >= 14], f))
    print('   ', line('excluding the 85 lag10+volume trades', df[~df.lag_trade], f))
    print('   ', line('Company (non-financial)', df[df.fin_type == 'Company'], f))
    print('   ', line('Bank / NBFC', df[df.fin_type != 'Company'], f))

print('\n== lag-rule overlap')
for f in TOP:
    fi = fifth(df, f)
    print(f'  {f:14s} lag trades in bottom fifth {int(((fi == 1) & df.lag_trade).sum())} of 85; '
          f'in top fifth {int(((fi == 5) & df.lag_trade).sum())}')
fi = fifth(df, 'slope_sma_50')
b = df[fi == 1]
print('  slope_sma_50 bottom fifth net: all {:+.2f} (n {}); without lag trades {:+.2f} (n {}); the lag trades inside it {:+.2f} (n {})'.format(
    b.three_day.mean() - COST, len(b), b[~b.lag_trade].three_day.mean() - COST, (~b.lag_trade).sum(),
    b[b.lag_trade].three_day.mean() - COST, b.lag_trade.sum()))

print('\n== market timing: outcome three_day minus Nifty 3-day; Nifty own trend as a "feature"')
for f in TOP:
    print('  ', line(f'{f} vs three_day - Nifty', df, f, 'xs_nifty'))
for f in ['nifty_slope_sma_50', 'nifty_dist_sma_50', 'nifty_ret50']:
    print('  ', line(f'{f} (market-level) vs three_day', df, f))
df['rel_slope_sma_50'] = df.slope_sma_50 - df.nifty_slope_sma_50
print('  ', line('slope_sma_50 minus Nifty slope vs three_day - Nifty', df, 'rel_slope_sma_50', 'xs_nifty'))
print('   corr within quarter (mean Spearman) slope_sma_50 vs nifty_slope_sma_50:',
      round(np.mean([stats.spearmanr(g.slope_sma_50, g.nifty_slope_sma_50)[0] for _, g in df.groupby('qn')]), 3))

print('\n== plain past return: IC of controls, correlation with the MA features, partial ICs')
ctrls = ['ret_5d_pct', 'stock_21d_pct', 'lag_pct', 'ret50', 'ret100', 'ret250']
for c in ctrls:
    print('  ', line(f'{c}', df, c))
print('   mean within-quarter Spearman between features and controls:')
for f in TOP:
    print('     ', f, ' '.join(f'{c}={np.mean([stats.spearmanr(g[f], g[c])[0] for _, g in df.groupby("qn")]):+.2f}' for c in ctrls))
print('   partial IC of the MA feature after controlling (within quarter, ranks):')
for f in TOP:
    for cl in [['stock_21d_pct'], ['lag_pct'], ['ret50'], ['ret100'], ['ret_5d_pct', 'stock_21d_pct', 'ret50', 'ret100']]:
        m, t, pos, p = partial_ic(df, f, cl, B=3000)
        print(f'      {f:14s} | {"+".join(cl):40s} partial IC {m:+.3f} t {t:+.2f} pos {pos}/22 p {fpv(p)}')
print('   reverse: partial IC of the past return after controlling for slope_sma_50:')
for c in ['stock_21d_pct', 'lag_pct', 'ret50', 'ret100']:
    m, t, pos, p = partial_ic(df, c, ['slope_sma_50'], B=3000)
    print(f'      {c:14s} | slope_sma_50 partial IC {m:+.3f} t {t:+.2f} pos {pos}/22 p {fpv(p)}')
