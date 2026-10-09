#!/usr/bin/env python3
"""Holdout evaluator - step 2: Nifty 50 OPEN for the next-open entry sessions (k+1 and e+1) of all winners (XN > 4).
Source: NSE ind_close_all_DDMMYYYY.csv (Open Index Value). Close is checked against index_close.csv 'Nifty 50'.
Writes nifty_open.csv (day, i, open, close_nse, close_ix)."""
import io
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd

SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = f'{SP}/more_avg/holdout'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
ses = pd.read_csv(f'{SP}/sector_lab/data/sessions.csv')
ix = pd.read_csv(f'{SP}/sector_lab/data/index_close.csv', index_col=0, usecols=['day', 'Nifty 50'])
P = pd.read_csv(f'{OUT}/panel.csv')
W = P[P.XN > 4]
need = set((W.i_react + 1).tolist()) | set((W.pb_e.dropna().astype(int) + 1).tolist())
need = sorted(i for i in need if i < len(ses))
print('sessions needed', len(need))


def get(i):
    d = ses.day.iloc[i]
    url = f'https://nsearchives.nseindia.com/content/indices/ind_close_all_{d[8:10]}{d[5:7]}{d[0:4]}.csv'
    for a in range(4):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': '*/*'})
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read().decode('utf-8', 'replace')
            t = pd.read_csv(io.StringIO(body))
            t.columns = [c.strip() for c in t.columns]
            row = t[t['Index Name'].str.strip().str.lower() == 'nifty 50']
            if len(row) == 1:
                return i, d, float(row['Open Index Value'].iloc[0]), float(row['Closing Index Value'].iloc[0])
            return i, d, np.nan, np.nan
        except Exception as e:
            time.sleep(2 * (a + 1))
    return i, d, np.nan, np.nan


with ThreadPoolExecutor(4) as pool:
    res = list(pool.map(get, need))
df = pd.DataFrame(res, columns=['i', 'day', 'open', 'close_nse'])
df['close_ix'] = ix['Nifty 50'].to_numpy()[df.i]
df.to_csv(f'{OUT}/nifty_open.csv', index=False)
print('missing', int(df.open.isna().sum()))
print('max |close_nse/close_ix - 1|', float(np.nanmax(np.abs(df.close_nse / df.close_ix - 1))))
prevc = ix['Nifty 50'].to_numpy()[df.i - 1]
print('open == prev close (exact) count', int((np.abs(df.open - prevc) < 0.01).sum()), 'of', len(df))
print('median |open/prevclose-1| %', float(np.nanmedian(np.abs(df.open / prevc - 1)) * 100))
