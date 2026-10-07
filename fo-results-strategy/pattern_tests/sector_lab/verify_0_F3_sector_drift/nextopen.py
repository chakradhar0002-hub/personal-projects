import os  # SECTOR_LAB: folder holding data/ from sector_lab_data.py
# Robustness add-on (counted as 1 extra check): entry at next session's open instead of reaction-day close.
import sys; sys.path.append('/root/.local/lib/python3.11/site-packages')
import numpy as np, pandas as pd
D=os.environ.get('SECTOR_LAB', 'sector_lab') + '/data/'
O=os.environ.get('SECTOR_LAB', 'sector_lab') + '/verify_0_F3_sector_drift/'
C=pd.read_csv(O+'candidate_trades_h20.csv'); B=pd.read_csv(O+'base_winners_h20.csv')
R=pd.read_csv(D+'returns.csv',index_col=0); I=pd.read_csv(D+'intraday.csv',index_col=0); IC=pd.read_csv(D+'index_close.csv',index_col=0)
n=IC['Nifty 50'].values
def f(df):
    out=[]
    for s,i in zip(df.symbol,df.i_react):
        d=R[s].values[i+1]; it=I[s].values[i+1]
        gap=(1+d)/(1+it)-1 if not(np.isnan(d) or np.isnan(it)) else np.nan
        out.append(gap)
    df=df.copy(); df['gap1']=out
    df['vsn_open']=(1+df.raw)/(1+df.gap1)-1 - (n[df.i_react+20]/n[df.i_react]-1) - 0.0019
    return df
for nm,df in [('C',C),('B',B)]:
    df=f(df); q=df.groupby('qn').vsn_open.mean()*100
    print(nm,'mean next-day gap %.2f%%'%(df.gap1.mean()*100),'vsn next-open avg %.2f qavg %.2f t %.2f f14 %.2f l8 %.2f'%(df.vsn_open.mean()*100,q.mean(),q.mean()/(q.std()/np.sqrt(len(q))),q[q.index<=13].mean(),q[q.index>=14].mean()))
# quarters >= +2% and yearly
q=C.groupby('qn').vsn.mean()*100; print('C quarters >=2%:',(q>=2).sum(),'of',len(q))
C['yr']=C.reaction_day.str[:4]; print(C.groupby('yr').vsn.agg(['size','mean']).round(4))
print(C.sort_values('vsn',ascending=False)[['symbol','qn','reaction_day','grp','n_exc','ex_react','vsn']].head(8))
