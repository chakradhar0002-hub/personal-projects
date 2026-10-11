#!/usr/bin/env python3
"""F&O positioning family - step 3: run the pre-registered tests (prereg.txt). First script to read any outcome.

usage: python3 -P p3_tests.py <family_dir> <scratchpad>
  family_dir holds prereg.txt, prereg.sha256 and work/ (features from p2_features.py); results go to family_dir/results.
Percent units. Refuses to run if prereg.txt changed after its hash was logged.
"""
import hashlib
import os
import sys

import numpy as np
import pandas as pd

FAM, SP = sys.argv[1], sys.argv[2]
WORK, OUTD = f'{FAM}/work', f'{FAM}/results'
os.makedirs(OUTD, exist_ok=True)
DATA = f'{SP}/sector_lab/data'
LOG = open(f'{OUTD}/run_tests.log', 'w')
COST_A, COST_B = 0.17, 0.19
NPERM, NPL, NSPLIT = 20000, 10000, 20000


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.write(s + '\n')
    LOG.flush()


h = hashlib.sha256(open(f'{FAM}/prereg.txt', 'rb').read()).hexdigest()
logged = open(f'{FAM}/prereg.sha256').read().split()[0]
P(f'prereg.txt sha256 {h} logged {logged} match={h == logged}')
assert h == logged, 'prereg.txt changed after it was hashed'

A_TESTS = [('A01', +1, 'long buildup 5 (price up, OI +10%)'), ('A02', -1, 'short buildup 5 (price down, OI +10%)'),
           ('A03', +1, 'short covering 5 (price up, OI -10%)'), ('A04', -1, 'long unwinding 5 (price down, OI -10%)'),
           ('A05', +1, 'long buildup 10'), ('A06', -1, 'short buildup 10'), ('A07', +1, 'short covering 10'),
           ('A08', -1, 'long unwinding 10'), ('A09', +1, 'OI vs 20-session avg top quintile'),
           ('A10', -1, 'OI vs 20-session avg bottom quintile'), ('A11', +1, 'basis vs own 60-session median top quintile'),
           ('A12', -1, 'basis vs own median bottom quintile'), ('A13', +1, 'PCR (OI) top quintile'),
           ('A14', -1, 'PCR bottom quintile'), ('A15', +1, 'PCR 5-session change top quintile'),
           ('A16', -1, 'PCR 5-session change bottom quintile'), ('A17', -1, 'ATM IV vs own 60-session median top quintile'),
           ('A18', +1, 'ATM IV vs own median bottom quintile'), ('A19', +1, 'call-put IV spread top quintile'),
           ('A20', -1, 'call-put IV spread bottom quintile'), ('A21', +1, 'call IV 20-session change top quintile'),
           ('A22', -1, 'put IV 20-session change top quintile')]
B_TESTS = [('B01', +1, 'fresh longs on k: OI up on the winner day'), ('B02', +1, 'OI +10% on the winner day'),
           ('B03', +1, 'long buildup 5 ending k'), ('B04', +1, 'long buildup 10 ending k'),
           ('B05', +1, 'short buildup 5 before results (at cutoff)'), ('B06', +1, 'OI vs 20-session avg top quintile at k'),
           ('B07', +1, 'basis vs own median top quintile at k'), ('B08', +1, 'basis change on k top quintile'),
           ('B09', +1, 'PCR top quintile at k'), ('B10', +1, 'PCR change on k top quintile'),
           ('B11', +1, 'ATM IV vs own median bottom quintile at k'), ('B12', +1, 'call-put IV spread top quintile at k'),
           ('B13', +1, 'call IV 20-session change top quintile at k'),
           ('B14', +1, 'put IV 20-session change bottom quintile at k')]
ALL = A_TESTS + B_TESTS
SIGN = {t: s for t, s, _ in ALL}
LABEL = {t: l for t, _, l in ALL}
assert len(ALL) == 36

# ------------------------------------------------------------------ data
RES = pd.read_csv(f'{WORK}/results_features.csv')
out = pd.read_csv(f'{SP}/perf/features/outcomes.csv',
                  usecols=['symbol', 'qn', 'three_day', 'vsN_H20', 'vsN_net_H20', 'tradable_B'])
