import os  # LAB_ROOT: scratch folder with search22/, sector/, sector_lab/data/, five_pct/; REPO_ROOT: this repo
import pandas as pd, numpy as np
D=os.environ.get('LAB_ROOT', 'lab') + '/sector_lab/data/'
V=os.environ.get('LAB_ROOT', 'lab') + '/lag5/verify_0_A_splits/'
ev=pd.read_csv(D+'events.csv'); R=pd.read_csv(D+'returns.csv',index_col=0); ic=pd.read_csv(D+'index_close.csv',index_col=0)
r=R.values; nif=ic['Nifty 50'].values
L=pd.DataFrame(np.cumprod(1+np.nan_to_num(r),axis=0)); L[pd.DataFrame(r).isna().cumprod().astype(bool).values]=np.nan
r1m=(L/L.shift(21)-1).values
n1m=np.r_[np.full(21,np.nan),nif[21:]/nif[:-21]-1]
vol60=(pd.DataFrame(r).rolling(60,min_periods=41).std()*np.sqrt(252)).values
lag=r1m-n1m[:,None]
fwd=np.full_like(r,np.nan); fwd[:-3]=np.nan_to_num(r[1:-2])+np.nan_to_num(r[2:-1])+np.nan_to_num(r[3:])
nf=np.full(len(nif),np.nan); nf[:-3]=nif[3:]/nif[:-3]-1
qcut=ev.groupby('qn').i_cut.median()
lo=int(ev[ev.qn==0].i_cut.min())-20; hi=int(ev[ev.qn==21].i_cut.max())+20
out=[]
for s,gq in ev.groupby('symbol'):
    if s not in R.columns: continue
    j=R.columns.get_loc(s); gq=gq.sort_values('i_cut'); rds=gq.i_rd.values; cuts=gq.i_cut.values; fo=gq.in_fo.values
    for c in range(lo,min(hi,len(nif)-4)+1):
        if not (lag[c,j]<-0.05): continue
        if ((rds>=c-10)&(rds<=c+13)).any(): continue
        k=np.searchsorted(cuts,c); prev=fo[k-1] if k>0 else None; nxt=fo[k] if k<len(fo) else None
        vals=[v for v in (prev,nxt) if v is not None]
        if not all(v==True for v in vals): continue
        out.append((s,c,lag[c,j],vol60[c,j],100*fwd[c,j],100*(fwd[c,j]-(nf[c]*3/3 if False else 0)),100*nf[c]))
P=pd.DataFrame(out,columns=['symbol','c','lag','vol60','ret','ret2','nifty3'])
P['exn']=P.ret-P.nifty3
qv,qc=qcut.index.values,qcut.values; P['qn']=qv[np.abs(P.c.values[:,None]-qc[None,:]).argmin(1)]
P.to_csv(V+'placebo_my.csv',index=False)
def st(s,lab):
    pq=s.groupby('qn').ret.mean()
    print(f"{lab}: n={len(s)} avg={s.ret.mean():.2f} exNifty={s.exn.mean():.2f} f14={s[s.qn<14].ret.mean():.2f} l8={s[s.qn>=14].ret.mean():.2f} qpos={(pq>0).sum()}/{len(pq)} qmean={pq.mean():.2f}")
st(P,'placebo lag>5')
st(P[P.lag<-0.15],'placebo lag>15')
st(P[(P.lag<-0.15)&(P.vol60>=0.35)],'placebo COMBO')
st(P[(P.lag<-0.15)&(P.vol60<0.35)],'placebo lag>15 vol<35')
st(P[(P.lag>=-0.15)&(P.vol60>=0.35)],'placebo lag5-15 vol>=35')
st(P[(P.lag<-0.20)&(P.vol60>=0.35)],'placebo lag>20 vol>=35')
# one obs per stock per quarter (first qualifying day) to reduce overlap
f=P[(P.lag<-0.15)&(P.vol60>=0.35)].sort_values('c').groupby(['symbol','qn']).head(1); st(f,'placebo COMBO first-day per stock-quarter')
