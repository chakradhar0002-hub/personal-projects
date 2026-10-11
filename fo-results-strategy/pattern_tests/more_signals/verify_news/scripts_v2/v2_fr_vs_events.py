#!/usr/bin/env python3
"""Does the fr table's first results broadcast date equal events.csv results_date? (matters for RDCHG of qn 2-3,
whose last-year date came from fr). usage: python3 v2_fr_vs_events.py SCRATCH"""
import sqlite3, sys
import numpy as np, pandas as pd
SC = sys.argv[1]
con = sqlite3.connect(f'file:{SC}/report/nse_events.db?mode=ro', uri=True)
fr = pd.read_sql('select symbol, to_date, broadcast, consolidated from fr', con)
fr['b'] = pd.to_datetime(fr.broadcast, format='%d-%b-%Y %H:%M:%S', errors='coerce')
fr['to'] = pd.to_datetime(fr.to_date, format='%d-%b-%Y', errors='coerce')
fr = fr.dropna(subset=['b', 'to'])
ff = fr.groupby(['symbol', 'to']).b.min().rename('fr_first').reset_index()
ev = pd.read_csv(f'{SC}/sector_lab/data/events.csv', usecols=['symbol', 'qn', 'quarter_end', 'results_date', 'results_time'])
ev['to'] = pd.to_datetime(ev.quarter_end); ev['results_date'] = pd.to_datetime(ev.results_date)
x = ev.merge(ff, on=['symbol', 'to'], how='left')
x['diff'] = (x.fr_first.dt.normalize() - x.results_date).dt.days
print('events rows', len(x), 'with fr', x.fr_first.notna().sum())
g = x.groupby('qn')['diff']
print(pd.DataFrame({'n': g.count(), 'mean': g.mean().round(2), 'eq0': g.apply(lambda s: (s == 0).mean()).round(3),
                    'gt0': g.apply(lambda s: (s > 0).mean()).round(3), 'lt0': g.apply(lambda s: (s < 0).mean()).round(3),
                    'gt2': g.apply(lambda s: (s > 2).mean()).round(3), 'max': g.max()}).to_string())
# 2020 quarters in fr: distribution of (first broadcast - quarter end), vs 2021 events
for qe in ['2020-09-30', '2020-12-31', '2021-09-30', '2021-12-31']:
    s = ff[ff.to == qe]
    print(qe, 'fr first broadcast days after QE: median', (s.fr_first.dt.normalize() - pd.Timestamp(qe)).dt.days.median(), 'n', len(s))
for qn in [2, 3]:
    s = ev[ev.qn == qn]
    print('events qn', qn, 'results days after QE: median', (s.results_date - s.to).dt.days.median())
