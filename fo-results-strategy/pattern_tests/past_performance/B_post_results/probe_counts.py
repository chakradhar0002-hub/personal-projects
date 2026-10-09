#!/usr/bin/env python3
"""FEATURE-ONLY probe (no forward return of any kind is read): subset sizes for the trade-B pre-registration and the
point-in-time check of within-quarter thresholds. From outcomes.csv only the tradability flag tradable_B is read."""
import numpy as np
import pandas as pd

SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
F = f'{SP}/perf/features'
OUT = f'{SP}/perf/B_post_results'
LOG = open(f'{OUT}/probe_counts.log', 'w')


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    LOG.write(s + '\n')


p = pd.read_csv(f'{F}/panel.csv')
o = pd.read_csv(f'{F}/outcomes.csv', usecols=['symbol', 'qn', 'tradable_B'])
p = p.merge(o, on=['symbol', 'qn'], validate='1:1')
h = pd.read_csv(f'{F}/history.csv')
P('rows', len(p), 'tradable_B', int(p.tradable_B.sum()))
T = p[p.tradable_B].copy()
W = T[T.W == True]
WR = W[W.cut_rsi14 > 50]
P('winners', len(W), 'winners RSI>50', len(WR), '(documented 392 / 232)')

# point-in-time check: every drift used in mean_drift_4 of ANY F&O row of quarter q ended before the earliest decision
# (cutoff and reaction day) of quarter q -> a within-quarter cross-sectional threshold uses only known values
hh = h.set_index(['symbol', 'qn'])
bad = 0
for q, g in p.groupby('qn'):
    first_dec = min(g.i_cut.min(), g.i_react.min())
    ends = []
    for s, qq in zip(g.symbol, g.qn):
        hs = h[(h.symbol == s) & (h.qn < qq)].sort_values('qn', ascending=False).head(4)
        ends += hs.h_dr_end[hs.h_dr.notna()].tolist() + hs.h_td_end.tolist() + hs.h_xn_end.tolist()
    if ends:
        mx = max(ends)
        if mx >= first_dec:
            bad += 1
            P(f'  qn {q}: latest history item ends {mx} >= first decision {first_dec}  NOT point in time')
        else:
            P(f'  qn {q}: latest last-4 history item of any F&O row ends at session {mx} < first decision {first_dec} (margin {first_dec - mx})')
P('quarters failing the point-in-time threshold check:', bad)

# within-quarter thresholds from ALL F&O results of the quarter (feature values only)
med = p.groupby('qn').mean_drift_4_B.median()
q80 = p.groupby('qn').mean_drift_4_B.quantile(0.8)
q20 = p.groupby('qn').mean_drift_4_B.quantile(0.2)
for d in (T, W, WR):
    pass


def flags(d):
    f = {}
    f['REPEAT1'] = (d.prev1_winner_B == 1, d.prev1_winner_B.notna())
    f['REPEAT4'] = (d.n_winner_4_B >= 2, d.n_winner_4_B.notna())
    f['FIRSTTIME4'] = (d.n_winner_4_B == 0, d.n_winner_4_B.notna())
    f['PREVWIN_RAN'] = ((d.prev1_winner_B == 1) & (d.prev1_drift20_B > 0),
                        d.prev1_winner_B.notna() & ((d.prev1_winner_B == 0) | d.prev1_drift20_B.notna()))
    m = d.qn.map(med)
    f['DRIFT4_TOP'] = (d.mean_drift_4_B >= m, d.mean_drift_4_B.notna())
    f['DRIFT4_BOT'] = (d.mean_drift_4_B < m, d.mean_drift_4_B.notna())
    for L in (63, 126, 252):
        c = d[f'rank_vsN_{L}_B']
        f[f'MOM{L}_TOP'] = (c > 50, c.notna())
        f[f'MOM{L}_BOT'] = (c <= 50, c.notna())
    f['NEAR52H'] = (d.dist_52wh_B >= -5, d.dist_52wh_B.notna())
    f['FAR52H'] = (d.dist_52wh_B < -5, d.dist_52wh_B.notna())
    f['SEC252_UP'] = (d.vsSec_252_B > 0, d.vsSec_252_B.notna())
    f['SEC252_DN'] = (d.vsSec_252_B <= 0, d.vsSec_252_B.notna())
    return f


for lab, d in (('W', W), ('WR', WR)):
    P(f'\n{lab}: subset n / eligible n / quarters with trades / first14 n / last8 n')
    for k, (s, e) in flags(d).items():
        s = s & e
        P(f'  {k:12s} {int(s.sum()):4d} / {int(e.sum()):4d}  q={d.qn[s].nunique():2d}  first14={int((s & (d.qn <= 13)).sum()):3d} last8={int((s & (d.qn >= 14)).sum()):3d}')
P('\ndist_52wh_B among winners: quantiles', W.dist_52wh_B.quantile([.1, .25, .5, .75, .9]).round(1).tolist())
P('rank_vsN_63/126/252_B among winners: share > 50', [round((W[f'rank_vsN_{L}_B'] > 50).mean(), 3) for L in (63, 126, 252)])
P('vsSec_252_B among winners: share > 0', round((W.vsSec_252_B > 0).mean(), 3))

# standalone (all tradable results, any reaction)
e = T.mean_drift_4_B.notna()
P(f'\nALL tradable with mean_drift_4 known: {int(e.sum())}')
top = T.mean_drift_4_B >= T.qn.map(q80)
bot = T.mean_drift_4_B <= T.qn.map(q20)
P(f'  DRIFT4_Q5 (>= quarter 80th pct of all F&O results): {int((top & e).sum())}; DRIFT4_Q1 (<= 20th pct): {int((bot & e).sum())}')
e4 = T.n_drift_4_B == 4
P(f'  CONSIST_DRIFT (n_pos_drift_4 >= 3 of 4 known): {int((e4 & (T.n_pos_drift_4_B >= 3)).sum())} of eligible {int(e4.sum())}')
P('  n_drift_4_B distribution:', T.n_drift_4_B.value_counts(dropna=False).to_dict())
LOG.close()
