#!/usr/bin/env python3
"""Holdout evaluator - step 3: NSE F&O bhavcopies for the option finalists (all 22 quarters).
Keeps stock-option CE rows and stock-futures rows for the WR50 symbols (and their old tickers) in my own sqlite cache.
usage: p3_fetch_bhav.py entry   -> sessions k and k+1 (and k+15..k+20) of every WR50 signal
       p3_fetch_bhav.py exit    -> sessions listed in exit_days_needed.csv (written by p4_options.py)
"""
import csv
import io
import sqlite3
import sys
import time
import urllib.request
import urllib.error
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
import pandas as pd

SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = f'{SP}/more_avg/holdout'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
UDIFF_START = '2024-07-08'
ses = pd.read_csv(f'{SP}/sector_lab/data/sessions.csv')
P = pd.read_csv(f'{OUT}/panel.csv')
S = P[(P.XN > 4) & (P.rsi_cut > 50)]
assert len(S) == 232

alias = {}   # new ticker -> old tickers
for r in csv.reader(open(f'{SP}/symbolchange.csv', encoding='latin-1')):
    if len(r) >= 4:
        alias.setdefault(r[2].strip(), set()).add(r[1].strip())
want = set()
for s in set(S.symbol):
    st = [s]
    while st:
        x = st.pop()
        if x in want:
            continue
        want.add(x)
        st.extend(alias.get(x, []))

db = sqlite3.connect(f'{OUT}/bhav.db')
db.executescript("""CREATE TABLE IF NOT EXISTS done(day TEXT PRIMARY KEY, ok INTEGER, fmt TEXT);
CREATE TABLE IF NOT EXISTS row(day TEXT, symbol TEXT, tp TEXT, expiry TEXT, act_expiry TEXT, kind TEXT, strike REAL,
  open REAL, close REAL, settle REAL, volume REAL, und REAL);
CREATE INDEX IF NOT EXISTS ri ON row(symbol, day);""")


def urls(d):
    dt = date.fromisoformat(d)
    mon = dt.strftime('%b').upper()
    old = f'https://nsearchives.nseindia.com/content/historical/DERIVATIVES/{dt:%Y}/{mon}/fo{dt:%d}{mon}{dt:%Y}bhav.csv.zip'
    new = f'https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{dt:%Y%m%d}_F_0000.csv.zip'
    return [new, old] if d >= UDIFF_START else [old, new]


def get(url):
    for a in range(4):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': '*/*'})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
        except Exception:
            pass
        time.sleep(2 * (a + 1))
    return None


def fetch(d):
    for u in urls(d):
        b = get(u)
        if b and b[:2] == b'PK':
            return d, b
    return d, None


def f0(x):
    x = (x or '').strip()
    return float(x) if x else 0.0


def parse(d, raw):
    z = zipfile.ZipFile(io.BytesIO(raw))
    text = z.read(z.namelist()[0]).decode('utf-8', 'replace')
    rd = csv.DictReader(io.StringIO(text))
    rd.fieldnames = [c.strip() for c in rd.fieldnames]
    out = []
    if 'TckrSymb' in rd.fieldnames:
        fmt = 'udiff'
        for r in rd:
            tp, sym = r['FinInstrmTp'].strip(), r['TckrSymb'].strip()
            if tp not in ('STO', 'STF') or sym not in want:
                continue
            kind = r['OptnTp'].strip() if tp == 'STO' else 'FUT'
            if tp == 'STO' and kind != 'CE':
                continue
            out.append((d, sym, tp, r['XpryDt'].strip(), (r.get('FininstrmActlXpryDt') or r['XpryDt']).strip(), kind,
                        f0(r['StrkPric']) if tp == 'STO' else 0.0, f0(r['OpnPric']), f0(r['ClsPric']),
                        f0(r['SttlmPric']), f0(r['TtlTradgVol']), f0(r['UndrlygPric'])))
    else:
        fmt = 'old'
        for r in rd:
            ins, sym = r['INSTRUMENT'].strip(), r['SYMBOL'].strip()
            if ins not in ('OPTSTK', 'FUTSTK') or sym not in want:
                continue
            kind = r['OPTION_TYP'].strip() if ins == 'OPTSTK' else 'FUT'
            if ins == 'OPTSTK' and kind != 'CE':
                continue
            ex = datetime.strptime(r['EXPIRY_DT'].strip(), '%d-%b-%Y').date().isoformat()
            out.append((d, sym, 'STO' if ins == 'OPTSTK' else 'STF', ex, ex, kind,
                        f0(r['STRIKE_PR']) if ins == 'OPTSTK' else 0.0, f0(r['OPEN']), f0(r['CLOSE']),
                        f0(r['SETTLE_PR']), f0(r['CONTRACTS']), None))
    return fmt, out


def run(days):
    have = {r[0] for r in db.execute('SELECT day FROM done WHERE ok=1')}
    todo = sorted(set(days) - have)
    print('to fetch', len(todo), 'of', len(set(days)), flush=True)
    n = 0
    with ThreadPoolExecutor(4) as pool:
        for d, raw in pool.map(fetch, todo):
            n += 1
            if raw is None:
                db.execute('INSERT OR REPLACE INTO done VALUES (?,0,NULL)', (d,))
                db.commit()
                print(d, 'MISSING', flush=True)
                continue
            fmt, rows = parse(d, raw)
            db.execute('DELETE FROM row WHERE day=?', (d,))
            db.executemany('INSERT INTO row VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', rows)
            db.execute('INSERT OR REPLACE INTO done VALUES (?,1,?)', (d, fmt))
            db.commit()
            if n % 25 == 0:
                print(n, d, fmt, len(rows), flush=True)


if __name__ == '__main__':
    LAST = len(ses) - 1
    if sys.argv[1] == 'entry':
        idx = set()
        for kk in S.i_react:
            for t in (0, 1, 20):
                if kk + t <= LAST:
                    idx.add(kk + t)
        run([ses.day.iloc[i] for i in idx])
    else:
        need = pd.read_csv(f'{OUT}/exit_days_needed.csv')
        run(list(need.day))