D = RES.merge(out, on=['symbol', 'qn'], how='left', validate='1:1')
assert len(D) == 3280
D['label'] = 'Results for ' + D.period + ' (' + D.quarter + ')'
LABQ = D.groupby('qn').label.first()

# trade A frame
DA = D[D.three_day.notna()].reset_index(drop=True)
yA = DA.three_day.to_numpy(float)
qA = DA.qn.to_numpy(int)
P(f'trade A: F&O results with three_day {len(DA)} of 3280; mean {yA.mean():+.3f}% (documented +0.04)')
QMA = pd.Series(yA).groupby(qA).mean()
# trade B frame (parent = plain winners)
DB = D[D.tradable_B == True].reset_index(drop=True)
Wm = (DB.W == True).to_numpy()
WRm = Wm & (DB.cut_rsi14 > 50).to_numpy()
yB_all = DB.vsN_net_H20.to_numpy(float)
P(f'trade B: tradable {len(DB)}; W {Wm.sum()} mean {yB_all[Wm].mean():+.3f}; WR {WRm.sum()} mean {yB_all[WRm].mean():+.3f}'
  f' (documented 392 +1.45, 232 +2.42)')
assert Wm.sum() == 392 and WRm.sum() == 232
DW = DB[Wm].reset_index(drop=True)
yB = DW.vsN_net_H20.to_numpy(float)
qB = DW.qn.to_numpy(int)
QMB = pd.Series(yB).groupby(qB).mean()

MA = {t: DA[t].to_numpy(bool) for t, _, _ in A_TESTS}
MB = {t: DW[t].to_numpy(bool) for t, _, _ in B_TESTS}


# ------------------------------------------------------------------ descriptive statistics
def describe(t, y, q, m, qmean, cost, sign):
    pnl = sign * y[m]
    qq = q[m]
    n = len(pnl)
    r = {'test': t, 'trade': t[0], 'dir': 'long' if sign > 0 else 'short', 'label': LABEL.get(t, t), 'n': n}
    if n == 0:
        return r
    net = pnl - cost
    base = sign * qmean.reindex(qq).to_numpy()
    r.update(avg_gross=pnl.mean(), avg_net=net.mean(), excess=(pnl - base).mean(), hit=(net > 0).mean() * 100)
    pq = pd.Series(net).groupby(qq).mean()
    r['q_pos'], r['q_with'] = int((pq > 0).sum()), int(len(pq))
    for hn, hm in (('f14', qq <= 13), ('l8', qq >= 14)):
        r[f'n_{hn}'] = int(hm.sum())
        r[f'net_{hn}'] = net[hm].mean() if hm.any() else np.nan
        r[f'exc_{hn}'] = (pnl[hm] - base[hm]).mean() if hm.any() else np.nan
    o = np.argsort(-pnl)
    keep = np.ones(n, bool)
    keep[o[:5]] = False
    r['net_wo5'] = net[keep].mean() if n > 5 else np.nan
    r['exc_wo5'] = (pnl - base)[keep].mean() if n > 5 else np.nan
    return r


def perm_stats(y, q, masks, signs, nperm, seed):
    rng = np.random.default_rng(seed)
    MM = np.column_stack(masks).astype(float)
    NN = MM.sum(0)
    SG = np.asarray(signs, float)
    obs = SG * (y @ MM) / np.where(NN > 0, NN, 1)
    qidx = [np.flatnonzero(q == x) for x in np.unique(q)]
    st = np.empty((nperm, MM.shape[1]))
    for c0 in range(0, nperm, 1000):
        nb = min(1000, nperm - c0)
        Yp = np.empty((nb, len(y)))
        for ix in qidx:
            Yp[:, ix] = y[ix][np.argsort(rng.random((nb, len(ix))), axis=1)]
        st[c0:c0 + nb] = SG * (Yp @ MM) / np.where(NN > 0, NN, 1)
    return obs, st


