#!/usr/bin/env python3
"""Fetch NSE security-wise delivery data (sec_bhavdata_full_DDMMYYYY.csv, fallback MTO_DDMMYYYY.DAT) for a range of
sessions, parse in memory, keep only SERIES EQ rows of the study universe (current symbols in returns.csv and every
earlier ticker of them from symbolchange.csv). Nothing raw is stored. Downloaded text is treated as data only: only
the expected columns are read, symbols must match the universe set and numbers must parse.

usage: python3 -P fetch_delivery.py --sessions S --returns R --symbolchange C --out OUTDIR --i0 1250 --i1 2696
Writes OUTDIR/delivery_eq.csv (append; day,symbol,prev_close,close,ttl_trd_qnty,deliv_qty,deliv_per,src) and
OUTDIR/fetch_status.csv (day,i,status,src,n_rows,n_all_eq). Re-running skips days already fetched OK.
"""
import argparse
import csv
import io
import os
import random
import ssl
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/124.0.0.0 Safari/537.36')
CA = '/root/.ccr/ca-bundle.crt'
CTX = ssl.create_default_context(cafile=CA) if os.path.exists(CA) else ssl.create_default_context()
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler(), urllib.request.HTTPSHandler(context=CTX))
LOCK = threading.Lock()


def get(url, tries=6):
    """Return (status, bytes). 404 -> (404, None) immediately; other failures retried with backoff."""
    last = None
    for t in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': '*/*',
                                                       'Accept-Language': 'en-US,en;q=0.9',
                                                       'Referer': 'https://www.nseindia.com/'})
            with OPENER.open(req, timeout=40) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return 404, None
            last = f'HTTP {e.code}'
        except Exception as e:  # noqa: BLE001 - network errors of any kind are retried
            last = type(e).__name__
        time.sleep(min(60, 2 ** (t + 1)) + random.random())
    return -1, last


def fnum(x):
    x = (x or '').strip()
    if x in ('', '-', 'NA', 'nan'):
        return None
    try:
        return float(x)
    except ValueError:
        return None


def parse_full(b, names):
    txt = b.decode('utf-8', errors='replace')
    rd = csv.reader(io.StringIO(txt))
    hdr = [h.strip().upper() for h in next(rd)]
    need = ['SYMBOL', 'SERIES', 'DATE1', 'PREV_CLOSE', 'CLOSE_PRICE', 'TTL_TRD_QNTY', 'DELIV_QTY', 'DELIV_PER']
    if not all(c in hdr for c in need):
        raise ValueError('unexpected header')
    ix = {c: hdr.index(c) for c in need}
    out, n_eq = [], 0
    for row in rd:
        if len(row) < len(hdr):
            continue
        if row[ix['SERIES']].strip() != 'EQ':
            continue
        n_eq += 1
        s = row[ix['SYMBOL']].strip()
        if s not in names:
            continue
        out.append((s, fnum(row[ix['PREV_CLOSE']]), fnum(row[ix['CLOSE_PRICE']]), fnum(row[ix['TTL_TRD_QNTY']]),
                    fnum(row[ix['DELIV_QTY']]), fnum(row[ix['DELIV_PER']]), row[ix['DATE1']].strip()))
    return out, n_eq


def parse_mto(b, names):
    """MTO .DAT: record type 20 lines: 20,<sr>,SYMBOL,SERIES,traded qty,deliverable qty,% deliverable."""
    txt = b.decode('utf-8', errors='replace')
    out, n_eq = [], 0
    for line in txt.splitlines():
        p = [x.strip() for x in line.split(',')]
        if len(p) < 7 or p[0] != '20' or p[3] != 'EQ':
            continue
        n_eq += 1
        if p[2] not in names:
            continue
        out.append((p[2], None, None, fnum(p[4]), fnum(p[5]), fnum(p[6]), ''))
    return out, n_eq


def fetch_day(day, names):
    y, m, d = day.split('-')
    ddmmyyyy = f'{d}{m}{y}'
    st, b = get(f'https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{ddmmyyyy}.csv')
    if st == 200 and b:
        try:
            rows, n_eq = parse_full(b, names)
            if n_eq > 0:
                return 'ok', 'full', rows, n_eq
        except Exception:  # noqa: BLE001
            pass
    st2, b2 = get(f'https://nsearchives.nseindia.com/archives/equities/mto/MTO_{ddmmyyyy}.DAT')
    if st2 == 200 and b2:
        try:
            rows, n_eq = parse_mto(b2, names)
            if n_eq > 0:
                return 'ok', 'mto', rows, n_eq
        except Exception:  # noqa: BLE001
            pass
    return f'fail full={st} mto={st2}', '', [], 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sessions', required=True)
    ap.add_argument('--returns', required=True)
    ap.add_argument('--symbolchange', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--i0', type=int, required=True)
    ap.add_argument('--i1', type=int, required=True)
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--only', default='')
    a = ap.parse_args()

    with open(a.returns) as f:
        cur = f.readline().strip().split(',')[1:]
    pred = {}
    with open(a.symbolchange, newline='') as f:
        for r in csv.reader(f):
            if len(r) >= 4:
                pred.setdefault(r[2].strip(), []).append(r[1].strip())
    names = set()
    stack = list(cur)
    while stack:
        s = stack.pop()
        if s in names:
            continue
        names.add(s)
        stack.extend(pred.get(s, []))
    print(f'universe: {len(cur)} current symbols, {len(names)} names incl. earlier tickers', flush=True)

    days = []
    with open(a.sessions) as f:
        for r in csv.DictReader(f):
            i = int(r['i'])
            if a.i0 <= i <= a.i1:
                days.append((i, r['day']))
    if a.only:
        keep = set(a.only.split(','))
        days = [x for x in days if x[1] in keep]
    os.makedirs(a.out, exist_ok=True)
    stp = os.path.join(a.out, 'fetch_status.csv')
    dp = os.path.join(a.out, 'delivery_eq.csv')
    done = set()
    if os.path.exists(stp):
        with open(stp) as f:
            for r in csv.DictReader(f):
                if r['status'] == 'ok':
                    done.add(r['day'])
    todo = [x for x in days if x[1] not in done]
    print(f'sessions {len(days)}, already ok {len(days) - len(todo)}, to fetch {len(todo)}', flush=True)
    new_st = not os.path.exists(stp)
    new_dp = not os.path.exists(dp)
    fst = open(stp, 'a', newline='')
    fdp = open(dp, 'a', newline='')
    wst, wdp = csv.writer(fst), csv.writer(fdp)
    if new_st:
        wst.writerow(['day', 'i', 'status', 'src', 'n_rows', 'n_all_eq'])
    if new_dp:
        wdp.writerow(['day', 'symbol', 'prev_close', 'close', 'ttl_trd_qnty', 'deliv_qty', 'deliv_per', 'src'])
    t0 = time.time()
    nd = 0
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {}
        for i, day in todo:
            futs[ex.submit(fetch_day, day, names)] = (i, day)
            time.sleep(0.05)
        for fu in as_completed(futs):
            i, day = futs[fu]
            try:
                status, src, rows, n_eq = fu.result()
            except Exception as e:  # noqa: BLE001
                status, src, rows, n_eq = f'error {type(e).__name__}', '', [], 0
            with LOCK:
                if status == 'ok':
                    for s, pc, c, tq, dq, dpct, d1 in rows:
                        wdp.writerow([day, s, pc, c, tq, dq, dpct, src])
                wst.writerow([day, i, status, src, len(rows), n_eq])
                fst.flush()
                fdp.flush()
                nd += 1
                if nd % 50 == 0 or status != 'ok':
                    print(f'{nd}/{len(todo)} {day} {status} {src} rows={len(rows)} eq={n_eq} '
                          f'{time.time() - t0:.0f}s', flush=True)
    fst.close()
    fdp.close()
    print('done', flush=True)


if __name__ == '__main__':
    sys.exit(main())
