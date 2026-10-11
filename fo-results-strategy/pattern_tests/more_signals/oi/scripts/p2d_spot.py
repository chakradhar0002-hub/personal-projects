#!/usr/bin/env python3
"""Spot-check features of a few results rows against the compact tables (features only).
usage: p2d_spot.py <db> <work_dir> <scratchpad>"""
import sqlite3, sys
import numpy as np, pandas as pd
DB, W, SP = sys.argv[1:4]
ses = pd.read_csv(f'{SP}/sector_lab/data/sessions.csv'); days = ses.day.tolist()
res = pd.read_csv(f'{W}/results_features.csv')
db = sqlite3.connect(DB)
rng = np.random.default_rng(1)
pick = res[res.symbol.isin(['INFY', 'HDFCBANK', 'TMPV', 'SHRIRAMFIN', 'LTM', 'ETERNAL'])].sample(8, random_state=3)
for _, r in pick.iterrows():
    i = int(r.i_cut); d0, d5 = days[i], days[i - 5]
    raw = {'INFY': ['INFY'], 'HDFCBANK': ['HDFCBANK'], 'TMPV': ['TATAMOTORS', 'TMPV'], 'SHRIRAMFIN': ['SRTRANSFIN', 'SHRIRAMFIN'],
           'LTM': ['LTI', 'LTIM', 'LTM'], 'ETERNAL': ['ZOMATO', 'ETERNAL']}[r.symbol]
    q = lambda d, t, c: pd.read_sql(f"select {c} from {t} where day=? and sym in ({','.join('?'*len(raw))})", db, params=[d] + raw)
    a, b = q(d0, 'fut', 'sym, oi_tot, e1, e1_settle, e2, e2_settle, und'), q(d5, 'fut', 'oi_tot')
    o = q(d0, 'opt', 'ce_oi, pe_oi')
    my_doi5 = (a.oi_tot.iloc[0] / b.oi_tot.iloc[0] - 1) * 100
    print(r.symbol, r.label if 'label' in r else r.qn, d0, a.sym.iloc[0], f'dOI5 table {r.A_dOI5:+.3f} direct {my_doi5:+.3f}',
          f'PCR table {r.A_PCR:.4f} direct {o.pe_oi.iloc[0] / o.ce_oi.iloc[0]:.4f}',
          f'BASIS {r.A_BASIS:+.3f} (e1 {a.e1.iloc[0]} {a.e1_settle.iloc[0]} e2 {a.e2.iloc[0]} {a.e2_settle.iloc[0]} und {a.und.iloc[0]})',
          f'IV {r.A_IV:.2f}')
