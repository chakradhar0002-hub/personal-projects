#!/usr/bin/env python3
"""Verifier, own code: descriptive splits (lag-rule 85 by A01-A22; plain winners and RSI>50 winners by B01-B14) on MY
flags; two-sided permutation p, Holm within each pool; compared with the study's split tables.
usage: python3 w7_splits.py <scratchpad> <verify_dir>
"""
import sys

import numpy as np
import pandas as pd

SP, VD = sys.argv[1], sys.argv[2]
W = f'{VD}/work'
LOG = open(f'{W}/w7_splits.log', 'w')
pd.set_option('display.width', 250)
rng = np.random.default_rng(3)


def log(*a):
    s = ' '.join(map(str, a))
    print(s, flush=True)
    LOG.write(s + '\n')


pan = pd.read_csv(f'{SP}/perf/features/panel.csv', usecols=['symbol', 'qn', 'lag21', 'vol_ratio_5_60', 'in_fo_events',
                                                            'cut_rsi14', 'W'])
oc = pd.read_csv(f'{SP}/perf/features/outcomes.csv', usecols=['symbol', 'qn', 'three_day', 'vsN_net_H20', 'tradable_B'])
fl = pd.read_csv(f'{W}/w4_flags.csv')
D = pan.merge(oc, on=['symbol', 'qn']).merge(fl, on=['symbol', 'qn'])
LR = (D.three_day.notna() & (D.lag21 < -10) & (D.vol_ratio_5_60 >= 1) & (D.in_fo_events == True)).to_numpy()
PB = ((D.W == True) & (D.tradable_B == True)).to_numpy()
WR = PB & (D.cut_rsi14 > 50).to_numpy()


def holm(p):
    p = np.asarray(p)
    o = np.argsort(p)
    adj = np.empty_like(p)
    run = 0
    for r_, i_ in enumerate(o):
        run = max(run, min(1, (len(p) - r_) * p[i_]))
        adj[i_] = run
    return adj


def split(pool, y, tests, cost, name):
    rows = []
    for t in tests:
        el = pool & D['el_' + t].to_numpy(bool)
        i_ = el & D[t].to_numpy(bool)
        o_ = el & ~D[t].to_numpy(bool)
        r = {'pool': name, 'cond': t, 'n_in': int(i_.sum()), 'net_in': y[i_].mean() - cost if i_.any() else np.nan,
             'n_out': int(o_.sum()), 'net_out': y[o_].mean() - cost if o_.any() else np.nan, 'p2s': np.nan}
        r['diff'] = r['net_in'] - r['net_out']
        if i_.sum() >= 5 and o_.sum() >= 5:
            ya = y[el]
            kk = int(i_.sum())
            perm = np.argsort(rng.random((20000, len(ya))), axis=1)[:, :kk]
            si = ya[perm].sum(1)
            dp = si / kk - (ya.sum() - si) / (len(ya) - kk)
            r['p2s'] = (1 + (np.abs(dp) >= abs(r['diff']) - 1e-12).sum()) / 20001
        rows.append(r)
    X = pd.DataFrame(rows)
    m = X.p2s.notna()
    X['holm'] = np.nan
    X.loc[m, 'holm'] = holm(X.p2s[m].to_numpy())
    return X


yA = D.three_day.to_numpy(float)
yB = D.vsN_net_H20.to_numpy(float)
SA = split(LR, yA, [f'A{i:02d}' for i in range(1, 23)], 0.17, 'lag rule 85')
SW = split(PB, yB, [f'B{i:02d}' for i in range(1, 15)], 0.0, 'W392')
SR = split(WR, yB, [f'B{i:02d}' for i in range(1, 15)], 0.0, 'WR232')
th_a = pd.read_csv(f'{SP}/more_signals/oi/results/split_lag_rule.csv')
th_w = pd.read_csv(f'{SP}/more_signals/oi/results/split_winners.csv')
for X, th in ((SA, th_a), (SW, th_w[th_w.pool.str.startswith('plain')]), (SR, th_w[th_w.pool.str.startswith('RSI')])):
    X = X.merge(th[['condition', 'n_in', 'net_in', 'perm_p_2s', 'holm_p']].rename(
        columns={'condition': 'cond', 'n_in': 'n_in_study', 'net_in': 'net_in_study', 'perm_p_2s': 'p2s_study',
                 'holm_p': 'holm_study'}), on='cond', how='left')
    log(X.round(3).to_string(index=False))
    log('')
log('lag rule pool size', LR.sum(), 'net', yA[LR].mean() - 0.17)
