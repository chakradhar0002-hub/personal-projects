#!/usr/bin/env python3
"""Probe NSE insider-trading (PIT) disclosures API (public, no login). Prints keys and a few rows only.
usage: python3 -P probe_pit.py SYMBOL FROM TO"""
import http.cookiejar, json, sys, urllib.parse, urllib.request
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
op.addheaders = [('User-Agent', UA), ('Accept', 'application/json, text/plain, */*'), ('Referer', 'https://www.nseindia.com/')]
sym, fr, to = sys.argv[1:4]
url = (f'https://www.nseindia.com/api/corporates-pit?index=equities&symbol={urllib.parse.quote(sym)}'
       f'&from_date={fr}&to_date={to}')
b = op.open(url, timeout=60).read()
d = json.loads(b)
print('bytes', len(b), type(d), list(d.keys()) if isinstance(d, dict) else '')
rows = d if isinstance(d, list) else d.get('data', [])
print('rows', len(rows))
if rows:
    print(sorted(rows[0].keys()))
    for x in rows[:5]:
        print({k: (str(v)[:60] if v is not None else None) for k, v in x.items() if k not in ('acqName',)})
