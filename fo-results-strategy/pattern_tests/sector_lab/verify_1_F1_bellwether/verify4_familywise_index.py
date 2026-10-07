"""Part 4: selection-adjusted placebo for the INDEX sub-family (their index_trades.csv is verified identical to my rebuild for BIG h1).
Each draw: permute bellwether signals within quarter separately per BW definition (same perm for all h, T), recompute the
18 U_all cells (BW{FIRST,BIG,ALL} x T{3,5%} x h{1,3,5}) net 0.04%, record best t among cells with >=30 trades. 2000 draws."""
import os  # SECTOR_LAB: folder holding data/ from sector_lab_data.py
import sys; sys.path.append('/root/.local/lib/python3.11/site-packages')
import numpy as np, pandas as pd
it=pd.read_csv(os.environ.get('SECTOR_LAB', 'sector_lab') + '/F1_bellwether/index_trades.csv')
rng=np.random.default_rng(99)
def tq(qn,v):
    s=pd.Series(v).groupby(qn).mean(); return s.mean()/(s.std(ddof=1)/np.sqrt(len(s)))
def best(perm):
    bt=-9
    for BW,df in it.groupby('BW'):
        trig=df[['qn','group','d','signal']].drop_duplicates(['qn','group','d']).reset_index(drop=True)
        sig=trig.signal.values.copy()
        if perm:
            for q in np.unique(trig.qn):
                idx=np.where(trig.qn.values==q)[0]; sig[idx]=sig[rng.permutation(idx)]
        mp=dict(zip(zip(trig.qn,trig.group,trig.d),sig))
        ps=np.array([mp[k] for k in zip(df.qn,df.group,df.d)])
        for h in [1,3,5]:
            for T in [0.03,0.05]:
                m=(df.h.values==h)&(np.abs(ps)>T)
                if m.sum()<30: continue
                bt=max(bt,tq(df.qn.values[m],np.sign(ps[m])*df.vsn.values[m]-0.0004))
    return bt
a=best(False); print('actual best t',round(a,2))
B=np.array([best(True) for _ in range(2000)])
print('placebo best-t median',round(np.median(B),2),'95th',round(np.percentile(B,95),2),'P(best>=actual)',np.mean(B>=a))
