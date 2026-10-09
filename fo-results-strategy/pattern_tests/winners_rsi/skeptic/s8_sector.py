#!/usr/bin/env python3
"""S8. Sector momentum check (diagnostic): how much of the RSI split is the stock's sector being hot?
  - sector index 20-session return to the cutoff (pre-results, knowable) as a control among winners;
  - the W x HI interaction on all results with the outcome measured vs the stock's own sector index;
  - calendar-time long-short (main minus RSI<=50 winners) on sector-relative daily returns.
"""
import numpy as np
import pandas as pd

from common import DATA, HERE, Log, ols

L = Log('s8_sector.log')
P = pd.read_csv(f'{HERE}/panel.csv.gz')
ix = pd.read_csv(f'{DATA}/index_close.csv', index_col=0)
c = P.i_cut.to_numpy(int)
sec_pre = np.full(len(P), np.nan)
for s_, g in P.groupby('sector_index'):
    B = ix[s_].to_numpy(float)
    cc = g.i_cut.to_numpy(int)
    sec_pre[P.index.get_indexer(g.index)] = (B[cc] / B[cc - 20] - 1) * 100
P['sec_pre20'] = sec_pre
P['HIf'] = (P.cut_rsi14 > 50).astype(float)
P['Wf'] = (P.XN_mine > 4).astype(float)
P['HIxW'] = P.HIf * P.Wf
P['sec10'] = P.sec_pre20 / 10
P['secrel10'] = (P.sec_pre20 - P.nifty_pre20) / 10
P['mom10'] = P.stock_pre21 / 10
P['stock_vs_sec10'] = (P.stock_pre21 - P.sec_pre20) / 10
W = P[P.Wf == 1]
L(f"winners: sector index 20-session return to the cutoff: RSI>50 {W.loc[W.HIf == 1, 'sec_pre20'].mean():+.2f}%, "
  f"RSI<=50 {W.loc[W.HIf == 0, 'sec_pre20'].mean():+.2f}%  (sector minus Nifty: "
  f"{(W.sec_pre20 - W.nifty_pre20)[W.HIf == 1].mean():+.2f} vs {(W.sec_pre20 - W.nifty_pre20)[W.HIf == 0].mean():+.2f})")
L('winners, vsN_net, quarter FE, quarter clusters:')
for X in (['HIf'], ['HIf', 'sec10'], ['HIf', 'secrel10'], ['secrel10'], ['HIf', 'stock_vs_sec10']):
    b, se, t, G = ols(W.vsN_net, W[X], cl=W.qn, fe=W.qn)
    L('   ' + ' + '.join(f'{x} {bb:+.2f} (t {tt:.2f})' for x, bb, tt in zip(X, b, t)))
L('winners, outcome vs OWN SECTOR INDEX (vsSEC_net), quarter FE:')
for X in (['HIf'], ['HIf', 'stock_vs_sec10']):
    b, se, t, G = ols(W.vsSEC_net, W[X], cl=W.qn, fe=W.qn)
    L('   ' + ' + '.join(f'{x} {bb:+.2f} (t {tt:.2f})' for x, bb, tt in zip(X, b, t)))
L('all results, vs sector: vsSEC ~ HI + W + HI x W, quarter FE')
b, se, t, G = ols(P.vsSEC_net, P[['HIf', 'Wf', 'HIxW']], cl=P.qn, fe=P.qn)
L('   ' + ', '.join(f'{x} {bb:+.2f} (t {tt:.2f})' for x, bb, tt in zip(['HI', 'W', 'HIxW'], b, t)))
L(f"   main rule vs own sector {W.loc[W.HIf == 1, 'vsSEC_net'].mean():+.2f}, all winners {W.vsSEC_net.mean():+.2f}, "
  f"RSI<=50 winners {W.loc[W.HIf == 0, 'vsSEC_net'].mean():+.2f}")
# per sector index: is the split there in most sectors?
rows = []
for s_, g in W.groupby('sector_index'):
    hi, lo = g[g.HIf == 1], g[g.HIf == 0]
    if len(hi) >= 5 and len(lo) >= 5:
        rows.append(dict(sector_index=s_, n_hi=len(hi), hi=hi.vsN_net.mean(), n_lo=len(lo), lo=lo.vsN_net.mean(),
                         gap=hi.vsN_net.mean() - lo.vsN_net.mean(), gap_vs_sector=hi.vsSEC_net.mean() - lo.vsSEC_net.mean()))
S = pd.DataFrame(rows).sort_values('gap')
L('\nwinners by sector index (>=5 in each group):')
L(S.round(2).to_string(index=False))
L(f"sectors with gap > 0: {(S.gap > 0).sum()}/{len(S)}")
S.to_csv(f'{HERE}/s8_by_sector.csv', index=False, float_format='%.4f')
