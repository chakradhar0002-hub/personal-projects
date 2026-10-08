import os  # LAB_ROOT: folder holding search22/, sector/, sector_lab/data/ and five_pct/
import pandas as pd, numpy as np, itertools
m=pd.read_csv('rebuilt.csv'); fo=m[m.in_fo==True].copy(); fo['pnl']=-fo.td
fo['year']=pd.to_datetime(fo.cutoff).dt.year
def st(p):
    q=p.groupby('qn').pnl.mean()
    return dict(n=len(p),win=round(100*(p.pnl>0).mean(),1),avg=round(100*p.pnl.mean(),2),qpos=f"{(q>0).sum()}/{len(q)}",
                is_q=f"{(q[q.index<14]>0).sum()}/{(q.index<14).sum()}",oos_q=f"{(q[q.index>=14]>0).sum()}/{(q.index>=14).sum()}",
                oos_avg=round(100*p[p.qn>=14].pnl.mean(),2) if (p.qn>=14).any() else np.nan)
A,B,C=-0.02782,-0.00891,-0.01338
base=fo[(fo.r3d_cmp<=A)&(fo.intra0<=B)&(fo.sec_3d>=C)]
print('BASE',st(base))
print('\n-- neighbour grid (r3d cut, intra0 cut, sec_3d cut)')
rows=[]
for a in [-0.015,-0.02,-0.025,-0.02782,-0.03,-0.035,-0.04,-0.05]:
  for b in [0,-0.005,-0.00891,-0.0125,-0.015,-0.02]:
    for c in [-1,-0.02,-0.01338,-0.01,-0.005,0]:
      p=fo[(fo.r3d_cmp<=a)&(fo.intra0<=b)&(fo.sec_3d>=c)]
      d=st(p); d.update(a=a,b=b,c=c); rows.append(d)
G=pd.DataFrame(rows); G.to_csv('neighbour_grid.csv',index=False)
G['is_all']=G.is_q.str.split('/').apply(lambda x:x[0]==x[1]); G['oosn']=G.oos_q.str.split('/').str[0].astype(int)
print('grid cells',len(G),'with 14/14 in-sample:',G.is_all.sum(),'; 22/22 all quarters:',(G.qpos=='22/22').sum())
print('OOS quarters positive across grid: ',G.oosn.value_counts().sort_index().to_dict(),' median oos avg',G.oos_avg.median())
print('cells with all 22 quarters positive:'); print(G[G.qpos.str.split('/').apply(lambda x:x[0]==x[1])].to_string())
print('\n-- single-condition pieces')
for nm,p in [('r3d<=A only',fo[fo.r3d_cmp<=A]),('intra0<=B only',fo[fo.intra0<=B]),('sec_3d>=C only',fo[fo.sec_3d>=C]),
             ('r3d & intra0',fo[(fo.r3d_cmp<=A)&(fo.intra0<=B)]),('r3d & sec',fo[(fo.r3d_cmp<=A)&(fo.sec_3d>=C)]),('intra0 & sec',fo[(fo.intra0<=B)&(fo.sec_3d>=C)])]:
    print(f'{nm:16s}',st(p))
print('\n-- without best trades')
b=base.sort_values('pnl',ascending=False)
for k in [1,3,5,10,15]:
    print('drop best',k,st(b.iloc[k:]))
print('\n-- by year'); print(base.groupby('year').pnl.agg(n='size',avg=lambda x:round(100*x.mean(),2),win=lambda x:round(100*(x>0).mean(),1)).to_string())
print('\n-- leave one quarter out (pooled avg, win)')
lo=[(q,round(100*base[base.qn!=q].pnl.mean(),2)) for q in range(22)]; print(lo)
print('\n-- per-trade: losers >5%',(base.pnl<-0.05).sum(),' worst 5',(100*base.pnl.nsmallest(5)).round(2).tolist())
print('per-quarter win rates',base.groupby('qn').pnl.apply(lambda x:f"{(x>0).sum()}/{len(x)}").tolist())
print('quarters where EVERY trade won:',(base.groupby('qn').pnl.min()>0).sum(), 'of 22')
# chance future quarter positive: quarter averages last 8
q=base.groupby('qn').pnl.mean()
print('quarter avg sd (all)',round(100*q.std(),2),'mean first14',round(100*q[:14].mean(),2),'last8',round(100*q[14:].mean(),2), 'last 8 list',(100*q[14:]).round(2).tolist())
from scipy import stats
print('t-test last8 trades mean>0 p=',stats.ttest_1samp(base[base.qn>=14].pnl,0).pvalue/2, ' last8 quarter means p=',stats.ttest_1samp(q[14:],0).pvalue/2)
print('t-test first14 vs last8 trade means p=',stats.ttest_ind(base[base.qn<14].pnl,base[base.qn>=14].pnl).pvalue)
# all-stocks
