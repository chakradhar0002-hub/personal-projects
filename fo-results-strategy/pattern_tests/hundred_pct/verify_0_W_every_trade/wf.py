import sys, numpy as np, pandas as pd
sys.path.insert(0,'.')
import vsearch as V, rulelib_copy as RL
thr=float(sys.argv[1]) if len(sys.argv)>1 else 0.0
df=RL.load('fo'); y=df.three_day.values; qn=df.qn.values
rows=[]; trades=[]
for q in range(6,22):
    tr=(qn<q)
    M,names,compat=RL.build_conditions(df,tr)
    found,_=V.search(M,compat,y,tr,qn,thr=thr)
    for m in (10,20):
        f={k:n for k,n in found.items() if n>=m}
        if not f: rows.append(dict(q=q,m=m,rule=None)); continue
        nmax=max(f.values()); best=sorted([k for k,n in f.items() if n==nmax],key=lambda k:(len(k),k))[0]
        mask=V.rule_trades(M,list(best))&(qn==q)
        r=y[mask]*100
        rows.append(dict(q=q,m=m,rule=RL.rule_str(names,list(best),1),n_is=nmax,n_trade=len(r),wins=int((r>thr*100).sum()),avg=r.mean() if len(r) else np.nan))
        for x,s in zip(r,df.symbol.values[mask]): trades.append(dict(q=q,m=m,sym=s,r=x))
    print(rows[-2]); print(rows[-1], flush=True)
R=pd.DataFrame(rows); T=pd.DataFrame(trades)
R.to_csv(f'wf_rules_thr{thr}.csv',index=False); T.to_csv(f'wf_trades_thr{thr}.csv',index=False)
for m in (10,20):
    t=T[T.m==m]; qa=t.groupby('q').r.mean()
    print(f'WF m={m}: trades {len(t)} win {(t.r>thr*100).mean()*100:.1f}% avg {t.r.mean():+.2f} worst {t.r.min():+.1f} quarters positive {(qa>0).sum()}/{len(qa)}; last8 trades {len(t[t.q>=14])} win {(t[t.q>=14].r>thr*100).mean()*100:.1f}%')
