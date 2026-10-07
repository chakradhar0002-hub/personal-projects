import os  # SECTOR_LAB: folder holding data/ from sector_lab_data.py
import sys
sys.path.append('/root/.local/lib/python3.11/site-packages')
import pandas as pd, numpy as np
pd.set_option('display.width',250); pd.set_option('display.max_columns',40); pd.set_option('display.max_rows',200)
D=os.environ.get('SECTOR_LAB', 'sector_lab') + '/data/'
ev=pd.read_csv(D+'events.csv')
print(ev.shape)
print(ev.groupby('qn').agg(n=('symbol','size'),fo=('in_fo','sum'),q=('quarter','first'),mind=('results_date','min'),maxd=('results_date','max')))
print(ev.sector_index.value_counts())
print(ev.timing.value_counts())
print(ev[['three_day','excess_sector','excess_nifty','sector_3d','nifty_3d']].describe())
print('na three_day',ev.three_day.isna().sum(),'na exsec', ev.excess_sector.isna().sum())
print(ev.quarter.unique())
# check excess_sector definition
print((ev.three_day-ev.sector_3d-ev.excess_sector).abs().max(), (ev.three_day-ev.nifty_3d-ev.excess_nifty).abs().max())
print(ev.groupby(['symbol','qn']).size().max())
print(ev.symbol.nunique())
ic=pd.read_csv(D+'index_close.csv',index_col=0)
for c in ev.sector_index.unique():
    s=ic[c]; print(c, s.first_valid_index(), s.last_valid_index(), s.isna().sum(), s.loc[s.first_valid_index():].isna().sum())
ses=pd.read_csv(D+'sessions.csv'); print(ses.head(), ses.tail(), len(ses))
r=pd.read_csv(D+'returns.csv',index_col=0); print(r.shape, r.index[:3], r.index[-3:])
