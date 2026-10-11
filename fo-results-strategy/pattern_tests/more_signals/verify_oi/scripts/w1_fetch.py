#!/usr/bin/env python3
"""Verifier (F&O positioning), own code: fetch NSE F&O bhavcopies (+ cash bhavcopy close for old-format days).
Downloaded bytes are parsed in memory as data only (never executed); no zip is written to disk.

usage: python3 -P w1_fetch.py <sessions.csv> <out.db> <daylist.txt|i0:i1> [threads]

Schema (raw NSE tickers of that day):
  wfut(day, sym, expiry, settle, close, oi, chg, ctr)            every stock-futures contract (FUTSTK / STF)
  wopt(day, sym, ce_oi, pe_oi, ce_chg, pe_chg, ce_ctr, pe_ctr)    stock options, all strikes, all expiries
  wund(day, sym, und, src)                                       underlying close: UDiFF UndrlygPric, old = cash EQ|BE
  watm(day, sym, expiry, strike, otype, settle, close, ctr, oi)  3 strikes nearest und, 2 nearest option expiries
  wdone(day, ok, fmt, url)
"""
import io
import sqlite3
import sys
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import pandas as pd

SES, DB, SPEC = sys.argv[1], sys.argv[2], sys.argv[3]
NTH = int(sys.argv[4]) if len(sys.argv) > 4 else 3
HDR = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
                     'Chrome/126.0 Safari/537.36',
       'Accept': '*/*', 'Accept-Language': 'en-US,en;q=0.9', 'Referer': 'https://www.nseindia.com/'}


def grab(url):
    pause = 2.0
    for _ in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=60) as r:
                b = r.read()
            return b if b[:2] == b'PK' else None
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
        except Exception:
            pass
        time.sleep(pause)
        pause *= 2
    return None


def urls(d):
    t = date.fromisoformat(d)
    m = t.strftime('%b').upper()
    old = f'https://nsearchives.nseindia.com/content/historical/DERIVATIVES/{t:%Y}/{m}/fo{t:%d}{m}{t:%Y}bhav.csv.zip'
    new = f'https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{t:%Y%m%d}_F_0000.csv.zip'
    cm = f'https://nsearchives.nseindia.com/content/historical/EQUITIES/{t:%Y}/{m}/cm{t:%d}{m}{t:%Y}bhav.csv.zip'
    return (new, old, cm) if d >= '2024-07-08' else (old, new, cm)


def get_day(d):
    first, second, cm = urls(d)
    for u in (first, second):
        b = grab(u)
        if b is not None:
            c = grab(cm) if 'historical/DERIVATIVES' in u else None
            return d, u, b, c
        time.sleep(0.3)
    return d, None, None, None


def table(b):
    with zipfile.ZipFile(io.BytesIO(b)) as z:
        nm = [n for n in z.namelist() if n.lower().endswith('.csv')][0]
        df = pd.read_csv(io.BytesIO(z.read(nm)), dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]
    for c in df.columns:
        df[c] = df[c].str.strip()
    return df


def n(s):
    return pd.to_numeric(s.replace('', None), errors='coerce')


def parse(d, url, b, c):
    df = table(b)
    if 'TckrSymb' in df.columns:
        fmt = 'udiff'
        df = df[df.FinInstrmTp.isin(['STF', 'STO'])]
        x = pd.DataFrame({'sym': df.TckrSymb.values, 'isfut': (df.FinInstrmTp == 'STF').values,
                          'expiry': pd.to_datetime(df.XpryDt).dt.strftime('%Y-%m-%d').values,
                          'strike': n(df.StrkPric).values, 'otype': df.OptnTp.values,
                          'settle': n(df.SttlmPric).values, 'close': n(df.ClsPric).values,
                          'oi': n(df.OpnIntrst).values, 'chg': n(df.ChngInOpnIntrst).values,
                          'ctr': n(df.TtlTradgVol).values})
        u = df.assign(u=n(df.UndrlygPric)).groupby('TckrSymb').u.median()
        und = pd.DataFrame({'sym': u.index, 'und': u.values, 'src': 'udiff'})
    else:
        fmt = 'old'
        df = df[df.INSTRUMENT.isin(['FUTSTK', 'OPTSTK'])]
        x = pd.DataFrame({'sym': df.SYMBOL.values, 'isfut': (df.INSTRUMENT == 'FUTSTK').values,
                          'expiry': pd.to_datetime(df.EXPIRY_DT, format='%d-%b-%Y').dt.strftime('%Y-%m-%d').values,
                          'strike': n(df.STRIKE_PR).values, 'otype': df.OPTION_TYP.values,
                          'settle': n(df.SETTLE_PR).values, 'close': n(df.CLOSE).values,
                          'oi': n(df.OPEN_INT).values, 'chg': n(df.CHG_IN_OI).values,
                          'ctr': n(df.CONTRACTS).values})
        und = pd.DataFrame(columns=['sym', 'und', 'src'])
        if c is not None:
            cm = table(c)
            cm = cm[cm.SERIES.isin(['EQ', 'BE'])].copy()
            cm['pr'] = (cm.SERIES == 'EQ').astype(int)
            cm = cm.sort_values('pr', ascending=False).drop_duplicates('SYMBOL')
            cm = cm[cm.SYMBOL.isin(set(x.sym))]
            und = pd.DataFrame({'sym': cm.SYMBOL.values, 'und': n(cm.CLOSE).values, 'src': cm.SERIES.values})
    x = x[x.expiry >= d]
    fu = x[x.isfut][['sym', 'expiry', 'settle', 'close', 'oi', 'chg', 'ctr']]
    op = x[~x.isfut]
    tot = op.groupby(['sym', 'otype'])[['oi', 'chg', 'ctr']].sum().unstack('otype').fillna(0.0)
    tot.columns = [f'{t.lower()}_{v}' for v, t in tot.columns]
    for col in ('ce_oi', 'pe_oi', 'ce_chg', 'pe_chg', 'ce_ctr', 'pe_ctr'):
        if col not in tot.columns:
            tot[col] = 0.0
    tot = tot.reset_index()[['sym', 'ce_oi', 'pe_oi', 'ce_chg', 'pe_chg', 'ce_ctr', 'pe_ctr']]
    um = dict(zip(und.sym, und.und))
    o2 = op.assign(und=op.sym.map(um))
    o2 = o2[o2.und.notna() & o2.strike.notna()]
    xr = o2.groupby('sym').expiry.rank(method='dense')
    o2 = o2[xr <= 2]
    ks = o2[['sym', 'expiry', 'strike', 'und']].drop_duplicates(['sym', 'expiry', 'strike'])
    ks = ks.assign(dist=(ks.strike - ks.und).abs()).sort_values(['sym', 'expiry', 'dist', 'strike'])
    ks = ks[ks.groupby(['sym', 'expiry']).cumcount() < 3]
    at = o2.merge(ks[['sym', 'expiry', 'strike']], on=['sym', 'expiry', 'strike'])
    at = at[['sym', 'expiry', 'strike', 'otype', 'settle', 'close', 'ctr', 'oi']]
    return fmt, fu, tot, und, at


