import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
D=S+'lag5/verify_1_B_search/'
pan=pd.read_pickle(D+'panel.pkl'); rp=pd.read_pickle(D+'res_price.pkl')
e=pd.read_csv(S+'sector_lab/data/events.csv')
g,feats=load()
PF=['r1w','r1m','r3m','r6m','r1y','r3d','r10d','r20d','r2d','vs_nifty_1w','vs_nifty_1m','vs_nifty_3m','exn_3d','exn_10d','vol60','vol5_60','vol20_60',
    'from_52w_high','from_52w_low','vs_ma50','vs_ma200','dist_20h','dist_20l','dist_60h','d0','d1','d2','maxabs5','z5','z20','up10','exn_d0',
    'nifty_1w','nifty_1m','nifty_3m','nifty_d0','nifty_3d']
G=g[['symbol','quarter','qn','ret','tp']].merge(rp[['symbol','quarter','i_cut']+PF],on=['symbol','quarter'],how='left')
assert len(G)==len(g)
pl=pan[(~pan.near_result)&(pan.in_fo)&(pan.vs_nifty_1m< -0.05)].copy()
print('placebo pool rows', len(pl), 'avg fwd', pl.fwd.mean().round(3), ' results group avg', G.ret.mean().round(3))
endq=e.groupby('qn').i_p1.max()
out=[]; outp=[]
for seed in range(5):
  for q in range(8,22):
    tr=G.qn<q; te=G.qn==q
    rf=RandomForestClassifier(n_estimators=300,min_samples_leaf=10,max_features=0.3,oob_score=True,random_state=seed,n_jobs=2)
    rf.fit(G.loc[tr,PF].values,(G.loc[tr,'ret']>3).astype(int)); thr=np.nanpercentile(rf.oob_decision_function_[:,1],90)
    s=rf.predict_proba(G.loc[te,PF].values)[:,1]
    out.append(G.loc[te,['symbol','qn','ret']].assign(score=s,thr=thr,seed=seed))
    w=pl[(pl.i>endq[q-1])&(pl.i<=endq[q])]
    sp=rf.predict_proba(w[PF].values)[:,1]
    outp.append(w[['symbol','i','fwd']].assign(score=sp,thr=thr,seed=seed,qn=q))
O=pd.concat(out); P=pd.concat(outp)
O.to_csv(D+'price_rf_results_scores.csv',index=False); P.to_pickle(D+'price_rf_placebo_scores.pkl')
for seed in range(5):
    a=O[(O.seed==seed)&(O.score>=O.thr)]; b=P[(P.seed==seed)&(P.score>=P.thr)]
    print(f'seed{seed}: results picks n={len(a)} avg={a.ret.mean():.2f} l8={a[a.qn>=14].ret.mean():.2f} | placebo picks n={len(b)} avg={b.fwd.mean():.2f} per-date avg={b.groupby("i").fwd.mean().mean():.2f} | placebo pool same windows avg={P[P.seed==seed].fwd.mean():.2f}')
# full model picks: nearest-neighbour price placebo
E=pd.read_csv(D+'ensemble_scores.csv'); t=E[E.score>=E.thr].merge(G[['symbol','quarter','i_cut']+PF],on=['symbol','quarter'])
key=['vol60','r6m','r1y','vs_nifty_1m','r3d','from_52w_high','r1m','vs_ma200']
plk=pl.dropna(subset=key); mu=plk[key].mean(); sd=plk[key].std()
Z=((plk[key]-mu)/sd).values
nn=[]
for _,row in t.iterrows():
    z=((row[key]-mu)/sd).values.astype(float); dist=np.sqrt(((Z-z)**2).sum(1))
    ix=np.argsort(dist)[:100]; nn.append(plk.fwd.values[ix].mean())
t['nn_placebo']=nn
print('\nFULL RF picks (ensemble, n=%d): results avg %.2f ; 100-nearest non-results lookalikes avg %.2f'%(len(t),t.ret.mean(),np.mean(nn)))
print('pick profile medians vs group medians:')
pr=pd.DataFrame({'picks':t[key+['r20d','dist_20h']].median(),'group':G[key+['r20d','dist_20h']].median()}).round(3); print(pr.to_string())
# simple profile rule from pick profile, on results (all 22 q) and placebo
for vthr,r6 in [(0.35,-0.2),(0.40,-0.25),(0.45,-0.2)]:
    a=G[(G.vol60>=vthr)&(G.r6m<=r6)]; b=pl[(pl.vol60>=vthr)&(pl.r6m<=r6)]
    print(f'profile vol60>={vthr} & r6m<={r6}: results n={len(a)} avg={a.ret.mean():.2f} q14-21 {a[a.qn>=14].ret.mean():.2f} | placebo n={len(b)} avg={b.fwd.mean():.2f} perdate={b.groupby("i").fwd.mean().mean():.2f}')
