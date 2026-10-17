#!/usr/bin/env python3
"""Three-day results sum (Day-1 + Result day + Day+1 daily returns) by sector and quarter, 22 seasons.

Universe: results of stocks that were in F&O at the time (events.csv in_fo == True).
three_day = ret_dm1 + ret_rd + ret_dp1 (sum of the three daily adjusted returns, as everywhere in this project);
the compounded return (close of Day+1 / close of the cutoff - 1) is also written for comparison.
Reads LAB_ROOT/sector_lab/data; writes OUT (default REPO_ROOT/results/sector_3day).
"""
import os
import numpy as np
import pandas as pd

LAB = os.environ.get('LAB_ROOT', 'lab')
OUT = os.environ.get('OUT', os.path.join(os.environ.get('REPO_ROOT', '.'), 'results', 'sector_3day'))
os.makedirs(OUT, exist_ok=True)
D = f'{LAB}/sector_lab/data'

SECTORS = {
    'Banks': ['Banks'],
    'NBFC & financials': ['Finance', 'Finance - Housing', 'Financial Institution', 'Insurance', 'Capital Markets'],
    'IT': ['Computers - Software'],
    'Pharma & healthcare': ['Pharmaceuticals'],
    'Auto & auto parts': ['Automobiles - 4 Wheelers', 'Automobiles - 2 And 3 Wheelers', 'Auto Ancillaries',
                          'Castings/Forgings'],
    'Capital goods & defence': ['Electrical Equipment', 'Engineering', 'Diesel Engines', 'Electronics - Industrial',
                                'Aerospace & Defence'],
    'Real estate & construction': ['Construction'],
    'Cement & building materials': ['Cement And Cement Products', 'Plastic And Plastic Products'],
    'Metals & mining': ['Steel And Steel Products', 'Aluminium', 'Metals', 'Mining'],
    'Oil & gas': ['Refineries', 'Oil Exploration/Production', 'Gas'],
    'Power': ['Power'],
    'FMCG': ['Food And Food Processing', 'Personal Care', 'Cigarettes', 'Brew/Distilleries', 'Diversified'],
    'Consumer durables & retail': ['Consumer Durables', 'Airconditioners', 'Gems Jewellery And Watches', 'Paints',
                                   'Retail', 'Textile Products'],
    'Chemicals & agro': ['Chemicals - Speciality', 'Pesticides And Agrochemicals', 'Textiles - Synthetic'],
    'Services, telecom & internet': ['Telecommunication - Services', 'Internet & E-commerce', 'Travel And Transport',
                                     'Shipping', 'Hotels', 'Trading'],
}
# 'Miscellaneous' holds hospitals, a cable maker and a retailer: place them by symbol
MISC = {'APOLLOHOSP': 'Pharma & healthcare', 'FORTIS': 'Pharma & healthcare', 'MAXHEALTH': 'Pharma & healthcare',
        'KEI': 'Capital goods & defence', 'TRENT': 'Consumer durables & retail'}
IND2SEC = {i: s for s, inds in SECTORS.items() for i in inds}

ev = pd.read_csv(f'{D}/events.csv')
ev = ev[ev.in_fo == True].copy()
ev['sector'] = ev.industry.map(IND2SEC)
m = ev.industry == 'Miscellaneous'
ev.loc[m, 'sector'] = ev.loc[m, 'symbol'].map(MISC)
assert ev.sector.notna().all(), ev[ev.sector.isna()][['symbol', 'industry']].drop_duplicates()

# checks: three_day is the sum of the three daily returns, and matches returns.csv
assert np.allclose(ev.three_day, ev.ret_dm1 + ev.ret_rd + ev.ret_dp1, equal_nan=True)
ret = pd.read_csv(f'{D}/returns.csv', index_col=0)
R = ret.to_numpy(float)
col = {s: j for j, s in enumerate(ret.columns)}
ok = ev.three_day.notna()
rs = np.array([np.nansum(R[[a, b, c], col[s]]) for s, a, b, c in
               zip(ev.symbol[ok], ev.i_m1[ok], ev.i_rd[ok], ev.i_p1[ok])])
diff = np.abs(rs - ev.three_day[ok].to_numpy())
print(f'check vs returns.csv: {ok.sum()} results, max abs diff {diff.max():.2e}')
cp = np.array([np.prod(1 + np.nan_to_num(R[[a, b, c], col[s]])) - 1 for s, a, b, c in
               zip(ev.symbol[ok], ev.i_m1[ok], ev.i_rd[ok], ev.i_p1[ok])])
ev.loc[ok, 'three_day_compounded'] = cp

ev = ev[ok].copy()
ev['td'] = ev.three_day * 100
ev['tdc'] = ev.three_day_compounded * 100
qlab = ev.groupby('qn').agg(period=('period', 'first'), quarter=('quarter', 'first'))
order = list(SECTORS)

avg = ev.pivot_table(index='qn', columns='sector', values='td', aggfunc='mean')[order]
cnt = ev.pivot_table(index='qn', columns='sector', values='td', aggfunc='size')[order].fillna(0).astype(int)
tot = ev.pivot_table(index='qn', columns='sector', values='td', aggfunc='sum')[order]
allq = ev.groupby('qn').td.agg(['mean', 'size', 'sum'])

