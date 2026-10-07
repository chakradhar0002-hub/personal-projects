import os  # LAB_ROOT: folder holding search22/, sector/ and sector_lab/data/
import pandas as pd, numpy as np
S=os.environ.get('LAB_ROOT', 'lab') + ''
D=S+'/sector_lab/data/'
e=pd.read_csv(D+'events.csv'); r=pd.read_csv(D+'returns.csv').set_index('day')
R=r.values; syms=list(r.columns); col={s:i for i,s in enumerate(syms)}
# price index: cumulative product, NaN stays NaN (no trade); fill price forward for levels
lr=np.where(np.isnan(R),0.0,R)
P=np.cumprod(1+lr,axis=0)
valid=~np.isnan(R)
P[~valid]=np.nan
Pf=pd.DataFrame(P).ffill().values
def feats(i,j):
    p=Pf[:i+1,j]; v=valid[:i+1,j]
    # require valid obs
    last200=Pf[i-199:i+1,j] if i>=199 else None
    nv200=v[max(0,i-199):i+1].sum()
    ma200=np.nanmean(last200) if last200 is not None else np.nan
    hi20=np.nanmax(Pf[i-19:i+1,j])
    return Pf[i,j]/ma200-1, Pf[i,j]/hi20-1, nv200
out=[]
for k,row in e.iterrows():
    j=col.get(row.symbol); i=int(row.i_cut)
    if j is None: out.append((np.nan,np.nan,0)); continue
    out.append(feats(i,j))
e['vs200'],e['vs20hi'],e['nv200']=zip(*out)
# my own three_day from returns
e['td_me']=[np.nansum(R[int(a):int(b)+1,col[s]]) if s in col else np.nan for s,a,b in zip(e.symbol,e.i_m1,e.i_p1)]
print('three_day check max abs diff', (e.td_me-e.three_day).abs().max())
# peers reported variants
for g in ['sector_index','industry','peer_group']:
    for name,cond in [('rd<=cut', lambda o,x: o.i_rd<=x.i_cut),('react<=cut',lambda o,x: o.i_react<=x.i_cut),('rd<cut',lambda o,x:o.i_rd<x.i_cut)]:
        cnt=[]
        for k,x in e.iterrows():
            if pd.isna(x[g]): cnt.append(np.nan); continue
            o=e[(e.qn==x.qn)&(e[g]==x[g])&(e.symbol!=x.symbol)]
            cnt.append(int(cond(o,x).sum()))
        e[f'pr_{g}_{name}']=cnt
e.to_csv(S+'/five_pct/verify_1_A_rule_search/my_events.csv',index=False)
