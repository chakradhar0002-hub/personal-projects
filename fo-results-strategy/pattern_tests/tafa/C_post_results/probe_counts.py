#!/usr/bin/env python3
"""Feature-only probe (no outcome read): prevalence of every pre-registered signal / subset."""
import os
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
f = pd.read_csv(f'{HERE}/features.csv')
q = pd.read_csv(f'{HERE}/quiet_days.csv.gz')
pd.set_option('display.width', 250)
P1 = {'P1_GOOD_BREAKOUT_VOL': f.GOOD & f.BREAKOUT_VOL, 'P2_GOOD_BELOW50': f.GOOD & f.BELOW50,
      'P3_BAD_BRKDN_VOL': f.BAD & f.BRKDN_VOL, 'GOOD': f.GOOD, 'BAD': f.BAD, 'BREAKOUT_VOL': f.BREAKOUT_VOL,
      'BRK20': f.BRK20, 'GAPHOLD': f.GAPHOLD, 'VOL15': f.VOL15, 'BELOW50': f.BELOW50, 'BRKDN_VOL': f.BRKDN_VOL,
      'W': f.W, 'E_GOOD': f.E_GOOD, 'E_BAD': f.E_BAD, 'E_TA_RX': f.E_TA_RX}
print(pd.DataFrame({k: v.groupby(f.qn).sum() for k, v in P1.items()}).astype(int).T.to_string())
w = f[f.W]
FA = ['GOOD', 'BAD', 'Q_HI', 'Q_LO', 'CHEAP', 'EXP']
TA = ['UP200', 'DN200', 'RSI_HI', 'RSI_LO']
S = {c: w[c] for c in FA + TA}
for a in FA:
    for b in TA:
        S[f'{a}&{b}'] = w[a] & w[b]
S['ALL_BULL'] = w.GOOD & w.UP200 & w.RSI_HI
S['ALL_BEAR'] = w.BAD & w.DN200 & w.RSI_LO
tab = pd.DataFrame({k: v.groupby(w.qn).sum() for k, v in S.items()}).astype(int).T
tab['total'] = tab.sum(1)
tab['nq'] = (tab.drop(columns='total') > 0).sum(1)
print('\nplain winners per quarter:', w.groupby('qn').size().to_dict(), 'total', len(w))
print(tab.to_string())
print('\nquiet days in_fo:', len(q), 'winners', int(q.W.sum()))
for c in ['BREAKOUT_VOL', 'BELOW50', 'BRKDN_VOL']:
    print(c, int(q[c].sum()), ' with L_GOOD' if c != 'BRKDN_VOL' else ' with L_BAD',
          int((q[c] & (q.L_GOOD if c != 'BRKDN_VOL' else q.L_BAD)).sum()))
qw = q[q.W]
for c in ['L_GOOD', 'L_BAD', 'UP200', 'DN200', 'RSI_HI', 'RSI_LO']:
    print('quiet winners', c, int(qw[c].sum()))
