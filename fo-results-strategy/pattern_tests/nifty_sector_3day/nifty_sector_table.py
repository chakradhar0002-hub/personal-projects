#!/usr/bin/env python3
"""Three-day results sum (Day-1 + Result day + Day+1 daily returns) by NSE's Nifty index sector and quarter, 22 seasons.

Same study as pattern_tests/sector_3day/sector_quarter_table.py, but the sector of each stock is NSE's own index sector
classification (the "Industry" column of NSE's Nifty 500 constituent list, ind_nifty500list.csv) instead of the
hand-made 15 sectors. All 206 F&O stocks are in the Nifty 500 list; 18 NSE sectors occur among them.
Caveat: the list is today's constituents with today's classification (look-ahead / survivorship, same as the stock
universe, which is today's F&O list).

Universe: results of stocks that were in F&O at the time (events.csv in_fo == True), 3,278 results.
three_day = ret_dm1 + ret_rd + ret_dp1 (sum of the three daily returns, not compounded).
Reads LAB_ROOT/sector_lab/data, LISTS_DIR/ind_nifty500list.csv (read as data only) and the custom-sector labels in
REPO_ROOT/results/sector_3day/results_3day.csv; writes OUT (default REPO_ROOT/results/nifty_sector_3day).
Also writes the quarter leaders table (best / worst sector each quarter) and the NSE-sector x custom-sector crosswalk.
"""
import os
import numpy as np
import pandas as pd

REPO = os.environ.get('REPO_ROOT', '.')
LAB = os.environ.get('LAB_ROOT', 'lab')
LISTS = os.environ.get('LISTS_DIR', 'lists')
OUT = os.environ.get('OUT', os.path.join(REPO, 'results', 'nifty_sector_3day'))
OLD = os.path.join(REPO, 'results', 'sector_3day', 'results_3day.csv')
os.makedirs(OUT, exist_ok=True)
D = f'{LAB}/sector_lab/data'
MIN_N = 4          # quarter leaders: best / worst only among sectors with at least this many results that quarter
AUTO = 'Automobile and Auto Components'

SHORT = {'Financial Services': 'Fin services', 'Capital Goods': 'Cap goods', AUTO: 'Auto',
         'Healthcare': 'Healthcare', 'Information Technology': 'IT', 'Fast Moving Consumer Goods': 'FMCG',
         'Metals & Mining': 'Metals', 'Consumer Durables': 'Cons dur', 'Consumer Services': 'Cons services',
         'Oil Gas & Consumable Fuels': 'Oil & gas', 'Power': 'Power', 'Realty': 'Realty', 'Services': 'Services',
         'Chemicals': 'Chemicals', 'Construction Materials': 'Constr mat', 'Telecommunication': 'Telecom',
         'Construction': 'Construction', 'Textiles': 'Textiles'}
OLD_SHORT = {'Banks': 'Banks', 'NBFC & financials': 'NBFC/Fin', 'IT': 'IT', 'Pharma & healthcare': 'Pharma',
             'Auto & auto parts': 'Auto', 'Capital goods & defence': 'Cap goods', 'Real estate & construction': 'Realty',
             'Cement & building materials': 'Cement', 'Metals & mining': 'Metals', 'Oil & gas': 'Oil & gas',
             'Power': 'Power', 'FMCG': 'FMCG', 'Consumer durables & retail': 'Cons dur', 'Chemicals & agro': 'Chem/agro',
             'Services, telecom & internet': 'Services'}
OLD_ORDER = list(OLD_SHORT)

log = []
def P(*a):
    s = ' '.join(str(x) for x in a)
    log.append(s)
    print(s)

P('== nifty_sector_table.py ==')
# ---- NSE index sector of each stock (downloaded list: data only) ----
n5 = pd.read_csv(f'{LISTS}/ind_nifty500list.csv', dtype=str)
n5.columns = [c.strip() for c in n5.columns]
n5['Symbol'] = n5.Symbol.str.strip()
n5['Industry'] = n5.Industry.str.strip()
assert not n5.Symbol.duplicated().any()
NSE = n5.set_index('Symbol').Industry
P(f'Nifty 500 list: {len(n5)} rows, {n5.Industry.nunique()} sectors')

ev = pd.read_csv(f'{D}/events.csv')
ev = ev[ev.in_fo == True].copy()
assert len(ev) == 3278, len(ev)
miss = sorted(set(ev.symbol) - set(NSE.index))
assert not miss, miss
ev['nifty_sector'] = ev.symbol.map(NSE)
assert ev.nifty_sector.notna().all()
assert set(ev.nifty_sector) <= set(SHORT), set(ev.nifty_sector) - set(SHORT)
P(f'F&O results {len(ev)}, stocks {ev.symbol.nunique()}, all mapped to an NSE sector; '
  f'{ev.nifty_sector.nunique()} NSE sectors among them')

