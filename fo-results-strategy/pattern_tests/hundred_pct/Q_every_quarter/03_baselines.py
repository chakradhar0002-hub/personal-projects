"""
03_baselines.py -- how many quarters are positive for 'buy everything' and broad filters (no search).
Universe in_fo (main) and all 4,460 (secondary).  3-day and TP exit, gross and after 0.17% costs.
Filters: all, short all, market-cap thirds within each season (by log_mcap rank among that season's
results), top 50 by market cap in the season, each sector index, fin_type, fiscal quarter.
Output: out/baselines.csv (percent units).
"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qengine as E

rows = []


def stats(name, m, y, qn, sign=1):
    p = sign * y[m]; q = qn[m]
    if len(p) == 0:
        return None
    qa = pd.Series(p).groupby(q).mean()
    d = {'filter': name, 'trades': len(p), 'win_rate_pct': 100 * (p > 0).mean(),
         'win_rate_net_pct': 100 * (p > E.COST).mean(), 'avg_pct': 100 * p.mean(),
         'quarters_with_picks': len(qa), 'quarters_pos': int((qa > 0).sum()), 'quarters_pos_net': int((qa > E.COST).sum()),
         'first14_with_picks': int((qa.index < 14).sum()), 'first14_pos': int((qa[qa.index < 14] > 0).sum()),
         'last8_with_picks': int((qa.index >= 14).sum()), 'last8_pos': int((qa[qa.index >= 14] > 0).sum()),
         'worst_quarter_pct': 100 * qa.min(), 'best_quarter_pct': 100 * qa.max()}
    return d


for uni in ('fo', 'all'):
    df = E.load(uni)
    qn = df.qn.values
    rk = df.groupby('qn').log_mcap.rank(pct=True).values
    rk50 = df.groupby('qn').log_mcap.rank(ascending=False).values
    filt = {'ALL': np.ones(len(df), bool),
            'mcap top third (season)': rk > 2 / 3, 'mcap middle third': (rk > 1 / 3) & (rk <= 2 / 3),
            'mcap bottom third': rk <= 1 / 3, 'mcap top 50 in season': rk50 <= 50}
    for c in ('sector_index', 'fin_type', 'fq'):
        for v, n in df[c].astype(str).value_counts().items():
            if n >= 30 and v != 'nan':
                filt[f'{c} == {v}'] = df[c].astype(str).values == v
    for name, m in filt.items():
        for ex, col in (('3day', 'three_day'), ('tp', 'tp3')):
            d = stats(name, m, df[col].values, qn)
            if d:
                d.update(universe=uni, exit=ex, direction='long'); rows.append(d)
        for ex, col in (('3day', 'three_day'), ('tp', 'tp3s')):
            sg = -1 if ex == '3day' else 1
            d = stats(name, m, df[col].values, qn, sign=sg)
            if d:
                d.update(universe=uni, exit=ex, direction='short'); rows.append(d)
B = pd.DataFrame(rows)
cols = ['universe', 'direction', 'exit', 'filter', 'trades', 'quarters_with_picks', 'quarters_pos', 'quarters_pos_net',
        'first14_with_picks', 'first14_pos', 'last8_with_picks', 'last8_pos', 'avg_pct', 'win_rate_pct',
        'win_rate_net_pct', 'worst_quarter_pct', 'best_quarter_pct']
B = B[cols]
B.to_csv(os.path.join(E.HERE, 'out', 'baselines.csv'), index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 300)
print(B[(B.universe == 'fo')].round(2).to_string(index=False))
print(B[(B.universe == 'all') & (B['filter'] == 'ALL')].round(2).to_string(index=False))
# how often is a broad filter positive in all quarters with picks?
fo = B[B.universe == 'fo']
print('broad filters (fo) with every quarter positive:',
      fo[fo.quarters_pos == fo.quarters_with_picks][['direction', 'exit', 'filter', 'trades', 'quarters_with_picks']].to_string(index=False))
print('max quarters positive among broad filters with >= 16 quarters with picks:')
x = fo[fo.quarters_with_picks >= 16].sort_values('quarters_pos', ascending=False).head(10)
print(x[['direction', 'exit', 'filter', 'trades', 'quarters_with_picks', 'quarters_pos', 'avg_pct']].round(2).to_string(index=False))
