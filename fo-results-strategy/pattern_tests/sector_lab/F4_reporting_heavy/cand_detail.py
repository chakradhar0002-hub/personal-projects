import sys; sys.path.append('/root/.local/lib/python3.11/site-packages')
import pandas as pd, numpy as np
s=pd.read_csv('variant_summary.csv'); pq=pd.read_csv('per_quarter_nifty_net.csv',index_col=0)
c=['name','trades','quarters','avg_raw_net','avg_nifty_net','avg_sector_net','pct_win','perq_nifty','t_q','t_date','first14','last8','q_pos','q_raw_ge2','q_gross_ge2','max_q_raw','perq_raw','t_q_raw','perq_nifty_gross','t_q_gross','first14_gross','last8_gross']
print(s.sort_values('t_q',ascending=False)[c].round(3).to_string())
print(pq[['A11','A01','A05','B07','C01','C03','D03','B03']].round(2).to_string())
f=pd.read_csv('events_with_signals.csv')
x=f[(f.G2_elig==True)&(f.G2_c5>=6)]
print('A11 by peer group', x.groupby('peer_group').agg(n=('o3_nifty','size'),m=('o3_nifty','mean')).round(2).to_string())
x=f[(f.G1_elig==True)&(f.G1_before==0)]
print('C01 by sector', x.groupby('sector_index').agg(n=('o3_nifty','size'),m=('o3_nifty','mean')).round(2).to_string())
