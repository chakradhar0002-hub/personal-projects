# Re-run the candidate's exact RF recipe (their model_table, config 0/1, -999 fill) with many random seeds.
import os, sys
os.environ['OMP_NUM_THREADS']='1'
import numpy as np, pandas as pd
from joblib import Parallel, delayed
from sklearn.ensemble import RandomForestClassifier
B=os.environ.get('LAB_ROOT', 'lab') + '/five_pct/B_models/'
T=pd.read_csv(B+'model_table.csv'); T=T[T.in_fo].reset_index(drop=True)
NON={'symbol','quarter','qn','results_date','cutoff','industry','fin_type','timing','three_day','excess_nifty','in_fo','tp3','after_close'}
feats=[c for c in T.columns if c not in NON]
X=T[feats].astype(float).values; X[~np.isfinite(X)]=np.nan
y=T.three_day.values; qn=T.qn.values; lab=(y>.05).astype(int)
cfg=[dict(n_estimators=200,min_samples_leaf=20,max_features=.3),dict(n_estimators=200,min_samples_leaf=60,max_features=.3)]
def fit(q,seed,ci,ntree):
    tr=qn<q; te=qn==q
    Xtr=X[tr]; keep=np.array([ (np.isfinite(Xtr[:,j]).sum()>=20 and np.unique(Xtr[:,j][np.isfinite(Xtr[:,j])][:2000]).size>1) for j in range(X.shape[1])])
    A=np.nan_to_num(Xtr[:,keep],nan=-999.); Bm=np.nan_to_num(X[te][:,keep],nan=-999.)
    c=dict(cfg[ci]); c['n_estimators']=ntree
    m=RandomForestClassifier(random_state=seed,n_jobs=1,**c).fit(A,lab[tr])
    return q,seed,ci,ntree,m.predict_proba(Bm)[:,1]
jobs=[(q,s,0,200) for s in range(30) for q in range(6,22)]+[(q,0,1,200) for q in range(6,22)]+[(q,s,0,1000) for s in range(3) for q in range(6,22)]
res=Parallel(n_jobs=3)(delayed(fit)(*j) for j in jobs)
sc={}
for q,s,ci,nt,p in res:
    k=(s,ci,nt); sc.setdefault(k,np.full(len(y),np.nan)); sc[k][qn==q]=p
rows=[]
for k,v in sc.items():
    for K in (1,2,3,5):
        idx=[]
        for q in range(6,22):
            m=np.where(qn==q)[0]; idx+=list(m[np.argsort(-v[m],kind='stable')[:K]])
        idx=np.array(idx); r=y[idx]*100; srt=np.sort(r)[::-1]
        rows.append(dict(seed=k[0],cfg=k[1],ntree=k[2],k=K,n=len(r),avg=r.mean(),is_=r[qn[idx]<=13].mean(),oos=r[qn[idx]>=14].mean(),
                         win=(r>0).mean()*100,ex5=srt[5:].mean()))
    if k==(0,0,200): pd.DataFrame({'symbol':T.symbol,'qn':qn,'score':v,'three_day':y}).to_csv('their_rf_seed0_scores.csv',index=False)
R=pd.DataFrame(rows); R.to_csv('their_rf_seeds.csv',index=False)
pd.set_option('display.width',200)
for K in (1,2,3,5):
    g=R[(R.cfg==0)&(R.ntree==200)&(R.k==K)]
    print(f'k={K} 30 seeds avg: mean {g.avg.mean():.2f} sd {g.avg.std():.2f} min {g.avg.min():.2f} max {g.avg.max():.2f} | oos mean {g.oos.mean():.2f} | ex-top5 mean {g.ex5.mean():.2f} | seed0 {g[g.seed==0].avg.iloc[0]:.2f}; seeds>=3.09: {(g.avg>=3.09).sum()}')
print(R[(R.ntree==1000)|(R.cfg==1)].round(2).to_string())
