import os  # LAB_ROOT: scratch folder with search22/, sector/, sector_lab/data/, five_pct/; REPO_ROOT: this repo
import pandas as pd, numpy as np
S=os.environ.get('LAB_ROOT', 'lab') + '/'
V=S+'lag5/verify_0_A_splits/'
X=pd.read_csv(V+'events_my.csv')
T=pd.read_csv(os.environ.get('REPO_ROOT', '.') + '/results/lagged_nifty/trades_lag5.csv')
F=pd.read_csv(S+'five_pct/A_rule_search/features_all.csv')
fo=X[X.in_fo==True]
g=fo[fo.my_lag<-0.05]; print('my lag5 group',len(g),'avg',g.my_3d.mean()*100, 'tp',g.my_tp.mean()*100)
m=g.merge(T[['symbol','quarter','vs_nifty_1m']],on=['symbol','quarter'],how='outer',indicator=True); print(m._merge.value_counts())
print('lag diff', (m.my_lag-m.vs_nifty_1m).abs().describe())
m2=X.merge(F[['symbol','quarter','vol60','vs_nifty_1m','r1w']],on=['symbol','quarter'])
print('vol60 diff ddof1', (m2.my_vol60-m2.vol60).abs().describe()); print('vol60 diff ddof0',(m2.my_vol60_0-m2.vol60).abs().describe())
print('r1w diff',(m2.my_r1w-m2.r1w).abs().describe())
def rep(s,lab):
    s=s.copy(); s['ret']=s.my_3d*100; s['tp']=s.my_tp*100
    pq=s.groupby('qn').ret.mean()
    a=s[s.qn<=13]; b=s[s.qn>=14]
    print(f"{lab}: n={len(s)} avg={s.ret.mean():.2f} net={s.ret.mean()-0.17:.2f} tp={s.tp.mean():.2f} up={100*(s.ret>0).mean():.1f} qpos={(pq>0).sum()}/{len(pq)} f14 n={len(a)} {a.ret.mean():.2f} l8 n={len(b)} {b.ret.mean():.2f} tp_l8={b.tp.mean():.2f} med={s.ret.median():.2f}")
    return s
c=rep(g[(g.my_lag<-0.15)&(g.my_vol60>=0.35)],'COMBO-H mine')
rep(g[(g.my_lag<-0.15)],'lag15 mine')
# also using features_all values
gf=m2[(m2.in_fo==True)&(m2.vs_nifty_1m<-0.15)&(m2.vol60>=0.35)]; rep(gf,'COMBO-H featuresfile')
c.sort_values('ret')[['symbol','quarter','qn','industry','my_lag','my_vol60','ret','tp']].to_csv(V+'combo_trades.csv',index=False)
print(c.sort_values('ret')[['symbol','quarter','qn','my_lag','my_vol60','ret','tp']].to_string())
