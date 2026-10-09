#!/usr/bin/env python3
"""Trade A x past performance: run the pre-registered tests (prereg.txt) on the signals from build_signals.py.

Outputs (this folder): tests.csv, per_quarter.csv, lag_rule_splits.csv, replacement.csv, trades_<test>.csv for the
replacement tests and the best main tests, run_tests.log. Percent units.
"""
import hashlib
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
FEAT = f'{SP}/perf/features'
LOG = open(f'{HERE}/run_tests.log', 'w')
COST = 0.17
B_PERM, B_PL, B_SPLIT = 20000, 10000, 20000


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    LOG.write(s + '\n')
    LOG.flush()


P('prereg.txt sha256', hashlib.sha256(open(f'{HERE}/prereg.txt', 'rb').read()).hexdigest())

TESTS = [  # id, sign, label
    ('TR01', +1, 'rose in last results window (prev1_three_day > 0)'),
    ('TR02', -1, 'fell in last results window (prev1_three_day < 0)'),
    ('TR03', +1, 'positive window in >= 3 of last 4'),
    ('TR04', -1, 'positive window in <= 1 of last 4'),
    ('TR05', +1, 'mean of last 4 windows top quintile'),
    ('TR06', -1, 'mean of last 4 windows bottom quintile'),
    ('TR07', +1, 'last results winner (prev1_xn > 4), repeat'),
    ('TR08', -1, 'last results winner (prev1_xn > 4), reversal'),
    ('TR09', +1, 'last results loser (prev1_xn < -4), reversal'),
    ('TR10', -1, 'last results loser (prev1_xn < -4), repeat'),
    ('TR11', +1, 'serial winner (>= 2 of last 4 reactions > +4%)'),
    ('TR12', +1, 'mean last-4 reaction vs Nifty top quintile'),
    ('TR13', -1, 'mean last-4 reaction vs Nifty bottom quintile'),
    ('TR14', +1, 'big typical mover (mean |reaction| last 4 top quintile)'),
    ('TR15', +1, 'mean last-4 post-results drift top quintile'),
    ('TR16', -1, 'mean last-4 post-results drift bottom quintile'),
    ('PP01', +1, '1-month vs Nifty bottom quintile (reversal)'),
    ('PP02', -1, '1-month vs Nifty top quintile (reversal)'),
    ('PP03', +1, '3-month vs Nifty top quintile'),
    ('PP04', -1, '3-month vs Nifty bottom quintile'),
    ('PP05', +1, '6-month vs Nifty top quintile'),
    ('PP06', -1, '6-month vs Nifty bottom quintile'),
    ('PP07', +1, '12-month vs Nifty top quintile'),
    ('PP08', -1, '12-month vs Nifty bottom quintile'),
    ('PP09', +1, '12-month top quintile and 1-month below Nifty (pullback)'),
    ('PP10', +1, '12-month top half and 1-month bottom quintile (deep pullback)'),
    ('PP11', +1, 'within 5% of 52-week high'),
    ('PP12', -1, '30%+ below 52-week high'),
    ('PP13', +1, '3-month vs sector top quintile'),
    ('PP14', -1, '3-month vs sector bottom quintile'),
    ('PP15', +1, '12-month vs sector top quintile'),
    ('PP16', -1, '12-month vs sector bottom quintile'),
    ('PP17', -1, '12-month and 1-month bottom quintile (falling knife)'),
]
REPL = [
    ('RP1', +1, 'volume >= 1.0 AND 3-month vs Nifty bottom quintile (replaces lag)'),
    ('RP2', +1, 'lag < -10 AND mean of last 4 windows > 0 (replaces volume)'),
    ('RP3', +1, 'lag < -10 AND 12-month vs Nifty top half (replaces volume)'),
]
REF = [
    ('LAGRULE', +1, 'lag 10% + volume (original rule)'),
    ('VOL_ALONE', +1, 'volume ratio >= 1.0 alone'),
    ('LAG_ALONE', +1, 'lag < -10 alone'),
]
ALL = TESTS + REPL + REF
SIGN = {t: s for t, s, _ in ALL}
LABEL = {t: l for t, _, l in ALL}

