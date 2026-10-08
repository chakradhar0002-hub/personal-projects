import os  # LAB_ROOT: folder holding search22/, sector/, sector_lab/data/ and five_pct/
import pandas as pd, numpy as np
S=os.environ.get('LAB_ROOT', 'lab') + '/'
D=S+'sector_lab/data/'
ev=pd.read_csv(D+'events.csv')
ret=pd.read_csv(D+'returns.csv',index_col=0)
intr=pd.read_csv(D+'intraday.csv',index_col=0)
idx=pd.read_csv(D+'index_close.csv',index_col=0)
ses=pd.read_csv(D+'sessions.csv')
assert (ses.day.values==ret.index.values).all()
print('events',ev.shape,'dups',ev.duplicated(['symbol','qn']).sum())
print('i_m1-i_cut',(ev.i_m1-ev.i_cut).value_counts().to_dict(),'i_rd-i_m1',(ev.i_rd-ev.i_m1).value_counts().to_dict(),'i_p1-i_rd',(ev.i_p1-ev.i_rd).value_counts().to_dict())
R=ret.values; I=intr.values; col={s:k for k,s in enumerate(ret.columns)}
rows=[]
for e in ev.itertuples():
    c=col[e.symbol]; i=e.i_cut
    r3=R[i-2:i+1,c]
    td=R[e.i_m1,c]+R[e.i_rd,c]+R[e.i_p1,c]
    si=e.sector_index
    if isinstance(si,str) and si in idx.columns:
        x=idx[si].values; s3=x[i]/x[i-3]-1
    else: s3=np.nan
    rows.append(dict(symbol=e.symbol,qn=e.qn,in_fo=e.in_fo,td=td,td_ev=e.three_day,r3d_sum=r3.sum(),r3d_cmp=np.prod(1+r3)-1,intra0=I[i,c],sec_3d=s3,
        dm1=R[e.i_m1,c],rd=R[e.i_rd,c],dp1=R[e.i_p1,c],cutoff=e.cutoff,day_cut=ses.day[i]))
m=pd.DataFrame(rows)
print('cutoff matches session',(m.cutoff==m.day_cut).mean())
print('td vs events three_day max diff',np.nanmax(abs(m.td-m.td_ev)))
fa=pd.read_csv(S+'five_pct/A_rule_search/features_all.csv')
j=m.merge(fa[['symbol','qn','r3d','intra0','sec_3d','three_day','in_fo']],on=['symbol','qn'],suffixes=('','_fa'))
print('merged',len(j))
for a,b in [('r3d_sum','r3d'),('r3d_cmp','r3d'),('intra0','intra0_fa'),('sec_3d','sec_3d_fa'),('td','three_day')]:
    d=abs(j[a]-j[b]); print(a,b,'maxdiff',np.nanmax(d),'n>1e-6',(d>1e-6).sum(),'nan a',j[a].isna().sum(),'nan b',j[b].isna().sum())
print('in_fo same',(j.in_fo==j.in_fo_fa).mean())
m.to_csv('rebuilt.csv',index=False)
