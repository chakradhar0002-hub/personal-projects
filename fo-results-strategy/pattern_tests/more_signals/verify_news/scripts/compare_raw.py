#!/usr/bin/env python3
"""Compare the re-downloaded NSE announcements (raw, sample) with the stored nse_events.db rows and the PR30 / BIZ
features used by the candidates.
usage: python3 -P compare_raw.py SP VDIR"""
import sqlite3
import sys

import numpy as np
import pandas as pd

SP, V = sys.argv[1:3]
LOG = open(f'{V}/compare_raw.log', 'w')


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.write(s + '\n')


raw = pd.read_csv(f'{V}/downloads/an_raw_sample.csv', dtype=str)
st = pd.read_csv(f'{V}/downloads/an_status.csv', dtype=str)
smp = pd.read_csv(f'{V}/work/sample.csv')
feat = pd.read_csv(f'{V}/work/my_feat.csv')
ses = pd.read_csv(f'{SP}/sector_lab/data/sessions.csv')
SD = pd.to_datetime(ses.day)
P(f'sample points {len(smp)}; fetch ok {int((st.status == "ok").sum())}; raw rows {len(raw)}')
con = sqlite3.connect(f'file:{SP}/report/nse_events.db?mode=ro', uri=True)
db = pd.read_sql('SELECT symbol, an_dt, descr, txt FROM an', con).drop_duplicates()
db['t'] = pd.to_datetime(db.an_dt, format='%d-%b-%Y %H:%M:%S')
raw['t'] = pd.to_datetime(raw.an_dt, format='%d-%b-%Y %H:%M:%S', errors='coerce')
raw['tx'] = pd.to_datetime(raw.exchdisstime, format='%d-%b-%Y %H:%M:%S', errors='coerce')
raw['lag_s'] = (raw.tx - raw.t).dt.total_seconds()
P(f'raw rows with returned symbol != queried: {int((raw.symbol != raw.q_symbol).sum())}')
P(f'dissemination lag (exchdisstime - an_dt) seconds: {raw.lag_s.describe().round(1).to_dict()}')
P(f'rows with lag > 60 s: {int((raw.lag_s > 60).sum())}; > 1 h: {int((raw.lag_s > 3600).sum())}')
if (raw.lag_s > 60).any():
    P(raw[raw.lag_s > 60][['q_symbol', 'an_dt', 'exchdisstime', 'difference', 'desc']].head(15).to_string())

rows = []
tim = []
for _, s in smp.iterrows():
    r = raw[(raw.q_symbol == s.symbol) & (raw.qn == str(s.qn)) & (raw.tag == s.tag)].drop_duplicates(
        ['an_dt', 'desc', 'seq_id'])
    t0 = pd.Timestamp(pd.to_datetime(s.from_date, format='%d-%m-%Y'))
    t1 = pd.Timestamp(pd.to_datetime(s.to_date, format='%d-%m-%Y')) + pd.Timedelta(hours=23, minutes=59, seconds=59)
    d = db[(db.symbol == s.symbol) & (db.t >= t0) & (db.t <= t1)]
    kr = set(zip(r.an_dt, r.desc.str.strip()))
    kd = set(zip(d.an_dt, d.descr.fillna('').str.strip()))
    ft = feat[(feat.symbol == s.symbol) & (feat.qn == s.qn)].iloc[0]
    T = SD.iloc[int(ft.i_cut)] + pd.Timedelta(hours=15)
    # PR30 from raw: press releases in [T-30d, T) by an_dt and by dissemination time, excluding own results days
    rd = pd.Timestamp(ft.rd).normalize()
    isp = r.desc.str.lower().str.startswith('press release')
    inw = (r.t >= T - pd.Timedelta(days=30)) & (r.t < T) & ~r.t.dt.normalize().isin([rd, rd + pd.Timedelta(days=1)])
    inwx = (r.tx >= T - pd.Timedelta(days=30)) & (r.tx < T)
    rows.append({'tag': s.tag, 'symbol': s.symbol, 'qn': s.qn, 'raw': len(r), 'db': len(d), 'common': len(kr & kd),
                 'raw_only': len(kr - kd), 'db_only': len(kd - kr), 'PR30_raw_andt': int((isp & inw).sum()),
                 'PR30_raw_diss': int((isp & inwx).sum()), 'PR30_stored': int(ft.pr30)})
    for _, x in r[isp].iterrows():
        tim.append((s.symbol, s.qn, x.an_dt, x.exchdisstime, T, x.t < T, x.tx < T))
res = pd.DataFrame(rows)
P('\nper sample point (window cutoff-32d .. cutoff+1d):')
P(res.to_string(index=False))
P(f'\ntotals: raw {res.raw.sum()}, db {res.db.sum()}, common {res.common.sum()}, raw-only {res.raw_only.sum()}, '
  f'db-only {res.db_only.sum()}')
P(f'points where PR30 from raw (an_dt) == stored: {int((res.PR30_raw_andt == res.PR30_stored).sum())}/{len(res)}; '
  f'(dissemination time) == stored: {int((res.PR30_raw_diss == res.PR30_stored).sum())}/{len(res)}; '
  f'IN/OUT flag agrees: {int(((res.PR30_raw_andt >= 1) == (res.PR30_stored >= 1)).sum())}/{len(res)}')
tm = pd.DataFrame(tim, columns=['symbol', 'qn', 'an_dt', 'exchdisstime', 'T', 'before_T_andt', 'before_T_diss'])
P(f'press-release rows in raw windows {len(tm)}; an_dt before T but dissemination after T: '
  f'{int((tm.before_T_andt & ~tm.before_T_diss).sum())}')
# details of mismatches
for _, s in res[(res.raw_only > 0) | (res.db_only > 0)].iterrows():
    r = raw[(raw.q_symbol == s.symbol) & (raw.qn == str(s.qn)) & (raw.tag == s.tag)]
    t0 = pd.to_datetime(smp[(smp.symbol == s.symbol) & (smp.qn == s.qn)].from_date.iloc[0], format='%d-%m-%Y')
    t1 = pd.to_datetime(smp[(smp.symbol == s.symbol) & (smp.qn == s.qn)].to_date.iloc[0], format='%d-%m-%Y') + \
        pd.Timedelta(hours=23, minutes=59, seconds=59)
    d = db[(db.symbol == s.symbol) & (db.t >= t0) & (db.t <= t1)]
    kr = set(zip(r.an_dt, r.desc.str.strip()))
    kd = set(zip(d.an_dt, d.descr.fillna('').str.strip()))
    P(f'  {s.symbol} qn {s.qn}: raw-only {sorted(kr - kd)[:6]} | db-only {sorted(kd - kr)[:6]}')
res.to_csv(f'{V}/raw_check.csv', index=False)
LOG.close()
