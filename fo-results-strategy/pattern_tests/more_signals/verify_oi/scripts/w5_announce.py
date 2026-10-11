#!/usr/bin/env python3
"""Verifier, own code: NSE corporate-announcement timestamps for a random sample of candidate trades.
JSON is parsed in memory as data only (announcement text is never interpreted as instructions); only a compact table
of (symbol, qn, desc, an_dt, exchdisstime, first 120 chars of text) is kept.

usage: python3 -P w5_announce.py <scratchpad> <oi_results_dir> <out_raw.csv> <out_cmp.csv> <n_B09> <n_B13> <n_A12>
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

SP, RES, OUT_RAW, OUT_CMP = sys.argv[1:5]
NB9, NB13, NA12 = map(int, sys.argv[5:8])
H = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/126.0 Safari/537.36', 'Accept': 'application/json,*/*',
     'Referer': 'https://www.nseindia.com/companies-listing/corporate-filings-announcements'}


def get(url):
    w = 2
    for _ in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=40) as r:
                j = json.loads(r.read())
            return j if isinstance(j, list) else None
        except Exception:
            time.sleep(w)
            w *= 2
    return None


ses = pd.read_csv(f'{SP}/sector_lab/data/sessions.csv').day.to_numpy()
ev = pd.read_csv(f'{SP}/sector_lab/data/events.csv',
                 usecols=['symbol', 'qn', 'period', 'results_date', 'results_time', 'timing', 'i_cut', 'i_rd', 'i_react'])
rng = np.random.default_rng(20261011)
picks = []
for f, nn in (('trades_B09.csv', NB9), ('trades_B13.csv', NB13), ('trades_A12.csv', NA12)):
    t = pd.read_csv(f'{RES}/{f}')[['symbol', 'qn']]
    t = t.iloc[rng.choice(len(t), size=min(nn, len(t)), replace=False)].assign(cand=f[7:10])
    picks.append(t)
S = pd.concat(picks).drop_duplicates(['symbol', 'qn']).merge(ev, on=['symbol', 'qn'], how='left')
raw = []
for _, r in S.iterrows():
    d0 = datetime.strptime(r.results_date, '%Y-%m-%d')
    q = urllib.parse.urlencode({'index': 'equities', 'symbol': r.symbol,
                                'from_date': (d0 - timedelta(days=6)).strftime('%d-%m-%Y'),
                                'to_date': (d0 + timedelta(days=3)).strftime('%d-%m-%Y')})
    j = get('https://www.nseindia.com/api/corporate-announcements?' + q)
    time.sleep(1.2)
    if j is None:
        raw.append({'symbol': r.symbol, 'qn': r.qn, 'status': 'fail'})
        continue
    if not j:
        raw.append({'symbol': r.symbol, 'qn': r.qn, 'status': 'empty'})
    for x in j:
        raw.append({'symbol': r.symbol, 'qn': r.qn, 'status': 'ok', 'ret_symbol': x.get('symbol'),
                    'desc': str(x.get('desc'))[:80], 'an_dt': x.get('an_dt'), 'diss': x.get('exchdisstime'),
                    'text': str(x.get('attchmntText'))[:160].replace('\n', ' ')})
RAW = pd.DataFrame(raw)
RAW.to_csv(OUT_RAW, index=False)


def is_results(desc, text):
    d, t = str(desc).lower(), str(text).lower()
    if 'financial result' in d:
        return True
    if 'outcome of board meeting' in d and ('result' in t):
        return True
    return 'financial result' in t and ('submitted' in t or 'approved' in t or 'outcome' in t)


def session_after(ts):
    """first session whose close is after ts (announcement before 15:30 on a session day -> that day)."""
    d = ts.strftime('%Y-%m-%d')
    i = int(np.searchsorted(ses, d))
    if i < len(ses) and ses[i] == d and ts.hour * 60 + ts.minute >= 15 * 60 + 30:
        i += 1
    return i


rows = []
for _, r in S.iterrows():
    g = RAW[(RAW.symbol == r.symbol) & (RAW.qn == r.qn) & (RAW.status == 'ok')]
    g = g[[is_results(a, b) for a, b in zip(g.desc, g.text)]]
    ts = [datetime.strptime(v, '%d-%b-%Y %H:%M:%S') for v in g.an_dt.dropna()]
    first = min(ts) if ts else None
    ev_ts = datetime.strptime(f'{r.results_date} {r.results_time}', '%Y-%m-%d %H:%M')
    rows.append({'cand': r.cand, 'symbol': r.symbol, 'qn': r.qn, 'period': r.period, 'timing': r.timing,
                 'events_ts': ev_ts.strftime('%Y-%m-%d %H:%M'), 'cut_day': ses[int(r.i_cut)],
                 'k_day': ses[int(r.i_react)], 'nse_first': first.strftime('%Y-%m-%d %H:%M:%S') if first else None,
                 'n_result_rows': len(g), 'min_diff': (first - ev_ts).total_seconds() / 60 if first else np.nan,
                 'nse_k_i': session_after(first) if first else np.nan, 'k_i': int(r.i_react), 'cut_i': int(r.i_cut)})
C = pd.DataFrame(rows)
C['k_match'] = C.nse_k_i == C.k_i
C['after_cut_close'] = C.nse_k_i > C.cut_i          # announcement after the cutoff close (needed for trade A)
C['before_k_close'] = C.nse_k_i <= C.k_i            # announcement known by the close of k (needed for trade B)
C.to_csv(OUT_CMP, index=False)
pd.set_option('display.width', 250)
print(C.drop(columns=['nse_k_i', 'k_i', 'cut_i']).to_string(index=False))
ok = C.nse_first.notna()
print(f'\nsample {len(C)}; NSE results announcement found {int(ok.sum())}; |diff| <= 5 min {int((C.min_diff[ok].abs() <= 5).sum())};'
      f' k implied by NSE time == panel k {int(C.k_match[ok].sum())}; announced after cutoff close {int(C.after_cut_close[ok].sum())};'
      f' known by close k {int(C.before_k_close[ok].sum())}')
print('fetch status:', RAW.drop_duplicates(['symbol', 'qn']).status.value_counts().to_dict())
