import os  # SECTOR_LAB: folder holding data/ from sector_lab_data.py
# SIGNAL-ONLY: daily count of sector F&O members inside their 3-day window (no outcomes used)
import sys; sys.path.append('/root/.local/lib/python3.11/site-packages')
import pandas as pd, numpy as np
D=os.environ.get('SECTOR_LAB', 'sector_lab') + '/data/'
e=pd.read_csv(D+'events.csv', usecols=['symbol','qn','sector_index','peer_group','in_fo','i_rd'])
f=e[e.in_fo==True]
for col in ['sector_index','peer_group']:
    g=f[f[col].notna() & (f[col]!='Nifty 500')]
    rows=[]
    for (q,sx),gg in g.groupby(['qn',col]):
        M=len(gg)
        if M<4: continue
        lo=gg.i_rd.min()-1; hi=gg.i_rd.max()+1
        for d in range(lo,hi+1):
            W=((gg.i_rd>=d-1)&(gg.i_rd<=d+1)).sum()
            rows.append((q,sx,d,W,M))
    x=pd.DataFrame(rows,columns=['qn','s','d','W','M']); x['sh']=x.W/x.M
    print(col, len(x), 'W dist', x.W.value_counts().sort_index().to_dict())
    print(' share bins', pd.cut(x.sh,[-0.01,0,0.1,0.2,0.3,0.4,0.5,1]).value_counts().sort_index().to_dict())
    print(' days per sector-quarter with sh>=0.25', x[x.sh>=0.25].groupby(['qn','s']).size().describe().to_dict())
    print(' days per sector-quarter with sh>=0.4', x[x.sh>=0.4].groupby(['qn','s']).size().describe().to_dict())
