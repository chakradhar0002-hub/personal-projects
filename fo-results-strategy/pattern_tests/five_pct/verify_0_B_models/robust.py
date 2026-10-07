import os  # LAB_ROOT: folder holding search22/, sector/ and sector_lab/data/
import numpy as np, pandas as pd
S=os.environ.get('LAB_ROOT', 'lab') + '/'
pk=pd.read_csv(S+'five_pct/B_models/picks_real_fo.csv'); g=pk[(pk.protocol=='WF')&(pk.family=='RFc+')&(pk.rule=='top2')].copy()
g['r']=g.three_day*100
ev=pd.read_csv(S+'sector_lab/data/events.csv'); R=pd.read_csv(S+'sector_lab/data/returns.csv').set_index('day')
g=g.merge(ev[['symbol','qn','i_cut','i_m1','i_rd','i_p1','results_date']],on=['symbol','qn'])
# window check
g['chk']=[np.nansum(R[s].values[a:b+1])*100 for s,a,b in zip(g.symbol,g.i_m1,g.i_p1)]
print('window recompute max abs diff', (g.chk-g.r).abs().max(), 'span sessions', (g.i_p1-g.i_m1).unique(), (g.i_m1-g.i_cut).unique())
r=g.r.values
print('n',len(r),'gross %.2f net %.2f win %.1f median %.2f'%(r.mean(),r.mean()-.17,(r>0).mean()*100,np.median(r)))
srt=np.sort(r)[::-1]; print('top5 share %.0f%%, ex-top5 %.2f, ex-top1 %.2f, ex-top2 %.2f'%(srt[:5].sum()/r.sum()*100,srt[5:].mean(),srt[1:].mean(),srt[2:].mean()))
loo=[g[g.qn!=q].r.mean() for q in sorted(g.qn.unique())]; print('leave-one-quarter-out range %.2f..%.2f'%(min(loo),max(loo)))
g['year']=pd.to_datetime(g.results_date).dt.year
print(g.groupby('year').r.agg(['size','mean']).round(2).T.to_string())
print('per-quarter', g.groupby('qn').r.mean().round(1).to_dict())
print('symbols', g.symbol.value_counts().head(8).to_dict())
# bootstrap CI of the mean
rng=np.random.default_rng(0); bs=[rng.choice(r,len(r)).mean() for _ in range(20000)]
print('bootstrap 95%% CI %.2f..%.2f, P(mean>=5) %.4f'%(np.percentile(bs,2.5),np.percentile(bs,97.5),np.mean(np.array(bs)>=5)))
# placebo: same stocks, same-length 3-day windows shifted away from results (non-results dates)
Rv=R.values; cols={c:i for i,c in enumerate(R.columns)}
fo=ev[ev.in_fo==True]
for sh in [-30,-20,-10,10,20,30]:
    p=[np.nansum(Rv[a+sh:b+sh+1,cols[s]])*100 for s,a,b in zip(g.symbol,g.i_m1,g.i_p1)]
    base=[np.nanmean(np.nansum(Rv[a+sh:b+sh+1][:,[cols[x] for x in fo[fo.qn==q].symbol if x in cols]],axis=0))*100 for q,a,b in zip(g.qn,g.i_m1,g.i_p1)]
    print(f'placebo shift {sh:+d} sessions: picks avg {np.mean(p):.2f}  all-F&O same dates {np.mean(base):.2f}')
# placebo across all shifts -40..+40 excluding +-5 around results
P=[]
for sh in list(range(-40,-5))+list(range(6,41)):
    P.append(np.mean([np.nansum(Rv[a+sh:b+sh+1,cols[s]])*100 for s,a,b in zip(g.symbol,g.i_m1,g.i_p1)]))
P=np.array(P); print('placebo over 70 shifts: mean %.2f sd %.2f max %.2f; share >= 3.09: %.2f'%(P.mean(),P.std(),P.max(),(P>=3.09).mean()))
