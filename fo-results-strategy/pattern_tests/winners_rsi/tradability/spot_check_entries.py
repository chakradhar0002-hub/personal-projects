#!/usr/bin/env python3
"""Spot check of the realistic-entry returns (E1a: open k+1 -> close k+21; E1b: close k+1 -> close k+21) against RAW
prices in report/nse_prices.db for MAIN trades with no corporate action between k and k+21. Writes spot_check_entries.log."""
import os, sqlite3
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.environ.get('LAB_ROOT', os.path.abspath(os.path.join(HERE, '..', '..')))  # scratch data folder
t = pd.read_csv(f'{HERE}/trades_all_entries.csv')
ses = pd.read_csv(f'{SP}/sector_lab/data/sessions.csv').day.to_numpy()
con = sqlite3.connect(f'file:{SP}/report/nse_prices.db?mode=ro', uri=True)
px = pd.read_sql('SELECT day, symbol, open, close FROM px', con).set_index(['symbol', 'day'])
ix = pd.read_sql("SELECT day, open, close FROM idx WHERE name='Nifty 50'", con).set_index('day')
ca = pd.read_sql('SELECT symbol, ex_date FROM ca', con)
out, n = [], 0
m = t[t.MAIN].copy()
for r in m.sample(len(m), random_state=1).itertuples():
    k = r.i_react
    if ((ca.symbol == r.symbol) & (ca.ex_date > ses[k]) & (ca.ex_date <= ses[k + 21])).any():
        continue
    try:
        o1, c1, c21 = px.loc[(r.symbol, ses[k + 1])].open, px.loc[(r.symbol, ses[k + 1])].close, px.loc[(r.symbol, ses[k + 21])].close
    except KeyError:
        continue
    e1a = ((c21 / o1 - 1) - (ix.loc[ses[k + 21]].close / ix.loc[ses[k + 1]].open - 1)) * 100
    e1b = ((c21 / c1 - 1) - (ix.loc[ses[k + 21]].close / ix.loc[ses[k + 1]].close - 1)) * 100
    out.append((r.symbol, r.quarter, ses[k + 1], round(e1a, 3), round(r.E1a_gross, 3), round(e1b, 3), round(r.E1b_gross, 3)))
    n += 1
    if n == 25:
        break
o = pd.DataFrame(out, columns=['symbol', 'quarter', 'entry_day', 'E1a_raw_db', 'E1a_mine', 'E1b_raw_db', 'E1b_mine'])
o['dA'] = (o.E1a_raw_db - o.E1a_mine).abs()
o['dB'] = (o.E1b_raw_db - o.E1b_mine).abs()
with open(f'{HERE}/spot_check_entries.log', 'w') as f:
    s = o.to_string(index=False) + f'\nmax |diff| E1a {o.dA.max():.4f}, E1b {o.dB.max():.4f} percentage points (25 random MAIN trades, no CA in window)\n'
    f.write(s)
    print(s)
