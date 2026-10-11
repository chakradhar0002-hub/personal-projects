#!/usr/bin/env python3
"""Data checks on the compact F&O tables (features only, no outcome).

usage: python3 -P p2b_checks.py <fo_compact.db> <out_log>
1. OI bookkeeping: OI_tot(t) - OI_tot(t-1) vs the sum of reported CHG_IN_OI on day t (days without an expiry between).
2. Units across the format switch (old to 2024-07-05, UDiFF from 2024-07-08): OI ratio distribution on that pair.
3. Put-call parity: forward implied by the ATM call/put settles (same expiry as the front future) vs the futures settle.
4. Underlying vs front-futures settle (sanity of the cash-close join on old-format days).
"""
import sqlite3
import sys

import numpy as np
import pandas as pd

DB, LOGP = sys.argv[1], sys.argv[2]
LOG = open(LOGP, 'w')


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.write(s + '\n')


db = sqlite3.connect(DB)
done = pd.read_sql('SELECT * FROM done', db)
P('sessions ok', int((done.ok == 1).sum()), 'missing', done.day[done.ok == 0].tolist())
P('format counts', done[done.ok == 1].fmt.value_counts().to_dict(), 'days without underlying',
  done.day[(done.ok == 1) & (done.has_und == 0)].tolist())
fut = pd.read_sql('SELECT day, sym, oi_tot, chg_oi_tot, e1, e1_settle, e2, e2_settle, und FROM fut', db)
fut = fut.sort_values(['sym', 'day']).reset_index(drop=True)
g = fut.groupby('sym')
fut['prev_oi'] = g.oi_tot.shift(1)
fut['prev_e1'] = g.e1.shift(1)
fut['prev_day'] = g.day.shift(1)
dd = sorted(done.day[done.ok == 1])
nxt = {a: b for a, b in zip(dd[:-1], dd[1:])}
consec = fut.prev_day.map(nxt) == fut.day
same_exp = fut.prev_e1 == fut.e1
m = consec & same_exp & (fut.prev_oi > 0)
err = (fut.oi_tot - fut.prev_oi - fut.chg_oi_tot).abs() / fut.prev_oi
P(f'1. OI bookkeeping on {int(m.sum())} consecutive non-expiry stock-days: |OI change - sum CHG_IN_OI| / OI: '
  f'median {err[m].median():.2e}, 99th pct {err[m].quantile(0.99):.2e}, share > 1%: {(err[m] > 0.01).mean():.4f}')
a = fut[fut.day == '2024-07-05'].set_index('sym')
b = fut[fut.day == '2024-07-08'].set_index('sym')
r = (b.oi_tot / a.oi_tot).dropna()
P(f'2. OI ratio 2024-07-08 / 2024-07-05 (old -> UDiFF): n {len(r)}, median {r.median():.3f}, 5th {r.quantile(.05):.3f}, '
  f'95th {r.quantile(.95):.3f}')
r2 = (b.chg_oi_tot / b.oi_tot).abs().median()
P(f'   UDiFF median |CHG_IN_OI| / OI on 2024-07-08: {r2:.4f}')
for d0, d1 in (('2024-07-04', '2024-07-05'), ('2024-07-08', '2024-07-09')):
    x, y = fut[fut.day == d0].set_index('sym'), fut[fut.day == d1].set_index('sym')
    rr = (y.oi_tot / x.oi_tot).dropna()
    P(f'   reference ratio {d1}/{d0}: median {rr.median():.3f}, 5th {rr.quantile(.05):.3f}, 95th {rr.quantile(.95):.3f}')

atm = pd.read_sql('SELECT * FROM atm', db)
f1 = fut[['day', 'sym', 'e1', 'e1_settle', 'und']].rename(columns={'e1': 'expiry'})
x = atm.merge(f1, on=['day', 'sym', 'expiry'])
x = x[(x.ce_ctr > 0) & (x.pe_ctr > 0) & (x.ce_settle > 0) & (x.pe_settle > 0)]
x['dist'] = (x.strike - x.und).abs()
x = x.sort_values(['day', 'sym', 'dist']).drop_duplicates(['day', 'sym'])
Tm = (pd.to_datetime(x.expiry) - pd.to_datetime(x.day)).dt.days / 365
x['fwd'] = x.strike + (x.ce_settle - x.pe_settle) * np.exp(0.065 * Tm)
dev = (x.fwd / x.e1_settle - 1) * 100
P(f'3. put-call parity forward vs futures settle (front expiry, both legs traded) n {len(x)}: median {dev.median():+.3f}%, '
  f'IQR {dev.quantile(.25):+.3f}..{dev.quantile(.75):+.3f}%, |dev| > 1%: {(dev.abs() > 1).mean():.3f}')
for fmt, days_ in (('old', set(done.day[done.fmt == 'old'])), ('udiff', set(done.day[done.fmt == 'udiff']))):
    mm = x.day.isin(days_)
    P(f'   {fmt}: median {dev[mm].median():+.3f}%, |dev| > 1%: {(dev[mm].abs() > 1).mean():.3f}')
bas = (fut.e1_settle / fut.und - 1) * 100
for fmt, days_ in (('old', set(done.day[done.fmt == 'old'])), ('udiff', set(done.day[done.fmt == 'udiff']))):
    mm = fut.day.isin(days_) & bas.notna()
    P(f'4. near futures settle / underlying - 1 ({fmt}): n {int(mm.sum())}, median {bas[mm].median():+.3f}%, '
      f'1st {bas[mm].quantile(.01):+.3f}%, 99th {bas[mm].quantile(.99):+.3f}%, |x| > 3%: {(bas[mm].abs() > 3).mean():.4f}')
