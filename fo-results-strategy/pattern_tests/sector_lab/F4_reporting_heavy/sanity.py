import os  # SECTOR_LAB: folder holding data/ from sector_lab_data.py
import sys; sys.path.append('/root/.local/lib/python3.11/site-packages')
import pandas as pd, numpy as np
f=pd.read_csv('events_with_signals.csv')
D=os.environ.get('SECTOR_LAB', 'sector_lab') + '/data/'
e=pd.read_csv(D+'events.csv')
print('ALL events three_day mean %', 100*e.three_day.mean(), 'excess_nifty', 100*e.excess_nifty.mean())
print('in_fo False three_day', 100*e[e.in_fo==False].three_day.mean(), 'excess', 100*e[e.in_fo==False].excess_nifty.mean(), len(e[e.in_fo==False]))
print('in_fo True three_day', 100*f.three_day.mean(), 'excess', 100*(f.three_day-f.nifty_3d).mean())
for g in ['G1','G2']:
    x=f[f[g+'_elig']]
    q=(100*(x.three_day-x.nifty_3d)).groupby(x.qn).mean()
    print(g,'eligible n',len(x),'gross 3d %',100*x.three_day.mean(),'gross vs nifty perq',q.mean(),'t',q.mean()/(q.std()/np.sqrt(len(q))))
# o10 check against next-day independent calc for one row
print(f[['symbol','qn','o3_gross','o3_nifty','o10_gross','o10_nifty','o10_sector']].describe().round(3))