obsA, stA = perm_stats(yA, qA, [MA[t] for t, _, _ in A_TESTS], [s for _, s, _ in A_TESTS], NPERM, 20261011)
obsB, stB = perm_stats(yB, qB, [MB[t] for t, _, _ in B_TESTS], [s for _, s, _ in B_TESTS], NPERM, 20261012)
obs = np.r_[obsA, obsB]
st = np.column_stack([stA, stB])
IDS = [t for t, _, _ in ALL]
luck = (1 + (st >= obs[None, :] - 1e-12).sum(0)) / (1 + NPERM)
mu, sd = st.mean(0), st.std(0, ddof=1)
Z = (st - mu) / sd
zobs = (obs - mu) / sd
maxz = Z.max(1)
maxT = (1 + (maxz[:, None] >= zobs[None, :] - 1e-12).sum(0)) / (1 + NPERM)
P(f'maxT: 95th pct of max z over 36 tests {np.percentile(maxz, 95):.2f}; observed max z {zobs.max():.2f}')


def holm(p):
    p = np.asarray(p, float)
    o = np.argsort(p)
    m = len(p)
    adj = np.empty(m)
    run = 0.0
    for r_, k in enumerate(o):
        run = max(run, min(1.0, (m - r_) * p[k]))
        adj[k] = run
    return adj


HOLM = dict(zip(IDS, holm(luck)))
LUCK = dict(zip(IDS, luck))
MAXT = dict(zip(IDS, maxT))
ZD = dict(zip(IDS, zobs))

# ------------------------------------------------------------------ placebo A (placebo_ta stock-days)
plA = pd.read_csv(f'{WORK}/placebo_A_features.csv.gz')
pta = pd.read_csv(f'{SP}/ta/build/placebo_ta.csv.gz', usecols=['symbol', 'i', 'three_day'])
plA = plA.merge(pta, on=['symbol', 'i'], how='left', validate='1:1')
plA = plA[plA.three_day.notna()].reset_index(drop=True)
py = plA.three_day.to_numpy(float)
pq = plA.qn_next.to_numpy(int)
PL_QM = pd.Series(py).groupby(pq).mean()
P(f'placebo A days with 3-day outcome: {len(plA)}, mean {py.mean():+.3f}%')
rngp = np.random.default_rng(7)


def placebo_A(t):
    s = SIGN[t]
    pm = plA[t].to_numpy(bool)
    pools = {q: s * py[pm & (pq == q)] for q in np.unique(pq[pm])}
    m = MA[t]
    q_tr = qA[m]
    keep = np.isin(q_tr, list(pools))
    pnl = s * yA[m][keep]
    qk = q_tr[keep]
    n = int(keep.sum())
    if n == 0:
        return {'pl_n': int(pm.sum())}
    nq = pd.Series(qk).value_counts().sort_index()
    e_res = pnl.mean() - (s * QMA.reindex(qk).to_numpy()).mean()
    w = nq / n
    pl_base = sum(w[q] * s * PL_QM[q] for q in nq.index)
    pl_sig = sum(w[q] * pools[q].mean() for q in nq.index)
    tot = np.zeros(NPL)
    for q, k in nq.items():
        pool = pools[q]
        tot += pool[rngp.integers(0, len(pool), size=(NPL, k))].sum(1)
    e_draw = tot / n - pl_base
    return {'pl_n': int(pm.sum()), 'pl_sig_avg': pl_sig, 'pl_excess': pl_sig - pl_base, 'res_excess_cmp': e_res,
            'DiD': e_res - (pl_sig - pl_base), 'placebo_p': (1 + (e_draw >= e_res - 1e-12).sum()) / (1 + NPL)}


# ------------------------------------------------------------------ placebo B (quiet-day winners)
ses = pd.read_csv(f'{DATA}/sessions.csv')
T = len(ses)
ret = pd.read_csv(f'{DATA}/returns.csv', index_col=0)
SYM = {s: j for j, s in enumerate(ret.columns)}
R = ret.to_numpy(float)
PX = np.cumprod(1.0 + np.nan_to_num(R), axis=0)
CVALID = np.cumsum(~np.isnan(R), axis=0)
NIFTY = pd.read_csv(f'{DATA}/index_close.csv', index_col=0)['Nifty 50'].to_numpy(float)


def hedged(js, k, H, start_off=0):
    """(stock - Nifty) % from close k+start_off to close k+start_off+H; NaN unless k+start_off+H+1 <= last session
    and <= 2 no-trade sessions in k+1..k+21 (outcomes tradable_B rule, shifted)."""
    js, k = np.asarray(js, int), np.asarray(k, int)
    a_ = k + start_off
    b_ = a_ + H
    ok = (b_ + 1 <= T - 1)
    bb = np.minimum(b_ + 1, T - 1)
    ok &= (H + 1 - (CVALID[bb, js] - CVALID[np.minimum(a_, T - 1), js])) <= 2
    aa = np.minimum(a_, T - 1)
    v = ((PX[bb - 1, js] / PX[aa, js] - 1) - (NIFTY[bb - 1] / NIFTY[aa] - 1)) * 100
    return np.where(ok, v, np.nan)


