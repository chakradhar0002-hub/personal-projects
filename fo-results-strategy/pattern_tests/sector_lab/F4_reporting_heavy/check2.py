import os  # SECTOR_LAB: folder holding data/ from sector_lab_data.py
import sys; sys.path.append('/root/.local/lib/python3.11/site-packages')
import pandas as pd, numpy as np
D=os.environ.get('SECTOR_LAB', 'sector_lab') + '/data/'
s=pd.read_csv(D+'sessions.csv'); r=pd.read_csv(D+'returns.csv',index_col=0); ic=pd.read_csv(D+'index_close.csv',index_col=0)
e=pd.read_csv(D+'events.csv')
i0=e.i_cut.min(); print('first cutoff i',i0, s.day[i0], 'last p1', e.i_p1.max(), s.day[e.i_p1.max()])
for c in ['Nifty Consumer Durables','Nifty Oil & Gas','Nifty India Manufacturing','Nifty India Digital','Nifty India Defence','Nifty Realty','Nifty 50','Nifty Bank','Nifty Financial Services','Nifty India Consumption']:
    x=ic[c].iloc[i0-30:]
    print(c, 'NaN since 2021 season:', x.isna().sum(), 'of', len(x))
# verify three_day
R=r.values; cols={c:k for k,c in enumerate(r.columns)}
chk=[]
for _,row in e.sample(300,random_state=1).iterrows():
    k=cols[row.symbol]; v=np.nansum(R[row.i_m1:row.i_p1+1,k]) if True else 0
    chk.append((row.three_day, R[row.i_m1,k]+R[row.i_rd,k]+R[row.i_p1,k]))
chk=np.array(chk,dtype=float); print('three_day check maxdiff', np.nanmax(np.abs(chk[:,0]-chk[:,1])), 'nan', np.isnan(chk).sum(axis=0))
nr=ic['Nifty 50'].pct_change().values
d=[]
for _,row in e.sample(300,random_state=2).iterrows():
    d.append(row.nifty_3d-(nr[row.i_m1]+nr[row.i_rd]+nr[row.i_p1]))
print('nifty_3d check', np.nanmax(np.abs(d)))
d=[]
for _,row in e.sample(300,random_state=3).iterrows():
    sr=ic[row.sector_index].pct_change(fill_method=None).values
    d.append(row.sector_3d-(sr[row.i_m1]+sr[row.i_rd]+sr[row.i_p1]))
print('sector_3d check', np.nanmax(np.abs(d)), np.isnan(d).sum())
print(pd.crosstab(e.peer_group.fillna('-'), e.sector_index).T.to_string())
print('returns NaN frac since 2021 among F&O names', np.isnan(R[i0:]).mean())
print(e[e.timing=='Non-trading day'][['results_date','result_day','reaction_day','i_rd','i_react']].head())
print((e.i_react-e.i_rd).value_counts())
print('three_day NaN', e.three_day.isna().sum(), 'sector_3d NaN', e.sector_3d.isna().sum(), 'nifty NaN', e.nifty_3d.isna().sum())
print(e[e.sector_3d.isna()][['symbol','qn','sector_index']])
