#!/usr/bin/env python3
"""Independent checks of panel.csv: look-ahead (different code path, merge-based), reproductions (85 lag-rule trades,
392 winners, 232 winners with RSI > 50), coverage by qn, A-vs-B differences. Writes check.log and coverage.csv."""
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = __import__('os').environ.get('REPO_ROOT', '.')  # this repo
LOG = open(f'{HERE}/check.log', 'w')


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    LOG.write(s + '\n')
    LOG.flush()


pd.set_option('display.width', 250, 'display.max_columns', 40)
pn = pd.read_csv(f'{HERE}/panel.csv')
oc = pd.read_csv(f'{HERE}/outcomes.csv')
hi = pd.read_csv(f'{HERE}/history.csv')
assert len(pn) == 3280 and not pn.duplicated(['symbol', 'qn']).any()
assert (pn[['symbol', 'qn']].values == oc[['symbol', 'qn']].values).all()

# ------------------------------------------------------------------ 1. look-ahead, merge-based recomputation
P('1. LOOK-AHEAD')
mx = {}
for tag, col in (('A', 'i_cut'), ('B', 'i_react')):
    x = pn[['symbol', 'qn', col]].rename(columns={'qn': 'qn0', col: 'dec'}).merge(hi, on='symbol')
    x = x[x.qn < x.qn0]
    naive_n = x.groupby(['symbol', 'qn0']).size()
    keep = (x.h_td_end < x.dec) & (x.h_xn_end < x.dec)
    P(f'  {tag}: earlier-quarter results {len(x)}, excluded because 3-day window/reaction not closed before the '
      f'decision: {int((~keep).sum())}')
    x = x[keep].copy()
    assert (x.h_td_end < x.dec).all() and (x.h_xn_end < x.dec).all()
    x['dr_ok'] = x.h_dr.where(x.h_dr_end < x.dec)
    P(f'  {tag}: drifts withheld because their 20-session window had not ended: {int((x.h_dr_end >= x.dec).sum())} '
      f'(of {len(x)} earlier results)')
    assert (x.loc[x.dr_ok.notna(), 'h_dr_end'] < x.loc[x.dr_ok.notna(), 'dec']).all()
    x = x.sort_values(['symbol', 'qn0', 'qn'], ascending=[True, True, False])
    x['rk'] = x.groupby(['symbol', 'qn0']).cumcount()
    g = x.groupby(['symbol', 'qn0'])
    re = pd.DataFrame({'n_prev': g.size()})
    p1 = x[x.rk == 0].set_index(['symbol', 'qn0'])
    re['prev1_three_day'], re['prev1_xn'], re['prev1_drift20'] = p1.h_td, p1.h_xn, p1.dr_ok
    re['mean_three_day_all'], re['mean_xn_all'], re['mean_drift_all'] = g.h_td.mean(), g.h_xn.mean(), g.dr_ok.mean()
    x4 = x[x.rk < 4]
    g4 = x4.groupby(['symbol', 'qn0'])
    f4 = re.n_prev >= 4
    re['mean_three_day_4'] = g4.h_td.mean().where(f4)
    re['n_pos_three_day_4'] = g4.h_td.apply(lambda s: (s > 0).sum()).where(f4)
    re['n_winner_4'] = g4.h_xn.apply(lambda s: (s > 4).sum()).where(f4)
    re['mean_abs_xn_4'] = g4.h_xn.apply(lambda s: s.abs().mean()).where(f4)
    re['mean_drift_4'] = g4.dr_ok.mean().where(f4)
    re['n_pos_drift_4'] = g4.dr_ok.apply(lambda s: (s > 0).sum()).where(f4)
    # rows with no history at all
    pk = pn.set_index(['symbol', 'qn'])
    re = re.reindex(pk.index)
    re['n_prev'] = re.n_prev.fillna(0)
    bad = []
    for c in re.columns:
        a, b = re[c].to_numpy(float), pk[f'{c}_{tag}'].to_numpy(float)
        same = (np.isnan(a) & np.isnan(b)) | (np.abs(a - b) < 1e-4)
        if not same.all():
            bad.append((c, int((~same).sum())))
    P(f'  {tag}: merge-based recomputation of {len(re.columns)} track-record columns vs panel: '
      f'{"all equal" if not bad else bad}')
    assert not bad
    naive = naive_n.reindex(pk.index).fillna(0).to_numpy()
    P(f'  {tag}: rows where the timing filter removed an earlier-quarter result: '
      f'{int((naive != pk[f"n_prev_{tag}"].to_numpy()).sum())}')

