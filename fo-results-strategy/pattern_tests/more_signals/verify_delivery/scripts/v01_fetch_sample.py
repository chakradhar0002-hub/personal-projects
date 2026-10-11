#!/usr/bin/env python3
"""Verifier (independent code): re-download a random sample of NSE sec_bhavdata_full / MTO files and keep a compact
table of the rows for the study universe (ALL series, so non-EQ days can be explained). Raw files are parsed in memory
and never stored. Downloaded text is data only: only expected columns are read and numbers must parse.

usage: python3 -P v01_fetch_sample.py SCRATCH OUTDIR
"""
import csv
import io
import os
import random
import ssl
import sys
import time
import urllib.error
import urllib.request

import numpy as np
import pandas as pd

SP, OUT = sys.argv[1], sys.argv[2]
DL = f'{OUT}/downloads'
os.makedirs(DL, exist_ok=True)
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
CA = '/root/.ccr/ca-bundle.crt'
CTX = ssl.create_default_context(cafile=CA) if os.path.exists(CA) else ssl.create_default_context()
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler(), urllib.request.HTTPSHandler(context=CTX))


def get(url, tries=5):
    last = None
    for t in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': '*/*',
                                                       'Referer': 'https://www.nseindia.com/'})
            with OPENER.open(req, timeout=40) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return 404, None
            last = e.code
        except Exception as e:  # noqa: BLE001
            last = type(e).__name__
        time.sleep(2 ** (t + 1) + random.random())
    return -1, last


def num(x):
    x = (x or '').strip()
    try:
        return float(x)
    except ValueError:
        return np.nan


ses = pd.read_csv(f'{SP}/sector_lab/data/sessions.csv')
days = ses.day.tolist()
cur = pd.read_csv(f'{SP}/sector_lab/data/returns.csv', nrows=0).columns[1:].tolist()
sc = pd.read_csv(f'{SP}/symbolchange.csv', header=None, names=['co', 'old', 'new', 'date'], dtype=str)
for c in sc:
    sc[c] = sc[c].str.strip()
names = set(cur)
stack = list(cur)
pred = {}
for o, n in zip(sc.old, sc.new):
    pred.setdefault(n, []).append(o)
while stack:
    s = stack.pop()
    for o in pred.get(s, []):
        if o not in names:
            names.add(o)
            stack.append(o)

# ---- choose days: decision-relevant days of the top candidates (seeded random), the MTO day, ticker-change days
panel = pd.read_csv(f'{SP}/perf/features/panel.csv')
fr = pd.read_csv(f'{SP}/more_signals/delivery/feat_results.csv')
rng = random.Random(20261011)
A10 = fr[fr.rank_DP60 > 80]
RA1 = fr[(fr.in_fo_events == True) & (fr.lag21 < -10) & (fr.DQR >= 1.0)]
DQK = fr[(fr.W == True) & (fr.DQK >= 3)]
pick = {}
for lab, df, col, nd in [('A10_e', A10, 'e_A', 6), ('RA1_e', RA1, 'e_A', 5), ('DQK_k', DQK, 'i_react', 6)]:
    ii = sorted(set(df[col].astype(int)))
    for i in rng.sample(ii, nd):
        pick.setdefault(days[i], set()).add(lab)
# window days (inside a 60-day base window of a random A10 trade and a random DQK trade)
for df, col in [(A10, 'e_A'), (DQK, 'i_react')]:
    r = df.iloc[rng.randrange(len(df))]
    pick.setdefault(days[int(r[col]) - rng.randint(5, 55)], set()).add('window')
pick.setdefault('2022-08-08', set()).add('MTO_day')
for d in ['2020-12-17', '2020-12-18', '2025-04-08', '2025-04-09', '2022-12-02', '2022-12-05', '2025-10-23',
          '2025-10-24', '2026-02-26', '2026-02-27']:
    if d in days:
        pick.setdefault(d, set()).add('ticker_change')
print(f'{len(pick)} days', flush=True)

rows, log = [], []
for d in sorted(pick):
    y, m, dd = d.split('-')
    st, b = get(f'https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{dd}{m}{y}.csv')
    src = 'full'
    n = 0
    date1 = ''
    note = ''
    if st == 200 and b:
      try:
        rd = csv.reader(io.StringIO(b.decode('utf-8', errors='replace'), newline=''))
        hdr = [h.strip().upper() for h in next(rd)]
        if 'DELIV_PER' not in hdr:
            raise ValueError('no DELIV_PER header')
        ix = {h: k for k, h in enumerate(hdr)}
        for r in rd:
            if len(r) < len(hdr):
                continue
            sym = r[ix['SYMBOL']].strip()
            if sym not in names:
                continue
            date1 = r[ix['DATE1']].strip()
            rows.append({'day': d, 'symbol': sym, 'series': r[ix['SERIES']].strip(), 'date1': date1,
                         'prev_close': num(r[ix['PREV_CLOSE']]), 'close': num(r[ix['CLOSE_PRICE']]),
                         'ttl_trd_qnty': num(r[ix['TTL_TRD_QNTY']]), 'deliv_qty': num(r[ix['DELIV_QTY']]),
                         'deliv_per': num(r[ix['DELIV_PER']]), 'src': 'full'})
            n += 1
      except Exception as e:  # noqa: BLE001
        note = f'parse_error {type(e).__name__} len={len(b)} head={b[:60]!r}'
        n = 0
    st2 = None
    if d == '2022-08-08' or n == 0:
        st2, b2 = get(f'https://nsearchives.nseindia.com/archives/equities/mto/MTO_{dd}{m}{y}.DAT')
        if st2 == 200 and b2:
            for line in b2.decode('utf-8', errors='replace').splitlines():
                p = [x.strip() for x in line.split(',')]
                if len(p) >= 7 and p[0] == '20' and p[2] in names:
                    rows.append({'day': d, 'symbol': p[2], 'series': p[3], 'date1': '', 'prev_close': np.nan,
                                 'close': np.nan, 'ttl_trd_qnty': num(p[4]), 'deliv_qty': num(p[5]),
                                 'deliv_per': num(p[6]), 'src': 'mto'})
    log.append({'day': d, 'why': '+'.join(sorted(pick[d])), 'full_status': st, 'full_rows': n, 'date1': date1,
                'mto_status': st2, 'note': note})
    print(log[-1], flush=True)
    time.sleep(0.7)

pd.DataFrame(rows).to_csv(f'{DL}/raw_sample_rows.csv', index=False)
pd.DataFrame(log).to_csv(f'{DL}/raw_sample_log.csv', index=False)
print('rows', len(rows))
