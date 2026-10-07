"""Extra descriptive checks on the base trade list (no new rule variants):
 - t of last-8 and first-14 per-quarter means alone
 - path: hedged return accumulated by day 1, 5, 10, 20 after entry
 - split by result timing (after close vs during market)
 - non-results placebo sensitivity to the exclusion window (+-10, +-20, +-30 sessions)
"""
import os  # SECTOR_LAB: folder holding data/ from sector_lab_data.py
import sys; sys.path.append('/root/.local/lib/python3.11/site-packages')
import numpy as np, pandas as pd
D=os.environ.get('SECTOR_LAB', 'sector_lab') + '/data/'
O=os.environ.get('SECTOR_LAB', 'sector_lab') + '/verify_2_F3_sector_drift/'
b=pd.read_csv(O+'base_trades.csv'); ev=pd.read_csv(D+'events.csv')
R=pd.read_csv(D+'returns.csv',index_col=0); IX=pd.read_csv(D+'index_close.csv',index_col=0)
Rv=R.values; N=len(R); syms=list(R.columns); sidx={s:k for k,s in enumerate(syms)}
CG=np.vstack([np.ones((1,Rv.shape[1])),np.cumprod(np.nan_to_num(Rv)+1,axis=0)])
nf=IX['Nifty 50'].values; nret=np.r_[np.nan,nf[1:]/nf[:-1]-1]
def tq(s):
    g=s; return g.mean(), g.mean()/(g.std()/np.sqrt(len(g)))
g=b.groupby('qn').hedged.mean()
for lab,sel in [('first14',g.index<=13),('last8',g.index>=14),('qn0-6',g.index<=6),('qn7-13',(g.index>=7)&(g.index<=13))]:
    m,t=tq(g[sel]); print(f'{lab}: perQ {100*m:.2f} t {t:.2f} nQ {sel.sum()}')
for h in [1,2,5,10,20]:
    v=[CG[r.i0+h+1,sidx[r.symbol]]/CG[r.i0+1,sidx[r.symbol]]-1-(nf[r.i0+h]/nf[r.i0]-1) for r in b.itertuples()]
    print(f'gross hedged after {h} sessions: {100*np.mean(v):.2f}')
e=ev.set_index(['symbol','i_react'])
b['timing']=[e.loc[(r.symbol,r.i0),'timing'] if (r.symbol,r.i0) in e.index else None for r in b.itertuples()]
print(b.groupby('timing').hedged.agg(['mean','size']).assign(mean=lambda x:(100*x['mean']).round(2)))
# non-results placebo window sensitivity
span=ev[ev.in_fo==True].assign(k=lambda x:x.symbol.map(sidx)).groupby('k').agg(lo=('i_react','min'),hi=('i_react','max'))
beat=Rv-nret[:,None]
for W in [10,20,30]:
    near=np.zeros_like(Rv,dtype=bool)
    for s,i in zip(ev.symbol,ev.i_react):
        if s in sidx: near[max(0,i-W):min(N,i+W+1),sidx[s]]=True
    rows=[]
    for k,(lo,hi) in span.iterrows():
        for i in range(lo,min(hi+1,N-21)):
            if not near[i,k] and beat[i,k]>0.06:
                raw=CG[i+21,k]/CG[i+1,k]-1; rows.append((R.index[i],raw-(nf[i+20]/nf[i]-1)-0.0019))
    d=pd.DataFrame(rows,columns=['day','h']); d['cq']=pd.to_datetime(d.day).dt.to_period('Q')
    gq=d.groupby('cq').h.mean()
    print(f'non-results +-{W}: n={len(d)} trade {100*d.h.mean():.2f} median {100*d.h.median():.2f} perCalQ {100*gq.mean():.2f}; trimmed(drop top/bottom 2%) {100*d.h[(d.h>d.h.quantile(.02))&(d.h<d.h.quantile(.98))].mean():.2f}')
print('base median hedged', round(100*b.hedged.median(),2), 'trimmed', round(100*b.hedged[(b.hedged>b.hedged.quantile(.02))&(b.hedged<b.hedged.quantile(.98))].mean(),2))
