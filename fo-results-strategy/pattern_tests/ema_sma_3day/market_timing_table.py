"""Is the EMA/SMA link a stock effect or a market-timing effect?

For the strongest continuous features, mean quarterly Spearman IC against (a) the raw three-day sum, (b) the three-day
sum minus Nifty 50's three-day sum on the same sessions, and (c) the three-day sum minus the average of all results with
the same cutoff session (results that share a cutoff with at least one other). p: 2,000 within-quarter shuffles of the
feature, two-sided. Also the IC of Nifty 50's own distance from its 50-day SMA at the cutoff (the same value for every
result that day). Writes table_market_timing.md and market_timing.csv in OUT.
"""
import os
import numpy as np
import pandas as pd

LAB = os.environ.get('LAB_ROOT', 'lab')
OUT = os.environ.get('OUT', os.path.join(os.environ.get('REPO_ROOT', '.'), 'results', 'ema_sma_3day'))
PACK = os.path.join(LAB, 'sector_lab', 'data')
FEATS = ['slope_sma_50', 'slope_ema_20', 'dist_sma_100', 'slope_ema_50', 'dist_ema_50', 'dist_sma_50', 'dist_ema_20',
         'dist_sma_20', 'dist_sma_200', 'dist_ema_200']
NAMES = {'slope_sma_50': 'SMA 50 slope over 5 days', 'slope_ema_20': 'EMA 20 slope over 5 days',
         'dist_sma_100': 'Close vs SMA 100', 'slope_ema_50': 'EMA 50 slope over 5 days', 'dist_ema_50': 'Close vs EMA 50',
         'dist_sma_50': 'Close vs SMA 50', 'dist_ema_20': 'Close vs EMA 20', 'dist_sma_20': 'Close vs SMA 20',
         'dist_sma_200': 'Close vs SMA 200', 'dist_ema_200': 'Close vs EMA 200', 'nifty_dist_sma_50': 'Nifty 50 vs its SMA 50'}
B, SEED = 2000, 20261019

fe = pd.read_csv(f'{OUT}/features_events.csv')
ev = pd.read_csv(f'{PACK}/events.csv')
ev = ev[ev.in_fo == True][['symbol', 'qn', 'i_cut', 'nifty_3d']]
d = fe.merge(ev, on=['symbol', 'qn'], how='left', validate='1:1')
assert len(d) == 3278 and d.nifty_3d.notna().all()
nif = pd.read_csv(f'{PACK}/index_close.csv', index_col=0)['Nifty 50'].to_numpy(float)
sma50 = pd.Series(nif).rolling(50, min_periods=50).mean().to_numpy()
d['nifty_dist_sma_50'] = (nif[d.i_cut] / sma50[d.i_cut] - 1) * 100
d['y_raw'] = d.three_day
d['y_nifty'] = d.three_day - d.nifty_3d * 100
g = d.groupby('i_cut').three_day
d['n_cut'] = g.transform('size')
d['y_cut'] = np.where(d.n_cut >= 2, d.three_day - g.transform('mean'), np.nan)

rng = np.random.default_rng(SEED)
def rank(a):
    return pd.Series(a).rank().to_numpy()
def mean_ic(df, f, y, perms=0):
    qs, obs, null = [], [], np.zeros(perms)
    for q, s in df[[f, y, 'qn']].dropna().groupby('qn'):
        if len(s) < 5:
            continue
        x, yy = rank(s[f].to_numpy()), rank(s[y].to_numpy())
        x, yy = x - x.mean(), yy - yy.mean()
        den = np.sqrt((x ** 2).sum() * (yy ** 2).sum())
        obs.append((x * yy).sum() / den if den > 0 else 0.0)
        if perms:
            P = np.array([rng.permutation(x) for _ in range(perms)])
            null += (P @ yy) / den if den > 0 else 0.0
        qs.append(q)
    obs = np.array(obs)
    if perms:
        null /= len(obs)
        p = (1 + np.sum(np.abs(null - null.mean()) >= abs(obs.mean() - null.mean()) - 1e-12)) / (perms + 1)
    else:
        p = np.nan
    return obs.mean(), (obs > 0).sum(), len(obs), p

rows = []
for f in FEATS + ['nifty_dist_sma_50']:
    r = {'feature': f}
    for y in ('y_raw', 'y_nifty', 'y_cut'):
        if f == 'nifty_dist_sma_50' and y == 'y_cut':
            r[f'{y}_ic'], r[f'{y}_pos'], r[f'{y}_nq'], r[f'{y}_p'] = np.nan, np.nan, np.nan, np.nan
            continue
        m, pos, nq, p = mean_ic(d, f, y, B)
        r[f'{y}_ic'], r[f'{y}_pos'], r[f'{y}_nq'], r[f'{y}_p'] = m, pos, nq, p
    rows.append(r)
R = pd.DataFrame(rows)
R.round(4).to_csv(f'{OUT}/market_timing.csv', index=False)

fic = lambda v: '-' if pd.isna(v) else f'{v:+.3f}'
fp = lambda v: '-' if pd.isna(v) else ('<0.001' if v < 0.001 else f'{v:.3f}')
md = ['| Feature at the cutoff | Raw three-day: IC (p) | Minus Nifty 50 same days: IC (p) | Minus same-cutoff results: IC (p) |',
      '|---|---:|---:|---:|']
for r in R.itertuples():
    md.append(f'| {NAMES[r.feature]} | {fic(r.y_raw_ic)} ({fp(r.y_raw_p)}) | {fic(r.y_nifty_ic)} ({fp(r.y_nifty_p)}) | '
              f'{fic(r.y_cut_ic)} ({fp(r.y_cut_p)}) |')
md += ['', f'IC: Spearman correlation inside each quarter, averaged over the 22 quarters; p from {B:,} within-quarter '
       'shuffles of the feature (two-sided). Minus same-cutoff results: each result minus the average of all results '
       f'with the same cutoff session ({int((d.n_cut >= 2).sum()):,} results share a cutoff with at least one other). '
       'Nifty 50 vs its SMA 50 is the same value for every result on a cutoff day, so it measures market timing only.']
open(f'{OUT}/table_market_timing.md', 'w').write('\n'.join(md) + '\n')
print('\n'.join(md))