# ------------------------------------------------------------------ data (outcomes are read only now, after prereg)
sig = pd.read_csv(f'{HERE}/signals_results.csv.gz')
out = pd.read_csv(f'{FEAT}/outcomes.csv', usecols=['symbol', 'qn', 'three_day'])
D = sig.merge(out, on=['symbol', 'qn'], how='left', validate='1:1')
assert len(D) == 3280
P('three_day missing on', int(D.three_day.isna().sum()), 'of 3280 F&O results (dropped)')
D = D[D.three_day.notna()].reset_index(drop=True)
y = D.three_day.to_numpy(float)
qn = D.qn.to_numpy(int)
N = len(D)
QS = np.unique(qn)
QMEAN = pd.Series(y).groupby(qn).mean()
H1 = qn <= 13
PERIOD = D.groupby('qn').agg(quarter=('quarter', 'first'), period=('period', 'first'))
P(f'all F&O results: n={N}, mean three_day {y.mean():+.3f}%, first 14 {y[H1].mean():+.3f}%, last 8 {y[~H1].mean():+.3f}%')
M = {t: D[t].to_numpy(bool) for t, _, _ in ALL}

# availability (feature known) for the lag-rule splits
AV = {
    'TR01': D.prev1_three_day_A.notna(), 'TR02': D.prev1_three_day_A.notna(),
    'TR03': D.n_pos_three_day_4_A.notna(), 'TR04': D.n_pos_three_day_4_A.notna(),
    'TR05': D.pct_mean_three_day_4_A.notna(), 'TR06': D.pct_mean_three_day_4_A.notna(),
    'TR07': D.prev1_xn_A.notna(), 'TR09': D.prev1_xn_A.notna(),
    'TR11': D.n_winner_4_A.notna(), 'TR12': D.pct_mean_xn_4_A.notna(), 'TR13': D.pct_mean_xn_4_A.notna(),
    'TR14': D.pct_mean_abs_xn_4_A.notna(), 'TR15': D.pct_mean_drift_4_A.notna(), 'TR16': D.pct_mean_drift_4_A.notna(),
    'PP01': D.rank_vsN_21.notna(), 'PP02': D.rank_vsN_21.notna(), 'PP03': D.rank_vsN_63.notna(),
    'PP04': D.rank_vsN_63.notna(), 'PP05': D.rank_vsN_126.notna(), 'PP06': D.rank_vsN_126.notna(),
    'PP07': D.rank_vsN_252.notna(), 'PP08': D.rank_vsN_252.notna(),
    'PP09': D.rank_vsN_252.notna() & D.vsN_21.notna(), 'PP10': D.rank_vsN_252.notna() & D.rank_vsN_21.notna(),
    'PP11': D.dist_52wh.notna(), 'PP12': D.dist_52wh.notna(), 'PP13': D.rank_vsSec_63.notna(),
    'PP14': D.rank_vsSec_63.notna(), 'PP15': D.rank_vsSec_252.notna(), 'PP16': D.rank_vsSec_252.notna(),
    'PP17': D.rank_vsN_252.notna() & D.rank_vsN_21.notna(),
    'RP1': D.rank_vsN_63.notna() & D.vol_ratio_5_60.notna(), 'RP2': D.mean_three_day_4_A.notna() & D.lag21.notna(),
    'RP3': D.rank_vsN_252.notna() & D.lag21.notna(),
}
AV = {k: v.to_numpy(bool) for k, v in AV.items()}


# ------------------------------------------------------------------ descriptive statistics
def describe(t, mask=None):
    m = M[t] if mask is None else mask
    s = SIGN[t]
    pnl = s * y[m]
    q = qn[m]
    n = len(pnl)
    r = {'test': t, 'dir': 'L' if s > 0 else 'S', 'label': LABEL[t], 'n': n}
    if n == 0:
        return r
    base = s * QMEAN.reindex(q).to_numpy()
    r.update(avg=pnl.mean(), net=pnl.mean() - COST, excess=pnl.mean() - base.mean(), hit=(pnl > 0).mean() * 100)
    pq = pd.Series(pnl - COST).groupby(q).mean()
    r['q_pos'] = int((pq > 0).sum())
    r['q_with'] = int(len(pq))
    for h, hm in (('h1', q <= 13), ('h2', q >= 14)):
        r[f'n_{h}'] = int(hm.sum())
        r[f'avg_{h}'] = pnl[hm].mean() if hm.any() else np.nan
        r[f'net_{h}'] = r[f'avg_{h}'] - COST
        r[f'excess_{h}'] = (pnl[hm] - base[hm]).mean() if hm.any() else np.nan
    srt = np.sort(pnl)[::-1]
    r['net_wo_best5'] = srt[5:].mean() - COST if n > 5 else np.nan
    return r


