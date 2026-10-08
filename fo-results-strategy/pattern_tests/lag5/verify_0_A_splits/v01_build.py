import os  # LAB_ROOT: scratch folder with search22/, sector/, sector_lab/data/, five_pct/; REPO_ROOT: this repo
import pandas as pd, numpy as np
D=os.environ.get('LAB_ROOT', 'lab') + '/sector_lab/data/'
V=os.environ.get('LAB_ROOT', 'lab') + '/lag5/verify_0_A_splits/'
ev=pd.read_csv(D+'events.csv'); R=pd.read_csv(D+'returns.csv',index_col=0); ic=pd.read_csv(D+'index_close.csv',index_col=0)
nif=ic['Nifty 50'].values; RA=R.values; cols={c:i for i,c in enumerate(R.columns)}
rows=[]
for _,e in ev.iterrows():
    if e.symbol not in cols: rows.append({}); continue
    j=cols[e.symbol]; c=int(e.i_cut)
    r21=RA[c-20:c+1,j]; s1m=np.prod(1+r21)-1 if np.isfinite(r21).all() else np.nan
    n1m=nif[c]/nif[c-21]-1
    r60=RA[c-59:c+1,j]; v60=np.nanstd(r60,ddof=1)*np.sqrt(252) if np.isfinite(r60).sum()>=40 else np.nan
    r5=RA[c-4:c+1,j]; r1w=np.prod(1+r5)-1
    td=RA[[int(e.i_m1),int(e.i_rd),int(e.i_p1)],j]
    rows.append(dict(my_s1m=s1m,my_n1m=n1m,my_lag=s1m-n1m,my_vol60=v60,my_vol60_0=np.nanstd(r60,ddof=0)*np.sqrt(252),my_r1w=r1w,
       my_dm1=td[0],my_rd=td[1],my_dp1=td[2],my_3d=td.sum()))
X=pd.concat([ev.reset_index(drop=True),pd.DataFrame(rows)],axis=1)
d=X[['my_dm1','my_rd','my_dp1']].values
X['my_tp']=np.where(d[:,0]>0.03,d[:,0],np.where(d[:,0]+d[:,1]>0.03,d[:,0]+d[:,1],d.sum(1)))
X.to_csv(V+'events_my.csv',index=False)
print(X[['three_day','my_3d']].corr()); print((X.three_day-X.my_3d).abs().max())
