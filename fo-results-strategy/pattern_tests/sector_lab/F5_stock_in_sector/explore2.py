import os  # SECTOR_LAB: folder holding data/ from sector_lab_data.py
import sys
sys.path.append('/root/.local/lib/python3.11/site-packages')
import pandas as pd, numpy as np
pd.set_option('display.width',250); pd.set_option('display.max_columns',50); pd.set_option('display.max_rows',200)
D=os.environ.get('SECTOR_LAB', 'sector_lab') + '/data/'
ev=pd.read_csv(D+'events.csv')
ic=pd.read_csv(D+'index_close.csv',index_col=0)
ses=pd.read_csv(D+'sessions.csv')
ir=ic.pct_change(fill_method=None)
# where are the NaN gaps after 2021?
for c in ['Nifty Consumer Durables','Nifty Oil & Gas','Nifty India Manufacturing','Nifty India Digital','Nifty India Defence']:
    s=ic[c]; na=s[s.isna()]; print(c, 'NaN after 2020-06:', (na.index>'2020-06-01').sum(), na.index[na.index>'2020-06-01'][:5].tolist())
# verify sector_3d / nifty_3d = sum of daily index returns over i_m1,i_rd,i_p1
nr=ir['Nifty 50'].values
e=ev.dropna(subset=['three_day']).copy()
calc=nr[e.i_m1]+nr[e.i_rd]+nr[e.i_p1]
print('nifty3d diff', np.nanmax(np.abs(calc-e.nifty_3d)))
sc=np.array([ir[s].values[a]+ir[s].values[b]+ir[s].values[c] for s,a,b,c in zip(e.sector_index,e.i_m1,e.i_rd,e.i_p1)])
print('sec3d diff', np.nanmax(np.abs(sc-e.sector_3d)), np.isnan(sc).sum())
print(e[np.isnan(sc)][['symbol','qn','sector_index','results_date','sector_3d']].head(20))
r=pd.read_csv(D+'returns.csv',index_col=0)
calc3=[r[s].values[a]+r[s].values[b]+r[s].values[c] for s,a,b,c in zip(e.symbol,e.i_m1,e.i_rd,e.i_p1)]
print('3d diff', np.nanmax(np.abs(np.array(calc3)-e.three_day)), np.isnan(calc3).sum())
print(ev[ev.three_day.isna()][['symbol','qn','results_date']])
print(ev.timing.value_counts())
print(ev[ev.timing=='Non-trading day'][['results_date','result_day','reaction_day','day_m1','day_p1','cutoff']].head())
print(ev.fin_type.value_counts())
print(ev[['sales_yoy','sales_qoq','pat_qoq']].describe())
print(ev.groupby('sector_index').in_fo.mean())
print(ev.peer_group.value_counts(dropna=False))
# in_fo by symbol switches
sw=ev.groupby('symbol').in_fo.agg(['min','max','sum','size']); print((sw['min']!=sw['max']).sum(),'symbols switch')
# sector_index constant per symbol?
print(ev.groupby('symbol').sector_index.nunique().max())
# i_p1 - i_cut
print((ev.i_p1-ev.i_cut).value_counts())