# ---- custom (hand-made 15-sector) label and three_day check against the earlier study ----
old = pd.read_csv(OLD)
assert len(old) == 3278 and not old.duplicated(['symbol', 'qn']).any()
ev = ev.merge(old[['symbol', 'qn', 'sector', 'three_day']].rename(columns={'sector': 'custom_sector', 'three_day': 'td_old'}),
              on=['symbol', 'qn'], how='left', validate='1:1')
assert ev.custom_sector.notna().all() and len(ev) == 3278
d_old = np.abs(ev.three_day - ev.td_old).max()
assert np.allclose(ev.three_day, ev.td_old, rtol=0, atol=1e-12), d_old
P(f'three_day vs results/sector_3day/results_3day.csv: 3278 matched, max abs diff {d_old:.2e}')

# checks: three_day is the sum of the three daily returns, and matches returns.csv
assert ev.three_day.notna().all()
assert np.allclose(ev.three_day, ev.ret_dm1 + ev.ret_rd + ev.ret_dp1)
ret = pd.read_csv(f'{D}/returns.csv', index_col=0)
R = ret.to_numpy(float)
col = {s: j for j, s in enumerate(ret.columns)}
rs = np.array([np.nansum(R[[a, b, c], col[s]]) for s, a, b, c in zip(ev.symbol, ev.i_m1, ev.i_rd, ev.i_p1)])
diff = np.abs(rs - ev.three_day.to_numpy())
assert diff.max() < 1e-6     # returns.csv is stored with fewer digits
P(f'check vs returns.csv: {len(ev)} results, max abs diff {diff.max():.2e}')

ev['td'] = ev.three_day * 100
qlab = ev.groupby('qn').agg(period=('period', 'first'), quarter=('quarter', 'first'))
assert list(qlab.index) == list(range(22))
size = ev.groupby('nifty_sector').agg(results=('td', 'size'), stocks=('symbol', 'nunique'))
order = sorted(size.index, key=lambda s: (-size.results[s], s))     # largest first, ties by name
P('sectors by number of results:', ', '.join(f'{SHORT[s]} {size.results[s]}' for s in order))

avg = ev.pivot_table(index='qn', columns='nifty_sector', values='td', aggfunc='mean').reindex(columns=order)
cnt = ev.pivot_table(index='qn', columns='nifty_sector', values='td', aggfunc='size').reindex(columns=order).fillna(0).astype(int)
tot = ev.pivot_table(index='qn', columns='nifty_sector', values='td', aggfunc='sum').reindex(columns=order)
allq = ev.groupby('qn').td.agg(['mean', 'size', 'sum'])
assert cnt.sum().sum() == 3278 and allq['size'].sum() == 3278

def summary_row(name, g):
    qa = g.groupby('qn').td.mean()
    best, worst = qa.idxmax(), qa.idxmin()
    return dict(sector=name, stocks=g.symbol.nunique(), results=len(g), avg=g.td.mean(), median=g.td.median(),
                up_pct=(g.td > 0).mean() * 100, q_with=len(qa), q_pos=int((qa > 0).sum()),
                first14=g[g.qn <= 13].td.mean(), last8=g[g.qn >= 14].td.mean(),
                best_q=f"{qlab.period[best]} ({qa[best]:+.2f}%)", worst_q=f"{qlab.period[worst]} ({qa[worst]:+.2f}%)")

summ = pd.DataFrame([summary_row(s, ev[ev.nifty_sector == s]) for s in order] + [summary_row('All F&O results', ev)])
allrow = summ.iloc[-1]
assert allrow.results == 3278 and f'{allrow.avg:+.2f}' == '+0.04', allrow.avg
P(f'All F&O results row: {allrow.results} results, avg {allrow.avg:+.2f}%')

def with_labels(df):
    d = df.copy()
    d.insert(0, 'quarter', qlab.quarter)
    d.insert(0, 'results_for', qlab.period)
    return d

with_labels(avg.assign(all_results=allq['mean'])).round(3).to_csv(f'{OUT}/avg_3day_by_sector_quarter.csv')
with_labels(cnt.assign(all_results=allq['size'])).to_csv(f'{OUT}/count_by_sector_quarter.csv')
with_labels(tot.assign(all_results=allq['sum'])).round(3).to_csv(f'{OUT}/sum_3day_by_sector_quarter.csv')
summ.round(3).to_csv(f'{OUT}/sector_summary.csv', index=False)
ev[['symbol', 'company', 'quarter', 'qn', 'period', 'results_date', 'timing', 'nifty_sector', 'custom_sector',
    'ret_dm1', 'ret_rd', 'ret_dp1', 'three_day']].to_csv(f'{OUT}/results_3day.csv', index=False)