plB = pd.read_csv(f'{WORK}/placebo_B_features.csv.gz')
jq = plB.symbol.map(SYM).to_numpy(int)
plB['vsN_net'] = hedged(jq, plB.i, 20) - COST_B
plB = plB[plB.vsN_net.notna()].reset_index(drop=True)
plB['month'] = plB.day.str[:7]
QW = plB.W.to_numpy(bool)
QX = plB.vsN_net.to_numpy(float)
QM = plB.month.to_numpy()
QWM = pd.Series(QX[QW]).groupby(QM[QW]).mean()
P(f'placebo B quiet days with 20-session outcome {len(plB)}; quiet winners {QW.sum()} mean {QX[QW].mean():+.3f}% '
  f'(all quiet days {QX.mean():+.3f}%)')
rngb = np.random.default_rng(8)


def placebo_B(t, e_res, n_res):
    qs = plB[t].to_numpy(bool) & QW
    if qs.sum() == 0:
        return {'pl_n': 0}
    dq = QX[qs] - QWM.reindex(QM[qs]).to_numpy()
    draws = dq[rngb.integers(0, len(dq), size=(NPL, n_res))].mean(1)
    return {'pl_n': int(qs.sum()), 'pl_sig_avg': QX[qs].mean(), 'pl_excess': dq.mean(), 'res_excess_cmp': e_res,
            'DiD': e_res - dq.mean(), 'placebo_p': (1 + (draws >= e_res - 1e-12).sum()) / (1 + NPL)}


# ------------------------------------------------------------------ main table
rows = []
for t, s, _ in A_TESTS:
    r = describe(t, yA, qA, MA[t], QMA, COST_A, s)
    r['parent_n'], r['parent_net'] = len(yA), s * yA.mean() - COST_A
    r.update(placebo_A(t))
    rows.append(r)
for t, s, _ in B_TESTS:
    r = describe(t, yB, qB, MB[t], QMB, 0.0, s)     # vsN_net_H20 is already net of 0.19
    r['avg_gross'] = r['avg_gross'] + COST_B
    r['parent_n'], r['parent_net'] = len(yB), yB.mean()
    r.update(placebo_B(t, r['excess'], r['n']))
    rows.append(r)
TAB = pd.DataFrame(rows)
TAB['luck_p'] = TAB.test.map(LUCK)
TAB['z'] = TAB.test.map(ZD)
TAB['holm_p'] = TAB.test.map(HOLM)
TAB['maxT_p'] = TAB.test.map(MAXT)


def verdict(r):
    a = (r.exc_f14 > 0) and (r.exc_l8 > 0) and (r.net_f14 > 0) and (r.net_l8 > 0)
    b = r.holm_p < 0.10
    c = (r.DiD > 0) and (r.placebo_p < 0.10)
    d = r.net_wo5 > 0
    return pd.Series({'c_halves': a, 'c_holm': b, 'c_placebo': c, 'c_wo5': d, 'WORKS': bool(a and b and c and d)})


TAB = pd.concat([TAB, TAB.apply(verdict, axis=1)], axis=1)
TAB.to_csv(f'{OUTD}/tests.csv', index=False, float_format='%.4f')
pd.set_option('display.width', 260)
show = ['test', 'dir', 'n', 'avg_net', 'excess', 'q_pos', 'q_with', 'n_f14', 'net_f14', 'exc_f14', 'n_l8', 'net_l8',
        'exc_l8', 'net_wo5', 'luck_p', 'holm_p', 'maxT_p', 'pl_n', 'pl_excess', 'DiD', 'placebo_p', 'WORKS']
P('\nTRADE A (parent: all F&O results, net long', f'{yA.mean() - COST_A:+.3f}%)')
P(TAB[TAB.trade == 'A'][show].round(3).to_string(index=False))
P('\nTRADE B (parent: plain winners W, 392, net', f'{yB.mean():+.3f}%)')
P(TAB[TAB.trade == 'B'][show].round(3).to_string(index=False))
P('\nWORKS:', TAB[TAB.WORKS].test.tolist())

