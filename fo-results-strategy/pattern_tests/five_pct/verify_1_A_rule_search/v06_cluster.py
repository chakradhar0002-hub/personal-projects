import pandas as pd, numpy as np
e=pd.read_csv('my_events.csv'); e['pr']=e['pr_industry_rd<cut']; fo=e[e.in_fo==True]
rng=np.random.default_rng(1)
for lab,t in [('candidate',fo[(fo.vs200<=-0.1685)&(fo.vs20hi<=-0.1018)&(fo.pr<=1)]),('no-peer 2-cond',fo[(fo.vs200<=-0.1685)&(fo.vs20hi<=-0.1018)])]:
    g=[x.values*100 for _,x in t.groupby('qn').three_day]
    bs=[np.concatenate([g[i] for i in rng.integers(0,len(g),len(g))]).mean() for _ in range(5000)]
    gd=[x.values*100 for _,x in t.groupby('cutoff').three_day]
    bd=[np.concatenate([gd[i] for i in rng.integers(0,len(gd),len(gd))]).mean() for _ in range(5000)]
    print(lab,'quarter-cluster bootstrap 90% CI',np.percentile(bs,[5,50,95]).round(2),' date-cluster',np.percentile(bd,[5,50,95]).round(2), 'sd trade',round(t.three_day.std()*100,2), 'excess nifty', round(t.excess_nifty.mean()*100,2))
