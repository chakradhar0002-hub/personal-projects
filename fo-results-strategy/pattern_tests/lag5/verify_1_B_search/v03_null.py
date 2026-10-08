import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
D=S+'lag5/verify_1_B_search/'
mode=sys.argv[1]; N=int(sys.argv[2])
g,feats=load()
rng=np.random.default_rng(123 if mode=='shuffle' else 456)
y0=g.ret.values; qn=g.qn.values
rows=[]
def variants(s, yv):
    out={}
    for p in (95,90,85,75):
        # need thr per pct -> recompute from stored oob percentile: wf stores only one thr; handle in wf2
        pass
    return out
def wf2(gg, label_thr, seed):
    X=gg[feats].values.astype(float); y=gg.ret.values; res=[]
    for q in range(8,22):
        tr=(gg.qn<q).values; te=(gg.qn==q).values
        rf=RandomForestClassifier(n_estimators=300,min_samples_leaf=10,max_features=0.3,oob_score=True,random_state=seed,n_jobs=2)
        rf.fit(X[tr],(y[tr]>label_thr).astype(int)); oob=rf.oob_decision_function_[:,1]; s=rf.predict_proba(X[te])[:,1]
        for p in (95,90,85,75):
            res += [(label_thr,'top%d'%(100-p),q,v) for v in y[te][s>=np.nanpercentile(oob,p)]]
        res += [(label_thr,'bot25',q,-v) for v in y[te][s<=np.nanpercentile(oob,25)]]
    return res
for r in range(N):
    yy=y0.copy()
    if mode=='shuffle':
        for q in np.unique(qn): ix=np.where(qn==q)[0]; yy[ix]=rng.permutation(yy[ix])
    elif mode=='signflip':
        for q in np.unique(qn):
            ix=np.where(qn==q)[0]; m=yy[ix].mean(); yy[ix]=m+rng.choice([-1,1],len(ix))*np.abs(yy[ix]-m)
    gg=g.copy(); gg['ret']=yy
    res=wf2(gg,3.0,r)+wf2(gg,0.0,r)
    R=pd.DataFrame(res,columns=['lab','var','qn','pnl'])
    for (l,v),d in R.groupby(['lab','var']): rows.append(dict(run=r,lab=l,var=v,n=len(d),avg=d.pnl.mean(),l8=d[d.qn>=14].pnl.mean()))
    pd.DataFrame(rows).to_csv(D+f'null_{mode}.csv',index=False); print(r,flush=True)
