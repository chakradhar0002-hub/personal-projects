#!/usr/bin/env python3
"""S2. Is the RSI split special to results WINNERS, a general results-period effect, or ordinary momentum?

All comparisons are WITHIN quarter (results) or WITHIN calendar month (quiet days), because the RSI>50 share moves
with the market and the 20-session outcome has big common quarter / month effects.
  A. results days, all 3,280: RSI>50 effect in losers (XN<-4), middle (-4..4), winners (>4); W x HI interaction.
  B. quiet days (no result in [k-10, k+20]): same split by the day-k move, month FE.
  C. difference-in-differences results vs quiet days (month FE, clustered by month), for winners and non-winners;
     triple difference HI x W x RES.
  D. horse race RSI vs 21-session stock return on results days, winners and non-winners.
"""
import numpy as np
import pandas as pd

from common import HERE, Log, ols, sg

L = Log('s2_momentum.log')
P = pd.read_csv(f'{HERE}/panel.csv.gz')
Q = pd.read_csv(f'{HERE}/quiet_panel.csv.gz')
P['HI'] = (P.cut_rsi14 > 50).astype(float)
Q['HI'] = (Q.rsi_mine > 50).astype(float)
grp = lambda x: np.where(x > 4, 'winner XN>4', np.where(x < -4, 'loser XN<-4', 'middle -4..4'))
P['grp'] = grp(P.XN_mine)
Q['grp'] = grp(Q.XN_mine)
rows = []


def split(df, mask, fe, cl, label):
    d = df[mask]
    hi, lo = d[d.HI == 1], d[d.HI == 0]
    b, se, t, G = ols(d.vsN_net, d[['HI']], cl=d[cl], fe=d[fe])
    rows.append(dict(sample=label, n_hi=len(hi), n_lo=len(lo), mean_hi=hi.vsN_net.mean(), mean_lo=lo.vsN_net.mean(),
                     pooled_gap=hi.vsN_net.mean() - lo.vsN_net.mean(), within_gap=b[0], se=se[0], t=t[0], G=G,
                     fe=fe))
    return b[0], se[0]


L('A/B. RSI(14)>50 vs <=50 (measured 2 sessions before the result session / before day k); 20-session hedged net')
for g in ['winner XN>4', 'middle -4..4', 'loser XN<-4']:
    split(P, P.grp == g, 'qn', 'qn', f'RESULTS {g}')
split(P, P.XN_mine <= 4, 'qn', 'qn', 'RESULTS non-winners XN<=4')
split(P, P.XN_mine > -1e9, 'qn', 'qn', 'RESULTS all')
for g in ['winner XN>4', 'middle -4..4', 'loser XN<-4']:
    split(Q, Q.grp == g, 'month', 'month', f'QUIET {g}')
split(Q, Q.XN_mine > -1e9, 'month', 'month', 'QUIET all')
# quiet winners non-overlapping (one per symbol per 20 sessions)
QW = Q[Q.XN_mine > 4].sort_values(['symbol', 'i'])
keep, last = [], {}
for idx, s, i in zip(QW.index, QW.symbol, QW.i):
    if i - last.get(s, -999) > 20:
        keep.append(idx)
        last[s] = i
split(Q, Q.index.isin(keep), 'month', 'month', 'QUIET winners, non-overlapping')
# results with month FE too (comparable to quiet)
split(P, P.grp == 'winner XN>4', 'month', 'month', 'RESULTS winner XN>4 (month FE)')
split(P, P.XN_mine <= 4, 'month', 'month', 'RESULTS non-winners (month FE)')
A = pd.DataFrame(rows)
L(A.round(3).to_string(index=False))
A.to_csv(f'{HERE}/s2_rsi_splits.csv', index=False, float_format='%.4f')

L('\nA2. results days, all 3,280: vsN ~ HI + W + HI x W, quarter FE, SE clustered by quarter')
P['Wf'] = (P.XN_mine > 4).astype(float)
P['HIxW'] = P.HI * P.Wf
b, se, t, G = ols(P.vsN_net, P[['HI', 'Wf', 'HIxW']], cl=P.qn, fe=P.qn)
for nm, bb, ss, tt in zip(['HI', 'W', 'HI x W'], b, se, t):
    L(f'   {nm:8s} {bb:+.3f} (se {ss:.3f}, t {tt:.2f})')
L(f'   -> RSI>50 effect for non-winners {b[0]:+.2f}; for winners {b[0] + b[2]:+.2f}; the winner-specific extra '
  f'{b[2]:+.2f} (t {t[2]:.2f})')
# same with continuous XN control and month clustering
b2, se2, t2, _ = ols(P.vsN_net, P[['HI', 'Wf', 'HIxW']], cl=P.month, fe=P.month)
L(f'   month FE / month clusters: HI {b2[0]:+.3f} (t {t2[0]:.2f}), HI x W {b2[2]:+.3f} (t {t2[2]:.2f})')

