#!/usr/bin/env python3
"""Check W_EARLY results dates against NSE financial-results API (re-downloaded).
usage: python3 v2_check_rd.py SCRATCH WORKDIR DLDIR"""
import sys
import numpy as np, pandas as pd
SC, W, DL = sys.argv[1:4]
smp = pd.read_csv(f'{W}/sample_w.csv'); fin = pd.read_csv(f'{DL}/fin_raw.csv')
ev = pd.read_csv(f'{SC}/sector_lab/data/events.csv', usecols=['symbol', 'qn', 'quarter_end', 'results_date', 'results_time'])
ev['quarter_end'] = pd.to_datetime(ev.quarter_end); ev['results_date'] = pd.to_datetime(ev.results_date)
fin = fin[fin.status == 'ok'].copy()
fin['b'] = pd.to_datetime(fin.broadCastDate, format='%d-%b-%Y %H:%M:%S', errors='coerce')
fin['to'] = pd.to_datetime(fin.toDate, format='%d-%b-%Y', errors='coerce')
print('fin rows', len(fin), 'symbols', fin.q_symbol.nunique(), 'returned != queried', (fin.symbol != fin.q_symbol).sum(),
      'range of quarters', fin.to.min().date(), fin.to.max().date())
first = fin.groupby(['q_symbol', 'to']).b.min()
rows = []
for r in smp.itertuples():
    e = ev[(ev.symbol == r.symbol) & (ev.qn == r.qn)].iloc[0]
    qe = e.quarter_end; qe_ly = (qe - pd.DateOffset(years=1)) + pd.offsets.MonthEnd(0)
    a = first.get((r.symbol, qe)); b = first.get((r.symbol, qe_ly))
    ely = ev[(ev.symbol == r.symbol) & (ev.qn == r.qn - 4)]
    rd_ly_ev = ely.results_date.iloc[0] if len(ely) else pd.NaT
    raw_rdchg = ((a.normalize() - qe).days - (b.normalize() - qe_ly).days) if (a is not None and b is not None) else np.nan
    rows.append(dict(tag=r.tag, symbol=r.symbol, qn=r.qn, rd_events=e.results_date.date(), time=e.results_time,
                     rd_api=a.date() if a is not None else None, rd_ly_events=rd_ly_ev.date() if pd.notna(rd_ly_ev) else None,
                     rd_ly_api=b.date() if b is not None else None, RDCHG_stored=r.RDCHG, RDCHG_api=raw_rdchg,
                     early_api=raw_rdchg < -7 if raw_rdchg == raw_rdchg else None))
o = pd.DataFrame(rows)
pd.set_option('display.width', 250)
print(o.to_string(index=False))
o['d_cur'] = [(pd.Timestamp(x) - pd.Timestamp(y)).days if x is not None else np.nan for x, y in zip(o.rd_api, o.rd_events)]
print('current-quarter API date - events date (days):', o.d_cur.value_counts().to_dict())
ok = o.RDCHG_api.notna()
print('points with API both years', ok.sum(), ' EARLY flag agrees', ((o.RDCHG_api < -7) == (o.RDCHG_stored < -7))[ok].sum(),
      ' |RDCHG diff| <= 1:', ((o.RDCHG_api - o.RDCHG_stored).abs() <= 1)[ok].sum())
o.to_csv(f'{W}/rd_check_v2.csv', index=False)
