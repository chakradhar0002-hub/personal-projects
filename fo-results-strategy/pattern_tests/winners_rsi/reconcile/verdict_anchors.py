#!/usr/bin/env python3
"""Anchors for the merged realistic per-trade number (diagnostics only). Next-open entry (E1a), 0.40 all-in cost."""
import os
import numpy as np
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.environ.get('LAB_ROOT', os.path.abspath(os.path.join(HERE, '..', '..')))  # scratch data folder
U = pd.read_csv(f'{HERE}/claims_panel.csv')
ev = pd.read_csv(f'{HERE}/truth_universe.csv', usecols=['symbol', 'qn', 'year'])
U = U.merge(ev, on=['symbol', 'qn'], validate='1:1')
U['W_LO'] = U.W & ~U.HI
U['n40'] = U.E1a_g - 0.40
out = []
def row(lab, m):
    x = U[m]
    qW = U[U.W & (m | ~U.MAIN) & U.old.where(lab.startswith('old'), True)].groupby('qn').n40.mean()
    out.append(dict(slice=lab, n=len(x), mean=x.n40.mean(), median=x.n40.median(),
                    wins10=np.clip(x.n40, -10, 10).mean(), q_pos=int((x.groupby('qn').n40.mean() > 0).sum()),
                    nq=x.qn.nunique()))
for lab, base in [('all', U.symbol.notna()), ('old cohort (in F&O by qn 1)', U.old), ('ex-2023', U.year != 2023),
                  ('old cohort ex-2023', U.old & (U.year != 2023))]:
    for g, m in [('MAIN', U.MAIN), ('all winners', U.W), ('RSI<=50 winners', U.W_LO)]:
        x = U[base & m]
        qW = U[base & U.W].groupby('qn').n40.mean()
        dW = (x.n40 - x.qn.map(qW)).mean() if g == 'MAIN' else np.nan
        out.append(dict(slice=lab, group=g, n=len(x), mean=x.n40.mean(), median=x.n40.median(),
                        wins10=np.clip(x.n40, -10, 10).mean(), q_pos=int((x.groupby('qn').n40.mean() > 0).sum()),
                        nq=x.qn.nunique(), dW_same_quarter=dW))
A = pd.DataFrame([r for r in out if 'group' in r])
A.to_csv(f'{HERE}/verdict_anchors.csv', index=False, float_format='%.4f')
print(A.round(2).to_string(index=False))
sb = f'{SP}/winners_rsi/skeptic/s1_bootstrap_bias.csv'
if os.path.exists(sb):
    print(open(sb).read())
