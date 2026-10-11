#!/usr/bin/env python3
"""Own check: coverage of the announcement table (an) by symbol and month; renamed tickers before/after rename.
usage: python3 v2_coverage.py DB PANEL OUTDIR"""
import sqlite3, sys
import pandas as pd
DB, PANEL, OUT = sys.argv[1:4]
c = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
a = pd.read_sql('select symbol, an_dt, descr from an', c)
a['t'] = pd.to_datetime(a.an_dt, format='%d-%b-%Y %H:%M:%S')
print('rows', len(a), 'dupes', a.duplicated().sum(), 'range', a.t.min(), a.t.max())
print('unparsed', a.t.isna().sum())
a['m'] = a.t.dt.to_period('M')
p = pd.read_csv(PANEL, usecols=['symbol', 'qn', 'cutoff'])
syms = sorted(p.symbol.unique())
print('panel symbols', len(syms), 'in an', len(set(syms) & set(a.symbol)))
cnt = a.groupby(['symbol', 'm']).size().unstack(fill_value=0)
months = pd.period_range('2021-03', '2026-09', freq='M')
cnt = cnt.reindex(columns=months, fill_value=0).reindex(syms, fill_value=0)
# monthly totals to see the fetch seam (Nov/Dec 2022)
tot = cnt.sum()
print('monthly totals around seam:', tot.loc[pd.Period('2022-09'):pd.Period('2023-02')].to_dict())
print('min/median monthly total', tot.min(), tot.median())
# per symbol: first month with any row, then months with zero after first
first = cnt.apply(lambda r: r[r > 0].index.min() if (r > 0).any() else None, axis=1)
gaps = []
for s in syms:
    f = first[s]
    if f is None:
        gaps.append((s, 'NO ROWS', 0)); continue
    z = [m for m in months if m >= f and cnt.loc[s, m] == 0]
    if z:
        gaps.append((s, ' '.join(str(m) for m in z), len(z)))
print('symbols with zero-announcement months after their first:', len(gaps), 'total months', sum(g[2] for g in gaps))
for g in sorted(gaps, key=lambda x: -x[2])[:25]:
    print('  ', g)
# first month with data vs first F&O cutoff in the panel
pf = p.groupby('symbol').cutoff.min()
late = [(s, str(first[s]), pf[s]) for s in syms if first[s] is not None and str(first[s]) > pf[s][:7] and first[s] > pd.Period('2021-03')]
print('symbols whose first announcement month is after (cutoff-1 month) of first panel result:')
for s, f, c0 in late:
    print('  ', s, 'first an', f, 'first panel cutoff', c0)
ren = {'360ONE': '2023-01-23', 'ADANIENSOL': '2023-08-24', 'ANGELONE': '2021-11-11', 'ETERNAL': '2025-04-09',
       'GMRAIRPORT': '2024-12-11', 'LTF': '2024-04-23', 'LTM': '2026-02-27', 'MOTHERSON': '2022-06-09',
       'SHRIRAMFIN': '2022-12-20', 'TMPV': '2025-10-24', 'UNOMINDA': '2022-08-05', 'UNITDSPR': '2024-06-07',
       'ZYDUSLIFE': '2022-03-07'}
print('renamed tickers: monthly mean announcements before / after the rename; first panel cutoff')
for s, d in ren.items():
    if s not in cnt.index:
        print('  ', s, 'not in panel'); continue
    r = cnt.loc[s]; dp = pd.Period(d[:7])
    b, af = r[r.index < dp], r[r.index > dp]
    print(f'   {s:11s} rename {d}: before {b.mean():5.1f}/m ({(b == 0).sum()} zero months of {len(b)}), after {af.mean():5.1f}/m; first panel cutoff {pf.get(s)}')
cnt.to_csv(f'{OUT}/an_monthly_counts.csv')