# ---- markdown tables ----
KEY = ('Columns (NSE Nifty index sector, from the Industry column of the Nifty 500 list; ordered by number of results): '
       + '; '.join(f'{SHORT[s]} = {s}' for s in order) + '.')

def md(df, fmt, allcol):
    hdr = ['Results for', 'Quarter'] + [SHORT[s] for s in order] + ['All']
    out = ['| ' + ' | '.join(hdr) + ' |', '|---|---|' + '---:|' * (len(order) + 1)]
    for q in df.index:
        cells = [qlab.period[q], qlab.quarter[q]] + [fmt(df.loc[q, s], cnt.loc[q, s]) for s in order] + [fmt(allcol[q], allq['size'][q])]
        out.append('| ' + ' | '.join(cells) + ' |')
    return '\n'.join(out) + '\n\n' + KEY + '\n'

f_pct = lambda v, n: '-' if n == 0 else f'{v:+.2f}'
f_cnt = lambda v, n: f'{int(n)}'
open(f'{OUT}/table_avg.md', 'w').write(md(avg, f_pct, allq['mean']))
open(f'{OUT}/table_count.md', 'w').write(md(cnt, f_cnt, allq['size']))
open(f'{OUT}/table_sum.md', 'w').write(md(tot, f_pct, allq['sum']))
s_md = ['| Sector | Stocks | Results | Avg 3-day sum | Median | Up | Quarters positive | First 14 q / last 8 q | Best quarter | Worst quarter |',
        '|---|---:|---:|---:|---:|---:|---:|---|---|---|']
for _, r in summ.iterrows():
    s_md.append(f"| {r.sector} | {r.stocks} | {r.results:,} | {r.avg:+.2f}% | {r['median']:+.2f}% | {r.up_pct:.0f}% | "
                f"{r.q_pos} of {r.q_with} | {r.first14:+.2f}% / {r.last8:+.2f}% | {r.best_q} | {r.worst_q} |")
open(f'{OUT}/table_summary.md', 'w').write('\n'.join(s_md) + '\n')
P('\n' + summ.round(2).to_string())

# ---- quarter leaders ----
rows = []
for qn, g in ev.groupby('qn'):
    s = g.groupby('nifty_sector').td.agg(['mean', 'size'])
    big = s[s['size'] >= MIN_N]
    best, worst = big['mean'].idxmax(), big['mean'].idxmin()
    rk = big['mean'].rank(ascending=False, method='min')
    rows.append(dict(qn=qn, period=g.period.iloc[0], quarter=g.quarter.iloc[0], results=len(g),
                     avg=g.td.mean(), up_pct=(g.td > 0).mean() * 100,
                     sectors_up=int((s['mean'] > 0).sum()), sectors=len(s),
                     best=best, best_avg=big.loc[best, 'mean'], best_n=int(big.loc[best, 'size']),
                     worst=worst, worst_avg=big.loc[worst, 'mean'], worst_n=int(big.loc[worst, 'size']),
                     auto_rank=int(rk[AUTO]) if AUTO in rk else np.nan, ranked=len(big)))
ql = pd.DataFrame(rows)
assert ql.results.sum() == 3278
ql.round(3).to_csv(f'{OUT}/quarter_leaders.csv', index=False)
out = ['| Results for | Quarter | Results | All F&O avg | Results up | Sectors up | Best sector | Worst sector | Auto rank |',
       '|---|---|---:|---:|---:|---:|---|---|---:|']
for _, r in ql.iterrows():
    ar = '-' if pd.isna(r.auto_rank) else f'{int(r.auto_rank)} of {r.ranked}'
    out.append(f'| {r.period} | {r.quarter} | {r.results} | {r.avg:+.2f}% | {r.up_pct:.0f}% | {r.sectors_up} of {r.sectors} | '
               f'{SHORT[r.best]} {r.best_avg:+.2f}% ({r.best_n}) | {SHORT[r.worst]} {r.worst_avg:+.2f}% ({r.worst_n}) | {ar} |')
out += ['', f'Best and worst sector: among NSE sectors with at least {MIN_N} results that quarter (average 3-day sum, '
        'number of results in brackets). Auto rank: rank of Automobile and Auto Components among those sectors '
        '(1 = best). Sectors up: sectors with a positive average, of sectors with any result that quarter.',
        '', KEY.replace('Columns', 'Short names').replace('; ordered by number of results', '')]
open(f'{OUT}/table_quarter_leaders.md', 'w').write('\n'.join(out) + '\n')
P('\nquarter leaders: best counts', ql.best.map(SHORT).value_counts().to_dict())
P('quarter leaders: worst counts', ql.worst.map(SHORT).value_counts().to_dict())
P(f'Auto rank 1 in {(ql.auto_rank == 1).sum()} of {ql.auto_rank.notna().sum()} quarters; top 3 in '
  f'{(ql.auto_rank <= 3).sum()}; bottom 3 in {(ql.auto_rank >= ql.ranked - 2).sum()}; median rank {ql.auto_rank.median():.0f}')

