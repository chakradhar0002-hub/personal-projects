import os  # LAB_ROOT: folder holding search22/, sector/ and sector_lab/data/
# Data check only: recompute price features at the cutoff and compare with features.csv.
# Does NOT touch three_day or any post-cutoff return.
import pandas as pd, numpy as np
D=os.environ.get('LAB_ROOT', 'lab') + '/'
f=pd.read_csv(D+'search22/features.csv')
e=pd.read_csv(D+'sector_lab/data/events.csv')
r=pd.read_csv(D+'sector_lab/data/returns.csv').drop(columns='day')
idx=pd.read_csv(D+'sector_lab/data/index_close.csv')
print('nifty col?', [c for c in idx.columns if 'Nifty' in c and len(c)<14][:20])
m=f.merge(e[['symbol','quarter','i_cut','i_m1','i_rd','i_p1','ret_dm1','ret_rd','ret_dp1','mcap']],on=['symbol','quarter'],how='left')
print('unmatched',m.i_cut.isna().sum())
R=r.values; P=np.nancumprod(np.where(np.isnan(R),0,R)+1,axis=0)
cols={s:j for j,s in enumerate(r.columns)}
j=m.symbol.map(cols).values; ic=m.i_cut.values.astype(int)
def ret(k): return P[ic,j]/P[ic-k,j]-1
for k,name in [(5,'r1w'),(21,'r1m'),(20,'r1m'),(22,'r1m'),(63,'r3m')]:
    x=ret(k); y=m[name].values; ok=~np.isnan(y)
    print(name,k,'corr',np.corrcoef(x[ok],y[ok])[0,1],'mad',np.nanmedian(np.abs(x[ok]-y[ok])))
nifty=idx['CNX Nifty'].values
nw=nifty[ic]/nifty[ic-5]-1
print('nifty_1w', np.nanmedian(np.abs(nw-m.nifty_1w)), 'vs_nifty_1w=r1w-nifty_1w?', np.nanmedian(np.abs(m.r1w-m.nifty_1w-m.vs_nifty_1w)))
print('vs_nifty_1w = (1+r)/(1+n)-1?', np.nanmedian(np.abs((1+m.r1w)/(1+m.nifty_1w)-1-m.vs_nifty_1w)))
# ma50
ma50=np.array([np.mean(P[i-49:i+1,jj]) for i,jj in zip(ic,j)])
print('vs_ma50 mad',np.nanmedian(np.abs(P[ic,j]/ma50-1-m.vs_ma50)))
hi=np.array([np.max(P[max(0,i-249):i+1,jj]) for i,jj in zip(ic,j)])
print('from_52w_high mad',np.nanmedian(np.abs(P[ic,j]/hi-1-m.from_52w_high)))
# three_day consistency (sanity only of definition)
td=m.ret_dm1+m.ret_rd+m.ret_dp1
print('three_day = sum of 3 daily:',np.nanmax(np.abs(td-m.three_day)))
d1=m.ret_dm1; d2=m.ret_dm1+m.ret_rd
tp=np.where(d1>0.03,d1,np.where(d2>0.03,d2,td))
print('tp3 def check:',np.nanmax(np.abs(tp-m.tp3)))
print('returns at i_m1 match ret_dm1:',np.nanmax(np.abs(R[m.i_m1.values.astype(int),j]-m.ret_dm1)))
print('vol60 check', np.nanmedian(np.abs(np.array([np.nanstd(R[i-59:i+1,jj],ddof=1) for i,jj in zip(ic,j)])*np.sqrt(252)-m.vol60)))
print('log_mcap vs mcap', np.nanmedian(np.abs(np.log(m.mcap)-m.log_mcap)))
print(m.in_fo.value_counts(), m.groupby('qn').size().to_dict())