# ------------------------------------------------------------------ within-quarter permutations (luck p, maxT)
rng = np.random.default_rng(20261009)
qidx = {q: np.flatnonzero(qn == q) for q in QS}
IDS = [t for t, _, _ in ALL]
MM = np.column_stack([M[t] for t in IDS]).astype(float)       # N x K
NN = MM.sum(0)
SG = np.array([SIGN[t] for t in IDS], float)
obs = SG * (y @ MM) / np.where(NN > 0, NN, 1)
perm_stats = np.empty((B_PERM, len(IDS)))
CH = 2000
for c0 in range(0, B_PERM, CH):
    nb = min(CH, B_PERM - c0)
    Yp = np.empty((nb, N))
    for q, ix in qidx.items():
        keys = rng.random((nb, len(ix)))
        Yp[:, ix] = y[ix][np.argsort(keys, axis=1)]
    perm_stats[c0:c0 + nb] = SG * (Yp @ MM) / np.where(NN > 0, NN, 1)
luck_p = (1 + (perm_stats >= obs[None, :] - 1e-12).sum(0)) / (1 + B_PERM)
LUCK = dict(zip(IDS, luck_p))
mu, sd = perm_stats.mean(0), perm_stats.std(0, ddof=1)
Z = (perm_stats - mu) / sd
zobs = (obs - mu) / sd
ZOBS = dict(zip(IDS, zobs))
main_ix = [IDS.index(t) for t, _, _ in TESTS]
maxz = Z[:, main_ix].max(1)
MAXT = {IDS[k]: (1 + (maxz >= zobs[k] - 1e-12).sum()) / (1 + B_PERM) for k in main_ix}


def holm(ps):
    ps = np.asarray(ps, float)
    o = np.argsort(ps)
    m = len(ps)
    adj = np.empty(m)
    run = 0.0
    for r, k in enumerate(o):
        run = max(run, min(1.0, (m - r) * ps[k]))
        adj[k] = run
    return adj


HOLM = dict(zip([t for t, _, _ in TESTS], holm([LUCK[t] for t, _, _ in TESTS])))
HOLM.update(dict(zip([t for t, _, _ in REPL], holm([LUCK[t] for t, _, _ in REPL]))))

# ------------------------------------------------------------------ placebo
pl = pd.read_csv(f'{HERE}/signals_placebo.csv.gz')
pl = pl[pl.three_day.notna()].reset_index(drop=True)
py = pl.three_day.to_numpy(float)
pq_ = pl.qn_next.to_numpy(int)
PL_QMEAN = pd.Series(py).groupby(pq_).mean()
P(f'placebo days: n={len(pl)}, mean 3-day {py.mean():+.3f}% (results: {y.mean():+.3f}%)')
rngp = np.random.default_rng(7)


def placebo(t):
    s = SIGN[t]
    pm = pl[t].to_numpy(bool)
    if pm.sum() == 0:
        return {}
    pools = {q: s * py[pm & (pq_ == q)] for q in np.unique(pq_[pm])}
    m = M[t]
    q_tr = qn[m]
    keep = np.isin(q_tr, list(pools))
    pnl = s * y[m][keep]
    qk = q_tr[keep]
    nq = pd.Series(qk).value_counts().sort_index()
    n = int(keep.sum())
    if n == 0:
        return {}
    e_res = pnl.mean() - (s * QMEAN.reindex(qk).to_numpy()).mean()
    w = nq / n
    pl_base = sum(w[q] * s * PL_QMEAN[q] for q in nq.index)
    pl_sig = sum(w[q] * pools[q].mean() for q in nq.index)
    e_pl = pl_sig - pl_base
    tot = np.zeros(B_PL)
    for q, k in nq.items():
        pool = pools[q]
        tot += pool[rngp.integers(0, len(pool), size=(B_PL, k))].sum(1)
    e_draw = tot / n - pl_base
    p = (1 + (e_draw >= e_res - 1e-12).sum()) / (1 + B_PL)
    return {'pl_n_days': int(pm.sum()), 'pl_n_trades_cmp': n, 'pl_sig_avg': pl_sig, 'pl_base_avg': pl_base,
            'pl_excess': e_pl, 'res_excess_cmp': e_res, 'DiD': e_res - e_pl, 'placebo_p': p}