# A vs B differences
dif = {c[:-2]: int(((pn[c].fillna(-9e9) - pn[c[:-2] + '_B'].fillna(-9e9)).abs() > 1e-9).sum())
       for c in pn.columns if c.endswith('_A') and c[:-2] + '_B' in pn.columns}
P('  rows where the A and B values differ (track record):',
  {k: v for k, v in dif.items() if not k.startswith(('vs', 'rank', 'dist'))})

# no outcome of the current result in panel.csv: correlation with outcomes
num = pn.select_dtypes('number').drop(columns=['qn', 'i_cut', 'i_rd', 'i_p1', 'i_react'])
for oc_c in ('three_day', 'vsN_H20'):
    cr = num.corrwith(oc[oc_c]).abs().sort_values(ascending=False)
    P(f'  max |corr| of panel columns with current {oc_c}: ' + ', '.join(f'{k} {v:.2f}' for k, v in cr.head(4).items()))
P('  (XN / W, and *_B price columns, contain the reaction-day move: known at close k, trade-B only)')

# ------------------------------------------------------------------ 2. reproductions
P('\n2. REPRODUCTIONS')
m = pn.merge(oc[['symbol', 'qn', 'three_day', 'vsN_net_H20', 'tradable_B']], on=['symbol', 'qn'])
lr = m[(m.in_fo_events == True) & (m.lag21 < -10) & (m.vol_ratio_5_60 >= 1.0) & m.three_day.notna()]
rp = pd.read_csv(f'{REPO}/results/lag10_volume/trades.csv')
same = set(zip(lr.symbol, lr.qn)) == set(zip(rp.symbol, rp.qn))
P(f'  lag rule (lag21 < -10, vol_ratio_5_60 >= 1.0, events in_fo True): {len(lr)} trades, mean three_day '
  f'{lr.three_day.mean():+.2f}% gross / {lr.three_day.mean() - 0.17:+.2f}% net; repo trades.csv {len(rp)} '
  f'mean {rp.three_day.mean() * 100:+.2f}%; same set: {same}')
assert len(lr) == 85 and same
x2 = m[(m.in_fo_events.isna()) & (m.lag21 < -10) & (m.vol_ratio_5_60 >= 1.0)]
P(f'  (the 2 rows with blank events in_fo that would also qualify: {len(x2)})')
w = m[m.W & m.tradable_B]
wr = w[w.RSI_HI]
P(f'  winners W & tradable: {len(w)} trades, vsN_net_H20 mean {w.vsN_net_H20.mean():+.2f}%')
P(f'  winners & cut_rsi14 > 50: {len(wr)} trades, mean {wr.vsN_net_H20.mean():+.2f}%; '
  f'via cut_rsi14 > 50 directly: {int((w.cut_rsi14 > 50).sum())}')
assert len(w) == 392 and len(wr) == 232 and abs(w.vsN_net_H20.mean() - 1.45) < 0.01 and \
    abs(wr.vsN_net_H20.mean() - 2.42) < 0.01

