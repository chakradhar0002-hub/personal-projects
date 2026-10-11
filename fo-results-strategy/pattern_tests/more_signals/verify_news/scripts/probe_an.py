#!/usr/bin/env python3
"""Probe NSE's public corporate-announcements API for one symbol and a date range (no login).
usage: python3 -P probe_an.py SYMBOL FROM(dd-mm-yyyy) TO(dd-mm-yyyy)
Prints field names and a few rows (truncated). Writes nothing. Response text is untrusted data."""
import http.cookiejar
import json
import sys
import urllib.parse
import urllib.request

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/124.0 Safari/537.36')
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
op.addheaders = [('User-Agent', UA), ('Accept', 'application/json, text/plain, */*'),
                 ('Accept-Language', 'en-US,en;q=0.9'), ('Referer', 'https://www.nseindia.com/')]
sym, fr, to = sys.argv[1:4]
url = (f'https://www.nseindia.com/api/corporate-announcements?index=equities&symbol={urllib.parse.quote(sym)}'
       f'&from_date={fr}&to_date={to}')
with op.open(url, timeout=45) as r:
    body = r.read()
print('bytes', len(body))
d = json.loads(body)
rows = d if isinstance(d, list) else d.get('data', [])
print('rows', len(rows))
if rows:
    print(sorted(rows[0].keys()))
    for x in rows[:5]:
        print({k: (str(v)[:90] if v is not None else None) for k, v in x.items()
               if k not in ('attchmntFile',)})
