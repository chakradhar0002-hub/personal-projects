#!/usr/bin/env python3
"""Verifier - announcement timestamps for a random sample of candidate trades vs NSE corporates-financial-results API.
Downloaded JSON is data only, parsed in memory; only a compact table is kept.

usage: python3 -P v5_announce.py <scratchpad> <out_compact.csv> <out_log> <n_trades>
"""
import json
import sys
import time
import urllib.request
from datetime import datetime

import numpy as np
import pandas as pd

SP, OUTC, OUTL, NS = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
H = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36',
     'Accept': 'application/json,*/*', 'Referer': 'https://www.nseindia.com/'}
LOG = open(OUTL, 'w')


def log(*a):
    s = ' '.join(map(str, a))
    print(s, flush=True)
    LOG.write(s + '\n')


def get(url):
    w = 2
    for _ in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=40) as r:
                return json.loads(r.read())
        except Exception:
            time.sleep(w)
            w *= 2
    return None


ses = pd.read_csv(f'{SP}/sector_lab/data/sessions.csv').day.to_numpy()
ev = pd.read_csv(f'{SP}/sector_lab/data/events.csv', usecols=['symbol', 'qn', 'period', 'quarter_end', 'results_date',
                                                               'results_time', 'timing', 'i_rd', 'i_react'])
t9 = pd.read_csv(f'{SP}/more_signals/oi/results/trades_B09.csv')[['symbol', 'qn']].assign(c='B09')
t13 = pd.read_csv(f'{SP}/more_signals/oi/results/trades_B13.csv')[['symbol', 'qn']].assign(c='B13')
tr = pd.concat([t9, t13]).drop_duplicates(['symbol', 'qn']).sample(NS, random_state=11)
tr = tr.merge(ev, on=['symbol', 'qn'], how='left')
rows = []
cache = {}
for sym in sorted(tr.symbol.unique()):
    j = get(f'https://www.nseindia.com/api/corporates-financial-results?index=equities&symbol={sym}&period=Quarterly')
    time.sleep(1.0)
    cache[sym] = j if isinstance(j, list) else []
for _, r in tr.iterrows():
    qe = datetime.strptime(r.quarter_end, '%Y-%m-%d').strftime('%d-%b-%Y')
    recs = [x for x in cache[r.symbol] if x.get('toDate') == qe and x.get('relatingTo') != 'Annual']
    times = []
    for x in recs:
        for fld in ('exchdisstime', 'broadCastDate'):
            v = x.get(fld)
            if v:
                try:
                    times.append(datetime.strptime(v, '%d-%b-%Y %H:%M:%S'))
                except ValueError:
                    pass
    first = min(times) if times else None
    rows.append({'cand': r.c, 'symbol': r.symbol, 'qn': r.qn, 'period': r.period, 'events_date': r.results_date,
                 'events_time': r.results_time, 'timing': r.timing, 'k_day': ses[int(r.i_react)],
                 'nse_first': first.strftime('%Y-%m-%d %H:%M') if first else None, 'n_filings': len(recs)})
X = pd.DataFrame(rows)


def first_session_after(ts):
    d = ts.strftime('%Y-%m-%d')
    hm = ts.hour * 60 + ts.minute
    i = np.searchsorted(ses, d)
    if i < len(ses) and ses[i] == d and hm >= 15 * 60 + 30:
        i += 1
    return ses[i] if i < len(ses) else None


X['nse_k'] = [first_session_after(datetime.strptime(v, '%Y-%m-%d %H:%M')) if isinstance(v, str) else None for v in X.nse_first]
X['date_match'] = X.nse_first.str[:10] == X.events_date
X['k_match'] = X.nse_k == X.k_day
ev_ts = pd.to_datetime(X.events_date + ' ' + X.events_time)
X['minutes_diff'] = (pd.to_datetime(X.nse_first) - ev_ts).dt.total_seconds() / 60
X.to_csv(OUTC, index=False)
log(X.to_string(index=False))
ok = X.nse_first.notna()
log(f'\nsample {len(X)}; found at NSE {int(ok.sum())}; results date equal {int(X.date_match[ok].sum())}; '
    f'reaction session k implied by the NSE time equal to the panel k {int(X.k_match[ok].sum())}; '
    f'|time diff| <= 5 min {int((X.minutes_diff[ok].abs() <= 5).sum())}')
