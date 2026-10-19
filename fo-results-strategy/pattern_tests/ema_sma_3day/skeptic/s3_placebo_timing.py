"""Skeptic 3: market-timing confound (results and placebo), specificity to results, result-day timing, components."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
from scipy import stats
from common import *

df = load_events()
TOP = ['slope_sma_50', 'slope_ema_20', 'dist_sma_100', 'slope_ema_50', 'dist_ema_50', 'dist_ema_100', 'dist_sma_50',
       'dist_sma_20', 'dist_ema_200']

print('== check: events nifty_3d vs my Nifty sum of daily returns i+1..i+3:',
      f'mean abs diff {np.abs(100 * df.nifty_3d - df.nifty_fwd3).mean():.3f} pp, corr {np.corrcoef(df.nifty_3d, df.nifty_fwd3)[0, 1]:.4f}')

# date-demeaned outcome for results: subtract mean three_day of results with the same cutoff session
g = df.groupby('i_cut').three_day
df['n_same_cut'] = g.transform('size')
df['y_dd'] = df.three_day - g.transform('mean')
dd = df[df.n_same_cut >= 2].copy()
print(f'results sharing a cutoff session with >= 1 other result: {len(dd)} of {len(df)}; distinct cutoff sessions '
      f'{df.i_cut.nunique()} (per quarter median {df.groupby("qn").i_cut.nunique().median():.0f})')
print('mean within-quarter Spearman of feature with Nifty dist from its SMA50 at the cutoff:')
print('   ' + ' '.join(f'{f}={np.mean([stats.spearmanr(x[f], x.nifty_dist_sma_50)[0] for _, x in df.groupby("qn")]):+.2f}' for f in TOP))

print('\n== results: IC raw / minus Nifty / cutoff-date demeaned (only results sharing a cutoff) ')
rows = {}
for f in TOP:
    r = {}
    for name, d, y in [('raw', df, 'three_day'), ('xs_nifty', df, 'xs_nifty'), ('raw_same_sample', dd, 'three_day'),
                       ('date_demeaned', dd, 'y_dd')]:
        ics = ic_by_q(d, f, y)
        m, t, pos, n = summ(ics)
        _, p, _ = perm_ic(d, f, y, B=3000)
        r[name] = (m, t, pos, n, p)
    rows[f] = r
    print(f'  {f:14s} ' + ' | '.join(f'{k} {v[0]:+.3f} (t {v[1]:+.2f}, {v[2]}/{v[3]}, p {fpv(v[4])})' for k, v in r.items()))

# ------------------------------------------------------------------------- placebo
pl = pd.read_csv(os.path.join(RES, 'features_placebo.csv.gz'), usecols=['symbol', 'i', 'qn', 'three_day'] + TOP)
cp = pd.read_csv(os.path.join(CACHE, 'ctrl_placebo.csv.gz'), usecols=['symbol', 'i', 'nifty_fwd3', 'nifty_dist_sma_50'])
pl = pl.merge(cp, on=['symbol', 'i'], how='left')
pl['xs_nifty'] = pl.three_day - pl.nifty_fwd3
pl['y_dd'] = pl.three_day - pl.groupby('i').three_day.transform('mean')
print(f'\n== placebo: {len(pl)} stock-days, {pl.i.nunique()} days; IC by season (raw = as the build / minus Nifty / day-demeaned)')
for f in TOP:
    out = []
    res = {}
    for y in ['three_day', 'xs_nifty', 'y_dd']:
        ics = ic_by_q(pl, f, y)
        res[y] = ics
        out.append(f'{y} {ics.mean():+.3f} (t {summ(ics)[1]:+.2f}, {summ(ics)[2]}/22)')
    # results minus placebo on the market-clean basis
    rr = ic_by_q(df, f, 'xs_nifty'); diff = rr - res['xs_nifty']
    rd = ic_by_q(dd, f, 'y_dd'); diff2 = rd - res['y_dd']
    out.append(f'res-pl (xs_nifty) {diff.mean():+.3f} p {stats.ttest_1samp(diff, 0).pvalue:.3f}')
    out.append(f'res-pl (demeaned) {diff2.mean():+.3f} p {stats.ttest_1samp(diff2, 0).pvalue:.3f}')
    print(f'  {f:14s} ' + ' | '.join(out))
ics = ic_by_q(pl, 'nifty_dist_sma_50', 'three_day')
print(f'  placebo: Nifty dist from SMA50 (market-level) vs three_day: mean IC {ics.mean():+.3f} (t {summ(ics)[1]:+.2f}, {summ(ics)[2]}/22)')
# per-day cross-sectional IC on placebo (pure cross-section), averaged by season
print('  placebo pure cross-section (Spearman inside each day, averaged over days):')
for f in TOP[:6]:
    dic = pl.groupby('i').apply(lambda x: stats.spearmanr(x[f], x.three_day)[0] if len(x) >= 20 else np.nan).dropna()
    print(f'     {f:14s} mean daily IC {dic.mean():+.4f} over {len(dic)} days (naive t {dic.mean() / dic.std() * np.sqrt(len(dic)):+.2f}; overlapping windows)')

# ------------------------------------------------------------------------- Nifty time-series check
nf = pd.read_csv(os.path.join(CACHE, 'ctrl_placebo.csv.gz'), usecols=['i', 'nifty_fwd3', 'nifty_dist_sma_50']).drop_duplicates('i')
nf = nf[(nf.i >= 1337)]
print(f'\n== Nifty itself, every session from the first results season ({len(nf)} sessions): Spearman(dist from SMA50, next-3-day return) '
      f'{stats.spearmanr(nf.nifty_dist_sma_50, nf.nifty_fwd3, nan_policy="omit")[0]:+.3f} (overlapping windows)')
e1 = df.drop_duplicates('i_cut')
print(f'   on the {len(e1)} results cutoff sessions only: {stats.spearmanr(e1.nifty_dist_sma_50, e1.nifty_fwd3)[0]:+.3f}')

# ------------------------------------------------------------------------- timing and components
print('\n== by result timing (mean IC over quarters; components; reaction day = d2 during market, d3 after close / non-trading)')
df['react'] = np.where(df.timing == 'During market', df.d2, df.d3)
df['pre'] = df.three_day - df.react
for f in ['slope_sma_50', 'slope_ema_20', 'dist_sma_100', 'dist_ema_50']:
    print(f'  {f}')
    for tname, d in [('all', df), ('After close', df[df.timing == 'After close']), ('During market', df[df.timing == 'During market']),
                     ('Non-trading day', df[df.timing == 'Non-trading day'])]:
        parts = []
        for y in ['three_day', 'd1', 'd2', 'd3', 'react', 'pre', 'xs_nifty']:
            ics = ic_by_q(d, f, y)
            parts.append(f'{y} {ics.mean():+.3f}')
        _, p, _ = perm_ic(d, f, 'three_day', B=2000)
        _, pr, _ = perm_ic(d, f, 'react', B=2000)
        print(f'    {tname:15s} n={len(d):4d} ' + ' '.join(parts) + f' | p(three_day) {fpv(p)} p(react) {fpv(pr)}')
# difference between timing groups
for f in ['slope_sma_50', 'slope_ema_20']:
    a = ic_by_q(df[df.timing == 'After close'], f); b = ic_by_q(df[df.timing == 'During market'], f)
    d = (a - b).dropna()
    print(f'  {f}: after close minus during market IC {d.mean():+.3f}, paired t p {stats.ttest_1samp(d, 0).pvalue:.3f} ({len(d)} q)')