# per-quarter
pqr = []
for t, s, _ in ALL:
    if t[0] == 'A':
        y, q, m, qm, c = yA, qA, MA[t], QMA, COST_A
    else:
        y, q, m, qm, c = yB, qB, MB[t], QMB, 0.0
    for x in np.unique(q):
        mm = m & (q == x)
        pqr.append({'test': t, 'qn': x, 'results_for': LABQ[x], 'n': int(mm.sum()),
                    'net': s * y[mm].mean() - c if mm.any() else np.nan, 'parent_net': s * qm[x] - c})
pd.DataFrame(pqr).to_csv(f'{OUTD}/per_quarter.csv', index=False, float_format='%.4f')

# ------------------------------------------------------------------ splits
rngs = np.random.default_rng(11)


def split_table(y, q, pool, tests, frame, cost, name):
    rows_ = []
    for t, s, lab in tests:
        el = frame['el_' + t].to_numpy(bool) & pool
        ins = el & frame[t].to_numpy(bool)
        outs = el & ~frame[t].to_numpy(bool)
        r = {'pool': name, 'condition': t, 'label': lab, 'pred': 'IN better' if s > 0 else 'IN worse',
             'n_in': int(ins.sum()), 'net_in': y[ins].mean() - cost if ins.any() else np.nan,
             'n_out': int(outs.sum()), 'net_out': y[outs].mean() - cost if outs.any() else np.nan}
        for hn, hm in (('f14', q <= 13), ('l8', q >= 14)):
            r[f'n_in_{hn}'] = int((ins & hm).sum())
            r[f'net_in_{hn}'] = y[ins & hm].mean() - cost if (ins & hm).any() else np.nan
            r[f'net_out_{hn}'] = y[outs & hm].mean() - cost if (outs & hm).any() else np.nan
        r['diff'] = r['net_in'] - r['net_out']
        if ins.sum() >= 5 and outs.sum() >= 5:
            ya = y[el]
            k = int(ins.sum())
            sel = np.argsort(rngs.random((NSPLIT, len(ya))), axis=1)[:, :k]
            s_in = ya[sel].sum(1)
            dperm = s_in / k - (ya.sum() - s_in) / (len(ya) - k)
            r['perm_p_2s'] = (1 + (np.abs(dperm) >= abs(r['diff']) - 1e-12).sum()) / (1 + NSPLIT)
            r['tested'] = True
        else:
            r['perm_p_2s'], r['tested'] = np.nan, False
        rows_.append(r)
    X = pd.DataFrame(rows_)
    X['holm_p'] = np.nan
    tm = X.tested.to_numpy(bool)
    if tm.any():
        X.loc[tm, 'holm_p'] = holm(X.perm_p_2s[tm].to_numpy())
    return X


LR = ((DA.lag21 < -10) & (DA.vol_ratio_5_60 >= 1.0) & (DA.in_fo_events == True)).to_numpy()
rep = pd.read_csv(__import__('os').environ.get('REPO_ROOT', '.') + '/results/lag10_volume/trades.csv')
assert set(zip(DA.symbol[LR], DA.qn[LR])) == set(zip(rep.symbol, rep.qn)) and LR.sum() == 85
P(f'\nLAG RULE (85 trades): net {yA[LR].mean() - COST_A:+.3f}% (gross {yA[LR].mean():+.3f}, documented +2.13)')
SA = split_table(yA, qA, LR, A_TESTS, DA, COST_A, 'lag rule 85')
SA.to_csv(f'{OUTD}/split_lag_rule.csv', index=False, float_format='%.4f')
scol = ['condition', 'pred', 'n_in', 'net_in', 'n_out', 'net_out', 'diff', 'n_in_f14', 'net_in_f14', 'net_out_f14',
        'n_in_l8', 'net_in_l8', 'net_out_l8', 'perm_p_2s', 'holm_p']
