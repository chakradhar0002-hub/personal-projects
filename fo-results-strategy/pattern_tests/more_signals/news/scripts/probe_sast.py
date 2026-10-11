#!/usr/bin/env python3
"""Probe NSE SAST Reg 29 API coverage. Prints counts, date spans and field samples only. usage: python3 -P probe_sast.py"""
import http.cookiejar, json, time, urllib.request
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
op.addheaders = [('User-Agent', UA), ('Accept', 'application/json, text/plain, */*'), ('Referer', 'https://www.nseindia.com/companies-listing/corporate-filings-regulation-29')]
B = 'https://www.nseindia.com/api/corporate-sast-reg29?index=equities'
for q in ['&symbol=ADANIENT', '&symbol=ADANIENT&from_date=01-01-2021&to_date=30-09-2026', '&symbol=TITAN&from_date=01-01-2021&to_date=30-09-2026',
          '&symbol=VEDL&from_date=01-01-2021&to_date=30-09-2026']:
    try:
        d = json.loads(op.open(B + q, timeout=60).read())
        rows = d if isinstance(d, list) else d.get('data', [])
        ds = sorted((x.get('timestamp') or '')[:11] for x in rows)
        print(q, 'rows', len(rows), ds[:2], ds[-2:])
        for x in rows[:3]:
            print('   ', {k: (str(v)[:40] if v is not None else None) for k, v in x.items() if k not in ('acquirerName', 'attachement', 'remarks')})
    except Exception as e:
        print(q, 'ERR', repr(e)[:120])
    time.sleep(2)
