import os  # SECTOR_LAB: folder holding data/ from sector_lab_data.py
import sys; sys.path.append('/root/.local/lib/python3.11/site-packages')
import pandas as pd
D=os.environ.get('SECTOR_LAB', 'sector_lab') + '/data/'
e=pd.read_csv(D+'events.csv'); print(e.shape); print(e.timing.value_counts()); print(e.peer_group.value_counts(dropna=False)); print(e.sector_index.value_counts()); print(e.in_fo.value_counts()); print(e.groupby('qn').in_fo.sum().tolist())
ic=pd.read_csv(D+'index_close.csv',nrows=2); print([c for c in ic.columns if 'Nifty 50' in c or 'Midcap' in c][:10])
print(e[['move','ret_rd','ret_dp1','timing','i_rd','i_react']].head(8))
print(e.groupby(['symbol','qn']).size().max())
