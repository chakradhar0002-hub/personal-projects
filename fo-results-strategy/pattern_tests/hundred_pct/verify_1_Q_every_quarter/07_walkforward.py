"""Walk-forward: for q=8..21 build cuts on quarters<q (13-percentile grid), find rules with picks in every
earlier quarter and every earlier quarter average >0 (1-2 cond exhaustive + 3-cond beam 1000), take top-1 by worst
quarter average (tie: more trades), trade it in quarter q (3-day exit, long/short)."""
import os; os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np, pandas as pd, sys
S=os.environ.get('LAB_ROOT', 'lab') + '/'
fa=pd.read_csv(S+'five_pct/A_rule_search/features_all.csv'); fa=fa[fa.in_fo].reset_index(drop=True)
EXCL={'qn','three_day','excess_nifty','tp3','after_close','i_cut','in_fo'}
feats=[c for c in fa.columns if pd.api.types.is_numeric_dtype(fa[c]) and fa[c].dtype!=bool and c not in EXCL]
qn=fa.qn.values; y=fa.three_day.values.astype(np.float32)
rows=[]
for Q in range(8,22):
    tr=qn<Q; conds=[];names=[]
    for f in feats:
        v=fa[f].values.astype(float); cuts=np.unique(np.nanpercentile(v[tr],[5,10,15,20,30,40,50,60,70,80,85,90,95]))
        for c in cuts:
            for op in ('<=','>='):
                m=(v<=c) if op=='<=' else (v>=c)
                if m[tr].sum()<20 or (~m[tr]).sum()<20: continue
                conds.append(m); names.append(f'{f} {op} {c:.5g}')
    M=np.array(conds); _,keep=np.unique(np.packbits(M[:,tr],axis=1),axis=0,return_index=True); keep=np.sort(keep); M=M[keep]; names=[names[k] for k in keep]
    X=M.astype(np.float32); C=len(names); ix={q:np.where(qn==q)[0] for q in range(Q+1)}
    def ev(A):
        R_=A[0].shape[0]; nq=np.zeros((R_,C),np.int16); nfl=nq.copy(); nfs=nq.copy(); mnl=np.full((R_,C),np.inf,np.float32); mns=mnl.copy(); K=np.zeros((R_,C),np.float32)
        for q in range(Q):
            Xq=X[:,ix[q]].T; k=A[q]@Xq; s=(A[q]*y[ix[q]][None,:])@Xq; h=k>0.5; a=np.where(h,s/np.maximum(k,1),0)
            nq+=h; nfl+=h&(a<=0); nfs+=h&(a>=0); mnl=np.minimum(mnl,np.where(h,a,np.inf)); mns=np.minimum(mns,np.where(h,-a,np.inf)); K+=k
        return nq,nfl,nfs,mnl,mns,K
    up=np.triu(np.ones((C,C),bool))
    nq,nfl,nfs,mnl,mns,K=ev({q:X[:,ix[q]] for q in range(Q)})
    best=[]
    for d,nf,mn in (('L',nfl,mnl),('S',nfs,mns)):
        ok=up&(nq==Q)&(nf==0)
        for a,b in zip(*np.nonzero(ok)): best.append((float(mn[a,b]),float(K[a,b]),d,(a,b)))
        key=np.where(up&(nq>=int(0.85*Q)),nf*100.-nq-np.clip(mn,-0.05,0.05),np.inf).ravel()
        top=np.argpartition(key,1000)[:1000]; aa,bb=np.unravel_index(top,(C,C))
        r3=ev({q:X[aa][:,ix[q]]*X[bb][:,ix[q]] for q in range(Q)})
        ok3=(r3[0]==Q)&((r3[1] if d=='L' else r3[2])==0); m3=r3[3] if d=='L' else r3[4]
        for i,j in zip(*np.nonzero(ok3)): best.append((float(m3[i,j]),float(r3[5][i,j]),d,(aa[i],bb[i],j)))
    best.sort(key=lambda t:(-t[0],-t[1])); mn_,k_,d,cs=best[0]
    mask=np.all(M[list(cs)],axis=0)&(qn==Q); sg=1 if d=='L' else -1; p=sg*y[mask]
    rows.append(dict(q=Q,n_qual=len(best),rule=d+': '+' AND '.join(names[c] for c in cs),n=int(mask.sum()),avg=100*p.mean() if len(p) else np.nan,win=100*(p>0).mean() if len(p) else np.nan,pnl_sum=p.sum()))
    print(rows[-1],flush=True)
W=pd.DataFrame(rows); W.to_csv('walkforward.csv',index=False)
h=W[W.n>0]; print('WF quarters with picks',len(h),'positive',(h.avg>0).sum(),'pooled avg',round(100*h.pnl_sum.sum()/h.n.sum(),2),'trades',h.n.sum())
