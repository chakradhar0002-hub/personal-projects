"""Skeptic 5: walk-forward selection (feature + direction from earlier quarters only), and the T5 tradable claim."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
from scipy import stats
from common import *

df = load_events()
df['ex'] = df.three_day - df.groupby('qn').three_day.transform('mean')
df['y_dd'] = df.three_day - df.groupby('i_cut').three_day.transform('mean')
qs = sorted(df.qn.unique())
IC = pd.DataFrame({f: ic_by_q(df, f) for f in CONT})          # 22 x 27
FI = pd.DataFrame({f: fifth(df, f) for f in CONT})


def report(name, tr):
    tr = pd.DataFrame(tr, columns=['qn', 'feature', 'side', 'net', 'net_ls'])
    pq = tr.groupby('qn').net.mean()
    pls = tr.groupby('qn').net_ls.first()
    t = pq.mean() / pq.std(ddof=1) * np.sqrt(len(pq))
    print(f'  {name:44s} OOS quarters {len(pq)}, trades {len(tr)}, avg net {tr.net.mean():+.2f}%, hit rate {(tr.net > 0).mean():.1%}, '
          f'quarters positive {(pq > 0).sum()}/{len(pq)}, quarter-mean t {t:+.2f} | long-short (fav - unfav fifth, 2 x cost) avg/quarter {pls.mean():+.2f}% '
          f'pos {(pls > 0).sum()}/{len(pls)}')
    return tr


print('== walk-forward: choose feature + direction on quarters < t only; trade the favourable fifth in quarter t (net of 0.17%)')
base = df.groupby('qn').three_day.mean() - COST
for t0 in [2, 4, 8, 14]:
    print(f' start quarter {t0} (baseline: all results long, same quarters: avg net {(df[df.qn >= t0].three_day.mean() - COST):+.2f}%, '
          f'hit {(df[df.qn >= t0].three_day > COST).mean():.1%})')
    for crit in ['absIC', 'abs_t']:
        tr = []
        picks = []
        for q in qs:
            if q < t0:
                continue
            past = IC.loc[[x for x in qs if x < q]]
            score = past.mean().abs() if crit == 'absIC' else (past.mean() / past.std(ddof=1) * np.sqrt(len(past))).abs()
            f = score.idxmax()
            sgn = np.sign(past[f].mean())
            fav = 5 if sgn > 0 else 1
            unf = 1 if fav == 5 else 5
            g = df[df.qn == q]
            fi = FI.loc[g.index, f]
            ls = g[fi == fav].three_day.mean() - g[fi == unf].three_day.mean() - 2 * COST
            for r in g[fi == fav].itertuples():
                tr.append((q, f, fav, r.three_day - COST, ls))
            picks.append(f'{q}:{f}{"+" if sgn > 0 else "-"}')
        out = report(f'continuous, pick by {crit}', tr)
        if crit == 'absIC':
            print('     picks:', ' '.join(picks))
            o = pd.DataFrame(tr, columns=['qn', 'feature', 'side', 'net', 'net_ls'])
            o14 = o[o.qn >= 14]
            print(f'     OOS in q14-21 only: trades {len(o14)}, avg net {o14.net.mean():+.2f}%, hit {(o14.net > 0).mean():.1%}')

# fixed choice decided on the first 14 quarters, applied to the last 8
past = IC.loc[[q for q in qs if q <= 13]]
f = past.mean().abs().idxmax(); s = np.sign(past[f].mean())
fav = 5 if s > 0 else 1
g = df[df.qn >= 14]
sel = g[FI.loc[g.index, f] == fav]
pq = sel.groupby('qn').three_day.mean() - COST
print(f'\n== choose once on q0-13 ({f}, mean IC {past[f].mean():+.3f}), trade it in q14-21: trades {len(sel)}, avg net '
      f'{sel.three_day.mean() - COST:+.2f}%, hit {(sel.three_day > COST).mean():.1%}, quarters positive {(pq > 0).sum()}/8; '
      f'without lag trades {sel[~sel.lag_trade].three_day.mean() - COST:+.2f}% (n {(~sel.lag_trade).sum()})')

print('\n== the T5 claim: long the bottom fifth of slope_sma_50 (chosen in-sample as the best of 59)')
fi = FI['slope_sma_50']
b = df[fi == 1].copy()
b['net'] = b.three_day - COST
pq = b.groupby('qn').net.mean()
print(f'  trades {len(b)}, avg net {b.net.mean():+.2f}%, hit {(b.net > 0).mean():.1%}, quarters positive {(pq > 0).sum()}/22, '
      f'quarter-mean t {pq.mean() / pq.std(ddof=1) * np.sqrt(22):+.2f}, trade-level t {b.net.mean() / b.net.std() * np.sqrt(len(b)):+.2f}')
bn = b[~b.lag_trade]
pqn = bn.groupby('qn').net.mean()
print(f'  without the 60 lag trades: {len(bn)} trades avg net {bn.net.mean():+.2f}%, hit {(bn.net > 0).mean():.1%}, quarters positive '
      f'{(pqn > 0).sum()}/22, quarter-mean t {pqn.mean() / pqn.std(ddof=1) * np.sqrt(22):+.2f}; q0-13 {bn[bn.qn <= 13].net.mean():+.2f}, q14-21 {bn[bn.qn >= 14].net.mean():+.2f}')
print(f'  bottom fifth market-adjusted: three_day - Nifty {b.xs_nifty.mean():+.2f}% (all results {df.xs_nifty.mean():+.2f}%), '
      f'minus same-cutoff-date mean of all results {b.y_dd.mean():+.2f}%; without lag trades {bn.y_dd.mean():+.2f}%')
print(f'  bottom fifth vs quarter mean (excess) {b.ex.mean():+.2f}%; without lag trades {bn.ex.mean():+.2f}%')
# selection bias: favourable fifth of every one of the 27 features
favs = []
for f in CONT:
    s = np.sign(IC[f].mean()); fav = 5 if s > 0 else 1
    favs.append((f, df[FI[f] == fav].three_day.mean() - COST, df[(FI[f] == fav) & ~df.lag_trade].three_day.mean() - COST))
favs = pd.DataFrame(favs, columns=['f', 'net', 'net_nolag']).sort_values('net', ascending=False)
print('  favourable fifth (side chosen in-sample) across the 27 features: net range', f'{favs.net.min():+.2f} .. {favs.net.max():+.2f}; '
      f'median {favs.net.median():+.2f}; without lag trades median {favs.net_nolag.median():+.2f}, max {favs.net_nolag.max():+.2f}')
print(favs.head(5).to_string(index=False))
# null for the best favourable fifth over 27 features with in-sample side choice (shuffle three_day within quarter)
rng = np.random.default_rng(3)
B = 2000
best = np.zeros(B)
y0 = df.three_day.values.copy()
grp = [df.index[df.qn == q].values for q in qs]
FIv = FI.values
for bb in range(B):
    y = y0.copy()
    for ix in grp:
        y[ix] = y0[rng.permutation(ix)]
    top = (np.where(FIv == 5, y[:, None], 0).sum(0) / (FIv == 5).sum(0))
    bot = (np.where(FIv == 1, y[:, None], 0).sum(0) / (FIv == 1).sum(0))
    best[bb] = np.maximum(top, bot).max()
obs = favs.net.max() + COST
print(f'  shuffle null for "best favourable fifth of 27, side chosen in-sample": mean {best.mean():+.2f}% gross, 95th pct {np.quantile(best, .95):+.2f}%; '
      f'observed {obs:+.2f}% -> p {(1 + (best >= obs).sum()) / (1 + B):.3f}')
# compare with plain past return and lag_pct fifths
for c in ['ret50', 'ret100', 'stock_21d_pct', 'lag_pct']:
    fc = fifth(df, c)
    x = df[fc == 1]
    print(f'  bottom fifth of {c:14s}: n {len(x)} avg net {x.three_day.mean() - COST:+.2f}%, without lag trades {x[~x.lag_trade].three_day.mean() - COST:+.2f}% '
          f'(lag trades inside {int(x.lag_trade.sum())}); overlap with slope_sma_50 bottom fifth {((fc == 1) & (fi == 1)).sum()}')
# after-close version (post hoc)
ac = df[(df.timing == 'After close')]
fa = fifth(ac, 'slope_sma_50')
x = ac[fa == 1]
print(f'  post hoc: after-close results only, bottom fifth of slope_sma_50: n {len(x)} avg net {x.three_day.mean() - COST:+.2f}%, '
      f'without lag trades {x[~x.lag_trade].three_day.mean() - COST:+.2f}%; q0-13 {x[x.qn <= 13].three_day.mean() - COST:+.2f}, q14-21 {x[x.qn >= 14].three_day.mean() - COST:+.2f}; '
      f'date-demeaned {x.y_dd.mean():+.2f}')
