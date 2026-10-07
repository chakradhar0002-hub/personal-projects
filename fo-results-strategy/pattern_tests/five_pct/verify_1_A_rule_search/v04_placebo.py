import os  # LAB_ROOT: folder holding search22/, sector/ and sector_lab/data/
import pandas as pd, numpy as np
S=os.environ.get('LAB_ROOT', 'lab') + ''
D=S+'/sector_lab/data/'
e=pd.read_csv('my_events.csv'); r=pd.read_csv(D+'returns.csv').set_index('day')
R=r.values; syms=list(r.columns); col={s:i for i,s in enumerate(syms)}
valid=~np.isnan(R); P=np.cumprod(1+np.where(valid,R,0),axis=0); P[~valid]=np.nan
Pf=pd.DataFrame(P).ffill()
ma200=Pf.rolling(200,min_periods=200).mean().values; hi20=Pf.rolling(20,min_periods=20).max().values
Pf=Pf.values
vs200=Pf/ma200-1; vs20=Pf/hi20-1
Rz=np.where(valid,R,np.nan)
fwd=np.full_like(R,np.nan)
fwd[:-3]=Rz[1:-2]+Rz[2:-1]+Rz[3:]   # sum of next 3 daily returns (cutoff+1..cutoff+3)
cond=(vs200<=-0.1685)&(vs20<=-0.1018)
# exclude windows within 10 sessions of any result event of that stock
near=np.zeros_like(cond)
for s,ic in zip(e.symbol,e.i_cut):
    if s in col: near[max(0,ic-10):ic+11,col[s]]=True
days=pd.to_datetime(r.index)
period=(days>=pd.Timestamp('2021-03-01'))[:,None]&np.ones_like(cond)
# restrict placebo to F&O-symbol columns via in_fo period: use first in_fo date per symbol
fo_start={}
for s,g in e[e.in_fo==True].groupby('symbol'): fo_start[s]=g.i_cut.min()
fomask=np.zeros_like(cond)
for s,i0 in fo_start.items(): fomask[i0:,col[s]]=True
def rep(m,lab):
    x=fwd[m]; x=x[~np.isnan(x)]*100
    print(f"{lab}: n={len(x)} mean={x.mean():.2f} median={np.median(x):.2f} win={(x>0).mean()*100:.1f}")
rep(cond&period&~near,'placebo all stocks, non-results days since 2021')
rep(cond&period&~near&fomask,'placebo F&O-era, non-results days')
rep(period&~near&fomask&~np.isnan(vs200),'unconditional F&O-era non-results days')
# by-date clustered placebo: average per date then mean
m=cond&period&~near&fomask
dm=np.nanmean(np.where(m,fwd,np.nan),axis=1); print('placebo mean of daily averages', np.nanmean(dm)*100, 'dates', np.sum(~np.isnan(dm)))
# placebo: same events shifted +/- k sessions (same stocks, same season-ish), price conditions recomputed, peer cond dropped
for k in [-20,-10,10,20,40]:
    xs=[]
    for s,ic in zip(e[e.in_fo==True].symbol,e[e.in_fo==True].i_cut):
        j=col[s]; i=ic+k
        if 0<=i<len(R)-3 and cond[i,j] and not np.isnan(fwd[i,j]): xs.append(fwd[i,j])
    print('shift',k,'n',len(xs),'mean',round(np.mean(xs)*100,2))
np.save('placebo_pieces.npy',np.array([0]))
