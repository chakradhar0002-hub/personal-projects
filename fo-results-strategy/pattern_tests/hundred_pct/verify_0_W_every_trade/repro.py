import os  # LAB_ROOT: folder holding search22/, sector/, sector_lab/data/ and five_pct/
import pandas as pd, numpy as np
SP=os.environ.get('LAB_ROOT', 'lab') + ''
d=pd.read_csv(f'{SP}/five_pct/A_rule_search/features_all.csv')
print('dups', d.duplicated(['symbol','qn']).sum(), len(d))
def rule(x, a=154, b=-0.01678, c=0.003908):
    return (x.days_since_dividend>=a)&(x.gap5<=b)&(x.own_dm1<=c)
for uni,sub in [('fo',d[d.in_fo]),('all',d)]:
    p=sub[rule(sub)].copy(); p['r']=p.three_day*100
    print(uni, len(p), 'win%', (p.r>0).mean()*100, 'avg', p.r.mean(), 'win>0.17', (p.r>0.17).mean()*100)
    for nm,s in [('first14',p[p.qn<14]),('last8',p[p.qn>=14])]:
        q=s.groupby('qn').r.mean()
        print(' ',nm,len(s),'wins',(s.r>0).sum(),'win%%=%.1f avg=%.2f med=%.2f worst=%.2f qpos=%d/%d net>0.17 %d'%((s.r>0).mean()*100,s.r.mean(),s.r.median(),s.r.min(),(q>0).sum(),len(q),(s.r>0.17).sum()))
    if uni=='fo':
        print(p[['symbol','qn','cutoff','days_since_dividend','gap5','own_dm1','r','tp3']].to_string())
