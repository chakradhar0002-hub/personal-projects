#!/usr/bin/env python3
"""Probe NSE PIT API date filtering. Prints counts and date spans only. usage: python3 -P probe_pit3.py"""
import http.cookiejar, json, time, urllib.request
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
op.addheaders = [('User-Agent', UA), ('Accept', 'application/json, text/plain, */*'), ('Referer', 'https://www.nseindia.com/companies-listing/corporate-filings-insider-trading')]
B = 'https://www.nseindia.com/api/corporates-pit?index=equities'
for q in ['&symbol=TITAN', '&symbol=TITAN&from_date=01-07-2026&to_date=30-09-2026',
          '&symbol=TITAN&from_date=01-01-2025&to_date=31-12-2025', '&symbol=TITAN&from_date=01-01-2023&to_date=31-12-2023',
          '&symbol=TITAN&from_date=01-04-2026&to_date=30-06-2026']:
    try:
        d = json.loads(op.open(B + q, timeout=60).read())
        rows = d if isinstance(d, list) else d.get('data', [])
        ds = sorted(x.get('date') or '' for x in rows)
        cats = {}
        for x in rows:
            k = (x.get('personCategory'), x.get('tdpTransactionType'), x.get('acqMode'))
            cats[k] = cats.get(k, 0) + 1
        print(q, 'rows', len(rows), ds[:1], ds[-1:], list(cats.items())[:6])
    except Exception as e:
        print(q, 'ERR', repr(e)[:120])
    time.sleep(2)
