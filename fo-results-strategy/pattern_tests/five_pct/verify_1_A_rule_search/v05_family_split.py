# Small family (the candidate's own 3 features, threshold grid). Choose on qn<=13, test on qn>=14; walk-forward; shuffles.
import pandas as pd, numpy as np
e=pd.read_csv('my_events.csv'); e['pr']=e['pr_industry_rd<cut']
fo=e[(e.in_fo==True)&e.vs200.notna()].reset_index(drop=True)
A=np.quantile(fo.vs200,np.linspace(0.01,0.30,30)); B=np.quantile(fo.vs20hi,np.linspace(0.01,0.30,30)); C=[0,1,2,3,5,99]
masks=[];labs=[]
for a in A:
  for b in B:
    for c in C:
      masks.append(((fo.vs200<=a)&(fo.vs20hi<=b)&(fo.pr<=c)).values); labs.append((a,b,c))
M=np.array(masks,dtype=np.float32); print('family size',len(M))
qn=fo.qn.values; y0=fo.three_day.values
OH=np.zeros((len(qn),22),np.float32); OH[np.arange(len(qn)),qn]=1
Nq=M@OH  # rules x quarters counts
def run(y,minn_in=10):
    Sq=M@(OH*y[:,None].astype(np.float32))
    def pick(qs,minn):
        n=Nq[:,qs].sum(1); s=Sq[:,qs].sum(1); m=np.where(n>=minn,s/np.maximum(n,1),-9); return m.argmax(), m.max()
    k,best=pick(slice(0,14),minn_in)
    on=Nq[k,14:].sum(); oos=Sq[k,14:].sum()/on if on else np.nan
    ws=0;wn=0
    for q in range(6,22):
        k2,_=pick(slice(0,q),max(5,int(minn_in*q/14))); ws+=Sq[k2,q]; wn+=Nq[k2,q]
    kall,ball=pick(slice(0,22),30)
    return best*100,oos*100,on,(ws/wn*100 if wn else np.nan),wn,ball*100,k
for minn in [10,19]:
    b,o,no,w,nw,ball,k=run(y0,minn)
    print(f'REAL minn={minn}: in-sample best {b:.2f} rule {np.round(labs[k],4)}; last8 {o:.2f} on {no}; walkfwd {w:.2f} on {nw}; all-22 best(n>=30) {ball:.2f}')
rng=np.random.default_rng(0)
res=[]
for it in range(200):
    y=y0.copy()
    for q in np.unique(qn):
        idx=np.where(qn==q)[0]; y[idx]=rng.permutation(y[idx])
    res.append(run(y,10)[:6])
res=np.array(res,dtype=float)
print('SHUFFLED within quarter (200): in-sample best median %.2f p95 %.2f; last8 mean %.2f; walkfwd mean %.2f; all22 best n>=30 median %.2f p95 %.2f'%(np.median(res[:,0]),np.percentile(res[:,0],95),np.nanmean(res[:,1]),np.nanmean(res[:,3]),np.median(res[:,5]),np.percentile(res[:,5],95)))
real_all=run(y0,10)[5]
print('p(all22 best >= real)', (res[:,5]>=real_all).mean())
# sign-flip (keeps stock & move size, random direction) - captures that oversold names have big moves
res2=[]
for it in range(200):
    y=y0*rng.choice([-1,1],size=len(y0)); res2.append(run(y,10)[:6])
res2=np.array(res2,dtype=float)
print('SIGN-FLIP (200): in-sample best median %.2f; all22 best n>=30 median %.2f p95 %.2f p=%.3f'%(np.median(res2[:,0]),np.median(res2[:,5]),np.percentile(res2[:,5],95),(res2[:,5]>=real_all).mean()))