rows = []
for s in order:
    g = ev[ev.sector == s]
    qa = g.groupby('qn').td.mean()
    best, worst = qa.idxmax(), qa.idxmin()
    rows.append(dict(sector=s, stocks=g.symbol.nunique(), results=len(g), avg=g.td.mean(), avg_compounded=g.tdc.mean(),
                     median=g.td.median(), up_pct=(g.td > 0).mean() * 100,
                     q_with=len(qa), q_pos=int((qa > 0).sum()),
                     first14=g[g.qn <= 13].td.mean(), last8=g[g.qn >= 14].td.mean(),
                     best_q=f"{qlab.period[best]} ({qa[best]:+.2f}%)", worst_q=f"{qlab.period[worst]} ({qa[worst]:+.2f}%)"))
summ = pd.DataFrame(rows)
g = ev
qa = g.groupby('qn').td.mean()
summ.loc[len(summ)] = dict(sector='All F&O results', stocks=g.symbol.nunique(), results=len(g), avg=g.td.mean(),
                           avg_compounded=g.tdc.mean(), median=g.td.median(), up_pct=(g.td > 0).mean() * 100,
                           q_with=len(qa), q_pos=int((qa > 0).sum()), first14=g[g.qn <= 13].td.mean(),
                           last8=g[g.qn >= 14].td.mean(),
                           best_q=f"{qlab.period[qa.idxmax()]} ({qa.max():+.2f}%)",
                           worst_q=f"{qlab.period[qa.idxmin()]} ({qa.min():+.2f}%)")

def with_labels(df):
    d = df.copy()
    d.insert(0, 'quarter', qlab.quarter)
    d.insert(0, 'results_for', qlab.period)
    return d

with_labels(avg.assign(all_results=allq['mean'])).round(3).to_csv(f'{OUT}/avg_3day_by_sector_quarter.csv')
with_labels(cnt.assign(all_results=allq['size'])).to_csv(f'{OUT}/count_by_sector_quarter.csv')
with_labels(tot.assign(all_results=allq['sum'])).round(3).to_csv(f'{OUT}/sum_3day_by_sector_quarter.csv')
summ.round(3).to_csv(f'{OUT}/sector_summary.csv', index=False)
ev[['symbol', 'company', 'quarter', 'qn', 'period', 'results_date', 'timing', 'industry', 'sector',
    'ret_dm1', 'ret_rd', 'ret_dp1', 'three_day', 'three_day_compounded']].to_csv(f'{OUT}/results_3day.csv', index=False)
pd.Series({s: ', '.join(SECTORS[s] + [k for k, v in MISC.items() if v == s]) for s in order},
          name='industries').to_csv(f'{OUT}/sector_map.csv')

# markdown tables for the doc
SHORT = {'Banks': 'Banks', 'NBFC & financials': 'NBFC/Fin', 'IT': 'IT', 'Pharma & healthcare': 'Pharma',
         'Auto & auto parts': 'Auto', 'Capital goods & defence': 'Cap goods', 'Real estate & construction': 'Realty',
         'Cement & building materials': 'Cement', 'Metals & mining': 'Metals', 'Oil & gas': 'Oil & gas',
         'Power': 'Power', 'FMCG': 'FMCG', 'Consumer durables & retail': 'Cons dur', 'Chemicals & agro': 'Chem/agro',
         'Services, telecom & internet': 'Services'}

def md(df, fmt, allcol):
    hdr = ['Results for', 'Quarter'] + [SHORT[s] for s in order] + ['All']
    out = ['| ' + ' | '.join(hdr) + ' |', '|---|---|' + '---:|' * (len(order) + 1)]
    for q in df.index:
        cells = [qlab.period[q], qlab.quarter[q]] + [fmt(df.loc[q, s], cnt.loc[q, s]) for s in order] + [fmt(allcol[q], allq['size'][q])]
        out.append('| ' + ' | '.join(cells) + ' |')
    return '\n'.join(out)

f_avg = lambda v, n: '-' if n == 0 else f'{v:+.2f}'
f_cnt = lambda v, n: f'{int(n)}'
f_sum = lambda v, n: '-' if n == 0 else f'{v:+.1f}'
open(f'{OUT}/table_avg.md', 'w').write(md(avg, f_avg, allq['mean']))
open(f'{OUT}/table_count.md', 'w').write(md(cnt, f_cnt, allq['size']))
open(f'{OUT}/table_sum.md', 'w').write(md(tot, f_sum, allq['sum']))
s_md = ['| Sector | Stocks | Results | Avg 3-day sum | Median | Up | Quarters positive | First 14 q / last 8 q | Best quarter | Worst quarter |',
        '|---|---:|---:|---:|---:|---:|---:|---|---|---|']
for _, r in summ.iterrows():
    s_md.append(f"| {r.sector} | {r.stocks} | {r.results:,} | {r.avg:+.2f}% | {r['median']:+.2f}% | {r.up_pct:.0f}% | "
                f"{r.q_pos} of {r.q_with} | {r.first14:+.2f}% / {r.last8:+.2f}% | {r.best_q} | {r.worst_q} |")
open(f'{OUT}/table_summary.md', 'w').write('\n'.join(s_md))
print(summ.round(2).to_string())
print('compounded vs summed, all results:', round(ev.tdc.mean(), 3), round(ev.td.mean(), 3))
