import os  # LAB_ROOT: scratch folder with search22/, sector/, sector_lab/data/, five_pct/; REPO_ROOT: this repo
# build price-only features for every stock-day + mark results rows; output panel.pkl
import numpy as np, pandas as pd
S=os.environ.get('LAB_ROOT', 'lab') + '/'
DD=S+'sector_lab/data/'
r=pd.read_csv(DD+'returns.csv').set_index('day'); ic=pd.read_csv(DD+'index_close.csv').set_index('day')
e=pd.read_csv(DD+'events.csv')
nif=ic['Nifty 50'].reindex(r.index).ffill(); nr=nif.pct_change()
R=r.values; T,Nn=R.shape
P=np.nancumprod(np.where(np.isnan(R),0,R)+1,axis=0); P[np.isnan(R)]=np.nan
P=pd.DataFrame(P,index=r.index,columns=r.columns)
Rr=pd.DataFrame(R,index=r.index,columns=r.columns)
def ret(k): return P/P.shift(k)-1
F={}
for nm,k in [('r1w',5),('r1m',21),('r3m',63),('r6m',126),('r1y',252),('r3d',3),('r10d',10),('r20d',20),('r2d',2),('pre5',5)]: F[nm]=ret(k)
NR={k:(nif/nif.shift(k)-1) for k in (1,3,5,10,21,63)}
F['vs_nifty_1w']=F['r1w'].sub(NR[5],axis=0); F['vs_nifty_1m']=F['r1m'].sub(NR[21],axis=0); F['vs_nifty_3m']=F['r3m'].sub(NR[63],axis=0)
F['exn_3d']=F['r3d'].sub(NR[3],axis=0); F['exn_10d']=F['r10d'].sub(NR[10],axis=0)
sd60=Rr.rolling(60,min_periods=40).std(); F['vol60']=sd60*np.sqrt(252)
F['vol5_60']=Rr.rolling(5).std()/sd60; F['vol20_60']=Rr.rolling(20).std()/sd60
F['from_52w_high']=P/P.rolling(252,min_periods=120).max()-1; F['from_52w_low']=P/P.rolling(252,min_periods=120).min()-1
F['vs_ma50']=P/P.rolling(50).mean()-1; F['vs_ma200']=P/P.rolling(200,min_periods=150).mean()-1
F['dist_20h']=P/P.rolling(20).max()-1; F['dist_20l']=P/P.rolling(20).min()-1; F['dist_60h']=P/P.rolling(60).max()-1
F['d0']=Rr; F['d1']=Rr.shift(1); F['d2']=Rr.shift(2); F['maxabs5']=Rr.abs().rolling(5).max()
F['z5']=F['pre5']/(sd60*np.sqrt(5)); F['z20']=F['r20d']/(sd60*np.sqrt(20)); F['up10']=(Rr>0).astype(float).where(Rr.notna()).rolling(10).mean()
F['exn_d0']=Rr.sub(nr,axis=0)
fwd=Rr.shift(-1)+Rr.shift(-2)+Rr.shift(-3)
NIF={'nifty_1w':NR[5],'nifty_1m':NR[21],'nifty_3m':NR[63],'nifty_d0':NR[1],'nifty_3d':NR[3]}
i0=e.i_cut.min()-5; i1=e.i_p1.max()
idx=np.arange(i0,i1-2)
cols=list(F)
long=[]
for c in r.columns:
    d=pd.DataFrame({k:F[k][c].values[idx] for k in cols}); d['i']=idx; d['symbol']=c; d['fwd']=fwd[c].values[idx]
    long.append(d)
pan=pd.concat(long,ignore_index=True)
for k,v in NIF.items(): pan[k]=v.values[pan.i]
pan=pan.dropna(subset=['fwd','r1m','vol60'])
# results proximity
ev=e[['symbol','i_cut','i_rd','qn','in_fo','quarter']]
near=np.zeros(len(pan),bool)
evd={s:g.i_rd.values for s,g in ev.groupby('symbol')}
for s,ix in pan.groupby('symbol').groups.items():
    rd=evd.get(s,np.array([]))
    ii=pan.loc[ix,'i'].values
    if len(rd): near[pan.index.get_indexer(ix)]=(np.abs(ii[:,None]-rd[None,:])<=10).any(1)
pan['near_result']=near
# in_fo proxy: in_fo of nearest event of that symbol
fo=[]
for s,ix in pan.groupby('symbol').groups.items():
    g=ev[ev.symbol==s].sort_values('i_cut')
    ii=pan.loc[ix,'i'].values
    if len(g)==0: fo.append(pd.Series(False,index=ix)); continue
    j=np.abs(ii[:,None]-g.i_cut.values[None,:]).argmin(1); fo.append(pd.Series(g.in_fo.values[j],index=ix))
pan['in_fo']=pd.concat(fo).reindex(pan.index).astype(bool)
pan['fwd']*=100
pan.to_pickle(S+'lag5/verify_1_B_search/panel.pkl')
# results-row features at i_cut
res=ev.merge(pan.drop(columns=['in_fo']),left_on=['symbol','i_cut'],right_on=['symbol','i'],how='left')
res.to_pickle(S+'lag5/verify_1_B_search/res_price.pkl')
print(pan.shape, pan.near_result.mean(), res.shape, res.r1m.isna().mean())
