import os  # LAB_ROOT: scratch folder with search22/, sector/, sector_lab/data/, five_pct/; REPO_ROOT: this repo
import numpy as np, pandas as pd
from sklearn.ensemble import RandomForestClassifier
S=os.environ.get('LAB_ROOT', 'lab') + '/'
EXCL={'symbol','quarter','qn','results_date','cutoff','industry','fin_type','timing','three_day','excess_nifty',
      'in_fo','tp3','after_close','i_cut','sector_index'}
def load(all_results=False):
    f=pd.read_csv(S+'five_pct/A_rule_search/features_all.csv').copy()
    g=f[f.vs_nifty_1m< -0.05].copy()
    if not all_results: g=g[g.in_fo==True].copy()
    g['ret']=g.three_day*100; g['tp']=g.tp3*100
    feats=[c for c in f.columns if c not in EXCL and pd.api.types.is_numeric_dtype(f[c])]
    return g.reset_index(drop=True), feats
def wf(g, feats, label_thr=3.0, seed=0, pct=90, start=8, min_leaf=10, mf=0.3, ntree=300, ycol='ret', shuffle_rng=None):
    out=[]
    y=g[ycol].values.copy()
    X=g[feats].values.astype(float)
    for q in range(start, g.qn.max()+1):
        tr=(g.qn<q).values; te=(g.qn==q).values
        if te.sum()==0: continue
        rf=RandomForestClassifier(n_estimators=ntree,min_samples_leaf=min_leaf,max_features=mf,oob_score=True,
                                  random_state=seed,n_jobs=2)
        rf.fit(X[tr], (y[tr]>label_thr).astype(int))
        oob=rf.oob_decision_function_[:,1]
        thr=np.nanpercentile(oob,pct)
        s=rf.predict_proba(X[te])[:,1]
        d=g.loc[te,['symbol','quarter','qn','industry','ret','tp']].copy(); d['score']=s; d['thr']=thr
        out.append(d)
    return pd.concat(out)
def summ(t, col='ret'):
    if len(t)==0: return dict(n=0)
    pq=t.groupby('qn')[col].mean()
    return dict(n=len(t), avg=round(t[col].mean(),2), net=round(t[col].mean()-0.17,2), up=round((t[col]>0).mean()*100,1),
                qpos=f"{(pq>0).sum()}/{len(pq)}", f14=round(t[t.qn<=13][col].mean(),2), nf14=int((t.qn<=13).sum()),
                l8=round(t[t.qn>=14][col].mean(),2), nl8=int((t.qn>=14).sum()),
                wo5=round(t[col].sort_values().iloc[:-5].mean(),2) if len(t)>5 else None)
