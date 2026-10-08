import os  # LAB_ROOT: folder holding search22/, sector/, sector_lab/data/ and five_pct/
import pandas as pd, numpy as np
D=os.environ.get('LAB_ROOT', 'lab') + '/sector_lab/data/'
ev=pd.read_csv(D+'events.csv'); ret=pd.read_csv(D+'returns.csv',index_col=0); intr=pd.read_csv(D+'intraday.csv',index_col=0); idx=pd.read_csv(D+'index_close.csv',index_col=0)
R=ret.values; I=intr.values; T=len(ret)
A,B,C=-0.02782,-0.00891,-0.01338
# best trade in candidate
c=pd.read_csv('cand_trades.csv'); print('top 5 candidate trades:'); print(c.nlargest(5,'pnl')[['symbol','qn','cutoff','pnl','dm1','rd','dp1']].to_string())
rows=[]
for sym,g in ev[ev.in_fo==True].groupby('symbol'):
    c=ret.columns.get_loc(sym); si=g.sector_index.iloc[0]
    x=idx[si].values if si in idx.columns else None
    lo,hi=g.i_cut.min(),g.i_cut.max()
    allres=ev[ev.symbol==sym].i_rd.values
    for i in range(max(lo,3),min(hi,T-4)+1):
        if np.min(np.abs(allres-(i+2)))<=10: continue
        r3=np.prod(1+R[i-2:i+1,c])-1; f=R[i+1:i+4,c].sum()
        s3=x[i]/x[i-3]-1 if x is not None else np.nan
        rows.append((sym,i,r3,I[i,c],s3,-f))
P=pd.DataFrame(rows,columns=['sym','i','r3d','intra0','sec_3d','pnl']).dropna()
P['day']=ret.index.values[P.i]; P['month']=P.day.str[:7]
print('placebo stock-days',len(P))
S=P[(P.r3d<=A)&(P.intra0<=B)&(P.sec_3d>=C)]
print('placebo filter hits',len(S),'win',round(100*(S.pnl>0).mean(),1),'avg',round(100*S.pnl.mean(),2),'(all placebo days short avg',round(100*P.pnl.mean(),3),')')
S=S.assign(q=pd.PeriodIndex(S.day,freq='Q'))
qq=S.groupby('q').pnl.mean(); print('placebo calendar quarters positive',(qq>0).sum(),'/',len(qq))
S['year']=S.day.str[:4]; print(S.groupby('year').pnl.agg(n='size',avg=lambda x:round(100*x.mean(),2),win=lambda x:round(100*(x>0).mean(),1)).to_string())
# random-pick baseline: draw same per-quarter counts of results-window shorts from in_fo at random
m=pd.read_csv('rebuilt.csv'); fo=m[m.in_fo==True].copy(); fo['pnl']=-fo.td
cand=pd.read_csv('cand_trades.csv'); cnt=cand.groupby('qn').size()
rng=np.random.default_rng(5); res=[]
grp={q:fo[fo.qn==q].pnl.values for q in range(22)}
for _ in range(5000):
    qa=np.array([rng.choice(grp[q],cnt[q],replace=False).mean() for q in range(22)])
    res.append(((qa[:14]>0).sum(),(qa[14:]>0).sum(),(qa>0).sum()))
res=np.array(res)
print('random same-size picks: P(14/14 first14)=',(res[:,0]==14).mean(),' P(>=5/8 last8)=',(res[:,1]>=5).mean(),' P(>=19/22)=',(res[:,2]>=19).mean(), ' P(22/22)=',(res[:,2]==22).mean())