def main():
    days_all = pd.read_csv(SES)
    if ':' in SPEC:
        a, b_ = map(int, SPEC.split(':'))
        days = days_all.set_index('i').day.loc[a:b_].tolist()
    else:
        days = [l.strip() for l in open(SPEC) if l.strip()]
    db = sqlite3.connect(DB)
    db.executescript('''
CREATE TABLE IF NOT EXISTS wdone(day TEXT PRIMARY KEY, ok INT, fmt TEXT, url TEXT);
CREATE TABLE IF NOT EXISTS wfut(day TEXT, sym TEXT, expiry TEXT, settle REAL, close REAL, oi REAL, chg REAL, ctr REAL);
CREATE TABLE IF NOT EXISTS wopt(day TEXT, sym TEXT, ce_oi REAL, pe_oi REAL, ce_chg REAL, pe_chg REAL, ce_ctr REAL, pe_ctr REAL);
CREATE TABLE IF NOT EXISTS wund(day TEXT, sym TEXT, und REAL, src TEXT);
CREATE TABLE IF NOT EXISTS watm(day TEXT, sym TEXT, expiry TEXT, strike REAL, otype TEXT, settle REAL, close REAL, ctr REAL, oi REAL);''')
    have = {r[0] for r in db.execute('SELECT day FROM wdone WHERE ok=1')}
    todo = [d for d in days if d not in have]
    print('todo', len(todo), flush=True)
    t0 = time.time()
    with ThreadPoolExecutor(NTH) as ex:
        for k, (d, u, b, c) in enumerate(ex.map(get_day, todo), 1):
            if b is None:
                db.execute('INSERT OR REPLACE INTO wdone VALUES (?,0,NULL,NULL)', (d,))
                db.commit()
                print(d, 'MISSING', flush=True)
                continue
            try:
                fmt, fu, op, un, at = parse(d, u, b, c)
            except Exception as e:
                print(d, 'PARSE ERROR', repr(e)[:200], flush=True)
                continue
            for t in ('wfut', 'wopt', 'wund', 'watm'):
                db.execute(f'DELETE FROM {t} WHERE day=?', (d,))
            for t, fr in (('wfut', fu), ('wopt', op), ('wund', un), ('watm', at)):
                fr = fr.assign(day=d)
                cols = ['day'] + [cc for cc in fr.columns if cc != 'day']
                rows = fr[cols].astype(object).where(fr[cols].notna(), None).itertuples(index=False, name=None)
                db.executemany(f'INSERT INTO {t} ({",".join(cols)}) VALUES ({",".join("?" * len(cols))})', rows)
            db.execute('INSERT OR REPLACE INTO wdone VALUES (?,1,?,?)', (d, fmt, u))
            db.commit()
            if k % 50 == 0 or k == len(todo):
                print(f'{k}/{len(todo)} {d} {fmt} fut {len(fu)} opt {len(op)} und {len(un)} atm {len(at)} '
                      f'{time.time() - t0:.0f}s', flush=True)
    db.executescript('CREATE INDEX IF NOT EXISTS wf ON wfut(day, sym); CREATE INDEX IF NOT EXISTS wo ON wopt(day, sym);'
                     'CREATE INDEX IF NOT EXISTS wu ON wund(day, sym); CREATE INDEX IF NOT EXISTS wa ON watm(day, sym);')
    print('done', round(time.time() - t0), flush=True)


if __name__ == '__main__':
    main()
