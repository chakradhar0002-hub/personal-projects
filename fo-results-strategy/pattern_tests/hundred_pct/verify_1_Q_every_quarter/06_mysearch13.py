"""Independent 'every quarter positive' search: choose on qn 0..13, report qn 14..21.
Conditions: each numeric cutoff feature <= / >= its 5,10,20,...,90,95th percentile (cuts on first-14 rows).
Rules: all 1- and 2-condition rules; 3-condition beam (best 400 pairs per direction x all conditions).
Directions long/short, 3-day exit. Qualify: picks in all 14 quarters and every quarter avg > 0 (gross).
Choice: best worst-quarter average (tie: more trades). Run real, then NULL runs (signflip / shuffle).
usage: python3 05_mysearch.py KIND NRUNS SEED"""
import os, sys, json, time
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np, pandas as pd
S=os.environ.get('LAB_ROOT', 'lab') + '/'
fa=pd.read_csv(S+'five_pct/A_rule_search/features_all.csv'); fa=fa[fa.in_fo].reset_index(drop=True)
EXCL={'qn','three_day','excess_nifty','tp3','after_close','i_cut','in_fo'}
feats=[c for c in fa.columns if pd.api.types.is_numeric_dtype(fa[c]) and fa[c].dtype!=bool and c not in EXCL]
qn=fa.qn.values; tr=qn<14
conds=[];names=[]
for f in feats:
    v=fa[f].values.astype(float); cuts=np.unique(np.nanpercentile(v[tr],[5,10,15,20,30,40,50,60,70,80,85,90,95]))
    for c in cuts:
        for op in ('<=','>='):
            m=(v<=c) if op=='<=' else (v>=c)
            if m[tr].sum()<20 or (~m[tr]).sum()<20: continue
            conds.append(m); names.append(f'{f} {op} {c:.5g}')
M=np.array(conds); 
# dedupe identical masks
_,keep=np.unique(np.packbits(M,axis=1),axis=0,return_index=True); keep=np.sort(keep); M=M[keep]; names=[names[k] for k in keep]
C=len(names); X=M.astype(np.float32)
ix={q:np.where(qn==q)[0] for q in range(22)}
def evalrules(Arows, Y):
    """Arows: dict q -> (R x n_q) float matrix of base rule masks. returns per (R,C): nq_tr, nf_long, nf_short, mn_long, mn_short, K/S train & test, te pos counts"""
    R_=Arows[0].shape[0]
    out={k:np.zeros((R_,C),np.float32) for k in ('nq','nfl','nfs','Ktr','Str','Kte','Ste','pl','ps')}
    out['mnl']=np.full((R_,C),np.inf,np.float32); out['mns']=np.full((R_,C),np.inf,np.float32)
    for q in range(22):
        Xq=X[:,ix[q]].T; Aq=Arows[q]; y=Y[ix[q]].astype(np.float32)
        K=Aq@Xq; Sm=(Aq*y[None,:])@Xq; has=K>0.5; avg=np.where(has,Sm/np.maximum(K,1),0)
        if q<14:
            out['nq']+=has; out['nfl']+=has&(avg<=0); out['nfs']+=has&(avg>=0)
            out['mnl']=np.minimum(out['mnl'],np.where(has,avg,np.inf)); out['mns']=np.minimum(out['mns'],np.where(has,-avg,np.inf))
            out['Ktr']+=K; out['Str']+=Sm
        else:
            out['Kte']+=K; out['Ste']+=Sm; out['pl']+=has&(avg>0); out['ps']+=has&(avg<0)
    return out
def search(Y):
    o2=evalrules({q:X[:,ix[q]] for q in range(22)},Y)
    up=np.triu(np.ones((C,C),bool))  # diagonal = single condition
    res=[]
    for d,nf,mn in (('L','nfl','mnl'),('S','nfs','mns')):
        ok=up&(o2['nq']==14)&(o2[nf]==0)
        r,c=np.nonzero(ok)
        for a,b in zip(r,c): res.append((d,(a,b),o2[mn][a,b],o2['Ktr'][a,b],o2['Str'][a,b],o2['Kte'][a,b],o2['Ste'][a,b],o2['pl' if d=='L' else 'ps'][a,b]))
    # beam
    n2=len(res)
    for d,nf,mn in (('L','nfl','mnl'),('S','nfs','mns')):
        key=np.where(up&(o2['nq']>=12),o2[nf]*100-o2['nq']-np.clip(o2[mn],-0.05,0.05),np.inf).ravel()
        top=np.argpartition(key,1000)[:1000]; a,b=np.unravel_index(top,(C,C))
        A3={q:X[a][:,ix[q]]*X[b][:,ix[q]] for q in range(22)}
        o3=evalrules(A3,Y)
        ok=(o3['nq']==14)&(o3[nf]==0)
        r,c=np.nonzero(ok)
        for i,j in zip(r,c): res.append((d,(a[i],b[i],j),o3[mn][i,j],o3['Ktr'][i,j],o3['Str'][i,j],o3['Kte'][i,j],o3['Ste'][i,j],o3['pl' if d=='L' else 'ps'][i,j]))
    if not res: return dict(n=0)
    R=pd.DataFrame(res,columns=['d','conds','mn','Ktr','Str','Kte','Ste','tepos'])
    R['sg']=np.where(R.d=='L',1,-1); R['te_avg']=R.sg*R.Ste/np.maximum(R.Kte,1)*100; R['tr_avg']=R.sg*R.Str/R.Ktr*100
    R=R.sort_values(['mn','Ktr'],ascending=False)
    t=R.iloc[0]; t10=R.iloc[:10]
    return dict(n=len(R),n2=n2,top_mn=float(t.mn)*100,top_K=int(t.Ktr),top_tepos=int(t.tepos),top_teavg=float(t.te_avg),top_Kte=int(t.Kte),
                top_rule=t.d+': '+' AND '.join(names[k] for k in t.conds),
                t10_tepos=float(t10.tepos.mean()),t10_teavg=float(t10.te_avg.mean()),all_tepos=float(R.tepos.mean()),all_teavg=float(R.te_avg.mean()),
                frac_all8=float((R.tepos==8).mean()),n_K50=int((R.Ktr>=50).sum()),n_K70=int((R.Ktr>=70).sum()))
if __name__=='__main__':
    kind,nr,seed=sys.argv[1],int(sys.argv[2]),int(sys.argv[3])
    y0=fa.three_day.values; rng=np.random.default_rng(seed); out=[]
    t0=time.time()
    print('conditions',C,'features',len(feats),flush=True)
    for s in range(nr):
        if kind=='real': Y=y0
        elif kind=='shuffle':
            Y=y0.copy()
            for q in range(22): Y[ix[q]]=rng.permutation(y0[ix[q]])
        else:
            qm=pd.Series(y0).groupby(qn).transform('mean').values; Y=qm+rng.choice([-1.,1.],len(y0))*(y0-qm)
        d=search(Y); d['run']=s; out.append(d); print(s,round(time.time()-t0),{k:d.get(k) for k in ('n','top_mn','top_K','top_tepos','top_teavg','top_rule')},flush=True)
        json.dump(out,open(f'my13_{kind}_{seed}.json','w'),default=float)
