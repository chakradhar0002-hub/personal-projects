#!/usr/bin/env python3
"""Verifier (F&O positioning) - independent re-download of NSE F&O bhavcopies (+ cash bhavcopy for old-format days).
Own code; downloaded content is parsed in memory as data only, nothing from it is executed; zips are not stored.

usage: python3 -P v1_fetch.py <sessions.csv> <out.db> <i0> <i1> [nthreads]

Tables (raw NSE tickers):
  vfut(day, sym, expiry, settle, close, oi, chg, ctr)                 every stock-futures contract
  vopt(day, sym, ce_oi, pe_oi, ce_chg, pe_chg, ce_ctr, pe_ctr)         stock options, all strikes/expiries
  vund(day, sym, und, src)                                             underlying close (udiff UndrlygPric / cash EQ|BE)
  vatm(day, sym, expiry, strike, otype, settle, close, ctr, oi)        3 strikes nearest und, 2 nearest opt expiries
  vdone(day, ok, fmt, nrows)
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

SES, DB, I0, I1 = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
NTH = int(sys.argv[5]) if len(sys.argv) > 5 else 3
HDR = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36',
       'Accept': 'application/zip,*/*', 'Referer': 'https://www.nseindia.com/'}


def download(url):
    wait = 1.5
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
        time.sleep(wait)
        wait *= 2
    return None


def unzip_csv(b):
    with zipfile.ZipFile(io.BytesIO(b)) as z:
        name = z.namelist()[0]
        df = pd.read_csv(io.BytesIO(z.read(name)), dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]
    return df.apply(lambda s: s.str.strip())


def f(s):
    return pd.to_numeric(s.replace('', None), errors='coerce')


def get_day(d):
    dt = date.fromisoformat(d)
    M = dt.strftime('%b').upper()
    if d >= '2024-07-08':
        b = download(f'https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{dt:%Y%m%d}_F_0000.csv.zip')
        return d, 'udiff', b, None
    b = download(f'https://nsearchives.nseindia.com/content/historical/DERIVATIVES/{dt:%Y}/{M}/fo{dt:%d}{M}{dt:%Y}bhav.csv.zip')
    c = download(f'https://nsearchives.nseindia.com/content/historical/EQUITIES/{dt:%Y}/{M}/cm{dt:%d}{M}{dt:%Y}bhav.csv.zip')
    return d, 'old', b, c


def parse(d, fmt, b, c):
    df = unzip_csv(b)
    if fmt == 'udiff':
        df = df[df.FinInstrmTp.isin(['STF', 'STO'])]
        x = pd.DataFrame({'sym': df.TckrSymb, 'fut': df.FinInstrmTp == 'STF', 'expiry': pd.to_datetime(df.XpryDt).dt.date.astype(str),
                          'strike': f(df.StrkPric), 'otype': df.OptnTp, 'settle': f(df.SttlmPric), 'close': f(df.ClsPric),
                          'oi': f(df.OpnIntrst), 'chg': f(df.ChngInOpnIntrst), 'ctr': f(df.TtlTradgVol)})
        und = df.groupby('TckrSymb').UndrlygPric.first().pipe(f)
        und = pd.DataFrame({'sym': und.index, 'und': und.values, 'src': 'udiff'})
    else:
        df = df[df.INSTRUMENT.isin(['FUTSTK', 'OPTSTK'])]
        x = pd.DataFrame({'sym': df.SYMBOL, 'fut': df.INSTRUMENT == 'FUTSTK',
                          'expiry': pd.to_datetime(df.EXPIRY_DT, format='%d-%b-%Y').dt.date.astype(str),
                          'strike': f(df.STRIKE_PR), 'otype': df.OPTION_TYP, 'settle': f(df.SETTLE_PR), 'close': f(df.CLOSE),
                          'oi': f(df.OPEN_INT), 'chg': f(df.CHG_IN_OI), 'ctr': f(df.CONTRACTS)})
        und = pd.DataFrame(columns=['sym', 'und', 'src'])
        if c is not None:
            cm = unzip_csv(c)
            cm = cm[cm.SERIES.isin(['EQ', 'BE'])]
            cm = cm.assign(r=(cm.SERIES == 'EQ').astype(int)).sort_values('r', ascending=False).drop_duplicates('SYMBOL')
            und = pd.DataFrame({'sym': cm.SYMBOL, 'und': f(cm.CLOSE), 'src': cm.SERIES})
            und = und[und.sym.isin(set(x.sym))]
    x = x[x.expiry >= d]
    fu = x[x.fut][['sym', 'expiry', 'settle', 'close', 'oi', 'chg', 'ctr']]
    op = x[~x.fut]
    agg = op.pivot_table(index='sym', columns='otype', values=['oi', 'chg', 'ctr'], aggfunc='sum', fill_value=0)
    agg.columns = [f'{t.lower()}_{v}' for v, t in agg.columns]
    for col in ['ce_oi', 'pe_oi', 'ce_chg', 'pe_chg', 'ce_ctr', 'pe_ctr']:
        if col not in agg.columns:
            agg[col] = 0.0
    agg = agg.reset_index()[['sym', 'ce_oi', 'pe_oi', 'ce_chg', 'pe_chg', 'ce_ctr', 'pe_ctr']]
    # ATM chain: 2 nearest option expiries, 3 strikes nearest the underlying
    u = dict(zip(und.sym, und.und))
    op = op.assign(und=op.sym.map(u))
    op = op[op.und.notna()]
    er = op.groupby('sym').expiry.rank(method='dense')
    op = op[er <= 2]
    st = op[['sym', 'expiry', 'strike', 'und']].drop_duplicates(['sym', 'expiry', 'strike'])
    st = st.assign(dd=(st.strike - st.und).abs()).sort_values(['sym', 'expiry', 'dd', 'strike'])
    st = st[st.groupby(['sym', 'expiry']).cumcount() < 3]
    at = op.merge(st[['sym', 'expiry', 'strike']], on=['sym', 'expiry', 'strike'])
    at = at[['sym', 'expiry', 'strike', 'otype', 'settle', 'close', 'ctr', 'oi']]
    return fu, agg, und, at


def main():
    days = pd.read_csv(SES).set_index('i').day.loc[I0:I1].tolist()
    db = sqlite3.connect(DB)
    db.executescript('''
CREATE TABLE IF NOT EXISTS vdone(day TEXT PRIMARY KEY, ok INT, fmt TEXT, nrows INT);
CREATE TABLE IF NOT EXISTS vfut(day TEXT, sym TEXT, expiry TEXT, settle REAL, close REAL, oi REAL, chg REAL, ctr REAL);
CREATE TABLE IF NOT EXISTS vopt(day TEXT, sym TEXT, ce_oi REAL, pe_oi REAL, ce_chg REAL, pe_chg REAL, ce_ctr REAL, pe_ctr REAL);
CREATE TABLE IF NOT EXISTS vund(day TEXT, sym TEXT, und REAL, src TEXT);
CREATE TABLE IF NOT EXISTS vatm(day TEXT, sym TEXT, expiry TEXT, strike REAL, otype TEXT, settle REAL, close REAL, ctr REAL, oi REAL);''')
    have = {r[0] for r in db.execute('SELECT day FROM vdone WHERE ok=1')}
    todo = [d for d in days if d not in have]
    print('todo', len(todo), flush=True)
    t0 = time.time()
    with ThreadPoolExecutor(NTH) as ex:
        for n, (d, fmt, b, c) in enumerate(ex.map(get_day, todo), 1):
            if b is None:
                db.execute('INSERT OR REPLACE INTO vdone VALUES (?,0,?,0)', (d, fmt))
                db.commit()
                print(d, 'MISSING', flush=True)
                continue
            try:
                fu, op, un, at = parse(d, fmt, b, c)
            except Exception as e:
                print(d, 'PARSE ERROR', repr(e)[:150], flush=True)
                continue
            for t in ('vfut', 'vopt', 'vund', 'vatm'):
                db.execute(f'DELETE FROM {t} WHERE day=?', (d,))
            for t, fr in (('vfut', fu), ('vopt', op), ('vund', un), ('vatm', at)):
                fr = fr.assign(day=d)
                cols = ['day'] + [cc for cc in fr.columns if cc != 'day']
                db.executemany(f'INSERT INTO {t} ({",".join(cols)}) VALUES ({",".join("?" * len(cols))})',
                               fr[cols].astype(object).where(fr[cols].notna(), None).itertuples(index=False, name=None))
            db.execute('INSERT OR REPLACE INTO vdone VALUES (?,1,?,?)', (d, fmt, len(fu) + len(op)))
            db.commit()
            if n % 50 == 0:
                print(f'{n}/{len(todo)} {d} {fmt} fut {len(fu)} opt {len(op)} und {len(un)} atm {len(at)} {time.time()-t0:.0f}s', flush=True)
    db.executescript('CREATE INDEX IF NOT EXISTS vf ON vfut(day, sym); CREATE INDEX IF NOT EXISTS vo ON vopt(day, sym);'
                     'CREATE INDEX IF NOT EXISTS vu ON vund(day, sym); CREATE INDEX IF NOT EXISTS va ON vatm(day, sym);')
    print('done', time.time() - t0, flush=True)


if __name__ == '__main__':
    main()
