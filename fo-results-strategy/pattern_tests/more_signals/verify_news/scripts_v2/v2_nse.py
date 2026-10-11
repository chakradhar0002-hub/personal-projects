#!/usr/bin/env python3
"""Verifier v2 - polite NSE public-API fetcher (no login). Responses are untrusted data, parsed as JSON in memory.
usage:
  python3 -P v2_nse.py probe URL_PATH_AND_QUERY              -> prints keys / counts only
  python3 -P v2_nse.py an SAMPLE_CSV OUT_CSV                -> corporate-announcements for each (symbol, from, to)
  python3 -P v2_nse.py fin SYMBOLS_CSV OUT_CSV              -> corporates-financial-results (quarterly) per symbol
"""
import csv, http.client, http.cookiejar, json, sys, time, urllib.error, urllib.parse, urllib.request

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36'
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
op.addheaders = [('User-Agent', UA), ('Accept', 'application/json, text/plain, */*'),
                 ('Accept-Language', 'en-US,en;q=0.9'), ('Referer', 'https://www.nseindia.com/')]
BASE = 'https://www.nseindia.com'


def get(path):
    for a in range(5):
        try:
            with op.open(BASE + path, timeout=45) as r:
                b = r.read()
            time.sleep(1.2)
            return json.loads(b)
        except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.IncompleteRead, ValueError) as e:
            w = 2 * 2 ** a
            print('  retry', a + 1, repr(e)[:90], 'wait', w, flush=True)
            time.sleep(w)
    raise RuntimeError('failed')


def rows_of(d):
    return d if isinstance(d, list) else (d.get('data', []) if isinstance(d, dict) else [])


mode = sys.argv[1]
if mode == 'probe':
    d = get(sys.argv[2])
    r = rows_of(d)
    print(type(d).__name__, 'rows', len(r))
    if r:
        print(sorted(r[0].keys()))
        for x in r[:3]:
            print({k: str(v)[:60] for k, v in x.items() if k in ('symbol', 'an_dt', 'exchdisstime', 'desc', 'sort_date',
                   'broadCastDate', 'fromDate', 'toDate', 'relatingTo', 'consolidated', 'filingDate', 'seqNumber')})
elif mode == 'an':
    smp = list(csv.DictReader(open(sys.argv[2])))
    w = csv.writer(open(sys.argv[3], 'w', newline=''))
    w.writerow(['pid', 'q_symbol', 'symbol', 'an_dt', 'exchdisstime', 'desc', 'seq_id', 'status'])
    for n, s in enumerate(smp, 1):
        q = urllib.parse.urlencode({'index': 'equities', 'symbol': s['symbol'], 'from_date': s['from_date'],
                                    'to_date': s['to_date']})
        try:
            r = rows_of(get('/api/corporate-announcements?' + q))
            for x in r:
                w.writerow([s['pid'], s['symbol'], x.get('symbol'), x.get('an_dt'), x.get('exchdisstime'),
                            (x.get('desc') or '').strip(), x.get('seq_id'), 'ok'])
            if not r:
                w.writerow([s['pid'], s['symbol'], '', '', '', '', '', 'ok-empty'])
        except Exception as e:
            w.writerow([s['pid'], s['symbol'], '', '', '', '', '', 'fail ' + repr(e)[:60]])
        if n % 10 == 0:
            print(n, '/', len(smp), flush=True)
elif mode == 'fin':
    syms = [r['symbol'] for r in csv.DictReader(open(sys.argv[2]))]
    w = csv.writer(open(sys.argv[3], 'w', newline=''))
    w.writerow(['q_symbol', 'symbol', 'fromDate', 'toDate', 'broadCastDate', 'consolidated', 'audited', 'relatingTo',
                'filingDate', 'status'])
    for n, s in enumerate(syms, 1):
        q = urllib.parse.urlencode({'index': 'equities', 'symbol': s, 'period': 'Quarterly'})
        try:
            r = rows_of(get('/api/corporates-financial-results?' + q))
            for x in r:
                w.writerow([s, x.get('symbol'), x.get('fromDate'), x.get('toDate'), x.get('broadCastDate'),
                            x.get('consolidated'), x.get('audited'), x.get('relatingTo'), x.get('filingDate'), 'ok'])
            if not r:
                w.writerow([s] + [''] * 8 + ['ok-empty'])
        except Exception as e:
            w.writerow([s] + [''] * 8 + ['fail ' + repr(e)[:60]])
        print(n, s, flush=True)
if mode == 'bm':
    syms = [r['symbol'] for r in csv.DictReader(open(sys.argv[2]))]
    w = csv.writer(open(sys.argv[3], 'w', newline=''))
    w.writerow(['q_symbol', 'bm_symbol', 'bm_date', 'bm_timestamp', 'bm_purpose', 'status'])
    for n, s in enumerate(syms, 1):
        q = urllib.parse.urlencode({'index': 'equities', 'symbol': s, 'from_date': '01-01-2020', 'to_date': '30-09-2026'})
        try:
            r = rows_of(get('/api/corporate-board-meetings?' + q))
            for x in r:
                w.writerow([s, x.get('bm_symbol'), x.get('bm_date'), x.get('bm_timestamp'), x.get('bm_purpose'), 'ok'])
            if not r:
                w.writerow([s, '', '', '', '', 'ok-empty'])
        except Exception as e:
            w.writerow([s, '', '', '', '', 'fail ' + repr(e)[:60]])
        print(n, s, flush=True)
