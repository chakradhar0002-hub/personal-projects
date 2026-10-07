import os  # SECTOR_LAB: folder holding data/ from sector_lab_data.py
# SIGNAL-ONLY exploration (no outcome columns are read or used). Purpose: choose fixed thresholds sensibly.
import sys; sys.path.append('/root/.local/lib/python3.11/site-packages')
import pandas as pd, numpy as np
D=os.environ.get('SECTOR_LAB', 'sector_lab') + '/data/'
e=pd.read_csv(D+'events.csv', usecols=['symbol','qn','sector_index','peer_group','in_fo','i_cut','i_rd','i_react','timing','results_date','result_day','cutoff'])
f=e[e.in_fo==True].copy()
print('F&O events', len(f))
print('i_rd-i_cut', (f.i_rd-f.i_cut).value_counts().to_dict())
# sector membership per quarter
m=f[f.sector_index!='Nifty 500'].groupby(['qn','sector_index']).size().unstack(fill_value=0)
print(m.T.to_string())
pg=f[f.peer_group.notna()].groupby(['qn','peer_group']).size().unstack(fill_value=0)
print(pg.T.to_string())
# strict count of sector peers (excl self) with i_rd in [t+1,t+2], t=i_cut ; foresight k=3,5
def counts(g, col):
    out=[]
    for (q,s),gg in g.groupby(['qn',col]):
        rd=gg.i_rd.values
        for idx,row in gg.iterrows():
            t=row.i_cut
            c2=((rd>=t+1)&(rd<=t+2)).sum()-1
            c3=((rd>=t+1)&(rd<=t+3)).sum()-1
            c5=((rd>=t+1)&(rd<=t+5)).sum()-1
            n=len(gg)-1
            before=(rd<row.i_rd).sum()
            out.append((idx,c2,c3,c5,n,before))
    return pd.DataFrame(out,columns=['idx','c2','c3','c5','npeers','before']).set_index('idx')
for col,sub in [('sector_index',f[f.sector_index!='Nifty 500']),('peer_group',f[f.peer_group.notna()])]:
    c=counts(sub,col)
    print(col, 'n',len(c))
    for k in ['c2','c3','c5']:
        print(k, c[k].value_counts().sort_index().to_dict())
    print('share c3', pd.cut(c.c3/c.npeers.clip(lower=1),[-0.01,0,0.1,0.2,0.3,0.5,1]).value_counts().sort_index().to_dict())
    print('before==0', (c.before==0).sum(), ' before/npeers>=0.5', (c.before/c.npeers.clip(lower=1)>=0.5).sum(), 'npeers>=3', (c.npeers>=3).sum())
# season start
s0=f.groupby('qn').i_rd.min(); s0d=f.groupby('qn').result_day.min()
first=f.loc[f.groupby('qn').i_rd.idxmin(),['qn','symbol','result_day']]
print(first.to_string())
f['sinc']=f.i_rd-f.qn.map(s0)
print('sessions since season start', f.sinc.describe().to_dict())
print(pd.cut(f.sinc,[-1,4,9,14,19,24,29,39,200]).value_counts().sort_index().to_dict())
# 5th-reporter based start
s5=f.groupby('qn').i_rd.apply(lambda x: np.sort(x.values)[4])
print('s5-s0', (s5-s0).to_dict())
