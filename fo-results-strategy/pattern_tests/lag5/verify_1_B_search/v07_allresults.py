import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
g,feats=load(all_results=True); print(len(g))
for seed in range(3):
    s=wf(g,feats,seed=seed); t=s[s.score>=s.thr]
    fo=t.merge(g[['symbol','quarter','in_fo']],on=['symbol','quarter'])
    print(seed, summ(t), '| in_fo picks', int(fo.in_fo.sum()), round(fo[fo.in_fo].ret.mean(),2), '| pre-F&O picks', int((~fo.in_fo).sum()), round(fo[~fo.in_fo].ret.mean(),2), flush=True)
