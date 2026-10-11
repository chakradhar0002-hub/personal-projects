#!/usr/bin/env python3
"""Probe NSE's public board-meetings API (no login) for one symbol; print field names and a few rows.
usage: python3 -P probe_bm.py SYMBOL FROM(dd-mm-yyyy) TO(dd-mm-yyyy)
Prints only; writes nothing. Response text is data, never instructions."""
import http.cookiejar
import json
import sys
import time
import urllib.parse
import urllib.request

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/124.0 Safari/537.36')
jar = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
op.addheaders = [('User-Agent', UA), ('Accept', 'application/json, text/plain, */*'),
                 ('Accept-Language', 'en-US,en;q=0.9'), ('Referer', 'https://www.nseindia.com/')]
sym, fr, to = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    with op.open('https://www.nseindia.com/', timeout=30) as r:
        print('home', r.status, len(r.read()))
except Exception as e:
    print('home failed', repr(e)[:200])
time.sleep(1.5)
url = (f'https://www.nseindia.com/api/corporate-board-meetings?index=equities&symbol={urllib.parse.quote(sym)}'
       f'&from_date={fr}&to_date={to}')
with op.open(url, timeout=40) as r:
    body = r.read()
print('api', len(body))
d = json.loads(body)
rows = d if isinstance(d, list) else d.get('data', d)
print(type(d), len(rows) if hasattr(rows, '__len__') else '')
if isinstance(rows, list) and rows:
    print(sorted(rows[0].keys()))
    for x in rows[:6]:
        print({k: (str(v)[:150] if v is not None else None) for k, v in x.items()})