# ---- crosswalk: NSE index sector x custom sector ----
st = ev.groupby('symbol').agg(company=('company', 'first'), industry=('industry', 'first'),
                              nifty_sector=('nifty_sector', 'first'), custom_sector=('custom_sector', 'first'),
                              results=('td', 'size'), avg=('td', 'mean')).reset_index()
assert (ev.groupby('symbol').custom_sector.nunique() == 1).all() and len(st) == 206
cw = pd.crosstab(st.nifty_sector, st.custom_sector).reindex(index=order, columns=OLD_ORDER).fillna(0).astype(int)
cw['Total'] = cw.sum(axis=1)
cw.loc['Total'] = cw.sum()
cw.to_csv(f'{OUT}/crosswalk.csv')
# main NSE counterpart of each custom sector = the NSE sector holding most of its stocks
main = {c: g.nifty_sector.value_counts().sort_index().idxmax() for c, g in st.groupby('custom_sector')}
st['main_nifty_for_custom'] = st.custom_sector.map(main)
st['differs'] = st.nifty_sector != st.main_nifty_for_custom
st.sort_values(['custom_sector', 'nifty_sector', 'symbol']).round(3).to_csv(f'{OUT}/crosswalk_stocks.csv', index=False)
dif = st[st.differs].copy()
dif['co'] = pd.Categorical(dif.custom_sector, OLD_ORDER)
dif = dif.sort_values(['co', 'results'], ascending=[True, False])
c_md = ['| NSE sector | ' + ' | '.join(OLD_SHORT[c] for c in OLD_ORDER) + ' | Total |',
        '|---|' + '---:|' * (len(OLD_ORDER) + 1)]
for s in order + ['Total']:
    c_md.append(f'| {s} | ' + ' | '.join('-' if cw.loc[s, c] == 0 else str(cw.loc[s, c]) for c in OLD_ORDER)
                + f' | {cw.loc[s, "Total"]} |')
c_md += ['', 'Number of F&O stocks by NSE index sector (rows) and the hand-made custom sector of the earlier study '
         '(columns: ' + '; '.join(f'{OLD_SHORT[c]} = {c}' for c in OLD_ORDER) + ').', '',
         f'Stocks whose NSE sector is not the main NSE counterpart of their custom sector ({len(dif)} stocks, '
         f'{dif.results.sum()} results; main counterpart = the NSE sector holding most of the custom sector\'s stocks):', '',
         '| Stock | Company | Old NSE industry | Custom sector | NSE index sector | Results | Avg 3-day sum |',
         '|---|---|---|---|---|---:|---:|']
for _, r in dif.iterrows():
    c_md.append(f'| {r.symbol} | {r.company} | {r.industry} | {r.custom_sector} | {r.nifty_sector} | {r.results} | {r.avg:+.2f}% |')
same = st[st.symbol.isin(['APOLLOHOSP', 'FORTIS', 'MAXHEALTH', 'KEI']) | (st.symbol.str.startswith('ADANI') & ~st.differs)]
c_md += ['', 'Same in both: ' + ', '.join(f'{r.symbol} ({r.custom_sector} / {r.nifty_sector})' for _, r in same.iterrows())
         + '.', '', 'Main NSE counterpart of each custom sector: '
         + '; '.join(f'{c} -> {main[c]}' for c in OLD_ORDER) + '.']
open(f'{OUT}/table_crosswalk.md', 'w').write('\n'.join(c_md) + '\n')
P(f'\ncrosswalk: {len(dif)} of 206 stocks ({dif.results.sum()} results) sit outside the main NSE counterpart of their custom sector')
P(dif[['symbol', 'custom_sector', 'nifty_sector', 'results']].to_string(index=False))
ac = ev[ev.custom_sector == 'Auto & auto parts']
an = ev[ev.nifty_sector == AUTO]
P(f'\nAuto, custom (16 stocks): {len(ac)} results avg {ac.td.mean():+.2f}%; NSE Auto ({an.symbol.nunique()} stocks): '
  f'{len(an)} results avg {an.td.mean():+.2f}%; custom Auto stocks not in NSE Auto: '
  f'{sorted(set(ac.symbol) - set(an.symbol))}; NSE Auto stocks not in custom Auto: {sorted(set(an.symbol) - set(ac.symbol))}')
P('caveat: Nifty 500 list = today\'s constituents and today\'s NSE classification (look-ahead / survivorship)')

open(f'{OUT}/run.log', 'w').write('\n'.join(log) + '\n')
