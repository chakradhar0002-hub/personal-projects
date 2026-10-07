"""Part 3: (a) definition sensitivity: size = current vs previous-quarter mcap, ties = mean vs largest only (4 cells, 1 is the candidate).
(b) duplicate triggers: same bellwether/date feeding several indices; collapse to one trade per (date, bellwether) and per date.
(c) which bellwethers/dates drive it."""
import os  # SECTOR_LAB: folder holding data/ from sector_lab_data.py
import sys; sys.path.append('/root/.local/lib/python3.11/site-packages')
sys.argv=['x']
import importlib.util, numpy as np, pandas as pd
P=os.environ.get('SECTOR_LAB', 'sector_lab') + '/verify_1_F1_bellwether/'
spec=importlib.util.spec_from_file_location('v2',P+'verify2.py'); v2=importlib.util.module_from_spec(spec); spec.loader.exec_module(v2)
e=v2.e; g=e[e.sector_index!='Nifty 500']
for sizecol in ['size','mcap']:
    for tie in ['mean','largest']:
        rows=[]
        for (q,s),m in g.groupby(['qn','sector_index']):
            k=m[m[sizecol].notna()] if sizecol=='mcap' else m[m['size'].notna()]
            if len(m)<2 or len(k)<3: continue
            top=k.nlargest(3,sizecol); d=top.i_react.min(); x=top[top.i_react==d]
            if tie=='largest': x=x.nlargest(1,sizecol)
            rows.append(dict(qn=q,sector=s,d=int(d),sig=x.xr.mean(),bws='|'.join(x.symbol)))
        T=pd.DataFrame(rows); x=v2.trade_vals(T,0.03,1)
        print(sizecol,tie,v2.summ(x.qn,x.vsn-0.0004))
b=pd.read_csv(P+'base_trades_theirdef.csv')
b['v']=b.vsn-0.0004
print('distinct (date,bellwether):',b[['d','bws']].drop_duplicates().shape[0],' distinct dates:',b.d.nunique(),' of',len(b))
c1=b.groupby(['qn','d','bws']).v.mean().reset_index(); print('collapsed per (date,bw):',v2.summ(c1.qn,c1.v))
c2=b.groupby(['qn','d']).v.mean().reset_index(); print('collapsed per date:',v2.summ(c2.qn,c2.v))
print(b.groupby('bws').agg(n=('v','size'),avg=('v',lambda z:z.mean()*100)).sort_values('n',ascending=False).head(15).round(3))
print(b.sort_values('v',ascending=False)[['qn','day','sector','bws','sig','v']].head(8).to_string())
