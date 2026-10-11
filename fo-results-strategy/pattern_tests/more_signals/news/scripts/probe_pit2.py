#!/usr/bin/env python3
"""Probe variants of the NSE PIT / SAST APIs (public). Prints sizes only. usage: python3 -P probe_pit2.py"""
import http.cookiejar, json, time, urllib.request
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
op.addheaders = [('User-Agent', UA), ('Accept', 'application/json, text/plain, */*'), ('Referer', 'https://www.nseindia.com/companies-listing/corporate-filings-insider-trading')]
for url in ['https://www.nseindia.com/api/corporates-pit?index=equities&from_date=01-09-2026&to_date=15-09-2026',
            'https://www.nseindia.com/api/corporates-pit?index=equities&symbol=TITAN',
            'https://www.nseindia.com/api/corporate-sast-reg29?index=equities&symbol=TITAN',
            'https://www.nseindia.com/api/corporates-sast-reg29?index=equities&from_date=01-09-2026&to_date=15-09-2026']:
    try:
        b = op.open(url, timeout=60).read()
        d = json.loads(b)
        rows = d if isinstance(d, list) else d.get('data', [])
        print(url[30:], 'bytes', len(b), 'rows', len(rows), (sorted(rows[0].keys()) if rows else ''))
    except Exception as e:
        print(url[30:], 'ERR', repr(e)[:120])
    time.sleep(2)
