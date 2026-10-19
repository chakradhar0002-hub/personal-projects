"""Skeptic prep: independent price-derived controls at each result cutoff and placebo day.
Writes ctrl_events.csv, ctrl_placebo.csv.gz to SK_CACHE (default LAB_ROOT/ema_sma_skeptic_cache).
"""
import os
import numpy as np
import pandas as pd

S = os.path.dirname(os.path.abspath(__file__))
# control features (prep.py output) are regenerated, not committed
CACHE = os.environ.get('SK_CACHE', os.path.join(os.environ.get('LAB_ROOT', 'lab'), 'ema_sma_skeptic_cache'))
os.makedirs(CACHE, exist_ok=True)
LAB = os.environ.get('LAB_ROOT', 'lab')
TA = os.environ.get('TA_BUILD', os.path.join(os.environ.get('LAB_ROOT', 'lab'), 'ta', 'build'))
REPO = os.environ.get('REPO_ROOT', '.')
PACK = os.path.join(LAB, 'sector_lab', 'data')

px = pd.read_csv(os.path.join(TA, 'adjusted_ohlcv.csv.gz'))
sess = pd.read_csv(os.path.join(PACK, 'sessions.csv'))
dmap = dict(zip(sess.day, sess.i))
px['i'] = px.day.map(dmap)
assert px.i.notna().all()
px['c'] = px.raw_close * px.price_factor
px = px[px.c.notna()].sort_values(['symbol', 'i'])

ev = pd.read_csv(os.path.join(PACK, 'events.csv'))
ev = ev[ev.in_fo == True][['symbol', 'qn', 'i_cut']].copy()
pl = pd.read_csv(os.path.join(REPO, 'results', 'ema_sma_3day', 'features_placebo.csv.gz'),
                 usecols=['symbol', 'i', 'qn'])

need = {}
for s, g in pd.concat([ev.rename(columns={'i_cut': 'i'})[['symbol', 'i']], pl[['symbol', 'i']]]).groupby('symbol'):
    need[s] = set(g.i)

rows = []
for s, g in px.groupby('symbol'):
    if s not in need:
        continue
    c = g.c.values
    ii = g.i.values.astype(int)
    pos = {v: k for k, v in enumerate(ii)}
    cs = np.concatenate([[0.0], np.cumsum(c)])
    for i in need[s]:
        k = pos.get(i)
        if k is None:
            rows.append((s, i) + (np.nan,) * 7)
            continue
        def ret(n):
            return (c[k] / c[k - n] - 1) * 100 if k >= n else np.nan
        def smaat(j, n):
            return (cs[j + 1] - cs[j + 1 - n]) / n if j + 1 >= n else np.nan
        sma50 = smaat(k, 50)
        sma50_5 = smaat(k - 5, 50) if k >= 5 else np.nan
        sma100 = smaat(k, 100)
        rows.append((s, i, ret(21), ret(50), ret(100), ret(250) if k >= 250 else np.nan,
                     (sma50 / sma50_5 - 1) * 100, (c[k] / sma100 - 1) * 100, (c[k] / sma50 - 1) * 100))
ctrl = pd.DataFrame(rows, columns=['symbol', 'i', 'ret21', 'ret50', 'ret100', 'ret250',
                                   'my_slope_sma_50', 'my_dist_sma_100', 'my_dist_sma_50'])

# Nifty 50 features at session i and Nifty 3-day return over i+1..i+3 (sum of daily returns, same as three_day)
ix = pd.read_csv(os.path.join(PACK, 'index_close.csv'), usecols=['day', 'Nifty 50'])
ix['i'] = ix.day.map(dmap)
ix = ix[ix.i.notna()].sort_values('i')
ix['i'] = ix.i.astype(int)
ix = ix[ix['Nifty 50'].notna()].reset_index(drop=True)
nc = ix['Nifty 50'].values
nr = np.concatenate([[np.nan], nc[1:] / nc[:-1] - 1]) * 100
sma50n = pd.Series(nc).rolling(50).mean().values
nf = pd.DataFrame({'i': ix.i.values,
                   'nifty_slope_sma_50': (sma50n / np.concatenate([[np.nan] * 5, sma50n[:-5]]) - 1) * 100,
                   'nifty_dist_sma_50': (nc / sma50n - 1) * 100,
                   'nifty_ret50': (nc / np.concatenate([[np.nan] * 50, nc[:-50]]) - 1) * 100})
# 3-day forward: daily returns on sessions i+1..i+3 of the session grid (index trades every session)
assert (np.diff(ix.i.values) == 1).all(), 'Nifty has gaps on the session grid'
fwd = np.full(len(nc), np.nan)
fwd[:-3] = nr[1:-2] + nr[2:-1] + nr[3:]
nf['nifty_fwd3'] = fwd

ev = ev.rename(columns={'i_cut': 'i'}).merge(ctrl, on=['symbol', 'i'], how='left').merge(nf, on='i', how='left')
pl = pl.merge(ctrl, on=['symbol', 'i'], how='left').merge(nf, on='i', how='left')
ev.to_csv(os.path.join(CACHE, 'ctrl_events.csv'), index=False)
pl.to_csv(os.path.join(CACHE, 'ctrl_placebo.csv.gz'), index=False, float_format='%.8g')
print('events', len(ev), ev.isna().sum().to_dict())
print('placebo', len(pl), pl.isna().sum().to_dict())
