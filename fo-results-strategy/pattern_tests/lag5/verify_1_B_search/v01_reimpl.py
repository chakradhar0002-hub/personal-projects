import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
g,feats=load(); print(len(g), len(feats)); print(feats)
print('NaN frac top:', g[feats].isna().mean().sort_values(ascending=False).head(8).round(2).to_dict())
res={}
for seed in range(10):
    s=wf(g,feats,seed=seed); s.to_csv(S+f'lag5/verify_1_B_search/wf_scores_seed{seed}.csv',index=False)
    t=s[s.score>=s.thr]; res[seed]=summ(t); print(seed, res[seed], 'tp', round(t.tp.mean(),2), flush=True)
