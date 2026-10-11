#!/usr/bin/env python3
"""F&O positioning family - step 1: fetch NSE F&O bhavcopies (and, for old-format days, the cash bhavcopy for the
underlying close) for sessions i0..i1 of sessions.csv; parse in memory; keep compact per (day, raw symbol) tables.
No zip is written to disk. Downloaded content is treated as data only.

usage: python3 -P p1_fetch.py <sessions.csv> <out.db> <i0> <i1>

Tables (raw NSE symbols of that day; ticker changes are mapped later):
  fut(day, sym, oi_tot, chg_oi_tot, ctr_tot, e1, e1_settle, e1_close, e1_oi, e1_ctr, e2, e2_settle, e2_close, e2_oi,
      und, lot)                      futures: OI (shares) summed over all expiries; nearest (e1) and next (e2) expiry
  opt(day, sym, ce_oi, pe_oi, ce_ctr, pe_ctr, ce_chg, pe_chg, ce_oi_e1, pe_oi_e1, ce_ctr_e1, pe_ctr_e1)
                                     options: all strikes, all expiries, and nearest expiry only
  atm(day, sym, expiry, strike, ce_settle, ce_close, ce_ctr, ce_oi, pe_settle, pe_close, pe_ctr, pe_oi)
                                     4 strikes nearest the underlying close, for the 2 nearest option expiries
  done(day, ok, fmt, n_fut, n_opt, has_und)
und: UDiFF UndrlygPric; old format: cash bhavcopy close (EQ, else BE series) of the same day.
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

import numpy as np
import pandas as pd

SES, DB, I0, I1 = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
UDIFF_START = '2024-07-08'


def get(url):
    for a in range(5):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': '*/*',
                                                       'Referer': 'https://www.nseindia.com/'})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
        except Exception:
            pass
        time.sleep(2 * (a + 1))
    return None


def fo_urls(d):
    dt = date.fromisoformat(d)
    mon = dt.strftime('%b').upper()
    old = f'https://nsearchives.nseindia.com/content/historical/DERIVATIVES/{dt:%Y}/{mon}/fo{dt:%d}{mon}{dt:%Y}bhav.csv.zip'
    new = f'https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{dt:%Y%m%d}_F_0000.csv.zip'
    return [new, old] if d >= UDIFF_START else [old, new]


def cm_url(d):
    dt = date.fromisoformat(d)
    mon = dt.strftime('%b').upper()
    return f'https://nsearchives.nseindia.com/content/historical/EQUITIES/{dt:%Y}/{mon}/cm{dt:%d}{mon}{dt:%Y}bhav.csv.zip'


def read_zip_csv(raw):
    z = zipfile.ZipFile(io.BytesIO(raw))
    df = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])), dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]
    return df


def num(s):
    return pd.to_numeric(s.str.strip().replace('', np.nan), errors='coerce')


def fetch(d):
    raw = None
    for u in fo_urls(d):
        b = get(u)
        if b and b[:2] == b'PK':
            raw = b
            break
    cm = None
    if raw is not None and d < UDIFF_START:
        b = get(cm_url(d))
        if b and b[:2] == b'PK':
            cm = b
    return d, raw, cm


def standardise(d, raw, cm):
    df = read_zip_csv(raw)
    if 'TckrSymb' in df.columns:
        fmt = 'udiff'
        tp = df.FinInstrmTp.str.strip()
        df = df[tp.isin(['STF', 'STO'])]
        x = pd.DataFrame({
            'sym': df.TckrSymb.str.strip(), 'inst': np.where(df.FinInstrmTp.str.strip() == 'STF', 'FUT', 'OPT'),
            'expiry': pd.to_datetime(df.XpryDt.str.strip()).dt.strftime('%Y-%m-%d'),
            'strike': num(df.StrkPric), 'otype': df.OptnTp.str.strip(),
            'close': num(df.ClsPric), 'settle': num(df.SttlmPric), 'ctr': num(df.TtlTradgVol),
            'oi': num(df.OpnIntrst), 'chg': num(df.ChngInOpnIntrst), 'und': num(df.UndrlygPric),
            'lot': num(df.NewBrdLotQty)})
    else:
        fmt = 'old'
        ins = df.INSTRUMENT.str.strip()
        df = df[ins.isin(['FUTSTK', 'OPTSTK'])]
        x = pd.DataFrame({
            'sym': df.SYMBOL.str.strip(), 'inst': np.where(df.INSTRUMENT.str.strip() == 'FUTSTK', 'FUT', 'OPT'),
            'expiry': pd.to_datetime(df.EXPIRY_DT.str.strip(), format='%d-%b-%Y').dt.strftime('%Y-%m-%d'),
            'strike': num(df.STRIKE_PR), 'otype': df.OPTION_TYP.str.strip(),
            'close': num(df.CLOSE), 'settle': num(df.SETTLE_PR), 'ctr': num(df.CONTRACTS),
            'oi': num(df.OPEN_INT), 'chg': num(df.CHG_IN_OI), 'und': np.nan, 'lot': np.nan})
        if cm is not None:
            c = read_zip_csv(cm)
            c = c[c.SERIES.str.strip().isin(['EQ', 'BE'])].copy()
            c['sym'] = c.SYMBOL.str.strip()
            c['pri'] = (c.SERIES.str.strip() == 'EQ').astype(int)
            c['cl'] = num(c.CLOSE)
            c = c.sort_values('pri').drop_duplicates('sym', keep='last')
            x['und'] = x.sym.map(dict(zip(c.sym, c.cl)))
    x = x[x.expiry >= d]
    return fmt, x


def aggregate(d, x):
    """Vectorised per-symbol aggregation (same outputs as the first loop version)."""
    und = x.dropna(subset=['und']).groupby('sym').und.first()
    lot = x.dropna(subset=['lot']).groupby('sym').lot.first()
    f = x[x.inst == 'FUT'].sort_values(['sym', 'expiry'])
    fut_rows = []
    if len(f):
        tot = f.groupby('sym')[['oi', 'chg', 'ctr']].sum()
        f = f.assign(rk=f.groupby('sym').cumcount())
        r1 = f[f.rk == 0].set_index('sym')
        r2 = f[f.rk == 1].set_index('sym')
        F = tot.join(r1[['expiry', 'settle', 'close', 'oi', 'ctr']].add_prefix('e1_'))
        F = F.join(r2[['expiry', 'settle', 'close', 'oi']].add_prefix('e2_'))
        F['und'] = und.reindex(F.index)
        F['lot'] = lot.reindex(F.index)
        for sym, r in F.iterrows():
            fut_rows.append((d, sym, r.oi, r.chg, r.ctr, r.e1_expiry, r.e1_settle, r.e1_close, r.e1_oi, r.e1_ctr,
                             r.e2_expiry if isinstance(r.e2_expiry, str) else None, r.e2_settle, r.e2_close, r.e2_oi,
                             r.und, r.lot))
    o = x[x.inst == 'OPT']
    opt_rows, atm_rows = [], []
    if len(o):
        e1 = o.groupby('sym').expiry.min()
        o = o.assign(is1=(o.expiry.to_numpy() == e1.reindex(o.sym).to_numpy()))
        g_all = o.pivot_table(index='sym', columns='otype', values=['oi', 'ctr', 'chg'], aggfunc='sum', fill_value=0)
        g1 = o[o.is1].pivot_table(index='sym', columns='otype', values=['oi', 'ctr'], aggfunc='sum', fill_value=0)
        g_all.columns = [f'{a}_{b}' for a, b in g_all.columns]
        g1.columns = [f'{a}_{b}_e1' for a, b in g1.columns]
        G = g_all.join(g1)
        for c in ['oi_CE', 'oi_PE', 'ctr_CE', 'ctr_PE', 'chg_CE', 'chg_PE', 'oi_CE_e1', 'oi_PE_e1', 'ctr_CE_e1',
                  'ctr_PE_e1']:
            if c not in G.columns:
                G[c] = 0.0
        for sym, r in G.iterrows():
            opt_rows.append((d, sym, r.oi_CE, r.oi_PE, r.ctr_CE, r.ctr_PE, r.chg_CE, r.chg_PE, r.oi_CE_e1, r.oi_PE_e1,
                             r.ctr_CE_e1, r.ctr_PE_e1))
        # ATM chain: 2 nearest option expiries, 4 strikes nearest the underlying
        o = o.assign(und=und.reindex(o.sym).to_numpy())
        o = o[np.isfinite(o.und) & o.strike.notna()]
        ex_rank = o.groupby('sym').expiry.rank(method='dense')
        o = o[ex_rank <= 2]
        ks = o[['sym', 'expiry', 'strike', 'und']].drop_duplicates(['sym', 'expiry', 'strike'])
        ks = ks.assign(dist=(ks.strike - ks.und).abs()).sort_values(['sym', 'expiry', 'dist', 'strike'])
        ks = ks[ks.groupby(['sym', 'expiry']).cumcount() < 4]
        oo = o.merge(ks[['sym', 'expiry', 'strike']], on=['sym', 'expiry', 'strike'])
        oo = oo.drop_duplicates(['sym', 'expiry', 'strike', 'otype'])
        ce = oo[oo.otype == 'CE'].set_index(['sym', 'expiry', 'strike'])[['settle', 'close', 'ctr', 'oi']].add_prefix('ce_')
        pe = oo[oo.otype == 'PE'].set_index(['sym', 'expiry', 'strike'])[['settle', 'close', 'ctr', 'oi']].add_prefix('pe_')
        A = ks.set_index(['sym', 'expiry', 'strike'])[[]].join(ce).join(pe).sort_index()
        for (sym, e_, k), r in A.iterrows():
            atm_rows.append((d, sym, e_, float(k), r.ce_settle, r.ce_close, r.ce_ctr, r.ce_oi, r.pe_settle, r.pe_close,
                             r.pe_ctr, r.pe_oi))
    return fut_rows, opt_rows, atm_rows


def clean(rows):
    out = []
    for r in rows:
        out.append(tuple(None if (isinstance(v, float) and not np.isfinite(v)) else
                         (float(v) if isinstance(v, (np.floating, np.integer)) else v) for v in r))
    return out


def main():
    ses = pd.read_csv(SES)
    days = ses.day.iloc[I0:I1 + 1].tolist()
    db = sqlite3.connect(DB)
    db.executescript("""
