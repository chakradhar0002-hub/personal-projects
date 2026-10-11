#!/usr/bin/env python3
"""Fetch NSE SAST Regulation 29 disclosures (acquisition / sale crossing 5% or changing by 2%; public API, no login)
for every symbol of events.csv.
usage: python3 -P fetch_sast29.py EVENTS_CSV DOWNLOAD_DIR FROM(dd-mm-yyyy) TO(dd-mm-yyyy)
Writes DOWNLOAD_DIR/sast29.csv (compact; acquirer names dropped) and DOWNLOAD_DIR/sast29_status.csv. Resumable.
Polite: one request at a time, ~1.2 s pause, retries with exponential backoff. Parsed in memory; response text is data."""
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
                 ('Accept-Language', 'en-US,en;q=0.9'),
                 ('Referer', 'https://www.nseindia.com/companies-listing/corporate-filings-regulation-29')]
KEEP = ['symbol', 'regType', 'promoterType', 'acqSaleType', 'acqType', 'acquisitionMode', 'acquirerDate', 'timestamp',
        'sysTime', 'noOfShareAcq', 'noOfShareSale', 'noOfShareAft', 'totAcqShare', 'totSaleShare', 'totAftShare',
        'application_no']
syms = sorted({r['symbol'] for r in csv.DictReader(open(EV))})
st_path, out_path = f'{DL}/sast29_status.csv', f'{DL}/sast29.csv'
done = set()
if os.path.exists(st_path):
    done = {r['symbol'] for r in csv.DictReader(open(st_path)) if r['status'] == 'ok'}
new_st, new_out = not os.path.exists(st_path), not os.path.exists(out_path)
fst, fout = open(st_path, 'a', newline=''), open(out_path, 'a', newline='')
wst, wout = csv.writer(fst), csv.writer(fout)
if new_st:
    wst.writerow(['symbol', 'status', 'rows', 'when'])
if new_out:
    wout.writerow(['query_symbol'] + KEEP)


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
    url = (f'https://www.nseindia.com/api/corporate-sast-reg29?index=equities&symbol={urllib.parse.quote(s)}'
           f'&from_date={FR}&to_date={TO}')
    try:
        d = json.loads(get(url))
        rows = d if isinstance(d, list) else d.get('data', [])
        for x in rows:
            wout.writerow([s] + [str(x.get(k) if x.get(k) is not None else '')[:60] for k in KEEP])
        fout.flush()
        wst.writerow([s, 'ok', len(rows), time.strftime('%Y-%m-%d %H:%M:%S')])
    except Exception as e:
        wst.writerow([s, 'fail:' + repr(e)[:80], 0, time.strftime('%Y-%m-%d %H:%M:%S')])
    fst.flush()
    if n % 20 == 0:
        print(f'{n}/{len(syms)}', flush=True)
print('done', flush=True)