P(SA[scol].round(3).to_string(index=False))
yBn = DB.vsN_net_H20.to_numpy(float)
qBn = DB.qn.to_numpy(int)
SW = split_table(yBn, qBn, Wm, B_TESTS, DB, 0.0, 'plain winners 392')
SWR = split_table(yBn, qBn, WRm, B_TESTS, DB, 0.0, 'RSI>50 winners 232')
pd.concat([SW, SWR]).to_csv(f'{OUTD}/split_winners.csv', index=False, float_format='%.4f')
P('\nPLAIN WINNERS (392) split')
P(SW[scol].round(3).to_string(index=False))
P('\nRSI>50 WINNERS (232) split')
P(SWR[scol].round(3).to_string(index=False))

# ------------------------------------------------------------------ robustness for the 6 lowest-luck-p tests
cand = TAB.sort_values('luck_p').test.head(6).tolist()
P('\nROBUSTNESS (not criteria) for', cand)
rngr = np.random.default_rng(13)


def single_luck(y, q, m, s, nd=NPERM):
    """random same-size picks per quarter from the whole pool."""
    tot = np.zeros(nd)
    for x in np.unique(q[m]):
        k = int((q[m] == x).sum())
        pool = s * y[q == x]
        if k == len(pool):
            tot += pool.sum()
            continue
        pick = np.argpartition(rngr.random((nd, len(pool))), k - 1, axis=1)[:, :k]
        tot += pool[pick].sum(1)
    return (1 + (tot / m.sum() >= s * y[m].mean() - 1e-12).sum()) / (1 + nd)


rob = []
kB1 = hedged(DW.symbol.map(SYM), DW.i_react, 20, start_off=1) - COST_B
for t in cand:
    s = SIGN[t]
    if t[0] == 'A':
        for var, col in (('features at i_cut-1', t + '_lag1'), ('previous-quarter cut-offs', t + '_pq')):
            if col not in DA.columns:
                continue
            m = DA[col].to_numpy(bool)
            r = describe(t, yA, qA, m, QMA, COST_A, s)
            r.update(variant=var, luck_p=single_luck(yA, qA, m, s) if m.any() else np.nan)
            rob.append(r)
    else:
        col = t + '_pq'
        if col in DW.columns:
            m = DW[col].to_numpy(bool)
            r = describe(t, yB, qB, m, QMB, 0.0, s)
            r.update(variant='previous-quarter cut-offs', luck_p=single_luck(yB, qB, m, s) if m.any() else np.nan)
            rob.append(r)
        ok = np.isfinite(kB1)
        m = MB[t] & ok
        qm1 = pd.Series(kB1[ok]).groupby(qB[ok]).mean()
        r = describe(t, np.nan_to_num(kB1), qB, m, qm1, 0.0, s)
        r.update(variant='entry close k+1 (hold to k+21)', parent_net_variant=kB1[ok].mean(),
                 luck_p=single_luck(np.where(ok, kB1, 0), np.where(ok, qB, -1), m, s))
        rob.append(r)
ROB = pd.DataFrame(rob)
ROB.to_csv(f'{OUTD}/robustness.csv', index=False, float_format='%.4f')
P(ROB[['test', 'variant', 'n', 'avg_net', 'excess', 'n_f14', 'net_f14', 'n_l8', 'net_l8', 'net_wo5', 'luck_p']]
  .round(3).to_string(index=False))

# trades for the candidates
for t in cand:
    if t[0] == 'A':
        m = MA[t]
        tr = DA.loc[m, ['symbol', 'qn', 'label', 'i_cut', 'lag21', 'vol_ratio_5_60', 'A_dP5', 'A_dOI5', 'A_dP10',
                        'A_dOI10', 'A_OI20', 'A_BASISDEV', 'A_PCR', 'A_dPCR5', 'A_IVREL', 'A_IVSPREAD', 'A_dCIV20',
                        'A_dPIV20', 'three_day']].copy()
        tr['pnl_net'] = SIGN[t] * tr.three_day - COST_A
    else:
        m = MB[t]
        tr = DW.loc[m, ['symbol', 'qn', 'label', 'i_react', 'XN', 'cut_rsi14', 'B_dOI1', 'B_dP5', 'B_dOI5', 'B_OI20',
                        'B_BASISDEV', 'B_dBASIS1', 'B_PCR', 'B_dPCR1', 'B_IVREL', 'B_IVSPREAD', 'B_dCIV20',
                        'B_dPIV20', 'vsN_H20', 'vsN_net_H20']].copy()
    tr.to_csv(f'{OUTD}/trades_{t}.csv', index=False, float_format='%.4f')
P('done')
