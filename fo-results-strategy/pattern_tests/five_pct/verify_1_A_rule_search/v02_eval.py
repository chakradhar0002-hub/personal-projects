import os  # LAB_ROOT: folder holding search22/, sector/ and sector_lab/data/
import pandas as pd, numpy as np
S=os.environ.get('LAB_ROOT', 'lab') + ''
e=pd.read_csv('my_events.csv')
f=pd.read_csv(S+'/search22/features.csv')
m=e.merge(f[['symbol','qn','vs_ma200','peers_reported_n','peers_reported_3d']],on=['symbol','qn'],how='left')
print('vs200 corr with features vs_ma200', m[['vs200','vs_ma200']].corr().iloc[0,1], (m.vs200-m.vs_ma200).abs().describe())
for c in [c for c in e.columns if c.startswith('pr_')]:
    print(c, 'agree with peers_reported_n:', (m[c]==m.peers_reported_n).mean().round(3))
def stats(t,lab):
    x=t.three_day*100
    if len(x)==0: print(lab,'none'); return
    qa=t.groupby('qn').three_day.mean()*100
    top=x.sort_values(ascending=False)
    print(f"{lab}: n={len(x)} q={t.qn.nunique()} mean={x.mean():.2f} net={x.mean()-0.17:.2f} qavg={qa.mean():.2f} med={x.median():.2f} win={(x>0).mean()*100:.1f} top5share={top[:5].sum()/x.sum()*100:.0f}% ex5={top[5:].mean():.2f} first14={x[t.qn<=13].mean():.2f}({(t.qn<=13).sum()}) last8={x[t.qn>=14].mean():.2f}({(t.qn>=14).sum()})")
fo=e[e.in_fo==True]
for c in [c for c in e.columns if c.startswith('pr_')]:
    t=fo[(fo.vs200<=-0.1685)&(fo.vs20hi<=-0.1018)&(fo[c]<=1)]
    stats(t,c)
t=fo[(fo.vs200<=-0.1685)&(fo.vs20hi<=-0.1018)]; stats(t,'no peer cond')
