import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from scipy import stats
D=S+'lag5/verify_1_B_search/'
g,feats=load()
E=pd.read_csv(D+'ensemble_scores.csv'); t=E[E.score>=E.thr].merge(g[['symbol','quarter']+feats],on=['symbol','quarter'])
prof=lambda d:(d.vol60>=0.35)&(d.r6m<=-0.2)
deep=lambda d:(d.vs_nifty_1m<=-0.15)|(d.r3d<=-0.08)
for nm,fn in [('profile vol60>=.35&r6m<=-.2',prof),('deep: lag15 or r3d<=-8%',deep)]:
    k=fn(t); print(nm,': picks in rule',k.sum(),'avg',t[k].ret.mean().round(2),'| picks outside',(~k).sum(),'avg',t[~k].ret.mean().round(2))
    gg=g[g.qn>=8]; k2=fn(gg); print('   rule on group q8-21: n',k2.sum(),'avg',gg[k2].ret.mean().round(2), ' all22 n',fn(g).sum(),'avg',g[fn(g)].ret.mean().round(2),'q14-21',g[fn(g)&(g.qn>=14)].ret.mean().round(2))
# patterns: rank corr with ret, first14 vs last8, tercile spread
rows=[]
for f in feats:
    a=g[g.qn<=13]; b=g[g.qn>=14]
    def sp(d):
        d=d[[f,'ret']].dropna()
        if len(d)<60 or d[f].nunique()<3: return np.nan,np.nan
        c=stats.spearmanr(d[f],d.ret).statistic
        lo,hi=d[f].quantile([1/3,2/3]); return c, d[d[f]>=hi].ret.mean()-d[d[f]<=lo].ret.mean()
    c1,s1=sp(a); c2,s2=sp(b); rows.append((f,c1,s1,c2,s2))
P=pd.DataFrame(rows,columns=['feat','rho14','spread14','rho8','spread8']).dropna()
P['same']=np.sign(P.rho14)==np.sign(P.rho8); P['minabs']=np.where(P.same,np.minimum(P.rho14.abs(),P.rho8.abs()),0)
print('\nfeatures with same-sign rank corr in both halves, strongest:'); print(P.sort_values('minabs',ascending=False).head(12).round(3).to_string(index=False))
print('share same sign', P.same.mean().round(2), 'of', len(P))
# bouncers vs fallers medians
b=g[g.ret>3]; f_=g[g.ret<-3]
print('\nn bouncers',len(b),'fallers',len(f_))
for c in ['vs_nifty_1m','vol60','r6m','r3d','from_52w_high','iv_t5','own_abs3d','past_avg_3d','log_mcap','india_vix','prev1_3d']:
    print(c, round(b[c].median(),3), round(f_[c].median(),3), round(g[(g.ret.abs()<=3)][c].median(),3))
