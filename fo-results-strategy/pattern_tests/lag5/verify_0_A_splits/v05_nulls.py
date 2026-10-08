import os  # LAB_ROOT: scratch folder with search22/, sector/, sector_lab/data/, five_pct/; REPO_ROOT: this repo
import pandas as pd, numpy as np, sys
A=os.environ.get('LAB_ROOT', 'lab') + '/lag5/A_splits/'
V=os.environ.get('LAB_ROOT', 'lab') + '/lag5/verify_0_A_splits/'
exec(open(A+'prereg_FROZEN.py').read())   # SPLITS list only (data definitions)
rng=np.random.default_rng(11)
G=pd.read_csv(A+'group_fo.csv').reset_index(drop=True)
y=G.three_day_pct.values; q=G.qn.values.astype(int); lag=G.lag.values; vol=G.vol60.values
f14=q<14
# ---- (1) does vol>=35 add anything inside lag>15? random subsets of lag>15 of same per-quarter size
h=lag<-0.15; c=h&(vol>=0.35)
print('lag>15 n',h.sum(),'combo n',c.sum())
cnt=np.bincount(q[c],minlength=22); draws=[];d8=[]
for it in range(20000):
    pick=[]
    for k in range(22):
        if cnt[k]: pick+=list(rng.choice(np.where(h&(q==k))[0],cnt[k],replace=False))
    pick=np.array(pick); draws.append(y[pick].mean()); d8.append(y[pick[q[pick]>=14]].mean())
draws=np.array(draws); d8=np.array(d8)
print('random same-size subsets of lag>15 (per quarter): mean %.2f p(all>=%.2f)=%.3f ; last8 mean %.2f p(l8>=%.2f)=%.3f'%(draws.mean(),y[c].mean(),(draws>=y[c].mean()).mean(),d8.mean(),y[c&~f14].mean(),(d8>=y[c&~f14].mean()).mean()))
# ---- (2) cluster bootstrap by quarter of the combo average
qs=np.unique(q[c]); bs=[]
for it in range(20000):
    qq=rng.choice(qs,len(qs)); idx=np.concatenate([np.where(c&(q==k))[0] for k in qq]); bs.append(y[idx].mean())
print('quarter-cluster bootstrap combo avg 90%% CI: %.2f to %.2f, P(<=0.17)=%.3f'%(np.percentile(bs,5),np.percentile(bs,95),(np.array(bs)<=0.17).mean()))
bs=[];ix=np.where(c)[0]
for it in range(20000): bs.append(y[rng.choice(ix,len(ix))].mean())
print('trade bootstrap 90%% CI: %.2f to %.2f, P(<=0.17)=%.3f'%(np.percentile(bs,5),np.percentile(bs,95),(np.array(bs)<=0.17).mean()))
# ---- (3) selection null preserving the depth effect: shuffle within (quarter, lag band)
MA=np.array([G.eval(s[3]).fillna(False).astype(bool).values for s in SPLITS]); MB=np.array([G.eval(s[4]).fillna(False).astype(bool).values for s in SPLITS])
fam=np.array([s[1] for s in SPLITS]); ids=[s[0] for s in SPLITS]
def tst(d):
    d=d[np.isfinite(d)]
    return d.mean()/(d.std(ddof=1)/np.sqrt(len(d))) if len(d)>2 and d.std(ddof=1)>0 else np.nan
def select(yy):
    rows=[]
    for i in range(len(SPLITS)):
        a=MA[i];b=MB[i]
        da=[yy[a&(q==k)].mean() if (a&(q==k)).any() else np.nan for k in range(14)]
        db=[yy[b&(q==k)].mean() if (b&(q==k)).any() else np.nan for k in range(14)]
        t=tst(np.array(da)-np.array(db)); nA=(a&f14).sum()
        if nA>=25 and t>=1.5 and yy[a&f14].mean()>0: rows.append((t,i))
    rows.sort(reverse=True); picks=[];fams=set()
    for t,i in rows:
        if fam[i] in fams: continue
        picks.append(i); fams.add(fam[i])
        if len(picks)==2: break
    return picks
real=select(y); print('real picks',[ids[i] for i in real])
band=np.digitize(lag,[-0.15,-0.10])  # 0:>15,1:10-15,2:5-10
cells=[np.where((q==k)&(band==b))[0] for k in range(22) for b in range(3)]
res=[]
for it in range(300):
    yy=y.copy()
    for ix in cells:
        if len(ix)>1: yy[ix]=y[rng.permutation(ix)]
    p=select(yy)
    if len(p)<2: res.append((np.nan,np.nan,np.nan,None)); continue
    m=MA[p[0]]&MA[p[1]]
    res.append((yy[m&f14].mean(),yy[m&~f14].mean(),yy[m].mean(),ids[p[0]]+'+'+ids[p[1]]))
R=pd.DataFrame(res,columns=['f14','l8','all','picks']); R.to_csv(V+'null_depth_preserved.csv',index=False)
print('depth-preserving null: runs with combo',R.f14.notna().sum(),'of',len(R))
print('null f14 mean %.2f p95 %.2f p(>=2.81)=%.3f | l8 mean %.2f p95 %.2f p(>=2.14)=%.3f | all mean %.2f p(>=2.54)=%.3f'%(R.f14.mean(),R.f14.quantile(.95),(R.f14>=2.81).mean(),R.l8.mean(),R.l8.quantile(.95),(R.l8>=2.14).mean(),R['all'].mean(),(R['all']>=2.54).mean()))
print(R.picks.value_counts().head(8).to_string())
