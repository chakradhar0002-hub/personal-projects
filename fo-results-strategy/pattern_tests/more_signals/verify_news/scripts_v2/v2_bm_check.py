#!/usr/bin/env python3
"""Results date known at the trade-A decision? Uses the study's board_meetings.csv (data only) after checking a sample
of it against a fresh NSE download. usage: python3 v2_bm_check.py SCRATCH WORKDIR STUDY_DL VERIFY_DL"""
import sys
import numpy as np, pandas as pd
SC, W, SDL, VDL = sys.argv[1:5]
bm = pd.read_csv(f'{SDL}/board_meetings.csv'); raw = pd.read_csv(f'{VDL}/bm_raw.csv')
raw = raw[raw.status == 'ok']
k1 = set(zip(bm.symbol, bm.bm_date, bm.bm_timestamp)); syms = set(raw.q_symbol)
k2 = set(zip(raw.q_symbol, raw.bm_date, raw.bm_timestamp))
k1s = {k for k in k1 if k[0] in syms}
print(f'board meetings sample ({len(syms)} symbols): raw {len(k2)}, study file {len(k1s)}, common {len(k1s & k2)}')
bm['t'] = pd.to_datetime(bm.bm_timestamp, format='%d-%b-%Y %H:%M:%S', errors='coerce')
bm['d'] = pd.to_datetime(bm.bm_date, format='%d-%b-%Y', errors='coerce')
f = pd.read_csv(f'{W}/feat_results.csv')
ses = pd.read_csv(f'{SC}/sector_lab/data/sessions.csv'); sday = pd.to_datetime(ses.day).values
ev = pd.read_csv(f'{SC}/sector_lab/data/events.csv', usecols=['symbol', 'qn', 'results_date'])
f = f.merge(ev, on=['symbol', 'qn']); f['rd'] = pd.to_datetime(f.results_date)
f['T'] = pd.to_datetime(sday[f.i_cut.values]) + pd.Timedelta(hours=15)
g = {s: x for s, x in bm.groupby('symbol')}
fi = []
for r in f.itertuples():
    x = g.get(r.symbol)
    if x is None:
        fi.append(pd.NaT); continue
    m = x[(x.d >= r.rd - pd.Timedelta(days=2)) & (x.d <= r.rd + pd.Timedelta(days=1))]
    fi.append(m.t.min() if len(m) else pd.NaT)
f['bmi'] = fi
print(f'results with a matching intimation: {f.bmi.notna().sum()} of {len(f)}; before decision {(f.bmi < f["T"]).sum()}, '
      f'after decision {(f.bmi >= f["T"]).sum()}')
for nm, mk in [('A01 LATE (RDCHG>7)', f.RDCHG > 7), ('A02 EARLY (RDCHG<-7)', f.RDCHG < -7)]:
    s = f[mk & f.three_day.notna()]
    late = s[(s.bmi >= s['T']) | s.bmi.isna()]
    print(f'  {nm}: n {len(s)}; date not intimated before the decision (or no intimation found) {len(late)}; '
          f'mean signed P&L of those {late.three_day.mean() * (1 if "EARLY" in nm else -1):+.2f}')
