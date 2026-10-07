import pandas as pd, numpy as np
e=pd.read_csv('my_events.csv'); e['pr']=e['pr_industry_rd<cut']
fo=e[e.in_fo==True].copy()
rule=lambda d,a=-0.1685,b=-0.1018,c=1: d[(d.vs200<=a)&(d.vs20hi<=b)&(d.pr<=c)]
t=rule(fo)
pd.set_option('display.width',200)
print(t[['symbol','qn','cutoff','results_date','industry','vs200','vs20hi','pr','three_day']].sort_values('cutoff').assign(three_day=lambda d:(d.three_day*100).round(2)).to_string())
print('\nper quarter:'); print(t.groupby('qn').three_day.agg(['size','mean']).assign(mean=lambda d:(d['mean']*100).round(2)))
print('distinct cutoff dates', t.cutoff.nunique(), ' trades in top 3 dates:', t.cutoff.value_counts().head(3).to_dict())
t['yr']=t.results_date.str[:4]; print('\nby year', t.groupby('yr').three_day.agg(['size','mean']).assign(mean=lambda d:(d['mean']*100).round(2)).to_dict())
# LOO quarter
print('\nleave one quarter out:', {q: round(t[t.qn!=q].three_day.mean()*100,2) for q in t.qn.unique()})
# date-clustered: average by cutoff date then mean
print('mean of per-cutoff-date averages', round(t.groupby('cutoff').three_day.mean().mean()*100,2))
# neighbouring thresholds
print('\nneighbour grid (n, mean%)')
for c in [0,1,2,3,5,99]:
  row=[]
  for a in [-0.10,-0.125,-0.15,-0.1685,-0.19,-0.22,-0.25]:
    for b in [-0.07,-0.1018,-0.13]:
      s=rule(fo,a,b,c); row.append(f"{a:.3f}/{b:.3f}:{len(s)},{s.three_day.mean()*100:.1f}")
  print('peers<=',c,' | '.join(row))
# all stocks
a=rule(e); print('\nall stocks', len(a), round(a.three_day.mean()*100,2), 'preFO', (a.in_fo!=True).sum(), round(a[a.in_fo!=True].three_day.mean()*100,2))
# excess vs nifty
print('excess_nifty mean', round(t.excess_nifty.mean()*100,2))