# ------------------------------------------------------------------ 3. coverage by qn
P('\n3. COVERAGE BY qn (counts of non-missing values)')
g = pn.groupby('qn')
cov = pd.DataFrame({
    'results_for': g.apply(lambda d: f'Results for {d.period.iloc[0]} ({d.quarter.iloc[0]})'),
    'n': g.size(),
    'prev>=1_A': g.n_prev_A.apply(lambda s: (s >= 1).sum()),
    'prev>=4_A': g.n_prev_A.apply(lambda s: (s >= 4).sum()),
    'prev>=1_B': g.n_prev_B.apply(lambda s: (s >= 1).sum()),
    'prev>=4_B': g.n_prev_B.apply(lambda s: (s >= 4).sum()),
    'prev1_drift_A': g.prev1_drift20_A.count(),
    'prev1_drift_B': g.prev1_drift20_B.count(),
    'vsN_63_A': g.vsN_63_A.count(), 'vsN_252_A': g.vsN_252_A.count(),
    'vsSec_252_A': g.vsSec_252_A.count(), 'rank_252_A': g.rank_vsN_252_A.count(),
    'd52wh_A': g.dist_52wh_A.count(), 'vsN_252_B': g.vsN_252_B.count(),
})
tot = cov.drop(columns='results_for').sum()
cov.loc['all'] = ['all'] + tot.tolist()
cov.to_csv(f'{HERE}/coverage.csv')
P(cov.to_string())
P('\n  n_prev_A distribution:', pn.n_prev_A.value_counts().sort_index().to_dict())
P('  prev1 is the immediately previous quarter (A):', int((pn.prev1_qn_A == pn.qn - 1).sum()), 'of',
  int(pn.prev1_qn_A.notna().sum()))
P('  NaN counts (A):', {c: int(pn[c].isna().sum()) for c in pn.columns if c.endswith('_A') and pn[c].isna().any()})

# ------------------------------------------------------------------ 4. the timing filter is live (all 4,462 events)
P('\n4. TIMING FILTER ON ALL 4,462 EVENTS (incl. non-F&O; shows where it bites)')
for tag, col in (('A', 'i_cut'), ('B', 'i_react')):
    x = hi[['symbol', 'qn', col, 'in_fo_events']].rename(columns={'qn': 'qn0', col: 'dec', 'in_fo_events': 'fo0'}) \
        .merge(hi, on='symbol')
    x = x[x.qn < x.qn0]
    w_ = x[x.h_dr_end >= x.dec]
    P(f'  {tag}: earlier results whose drift had NOT ended at the decision (withheld): {len(w_)} -> ' +
      '; '.join(f'{r.symbol} qn{r.qn0} (in_fo {r.fo0}): prev qn{r.qn} exit {r.h_dr_end} >= dec {r.dec}'
                for r in w_.itertuples()))
    P(f'  {tag}: earlier results whose 3-day window had not closed: {int((x.h_td_end >= x.dec).sum())}')

# ------------------------------------------------------------------ 5. spot check of a rank value from returns.csv
D = __import__('os').environ.get('LAB_ROOT', 'lab') + '/sector_lab/data'
ret = pd.read_csv(f'{D}/returns.csv', index_col=0)
rng = np.random.default_rng(7)
okn = 0
for n in rng.choice(len(pn), 25, replace=False):
    r = pn.iloc[n]
    i = int(r.i_cut)
    peers = pn[pn.qn == r.qn].symbol
    w = ret.iloc[i - 62:i + 1][peers]
    lst = ret[peers].apply(lambda s: ret.index.get_loc(s.first_valid_index()))
    v = (1 + w.fillna(0)).prod() - 1
    v[(lst > i - 63) | (w.isna().sum() > 3)] = np.nan
    rk = v.rank(pct=True)[r.symbol] * 100
    okn += abs(rk - r.rank_vsN_63_A) < 1e-3 or (np.isnan(rk) and np.isnan(r.rank_vsN_63_A))
P(f'\n5. rank_vsN_63_A recomputed from returns.csv for 25 random rows: {okn}/25 equal')
assert okn == 25
