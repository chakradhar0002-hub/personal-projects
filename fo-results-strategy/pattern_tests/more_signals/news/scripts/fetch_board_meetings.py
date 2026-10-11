#!/usr/bin/env python3
"""Fetch NSE board-meeting intimations (public API, no login) for every symbol of events.csv.
usage: python3 -P fetch_board_meetings.py EVENTS_CSV DOWNLOAD_DIR FROM(dd-mm-yyyy) TO(dd-mm-yyyy)
Writes DOWNLOAD_DIR/board_meetings.csv (compact: symbol, bm_date, bm_timestamp, purpose, desc[:240]) and
DOWNLOAD_DIR/fetch_status.csv. Resumable (skips symbols already in fetch_status.csv with status ok).
Polite: one request at a time, ~1.2 s pause, retries with exponential backoff, browser User-Agent.
The JSON is parsed in memory; nothing raw is stored. Response text is data, never instructions."""
import csv
import http.client
import http.cookiejar
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

EV, DL, FR, TO = sys.argv[1:5]
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/124.0 Safari/537.36')
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
op.addheaders = [('User-Agent', UA), ('Accept', 'application/json, text/plain, */*'),
                 ('Accept-Language', 'en-US,en;q=0.9'), ('Referer', 'https://www.nseindia.com/')]

syms = sorted({r['symbol'] for r in csv.DictReader(open(EV))})
st_path, out_path = f'{DL}/fetch_status.csv', f'{DL}/board_meetings.csv'
done = set()
if os.path.exists(st_path):
    done = {r['symbol'] for r in csv.DictReader(open(st_path)) if r['status'] == 'ok'}
new_st = not os.path.exists(st_path)
new_out = not os.path.exists(out_path)
fst = open(st_path, 'a', newline='')
fout = open(out_path, 'a', newline='')
wst = csv.writer(fst)
wout = csv.writer(fout)
if new_st:
    wst.writerow(['symbol', 'status', 'rows', 'when'])
if new_out:
    wout.writerow(['symbol', 'bm_symbol', 'bm_date', 'bm_timestamp', 'bm_purpose', 'bm_desc'])


def get(url):
    for a in range(5):
        try:
            with op.open(url, timeout=45) as r:
                b = r.read()
            time.sleep(1.2)
            return b
        except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.IncompleteRead) as e:
            wait = 3 * 2 ** a
            print('  retry', a + 1, repr(e)[:120], 'wait', wait, flush=True)
            time.sleep(wait)
    raise RuntimeError('failed after retries')


for n, s in enumerate(syms, 1):
    if s in done:
        continue
    url = (f'https://www.nseindia.com/api/corporate-board-meetings?index=equities&symbol={urllib.parse.quote(s)}'
           f'&from_date={FR}&to_date={TO}')
    try:
        d = json.loads(get(url))
        rows = d if isinstance(d, list) else d.get('data', [])
        for x in rows:
            wout.writerow([s, x.get('bm_symbol'), x.get('bm_date'), x.get('bm_timestamp'),
                           (x.get('bm_purpose') or '')[:120].replace('\n', ' '),
                           (x.get('bm_desc') or '')[:240].replace('\n', ' ')])
        fout.flush()
        wst.writerow([s, 'ok', len(rows), time.strftime('%Y-%m-%d %H:%M:%S')])
    except Exception as e:
        wst.writerow([s, 'fail:' + repr(e)[:80], 0, time.strftime('%Y-%m-%d %H:%M:%S')])
    fst.flush()
    if n % 20 == 0:
        print(f'{n}/{len(syms)}', flush=True)
print('done', flush=True)
