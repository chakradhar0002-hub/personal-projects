"""Skeptic 7: how much of the feature variation is between cutoff dates (is date-demeaning over-controlling?);
sector-adjusted outcome."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
from common import *

df = load_events()
ev = pd.read_csv(os.path.join(PACK, 'events.csv'))
ev = ev[ev.in_fo == True][['symbol', 'qn', 'excess_sector', 'sector_3d']]
df = df.merge(ev, on=['symbol', 'qn'])
df['xs_sector'] = 100 * df.excess_sector
rng = np.random.default_rng(4)
for f in ['slope_sma_50', 'dist_sma_100', 'slope_ema_20', 'dist_ema_50']:
    df['r'] = df.groupby('qn')[f].rank(pct=True)
    def r2(d):
        tot = ((d.r - d.groupby('qn').r.transform('mean')) ** 2).sum()
        btw = ((d.groupby('i_cut').r.transform('mean') - d.groupby('qn').r.transform('mean')) ** 2).sum()
        return btw / tot
    obs = r2(df)
    sims = []
    for _ in range(200):
        d = df.copy()
        d['i_cut'] = d.groupby('qn').i_cut.transform(lambda s: rng.permutation(s.values))
        sims.append(r2(d))
    print(f'{f:14s} share of within-quarter rank variance between cutoff dates {obs:.1%} (random date labels {np.mean(sims):.1%})')
for f in ['slope_sma_50', 'slope_ema_20', 'dist_sma_100', 'slope_ema_50', 'dist_ema_50']:
    m, p, _ = perm_ic(df, f, 'xs_sector', B=3000)
    ics = ic_by_q(df, f, 'xs_sector')
    print(f'{f:14s} vs three_day minus sector index: mean IC {m:+.3f} t {summ(ics)[1]:+.2f} pos {summ(ics)[2]}/22 p {fpv(p)}')
