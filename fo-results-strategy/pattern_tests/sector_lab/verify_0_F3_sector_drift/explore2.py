import os  # SECTOR_LAB: folder holding data/ from sector_lab_data.py
import sys; sys.path.append('/root/.local/lib/python3.11/site-packages')
import pandas as pd, numpy as np
D=os.environ.get('SECTOR_LAB', 'sector_lab') + '/data/'
e=pd.read_csv(D+'events.csv')
print(e[e.timing=='Non-trading day'][['results_date','results_time','result_day','reaction_day','i_rd','i_react']].head())
print(e[e.timing=='Before open'][['results_date','results_time','result_day','reaction_day','i_rd','i_react']].head())
r=pd.read_csv(D+'returns.csv',index_col=0); print(r.index[-5:], r.notna().sum(axis=1).tail(10).tolist())
ic=pd.read_csv(D+'index_close.csv',index_col=0); print(ic.index[-3:], ic['Nifty 50'].tail(3).tolist())
s=pd.read_csv(D+'sessions.csv'); print(len(s), len(r), (s.day.values==r.index.values).all() if len(s)==len(r) else 'len mismatch')
print(e.i_react.max(), e.reaction_day.max())
print(e[e.in_fo.isna()][['symbol','qn']])
# how in_fo changes per symbol
x=e.sort_values('qn').groupby('symbol').in_fo.apply(lambda v: ''.join('1' if a==True else '0' for a in v))
print(x[x.str.contains('10')].head(20))
