import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from scipy import stats
D=S+'lag5/verify_1_B_search/'
g,feats=load()
ss=[pd.read_csv(D+f'wf_scores_seed{s}.csv') for s in range(10)]
# per-seed picks, collect all trades with seed tag
allp=pd.concat([s[s.score>=s.thr].assign(seed=i) for i,s in enumerate(ss)])
print('seed-pooled (10 seeds) trades/seed', len(allp)/10, 'avg', allp.ret.mean().round(2), 'median', allp.ret.median().round(2))
# frequency each trade picked across seeds
fr=allp.groupby(['symbol','quarter','qn','industry','ret','tp']).size().rename('nseeds').reset_index().sort_values('ret',ascending=False)
print('distinct trades picked by any seed', len(fr), ' by >=5 seeds', (fr.nseeds>=5).sum())
core=fr[fr.nseeds>=5]; print('core (>=5/10 seeds):', summ(core), 'tp', core.tp.mean().round(2), 'median', core.ret.median().round(2))
print(core.sort_values('ret',ascending=False).to_string())
# ensemble score: mean of seeds
E=ss[0][['symbol','quarter','qn','industry','ret','tp']].copy(); E['score']=np.mean([s.score for s in ss],0); E['thr']=np.mean([s.thr for s in ss],0)
E.to_csv(D+'ensemble_scores.csv',index=False)
t=E[E.score>=E.thr]
print('\nENSEMBLE top10:', summ(t), 'tp', t.tp.mean().round(2), 'median', t.ret.median().round(2), 't-stat', round(stats.ttest_1samp(t.ret,0).statistic,2))
print('per quarter:'); print(t.groupby('qn').ret.agg(['size','mean']).round(2).T.to_string())
pq=t.groupby('qn').ret.mean(); print('without best quarter', round(t[t.qn!=pq.idxmax()].ret.mean(),2), 'best q', pq.idxmax())
print('without best 1/3/5/8 trades', [round(t.ret.sort_values().iloc[:-k].mean(),2) for k in (1,3,5,8)])
print('LOQO min/max', round(min(t[t.qn!=q].ret.mean() for q in t.qn.unique()),2), round(max(t[t.qn!=q].ret.mean() for q in t.qn.unique()),2))
print('industry counts', t.industry.value_counts().head(6).to_dict())
print('leave-one-industry-out min', round(min(t[t.industry!=i].ret.mean() for i in t.industry.unique()),2))
print('symbol repeats', t.symbol.value_counts().head(5).to_dict())
yr=t.merge(g[['symbol','quarter','results_date']],on=['symbol','quarter']); yr['yr']=yr.results_date.str[:4]
print('by year', yr.groupby('yr').ret.agg(['size','mean']).round(2).T.to_string())
# neighbouring thresholds using ensemble: threshold = pct of training OOB; approximate via ranking within test? use per-seed thresholds
for pct in (80,85,88,90,92,95):
    # recompute thresholds for pct requires oob; approximate with seed-0 scores scaled: not available -> rerun later
    pass
# score deciles across all walk-forward rows (q8-21)
E['dec']=E.groupby('qn').score.rank(pct=True)
E['bin']=pd.cut(E.dec,[0,.5,.7,.8,.9,.95,1.0])
print('\nwithin-quarter score rank bins (all wf rows q8-21):'); print(E.groupby('bin',observed=True).ret.agg(['size','mean','median']).round(2).to_string())
from sklearn.metrics import roc_auc_score
print('AUC up3', round(roc_auc_score(E.ret>3,E.score),3), 'spearman', round(stats.spearmanr(E.score,E.ret).statistic,3))
# random same-size per-quarter subsets
rng=np.random.default_rng(0); n_q=t.groupby('qn').size(); pool={q:E[E.qn==q].ret.values for q in n_q.index}
R=np.array([np.mean(np.concatenate([rng.choice(pool[q],k,replace=False) for q,k in n_q.items()])) for _ in range(10000)])
print('random same-size: mean', R.mean().round(2), 'p95', np.percentile(R,95).round(2), 'p(>=real)', (R>=t.ret.mean()).mean())
