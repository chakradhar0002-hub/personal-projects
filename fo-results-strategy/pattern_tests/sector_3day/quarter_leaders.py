"""Each quarter: all-F&O average three-day sum, sectors up, best and worst sector.

Reads results_3day.csv written by sector_quarter_table.py; writes quarter_leaders.csv and table_quarter_leaders.md
in OUT (default REPO_ROOT/results/sector_3day). Best and worst count only sectors with at least MIN_N results in
that quarter.
"""
import os
import pandas as pd

OUT = os.environ.get('OUT', os.path.join(os.environ.get('REPO_ROOT', '.'), 'results', 'sector_3day'))
MIN_N = 4
SHORT = {'Banks': 'Banks', 'NBFC & financials': 'NBFC/Fin', 'IT': 'IT', 'Pharma & healthcare': 'Pharma',
         'Auto & auto parts': 'Auto', 'Capital goods & defence': 'Cap goods', 'Real estate & construction': 'Realty',
         'Cement & building materials': 'Cement', 'Metals & mining': 'Metals', 'Oil & gas': 'Oil & gas',
         'Power': 'Power', 'FMCG': 'FMCG', 'Consumer durables & retail': 'Cons dur', 'Chemicals & agro': 'Chem/agro',
         'Services, telecom & internet': 'Services'}

ev = pd.read_csv(f'{OUT}/results_3day.csv')
ev['td'] = ev.three_day * 100
rows = []
for qn, g in ev.groupby('qn'):
    s = g.groupby('sector').td.agg(['mean', 'size'])
    big = s[s['size'] >= MIN_N]
    best, worst = big['mean'].idxmax(), big['mean'].idxmin()
    rows.append(dict(qn=qn, period=g.period.iloc[0], quarter=g.quarter.iloc[0], results=len(g),
                     avg=g.td.mean(), up_pct=(g.td > 0).mean() * 100,
                     sectors_up=int((s['mean'] > 0).sum()), sectors=len(s),
                     best=best, best_avg=big.loc[best, 'mean'], best_n=int(big.loc[best, 'size']),
                     worst=worst, worst_avg=big.loc[worst, 'mean'], worst_n=int(big.loc[worst, 'size']),
                     auto_rank=int(big['mean'].rank(ascending=False)['Auto & auto parts']), ranked=len(big)))
q = pd.DataFrame(rows)
q.round(3).to_csv(f'{OUT}/quarter_leaders.csv', index=False)

out = ['| Results for | Quarter | Results | All F&O avg | Results up | Sectors up | Best sector | Worst sector | Auto rank |',
       '|---|---|---:|---:|---:|---:|---|---|---:|']
for _, r in q.iterrows():
    out.append(f'| {r.period} | {r.quarter} | {r.results} | {r.avg:+.2f}% | {r.up_pct:.0f}% | {r.sectors_up} of {r.sectors} | '
               f'{SHORT[r.best]} {r.best_avg:+.2f}% ({r.best_n}) | {SHORT[r.worst]} {r.worst_avg:+.2f}% ({r.worst_n}) | '
               f'{r.auto_rank} of {r.ranked} |')
open(f'{OUT}/table_quarter_leaders.md', 'w').write('\n'.join(out))
print('\n'.join(out))
print('best counts:', q.best.map(SHORT).value_counts().to_dict())
print('worst counts:', q.worst.map(SHORT).value_counts().to_dict())