CREATE TABLE IF NOT EXISTS done(day TEXT PRIMARY KEY, ok INTEGER, fmt TEXT, n_fut INTEGER, n_opt INTEGER, has_und INTEGER);
CREATE TABLE IF NOT EXISTS fut(day TEXT, sym TEXT, oi_tot REAL, chg_oi_tot REAL, ctr_tot REAL, e1 TEXT, e1_settle REAL,
  e1_close REAL, e1_oi REAL, e1_ctr REAL, e2 TEXT, e2_settle REAL, e2_close REAL, e2_oi REAL, und REAL, lot REAL);
CREATE TABLE IF NOT EXISTS opt(day TEXT, sym TEXT, ce_oi REAL, pe_oi REAL, ce_ctr REAL, pe_ctr REAL, ce_chg REAL,
  pe_chg REAL, ce_oi_e1 REAL, pe_oi_e1 REAL, ce_ctr_e1 REAL, pe_ctr_e1 REAL);
CREATE TABLE IF NOT EXISTS atm(day TEXT, sym TEXT, expiry TEXT, strike REAL, ce_settle REAL, ce_close REAL, ce_ctr REAL,
  ce_oi REAL, pe_settle REAL, pe_close REAL, pe_ctr REAL, pe_oi REAL);
CREATE INDEX IF NOT EXISTS fut_i ON fut(day, sym);
CREATE INDEX IF NOT EXISTS opt_i ON opt(day, sym);
CREATE INDEX IF NOT EXISTS atm_i ON atm(day, sym);""")
    have = {r[0] for r in db.execute('SELECT day FROM done WHERE ok=1')}
    todo = [d for d in days if d not in have]
    print('sessions', len(days), 'to fetch', len(todo), flush=True)
    t0 = time.time()
    with ThreadPoolExecutor(3) as pool:
        for n, (d, raw, cm) in enumerate(pool.map(fetch, todo), 1):
            if raw is None:
                db.execute('INSERT OR REPLACE INTO done VALUES (?,0,NULL,0,0,0)', (d,))
                db.commit()
                print(d, 'MISSING', flush=True)
                continue
            try:
                fmt, x = standardise(d, raw, cm)
                fr, orows, ar = aggregate(d, x)
            except Exception as e:  # keep going; the day is retried on the next run
                print(d, 'PARSE ERROR', repr(e)[:200], flush=True)
                continue
            for t in ('fut', 'opt', 'atm'):
                db.execute(f'DELETE FROM {t} WHERE day=?', (d,))
            db.executemany('INSERT INTO fut VALUES (' + ','.join('?' * 16) + ')', clean(fr))
            db.executemany('INSERT INTO opt VALUES (' + ','.join('?' * 12) + ')', clean(orows))
            db.executemany('INSERT INTO atm VALUES (' + ','.join('?' * 12) + ')', clean(ar))
            has_und = int(x.und.notna().any())
            db.execute('INSERT OR REPLACE INTO done VALUES (?,1,?,?,?,?)', (d, fmt, len(fr), len(orows), has_und))
            db.commit()
            if n % 25 == 0 or n == len(todo):
                print(f'{n}/{len(todo)} {d} {fmt} fut {len(fr)} opt {len(orows)} atm {len(ar)} und {has_und} '
                      f'{time.time() - t0:.0f}s', flush=True)
    print('done', flush=True)


if __name__ == '__main__':
    main()
