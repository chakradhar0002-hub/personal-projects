"""ADDED AFTER A35: C10 with VIX at k-1 (discovery only)."""
import numpy as np, pandas as pd
SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = SP + '/more_avg/search_context'
H, DISC_MAX = 20, 13
D = pd.read_csv(OUT + '/discovery_trades.csv')
assert D.qn.max() <= DISC_MAX
T1 = pd.read_csv(OUT + '/cutpoints.csv').set_index('feature').loc['vix', 't1']
V = pd.read_csv(SP + '/sector_lab/data/index_close.csv', index_col=0)['India VIX'].values
D['vix_lag'] = V[D.i_react.values - 1]
for name, m in [('C10 VIX(k)<=t1', D.vix <= T1), ('A35 VIX(k-1)<=t1', D.vix_lag <= T1)]:
    t = D[m]; qm = t.groupby('qn').vsN_net.mean()
    print(f'{name:20s} n={len(t)} avg={t.vsN_net.mean():+.2f} wo5={t.vsN_net.sort_values().iloc[:-5].mean():+.2f} q+={int((qm>0).sum())}/{len(qm)}')
print('disagreements:', int(((D.vix <= T1) != (D.vix_lag <= T1)).sum()))
