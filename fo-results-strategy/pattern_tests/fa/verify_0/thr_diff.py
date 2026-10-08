import os  # LAB_ROOT: scratch folder with report/, search22/, sector_lab/data, fa/; REPO_ROOT: this repo
import numpy as np, pandas as pd
D=os.environ.get('LAB_ROOT', 'lab') + ""
mc=pd.read_csv(f"{D}/fa/verify_0/mcap_pit.csv"); mc["adj"]=mc.mcap_a*21700/mc.nifty
t=pd.read_csv(os.environ.get('REPO_ROOT', '.') + "/results/lag10_volume/trades.csv").merge(mc[["symbol","quarter","adj"]],on=["symbol","quarter"],how="left")
t["ret"]=100*t.three_day; y=t.ret.to_numpy(); q=t.qn.to_numpy(); rng=np.random.default_rng(7)
groups=[np.where(q==k)[0] for k in np.unique(q)]
thrs=[40000,50000,60000,67000,75000,85000,100000]
obs={}; sims={th:[] for th in thrs}
F={th:(t.adj>=th).to_numpy() for th in thrs}
for th in thrs: obs[th]=y[F[th]].mean()-y[~F[th]].mean()
R=20000; maxz=np.empty(R)
for r in range(R):
    perm=np.arange(len(y))
    for g in groups: perm[g]=rng.permutation(g)
    yp=y[perm]; m=-9
    for th in thrs:
        d=yp[F[th]].mean()-yp[~F[th]].mean(); sims[th].append(d); m=max(m,abs(d))
    maxz[r]=m
for th in thrs:
    s=np.array(sims[th]); f=F[th]
    l8=(q>=14); 
    print(f"thr {th:>6}: n={f.sum():2d} diff {obs[th]:+.2f} p2(within-q)={np.mean(np.abs(s)>=abs(obs[th])):.3f} "
          f"f14 diff {y[f&~l8].mean()-y[~f&~l8].mean():+.2f} l8 diff {y[f&l8].mean()-y[~f&l8].mean():+.2f}")
print("max over thresholds (raw diff, same scale) p for 67k:", np.mean(maxz>=abs(obs[67000])))
# best-5 removal from the large group and the not-large group comparison
L=t[F[67000]]; N=t[~F[67000]]
print("large wo best5", np.sort(L.ret)[:-5].mean().round(2), "not-large wo best5", np.sort(N.ret)[:-5].mean().round(2))
print("large worst/best", L.ret.min().round(2), L.ret.max().round(2), "median", L.ret.median().round(2), "not-large median", N.ret.median().round(2))
