#!/usr/bin/env python3
"""Compare re-downloaded raw NSE rows with the stored db rows and stored features.
usage: python3 v2_compare_raw.py SCRATCH WORKDIR DLDIR"""
import sqlite3, sys
import numpy as np, pandas as pd
SC, W, DL = sys.argv[1:4]
smp = pd.read_csv(f'{W}/sample_an.csv'); raw = pd.read_csv(f'{DL}/an_raw.csv')
feat = pd.read_csv(f'{W}/feat_results.csv')
biz = pd.read_csv(f'{W}/biz_items.csv')
con = sqlite3.connect(f'file:{SC}/report/nse_events.db?mode=ro', uri=True)
db = pd.read_sql('select symbol, an_dt, descr from an', con).drop_duplicates()
db['t'] = pd.to_datetime(db.an_dt, format='%d-%b-%Y %H:%M:%S')
raw['t'] = pd.to_datetime(raw.an_dt, format='%d-%b-%Y %H:%M:%S', errors='coerce')
raw['td'] = pd.to_datetime(raw.exchdisstime, format='%d-%b-%Y %H:%M:%S', errors='coerce')
ok = raw[raw.status == 'ok']
print('raw rows', len(ok), ' returned symbol != queried', (ok.symbol != ok.q_symbol).sum())
lag = (ok.td - ok.t).dt.total_seconds()
print('dissemination lag s: median', lag.median(), 'max', lag.max(), ' >300s', (lag > 300).sum())
PR = {'Press Release', 'Press Release (Revised)'}
rows = []
for s in smp[smp.tag != 'ticker'].itertuples():
    lo = pd.to_datetime(s.from_date, format='%d-%m-%Y'); hi = pd.to_datetime(s.to_date, format='%d-%m-%Y') + pd.Timedelta(days=1)
    r = ok[(ok.pid == s.pid)].copy(); r = r.drop_duplicates(['t', 'desc'])
    d = db[(db.symbol == s.symbol) & (db.t >= lo) & (db.t < hi)].drop_duplicates(['t', 'descr'])
    kr = set(zip(r.t, r.desc.str.strip())); kd = set(zip(d.t, d.descr.str.strip()))
    T = pd.Timestamp(s.T)
    pr_raw = r[r.desc.isin(PR) & (r.t >= T - pd.Timedelta(days=30)) & (r.t < T)]
    pr_raw_d = r[r.desc.isin(PR) & (r.td >= T - pd.Timedelta(days=30)) & (r.td < T)]
    f = feat[(feat.symbol == s.symbol) & (feat.qn == s.qn)].iloc[0]
    # own-results-day exclusion is not applied to raw: count it too
    o = dict(pid=s.pid, tag=s.tag, symbol=s.symbol, qn=s.qn, T=str(T)[:16], raw=len(kr), db=len(kd), common=len(kr & kd),
             raw_only=len(kr - kd), db_only=len(kd - kr), PR30_raw_andt=len(pr_raw), PR30_raw_diss=len(pr_raw_d),
             PR30_stored=int(f.PR30), PR30_incl_stored=int(f.PR30_incl))
    if s.tag == 'A12_in':
        b = biz[(biz.symbol == s.symbol)].copy(); b['t'] = pd.to_datetime(b.an_dt, format='%d-%b-%Y %H:%M:%S')
        b = b[(b.t >= T - pd.Timedelta(days=45)) & (b.t < T)]
        o['biz_items_db'] = len(b)
        o['biz_in_raw'] = sum((t, de) in kr for t, de in zip(b.t, b.descr.str.strip()))
        o['BIZ_RX'] = round(float(f.BIZ_RX), 2)
    rows.append(o)
o = pd.DataFrame(rows)
pd.set_option('display.width', 250)
print(o.to_string(index=False))
print('points', len(o), ' raw==db sets:', ((o.raw_only == 0) & (o.db_only == 0)).sum(),
      ' PR30 raw(an_dt)==stored:', (o.PR30_raw_andt == o.PR30_stored).sum(), ' PR flag agree:',
      ((o.PR30_raw_andt >= 1) == (o.PR30_stored >= 1)).sum(), ' PR flag by dissemination time agree:',
      ((o.PR30_raw_diss >= 1) == (o.PR30_stored >= 1)).sum())
o.to_csv(f'{W}/raw_check_v2.csv', index=False)
print('\nTICKER CHANGE PROBES (raw rows returned by NSE for old and new symbol, and db rows under new symbol)')
for s in smp[smp.tag == 'ticker'].itertuples():
    lo = pd.to_datetime(s.from_date, format='%d-%m-%Y'); hi = pd.to_datetime(s.to_date, format='%d-%m-%Y') + pd.Timedelta(days=1)
    r = raw[raw.pid == s.pid]
    d = db[(db.symbol == s.symbol) & (db.t >= lo) & (db.t < hi)]
    print(f'  {s.symbol:11s} {s.from_date}..{s.to_date}: raw rows {int((r.status == "ok").sum())} (returned symbols {sorted(set(r.symbol.dropna()))}), db rows {len(d)}')