L('\nC. difference-in-differences results vs quiet days (month FE, SE clustered by month)')
for lab, mr, mq in [('winners XN>4', P.XN_mine > 4, Q.XN_mine > 4), ('non-winners XN<=4', P.XN_mine <= 4, Q.XN_mine <= 4),
                    ('all', P.XN_mine > -1e9, Q.XN_mine > -1e9)]:
    pool = pd.concat([pd.DataFrame({'y': P.loc[mr, 'vsN_net'], 'HI': P.loc[mr, 'HI'], 'RES': 1.0,
                                    'month': P.loc[mr, 'month']}),
                      pd.DataFrame({'y': Q.loc[mq, 'vsN_net'], 'HI': Q.loc[mq, 'HI'], 'RES': 0.0,
                                    'month': Q.loc[mq, 'month']})], ignore_index=True)
    pool['HIxRES'] = pool.HI * pool.RES
    b, se, t, G = ols(pool.y, pool[['HI', 'RES', 'HIxRES']], cl=pool.month, fe=pool.month)
    L(f'   {lab:18s}: HI (quiet) {b[0]:+.3f} (se {se[0]:.3f}); HI x RES (results-specific) {b[2]:+.3f} '
      f'(se {se[2]:.3f}, t {t[2]:.2f}); G={G}')
# triple difference
pool = pd.concat([pd.DataFrame({'y': P.vsN_net, 'HI': P.HI, 'W': (P.XN_mine > 4).astype(float), 'RES': 1.0,
                                'month': P.month}),
                  pd.DataFrame({'y': Q.vsN_net, 'HI': Q.HI, 'W': (Q.XN_mine > 4).astype(float), 'RES': 0.0,
                                'month': Q.month})], ignore_index=True)
for a, b_ in [('HI', 'W'), ('HI', 'RES'), ('W', 'RES')]:
    pool[f'{a}x{b_}'] = pool[a] * pool[b_]
pool['HIxWxRES'] = pool.HI * pool.W * pool.RES
cols = ['HI', 'W', 'RES', 'HIxW', 'HIxRES', 'WxRES', 'HIxWxRES']
b, se, t, G = ols(pool.y, pool[cols], cl=pool.month, fe=pool.month)
L('   triple difference (all stocks, month FE, month clusters):')
for nm, bb, ss, tt in zip(cols, b, se, t):
    L(f'      {nm:9s} {bb:+.3f} (se {ss:.3f}, t {tt:.2f})')

L('\nD. horse race on results days (quarter FE, quarter clusters): vsN ~ HI + stock 21-session return (per 10 pts)')
P['mom10'] = P.stock_pre21 / 10
P['rsi10'] = (P.cut_rsi14 - 50) / 10
for lab, m in [('winners', P.XN_mine > 4), ('non-winners', P.XN_mine <= 4), ('all', P.XN_mine > -1e9)]:
    d = P[m]
    out = []
    for X in (['HI'], ['mom10'], ['HI', 'mom10'], ['rsi10'], ['rsi10', 'mom10']):
        b, se, t, G = ols(d.vsN_net, d[X], cl=d.qn, fe=d.qn)
        out.append(' + '.join(f'{x} {bb:+.2f} (t {tt:.2f})' for x, bb, tt in zip(X, b, t)))
    L(f'   {lab:11s} (n {m.sum()}, corr RSI vs 21d ret {d.cut_rsi14.corr(d.stock_pre21, method="spearman"):.2f}): '
      + ' | '.join(out))
# quiet days same horse race (month FE)
for lab, m in [('QUIET winners', Q.XN_mine > 4), ('QUIET all', Q.XN_mine > -1e9)]:
    d = Q[m].copy()
    d['mom10'] = d.stock_pre21 / 10
    out = []
    for X in (['HI'], ['mom10'], ['HI', 'mom10']):
        b, se, t, G = ols(d.vsN_net, d[X], cl=d.month, fe=d.month)
        out.append(' + '.join(f'{x} {bb:+.2f} (t {tt:.2f})' for x, bb, tt in zip(X, b, t)))
    L(f'   {lab:13s} (n {m.sum()}): ' + ' | '.join(out))

L('\nE. RSI>50 share by group (is "RSI>50" just a bull-market label?)')
L(f"   results winners {P.loc[P.XN_mine > 4, 'HI'].mean() * 100:.1f}%, results non-winners "
  f"{P.loc[P.XN_mine <= 4, 'HI'].mean() * 100:.1f}%, quiet winners {Q.loc[Q.XN_mine > 4, 'HI'].mean() * 100:.1f}%, "
  f"quiet all {Q.HI.mean() * 100:.1f}%")
