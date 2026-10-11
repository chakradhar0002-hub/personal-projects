#!/usr/bin/env python3
"""Results dates (events.csv) vs raw NSE results-type announcements. usage: python3 v2_check_rd_an.py WORKDIR DLDIR"""
import sys
import pandas as pd
W, DL = sys.argv[1:3]
s = pd.read_csv(f'{W}/sample_rd_an.csv'); r = pd.read_csv(f'{DL}/an_raw_rd.csv')
r['t'] = pd.to_datetime(r.an_dt, format='%d-%b-%Y %H:%M:%S', errors='coerce')
key = r.desc.fillna('').str.contains('Outcome of Board Meeting|Financial Result|Integrated Filing', case=False)
ok = 0
for x in s.itertuples():
    days = sorted(set(r[(r.pid == x.pid) & key].t.dt.date.astype(str)))
    m = str(x.T)[:10] in days; ok += m
    print(x.symbol, x.qn, 'events results_date', str(x.T)[:10], '| raw results-type announcement days', days[:4], 'match' if m else 'NO MATCH')
print(f'matched {ok} of {len(s)}')
