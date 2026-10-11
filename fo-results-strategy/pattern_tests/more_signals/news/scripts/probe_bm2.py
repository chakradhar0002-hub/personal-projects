#!/usr/bin/env python3
"""Probe: list (bm_date, bm_timestamp, purpose) for a symbol over a range. Prints only. usage: SYMBOL FROM TO"""
import http.cookiejar, json, sys, urllib.parse, urllib.request
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
op.addheaders = [('User-Agent', UA), ('Accept', 'application/json, text/plain, */*'), ('Referer', 'https://www.nseindia.com/')]
sym, fr, to = sys.argv[1:4]
url = (f'https://www.nseindia.com/api/corporate-board-meetings?index=equities&symbol={urllib.parse.quote(sym)}'
       f'&from_date={fr}&to_date={to}')
rows = json.loads(op.open(url, timeout=40).read())
rows = rows if isinstance(rows, list) else rows.get('data', [])
print(sym, len(rows))
for x in rows:
    print(x.get('bm_date'), '|', x.get('bm_timestamp'), '|', (x.get('bm_purpose') or '')[:60], '|', (x.get('bm_desc') or '')[-80:])
