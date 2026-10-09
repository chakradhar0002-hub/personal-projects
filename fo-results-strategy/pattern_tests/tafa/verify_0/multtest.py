"""Family-wise maxT (within-quarter joint permutations) over a family of splits of the 85 lag-rule trades:
the 12 pre-registered TA+FA pairs (labels from B's flags file; X8 reproduced exactly by the rebuild) + the single
parts actually tried before on the same 85 trades that I can rebuild (6 oversold indicators, os>=3, loss-free 4q,
sales growth, PAT growth, good_fund) = 23 splits. Plus Holm/Bonferroni over the overall count of things tried."""
import os  # LAB_ROOT: scratch folder with ta/, fa/, report/, sector_lab/data; REPO_ROOT: this repo
import numpy as np, pandas as pd
SCR=os.environ.get('LAB_ROOT', 'lab') + ""
rng=np.random.default_rng(3)
S=pd.read_csv("s85_verified.csv")
T=pd.read_csv(f"{SCR}/tafa/B_lag_rule_and_model/part1_trades_S85_flags.csv")
S=S.merge(T.drop(columns=["qn","cutoff","lag_pct","vol_ratio_5_60","three_day","tp3"]),on=["symbol","quarter"])
assert len(S)==85 and (S.x8==S["X8_goodfund&oversold3"]).all()
L={c:S[c].to_numpy() for c in T.columns if c.startswith("X")}
def tri(good,bad): return np.where(good,1,np.where(bad,0,-1))
L["rsi14<30"]=(S.rsi14<30).astype(int).to_numpy(); L["rsi2<10"]=(S.rsi2<10).astype(int).to_numpy()
L["stoch<20"]=(S.stochk<20).astype(int).to_numpy(); L["belowBB"]=(S.pctb<0).astype(int).to_numpy()
L["cci<-100"]=(S.cci<-100).astype(int).to_numpy(); L["mfi<20"]=(S.mfi<20).astype(int).to_numpy()
L["os>=3"]=(S.os>=3).astype(int).to_numpy()
L["noloss4q"]=tri(S.loss4==0,S.loss4==1); L["sales_up"]=tri(S.sales_yoy>0,S.sales_yoy<=0)
L["pat_up"]=tri(S.pat_yoy>0,S.pat_yoy<=0); L["good_fund"]=S.gf.to_numpy()
y=S.three_day.to_numpy(); q=S.qn.to_numpy()
names=list(L); NP=20000
def Ds(yy):
    out=[]
    for n in names:
        l=L[n]; t=l==1; f=l==0
        out.append(yy[t].mean()-yy[f].mean() if t.any() and f.any() else np.nan)
    return np.array(out)
D0=Ds(y)
perm=np.empty((NP,len(names)))
groups=[np.where(q==z)[0] for z in np.unique(q)]
for i in range(NP):
    yy=y.copy()
    for g in groups: yy[g]=y[rng.permutation(g)]
    perm[i]=Ds(yy)
sd=np.nanstd(perm,0); Z=np.abs(perm)/sd; z0=np.abs(D0)/sd
mx=np.nanmax(Z,1)
p_raw=(np.sum(np.abs(perm)>=np.abs(D0),0)+1)/(NP+1)
p_fw=np.array([(np.sum(mx>=z)+1)/(NP+1) for z in z0])
o=np.argsort(p_raw); m=len(p_raw); holm=np.empty(m); run=0
for r,i in enumerate(o):
    run=max(run,min(1,(m-r)*p_raw[i])); holm[i]=run
R=pd.DataFrame({"split":names,"n_yes":[int((L[n]==1).sum()) for n in names],"D":D0,"p_raw2s":p_raw,"holm23":holm,"maxT23":p_fw}).sort_values("p_raw2s")
print(R.round(3).to_string(index=False))
x=R[R.split.str.startswith("X8")].iloc[0]
for N in (12,23,87,40+87+117,44+19+44+12+40+87+117):
    print(f"Bonferroni over {N} things tried: {min(1,N*x.p_raw2s):.3f}  (one-sided {min(1,N*x.p_raw2s/2):.3f})")
