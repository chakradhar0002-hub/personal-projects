import os  # LAB_ROOT: scratch folder with search22/, sector/, sector_lab/data/, five_pct/; REPO_ROOT: this repo
import pandas as pd, numpy as np
from scipy import stats
V=os.environ.get('LAB_ROOT', 'lab') + '/lag5/verify_0_A_splits/'
X=pd.read_csv(V+'events_my.csv'); X['ret']=X.my_3d*100; X['tp']=X.my_tp*100
X['exn']=X.excess_nifty*100; X['year']=X.results_date.str[:4]
fo=X[X.in_fo==True]; g=fo[fo.my_lag<-0.05].copy()
def st(s):
    pq=s.groupby('qn').ret.mean()
    return dict(n=len(s),avg=round(s.ret.mean(),2),tp=round(s.tp.mean(),2),f14=round(s[s.qn<14].ret.mean(),2),n14=(s.qn<14).sum(),
        l8=round(s[s.qn>=14].ret.mean(),2),n8=(s.qn>=14).sum(),qpos=f"{(pq>0).sum()}/{len(pq)}",
        tq=round(pq.mean()/(pq.std(ddof=1)/np.sqrt(len(pq))),2) if len(pq)>2 else np.nan, med=round(s.ret.median(),2))
print('== threshold grid: avg (n) [f14 / l8]')
rows=[]
for L in [0.10,0.12,0.13,0.14,0.15,0.16,0.17,0.18,0.20]:
    for vv in [0.0,0.25,0.30,0.32,0.35,0.38,0.40,0.45,0.50]:
        s=g[(g.my_lag<-L)&(g.my_vol60>=vv)]; d=st(s); d.update(L=L,v=vv); rows.append(d)
G=pd.DataFrame(rows)
for k in ['avg','n','f14','l8']:
    print(k); print(G.pivot(index='L',columns='v',values=k).to_string())
c=g[(g.my_lag<-0.15)&(g.my_vol60>=0.35)].copy()
print('\nCOMBO',st(c))
print('excess over Nifty (3d):',round(c.exn.mean(),2),' whole group exn',round(g.exn.mean(),2))
print('lag>15 & vol<35 (complement):',st(g[(g.my_lag<-0.15)&(g.my_vol60<0.35)]))
print('vol>=35 & lag 5-15:',st(g[(g.my_lag>=-0.15)&(g.my_vol60>=0.35)]))
print('vol>=35 all group:',st(g[g.my_vol60>=0.35]), ' vol<25:',st(g[g.my_vol60<0.25]))
s=np.sort(c.ret.values); print('without best5',round(s[:-5].mean(),2),' without best3',round(s[:-3].mean(),2),' without worst5',round(s[5:].mean(),2), 'median',round(np.median(s),2))
print('trimmed mean 10%',round(stats.trim_mean(s,0.1),2))
qc=c.groupby('qn').ret.agg(['size','mean','sum']); print(qc.T.round(2).to_string())
for drop in qc['sum'].sort_values(ascending=False).index[:2]:
    print('drop quarter',drop, st(c[c.qn!=drop]))
print('leave-one-quarter-out min/max avg', round(min(c[c.qn!=k].ret.mean() for k in qc.index),2), round(max(c[c.qn!=k].ret.mean() for k in qc.index),2))
print('by industry'); print(c.groupby('industry').ret.agg(['size','mean']).sort_values('size',ascending=False).head(12).round(2).to_string())
print('leave-one-industry-out min', round(min(c[c.industry!=k].ret.mean() for k in c.industry.unique()),2))
print('by sector_index'); print(c.groupby('sector_index').ret.agg(['size','mean']).round(2).to_string())
print('by year'); print(c.groupby('year').ret.agg(['size','mean']).round(2).to_string())
print('by symbol repeats'); print(c.symbol.value_counts().head(5).to_string())
# t-test across trades and across quarters
print('t trades',stats.ttest_1samp(c.ret,0)); 
# within lag>15%: does vol matter? regression
h=g[g.my_lag<-0.15]; print('within lag>15 corr(vol60,ret)',stats.spearmanr(h.my_vol60,h.ret), 'f14',stats.spearmanr(h[h.qn<14].my_vol60,h[h.qn<14].ret),'l8',stats.spearmanr(h[h.qn>=14].my_vol60,h[h.qn>=14].ret))
import statsmodels.api as sm