# ------------------------------------------------------------------ main table
rows = []
for t, _, _ in TESTS + REPL + REF:
    r = describe(t)
    r['luck_p'] = LUCK[t]
    r['z'] = ZOBS[t]
    r['holm_p'] = HOLM.get(t, np.nan)
    r['maxT_p'] = MAXT.get(t, np.nan)
    r.update(placebo(t))
    rows.append(r)
TAB = pd.DataFrame(rows)


def verdict(r):
    a = (r.excess_h1 > 0) and (r.excess_h2 > 0) and (r.net_h1 > 0) and (r.net_h2 > 0)
    b = r.holm_p < 0.10
    c = (r.DiD > 0) and (r.placebo_p < 0.10)
    d = r.net_wo_best5 > 0
    return pd.Series({'crit_halves': a, 'crit_holm': b, 'crit_placebo': c, 'crit_wo_best5': d,
                      'WORKS': bool(a and b and c and d)})


TAB = pd.concat([TAB, TAB.apply(verdict, axis=1)], axis=1)
for c_ in ('crit_halves', 'crit_holm', 'crit_placebo', 'crit_wo_best5', 'WORKS'):
    TAB[c_] = TAB[c_].astype(object)
TAB.loc[TAB.test.isin([t for t, _, _ in REF]), ['holm_p', 'maxT_p', 'crit_holm', 'WORKS']] = np.nan
TAB.to_csv(f'{HERE}/tests.csv', index=False, float_format='%.4f')

pd.set_option('display.width', 250)
show = ['test', 'dir', 'n', 'avg', 'net', 'excess', 'q_pos', 'q_with', 'n_h1', 'avg_h1', 'n_h2', 'avg_h2',
        'net_wo_best5', 'luck_p', 'holm_p', 'maxT_p', 'pl_sig_avg', 'pl_excess', 'DiD', 'placebo_p', 'WORKS']
P('\nMAIN FAMILY (33) + REPLACEMENT (3) + REFERENCE')
P(TAB[show].round(3).to_string(index=False))

# per-quarter (n, signed avg) for every test
pqrows = []
for t, _, _ in ALL:
    m = M[t]
    for q in QS:
        mm = m & (qn == q)
        pqrows.append({'test': t, 'qn': q, 'results_for': f"Results for {PERIOD.period[q]} ({PERIOD.quarter[q]})",
                       'n': int(mm.sum()), 'avg': SIGN[t] * y[mm].mean() if mm.any() else np.nan,
                       'all_fo_avg': SIGN[t] * QMEAN[q]})
pd.DataFrame(pqrows).to_csv(f'{HERE}/per_quarter.csv', index=False, float_format='%.4f')

# ------------------------------------------------------------------ split of the lag 10% + volume rule
LR = M['LAGRULE']
P(f'\nLAG RULE: n={LR.sum()} avg {y[LR].mean():+.3f}% net {y[LR].mean() - COST:+.3f}%')
rngs = np.random.default_rng(11)
srows = []
for t, s, lab in TESTS:
    if t in ('TR08', 'TR10'):
        continue
    av = LR & AV[t]
    yin = y[av & M[t]]
    yout = y[av & ~M[t]]
    r = {'condition': t, 'label': lab, 'pred': 'IN better' if s > 0 else 'IN worse', 'n_avail': int(av.sum()),
         'n_in': len(yin), 'avg_in': yin.mean() if len(yin) else np.nan, 'n_out': len(yout),
         'avg_out': yout.mean() if len(yout) else np.nan}
    r['net_in'] = r['avg_in'] - COST
    r['net_out'] = r['avg_out'] - COST
    for h, hm in (('h1', qn <= 13), ('h2', qn >= 14)):
        a_in = y[av & M[t] & hm]
        a_out = y[av & ~M[t] & hm]
        r[f'n_in_{h}'] = len(a_in)
        r[f'avg_in_{h}'] = a_in.mean() if len(a_in) else np.nan
        r[f'n_out_{h}'] = len(a_out)
        r[f'avg_out_{h}'] = a_out.mean() if len(a_out) else np.nan
    r['diff'] = r['avg_in'] - r['avg_out']
    if len(yin) and len(yout):
        ya = y[av]
        lab_in = M[t][av]
        k = lab_in.sum()
        keys = rngs.random((B_SPLIT, len(ya)))
        sel = np.argsort(keys, axis=1)[:, :k]
        s_in = ya[sel].sum(1)
        d_perm = s_in / k - (ya.sum() - s_in) / (len(ya) - k)
        r['perm_p_2s'] = (1 + (np.abs(d_perm) >= abs(r['diff']) - 1e-12).sum()) / (1 + B_SPLIT)
    else:
        r['perm_p_2s'] = np.nan
    r['tested'] = (len(yin) >= 5) and (len(yout) >= 5)
    srows.append(r)
