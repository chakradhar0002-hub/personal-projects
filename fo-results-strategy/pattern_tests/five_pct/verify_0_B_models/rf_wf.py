import os  # LAB_ROOT: folder holding search22/, sector/ and sector_lab/data/
# Independent re-implementation: walk-forward RF P(three_day>5%), top-k per quarter, long.
import sys, numpy as np, pandas as pd
from sklearn.ensemble import RandomForestClassifier
D=os.environ.get('LAB_ROOT', 'lab') + '/'
d=pd.read_csv(D+'search22/features.csv')
EXCL={'symbol','quarter','qn','results_date','cutoff','industry','fin_type','timing','three_day','excess_nifty','in_fo','tp3','after_close'}
feats=[c for c in d.columns if c not in EXCL]
d['is_bank']=(d.fin_type=='Bank').astype(int); d['is_nbfc']=(d.fin_type=='NBFC / financial').astype(int)
feats+= ['is_bank','is_nbfc']
X=d[feats].astype(float).fillna(-999).values
COST=0.0017

def run(y_ret, train_fo_only=True, k=2, leaf=20, ntree=300, seed=0, mf='sqrt', thr=0.05, start=6, depth=None):
    lab=(y_ret>thr).astype(int)
    scores=np.full(len(d),np.nan)
    for q in range(start,22):
        tr=(d.qn<q).values & (d.in_fo.values if train_fo_only else True)
        te=(d.qn==q).values & d.in_fo.values
        m=RandomForestClassifier(n_estimators=ntree,min_samples_leaf=leaf,max_features=mf,max_depth=depth,random_state=seed,n_jobs=2)
        m.fit(X[tr],lab[tr]); scores[te]=m.predict_proba(X[te])[:,1]
    return scores

def picks(scores,k=2):
    s=pd.Series(scores,index=d.index).dropna()
    dd=d.loc[s.index].assign(score=s)
    return dd.sort_values('score',ascending=False).groupby('qn').head(k).sort_values(['qn','score'],ascending=[True,False])

def stats(p,col='three_day'):
    r=p[col].values*100
    out=dict(n=len(r),avg=r.mean(),net=r.mean()-17*0.01,qavg=p.groupby('qn')[col].mean().mean()*100,
             win=(r>0).mean()*100,med=np.median(r))
    srt=np.sort(r)[::-1]; out['top5_share']=srt[:5].sum()/r.sum()*100 if r.sum()!=0 else np.nan
    out['ex_top5']=srt[5:].mean() if len(r)>5 else np.nan
    out['is_6_13']=p[p.qn<=13][col].mean()*100; out['oos_14_21']=p[p.qn>=14][col].mean()*100
    return out
if __name__=='__main__':
    for fo in [True,False]:
      for seed in [0,1,2]:
        sc=run(d.three_day.values,train_fo_only=fo,seed=seed)
        for k in [1,2,3,5]:
            print('trainFO',fo,'seed',seed,'k',k,{a:round(b,2) for a,b in stats(picks(sc,k)).items()})
        if seed==0:
            np.save(D+f'five_pct/verify_0_B_models/sc_fo{int(fo)}.npy',sc)
            picks(sc,2)[['symbol','qn','results_date','score','three_day']].to_csv(D+f'five_pct/verify_0_B_models/picks_fo{int(fo)}.csv',index=False)
