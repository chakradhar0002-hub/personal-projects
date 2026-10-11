#!/usr/bin/env python3
"""Look-ahead checks. usage: python3 v2_lookahead.py SCRATCH WORKDIR STUDY_DIR
1) Was the results date known at the trade-A decision (15:00 on the cutoff day)? Uses 'Board Meeting Intimation'
   announcements in the an table (first intimation in the 75 days before the results date).
2) For the study's trades_A rows of A01/A02 (results-date timing), how many used a date not yet intimated?
3) PR timestamps relative to the decision: any PR counted that is broadcast at/after 15:00 of the cutoff day?"""
import sqlite3, sys
import numpy as np, pandas as pd
SC, W, ST = sys.argv[1:4]
con = sqlite3.connect(f'file:{SC}/report/nse_events.db?mode=ro', uri=True)
an = pd.read_sql("select symbol, an_dt, descr from an where descr like 'Board Meeting%'", con).drop_duplicates()
an['t'] = pd.to_datetime(an.an_dt, format='%d-%b-%Y %H:%M:%S')
print(an.descr.value_counts().to_dict())
bmi = an[an.descr.str.contains('Intimation')]
f = pd.read_csv(f'{W}/feat_results.csv')
ses = pd.read_csv(f'{SC}/sector_lab/data/sessions.csv'); sday = pd.to_datetime(ses.day).values
ev = pd.read_csv(f'{SC}/sector_lab/data/events.csv', usecols=['symbol', 'qn', 'results_date'])
f = f.merge(ev, on=['symbol', 'qn'])
f['T'] = pd.to_datetime(sday[f.i_cut.values]) + pd.Timedelta(hours=15)
f['rd'] = pd.to_datetime(f.results_date)
g = {s: x.t.sort_values().values for s, x in bmi.groupby('symbol')}
first = []
for r in f.itertuples():
    a = g.get(r.symbol)
    if a is None:
        first.append(pd.NaT); continue
    lo, hi = np.datetime64(r.rd - pd.Timedelta(days=75)), np.datetime64(r.rd)
    m = a[(a >= lo) & (a < hi)]
    first.append(pd.Timestamp(m[0]) if len(m) else pd.NaT)
f['bmi'] = first
f['known'] = f.bmi < f['T']
print(f'results with a board-meeting intimation in the 75 days before: {f.bmi.notna().sum()} of {len(f)}; '
      f'intimated before the decision: {f.known.sum()}; intimated after the decision: {(f.bmi >= f["T"]).sum()}; none found: {f.bmi.isna().sum()}')
for nm, mk in [('A01 LATE', f.RDCHG > 7), ('A02 EARLY', f.RDCHG < -7)]:
    s = f[mk]
    print(f'  {nm}: n {len(s)}; intimation after decision {(s.bmi >= s["T"]).sum()}, none found {s.bmi.isna().sum()}')
# 3) PR counted at/after T? recount PR with an_dt < T vs <= T+0
an2 = pd.read_sql("select symbol, an_dt, descr from an where descr in ('Press Release','Press Release (Revised)')", con).drop_duplicates()
an2['t'] = pd.to_datetime(an2.an_dt, format='%d-%b-%Y %H:%M:%S')
g2 = {s: x.t.sort_values().values for s, x in an2.groupby('symbol')}
late = 0; same_day_after = 0
for r in f[f.PR30 >= 1].itertuples():
    a = g2[r.symbol]
    d0 = np.datetime64(r.T.normalize())
    same_day_after += int(((a >= np.datetime64(r.T)) & (a < d0 + np.timedelta64(1, 'D'))).sum())
print(f'PR items on the cutoff day at/after 15:00 (excluded by construction): {same_day_after}')
# what share of A08 trades depend only on PRs in the last 24h before T
cnt24 = []
for r in f[f.PR30 >= 1].itertuples():
    a = g2[r.symbol]
    m = (a >= np.datetime64(r.T - pd.Timedelta(days=30))) & (a < np.datetime64(r.T))
    cnt24.append((a[m] >= np.datetime64(r.T - pd.Timedelta(hours=24))).all())
print(f'A08 trades whose only PRs fall in the last 24h before the decision: {sum(cnt24)}')