SPL = pd.DataFrame(srows)
tm = SPL.tested.to_numpy(bool)
SPL['holm_p'] = np.nan
SPL.loc[tm, 'holm_p'] = holm(SPL.perm_p_2s[tm].to_numpy())
SPL.to_csv(f'{HERE}/lag_rule_splits.csv', index=False, float_format='%.4f')
P(SPL[['condition', 'pred', 'n_in', 'avg_in', 'n_out', 'avg_out', 'diff', 'n_in_h1', 'avg_in_h1', 'n_in_h2',
       'avg_in_h2', 'avg_out_h1', 'avg_out_h2', 'perm_p_2s', 'holm_p']].round(3).to_string(index=False))

# ------------------------------------------------------------------ replacement tests
rngr = np.random.default_rng(13)
rrows = []
base_of = {'RP1': ('VOL_ALONE', D.rank_vsN_63.notna().to_numpy()),
           'RP2': ('LAG_ALONE', D.mean_three_day_4_A.notna().to_numpy()),
           'RP3': ('LAG_ALONE', D.rank_vsN_252.notna().to_numpy())}
for t, _, _ in REPL:
    r = TAB[TAB.test == t].iloc[0].to_dict()
    r['overlap_with_85'] = int((M[t] & LR).sum())
    r['rule_avg'] = y[LR].mean()
    bname, avail = base_of[t]
    bm = M[bname] & avail
    yin = y[bm & M[t]]
    yout = y[bm & ~M[t]]
    r['alone_set'] = bname
    r['alone_n'] = int(M[bname].sum())
    r['alone_avg'] = y[M[bname]].mean()
    r['in_vs_out_within_alone'] = yin.mean() - yout.mean()
    ya = y[bm]
    k = len(yin)
    keys = rngr.random((B_SPLIT, len(ya)))
    sel = np.argsort(keys, axis=1)[:, :k]
    s_in = ya[sel].sum(1)
    d_perm = s_in / k - (ya.sum() - s_in) / (len(ya) - k)
    r['adds_p_1s'] = (1 + (d_perm >= r['in_vs_out_within_alone'] - 1e-12).sum()) / (1 + B_SPLIT)
    r['CAN_REPLACE'] = bool(r['WORKS'] and r['avg'] >= r['rule_avg'])
    rrows.append(r)
RPT = pd.DataFrame(rrows)
RPT.to_csv(f'{HERE}/replacement.csv', index=False, float_format='%.4f')
P('\nREPLACEMENT')
P(RPT[['test', 'n', 'avg', 'net', 'q_pos', 'q_with', 'avg_h1', 'avg_h2', 'net_wo_best5', 'luck_p', 'holm_p',
       'DiD', 'placebo_p', 'overlap_with_85', 'alone_set', 'alone_n', 'alone_avg', 'in_vs_out_within_alone',
       'adds_p_1s', 'WORKS', 'CAN_REPLACE']].round(3).to_string(index=False))

# trades files for replacement tests and the 5 lowest-luck-p main tests
best = TAB[TAB.test.isin([t for t, _, _ in TESTS])].sort_values('luck_p').test.head(5).tolist()
for t in [t for t, _, _ in REPL] + best:
    m = M[t]
    tr = D.loc[m, ['symbol', 'qn', 'quarter', 'period', 'lag21', 'vol_ratio_5_60', 'three_day']].copy()
    tr.insert(2, 'results_for', 'Results for ' + tr.period + ' (' + tr.quarter + ')')
    tr['pnl'] = SIGN[t] * tr.three_day
    tr['pnl_net'] = tr.pnl - COST
    tr.to_csv(f'{HERE}/trades_{t}.csv', index=False, float_format='%.4f')
P('\nbest main tests by luck p:', best)
P('WORKS (main):', TAB[TAB.test.isin([t for t, _, _ in TESTS]) & (TAB.WORKS == True)].test.tolist())
