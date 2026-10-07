import os  # SECTOR_LAB: folder holding data/ from sector_lab_data.py
import sys; sys.path.append('/root/.local/lib/python3.11/site-packages')
import pandas as pd, numpy as np
D=os.environ.get('SECTOR_LAB', 'sector_lab') + '/data/'
s=pd.read_csv(D+'sessions.csv'); print('sessions',s.shape, s.day.min(), s.day.max())
r=pd.read_csv(D+'returns.csv',index_col=0); print('returns',r.shape, r.index[:2].tolist(), r.index[-2:].tolist())
ic=pd.read_csv(D+'index_close.csv',index_col=0); print('index',ic.shape)
e=pd.read_csv(D+'events.csv'); print('events',e.shape)
print(e.qn.value_counts().sort_index().to_dict())
print(e.groupby('qn').in_fo.sum().to_dict())
print(e.sector_index.value_counts())
print(e.peer_group.value_counts(dropna=False))
print(e.timing.value_counts())
for c in e.sector_index.unique():
    if c in ic.columns:
        x=ic[c]; print(c, x.first_valid_index(), x.last_valid_index(), x.isna().sum(), 'nan after first', x.loc[x.first_valid_index():].isna().sum())
    else: print('MISSING', c)
print('Nifty 50' in ic.columns, ic['Nifty 50'].first_valid_index())
print((r.index==s.day.values).all() if len(r)==len(s) else ('len mismatch',len(r),len(s)))
print(e[['cutoff','result_day','reaction_day']].head())
print(e.describe().T[['count','mean']])
