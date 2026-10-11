#!/usr/bin/env python3
"""DELIVERY % family: run exactly the tests of prereg.txt (refuses to run if its sha256 differs from prereg.sha256).
usage: python3 run_tests.py OUT SP     (OUT = .../more_signals/delivery; writes only into OUT)
Percent units. Trade A: three_day (close i_cut -> close i_p1), cost 0.17. Trade B: 20-session Nifty-hedged return
from the entry close (k, k+1 or k+2), cost 0.19."""
import hashlib
import sys

import numpy as np
import pandas as pd

OUT, SP = sys.argv[1], sys.argv[2]
DATA = f'{SP}/sector_lab/data'
F = f'{SP}/perf/features'
LOG = open(f'{OUT}/run.log', 'w')
CA, CB = 0.17, 0.19
B_PERM, B_PL, B_SPLIT, NDRAW_B, NPERM_B = 20000, 10000, 20000, 20000, 10000


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.write(s + '\n')
    LOG.flush()


h = hashlib.sha256(open(f'{OUT}/prereg.txt', 'rb').read()).hexdigest()
logged = open(f'{OUT}/prereg.sha256').read().split()[0]
P(f'prereg.txt sha256 {h}  logged {logged}  match={h == logged}')
assert h == logged, 'prereg.txt changed after it was hashed'


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


def fx(x, nd=2, sign=True):
    if x is None or (isinstance(x, (float, np.floating)) and not np.isfinite(x)):
        return 'n/a'
    return f'{x:+.{nd}f}' if sign else f'{x:.{nd}f}'


# =================================================================== pre-registered definitions
def a_masks(df):
    """signal masks for trade A tests on results rows or placebo days (same column names)."""
    m = {
        'A01': df.ACC > 0,
        'A02': df.rank_ACC > 80,
        'A03': df.rank_ACC <= 20,
        'A04': df.DQR >= 1.5,
        'A05': df.rank_DQR > 80,
        'A06': df.rank_DPL > 80,
        'A07': (df.PR5 < 0) & (df.ACC > 0),
        'A08': (df.PR5 > 0) & (df.ACC > 0),
        'A09': (df.PR5 > 0) & (df.ACC < 0),
        'A10': df.rank_DP60 > 80,
    }
    return {k: v.fillna(False).to_numpy(bool) for k, v in m.items()}


A_TESTS = [  # id, sign, label
    ('A01', +1, '5-day delivery % above its 60-day average (ACC > 0)'),
    ('A02', +1, 'ACC top quintile of the quarter'),
    ('A03', -1, 'ACC bottom quintile (delivery drying up), short'),
    ('A04', +1, 'delivery qty 5/60 ratio >= 1.5'),
    ('A05', +1, 'delivery qty 5/60 ratio top quintile'),
    ('A06', +1, 'last published day delivery % vs 60-day avg top quintile'),
    ('A07', +1, 'price down + delivery up (PR5 < 0, ACC > 0)'),
    ('A08', +1, 'price up + delivery up (PR5 > 0, ACC > 0)'),
    ('A09', -1, 'price up + delivery down (PR5 > 0, ACC < 0), short'),
    ('A10', +1, '60-day delivery % level top quintile'),
]
A_SIGN = {t: s for t, s, _ in A_TESTS}
A_LABEL = {t: l for t, _, l in A_TESTS}
A_FEATS = {'A01': ['ACC'], 'A02': ['rank_ACC'], 'A03': ['rank_ACC'], 'A04': ['DQR'], 'A05': ['rank_DQR'],
           'A06': ['rank_DPL'], 'A07': ['PR5', 'ACC'], 'A08': ['PR5', 'ACC'], 'A09': ['PR5', 'ACC'],
           'A10': ['rank_DP60']}

# B: feature -> (entry offset j, signal function, eligibility columns)
B_FEATS = {
    'ACCPRE_HI': (0, lambda d: d.ACC_pre > 0, ['ACC_pre']),
    'ACCPRE_LO': (0, lambda d: d.ACC_pre <= 0, ['ACC_pre']),
    'DPK_HI': (1, lambda d: d.DPK >= d.DPK_med, ['DPK', 'DPK_med']),
    'DPK_LO': (1, lambda d: d.DPK < d.DPK_med, ['DPK', 'DPK_med']),
    'DQK_HI': (1, lambda d: d.DQK >= 3, ['DQK']),
    'DQK_LO': (1, lambda d: d.DQK < 3, ['DQK']),
    'DPK1_HI': (2, lambda d: d.DPK1 > 0, ['DPK1']),
    'DPK1_LO': (2, lambda d: d.DPK1 <= 0, ['DPK1']),
}
B_LABEL = {
    'ACCPRE_HI': 'pre-results accumulation: 5-day delivery % (to k-1) above 60-day avg; entry close k',
    'ACCPRE_LO': 'no pre-results accumulation (ACC to k-1 <= 0); entry close k',
    'DPK_HI': 'reaction-day delivery % vs 60-day avg in the top half of the quarter\'s winners; entry close k+1',
    'DPK_LO': 'reaction-day delivery % vs 60-day avg in the bottom half of the quarter\'s winners; entry close k+1',
    'DQK_HI': 'reaction-day delivery qty >= 3x its 60-day avg; entry close k+1',
    'DQK_LO': 'reaction-day delivery qty < 3x its 60-day avg; entry close k+1',
    'DPK1_HI': 'day k+1 delivery % above the 60-day avg (k-60..k-1); entry close k+2',
    'DPK1_LO': 'day k+1 delivery % at/below that avg; entry close k+2',
}

# =================================================================== TRADE A
fr = pd.read_csv(f'{OUT}/feat_results.csv')
out = pd.read_csv(f'{F}/outcomes.csv')
D = fr.merge(out[['symbol', 'qn', 'three_day', 'tradable_B', 'raw_H20', 'nifty_H20', 'vsN_H20', 'vsN_net_H20']],
             on=['symbol', 'qn'], how='left', validate='1:1')
assert len(D) == 3280
D['results_for'] = 'Results for ' + D.period + ' (' + D.quarter + ')'
PERIOD = D.groupby('qn').results_for.first()
A = D[D.three_day.notna()].reset_index(drop=True)
P(f'TRADE A: F&O results with three_day {len(A)} of 3280')
y = A.three_day.to_numpy(float)
qn = A.qn.to_numpy(int)
N = len(A)
QS = np.unique(qn)
QMEAN = pd.Series(y).groupby(qn).mean()
P(f'  all F&O results mean three_day {y.mean():+.3f}% (net {y.mean() - CA:+.3f}%) [documented +0.04% ... see log]')
MA = a_masks(A)
LRm = ((A.in_fo_events == True) & (A.lag21 < -10) & (A.vol_ratio_5_60 >= 1.0)).to_numpy(bool)
LAGm = ((A.in_fo_events == True) & (A.lag21 < -10)).to_numpy(bool)
MA['RA1'] = LAGm & (A.DQR >= 1.0).fillna(False).to_numpy(bool)
MA['RA2'] = LAGm & (A.ACC > 0).fillna(False).to_numpy(bool)
MA['LAGRULE'] = LRm
MA['LAG_ALONE'] = LAGm
REPL = [('RA1', +1, 'lag < -10 AND delivery qty 5/60 >= 1.0 (delivery volume replaces total volume)'),
        ('RA2', +1, 'lag < -10 AND ACC > 0 (rising delivery % replaces volume)')]
REF = [('LAGRULE', +1, 'lag 10% + volume (original rule)'), ('LAG_ALONE', +1, 'lag < -10 alone')]
for t, s, l in REPL + REF:
    A_SIGN[t] = s
    A_LABEL[t] = l
ALL_A = A_TESTS + REPL + REF
IDS_A = [t for t, _, _ in ALL_A]
P(f'  lag rule trades {LRm.sum()}, mean {y[LRm].mean():+.3f}% [documented 85, +2.13%]')
assert LRm.sum() == 85 and abs(y[LRm].mean() - 2.13) < 0.01
# the 85 match the repo trades file
rp = pd.read_csv(__import__('os').environ.get('REPO_ROOT', '.') + '/results/lag10_volume/trades.csv',
                 usecols=['symbol', 'qn'])
assert set(zip(rp.symbol, rp.qn)) == set(zip(A.symbol[LRm], A.qn[LRm]))


def describe_a(t, m):
    s = A_SIGN[t]
    pnl = s * y[m]
    q = qn[m]
    n = len(pnl)
    r = {'test': t, 'trade': 'A', 'dir': 'L' if s > 0 else 'S', 'label': A_LABEL[t], 'n': n}
    if n == 0:
        return r
    base = s * QMEAN.reindex(q).to_numpy()
    r.update(avg=pnl.mean(), net=pnl.mean() - CA, excess=pnl.mean() - base.mean(), hit=(pnl > 0).mean() * 100,
             parent_avg=base.mean())
    pq = pd.Series(pnl - CA).groupby(q).mean()
    r['q_pos'], r['q_with'] = int((pq > 0).sum()), int(len(pq))
    for hh, hm in (('h1', q <= 13), ('h2', q >= 14)):
        r[f'n_{hh}'] = int(hm.sum())
        r[f'net_{hh}'] = pnl[hm].mean() - CA if hm.any() else np.nan
        r[f'excess_{hh}'] = (pnl[hm] - base[hm]).mean() if hm.any() else np.nan
    srt = np.sort(pnl)[::-1]
    r['net_wo_best5'] = srt[5:].mean() - CA if n > 5 else np.nan
    r['excess_wo_best5'] = (np.delete(pnl, np.argsort(-pnl)[:5]) - np.delete(base, np.argsort(-pnl)[:5])).mean() \
        if n > 5 else np.nan
    return r


# luck p (within-quarter permutation = random same-size picks per quarter from all F&O results) and maxT (A tests)
rng = np.random.default_rng(20261011)
qidx = {q: np.flatnonzero(qn == q) for q in QS}
MM = np.column_stack([MA[t] for t in IDS_A]).astype(float)
NN = MM.sum(0)
SG = np.array([A_SIGN[t] for t in IDS_A], float)
obsA = SG * (y @ MM) / np.where(NN > 0, NN, 1)
permA = np.empty((B_PERM, len(IDS_A)))
for c0 in range(0, B_PERM, 2000):
    nb = min(2000, B_PERM - c0)
    Yp = np.empty((nb, N))
    for q, ix in qidx.items():
        Yp[:, ix] = y[ix][np.argsort(rng.random((nb, len(ix))), axis=1)]
    permA[c0:c0 + nb] = SG * (Yp @ MM) / np.where(NN > 0, NN, 1)
LUCK = dict(zip(IDS_A, (1 + (permA >= obsA[None, :] - 1e-12).sum(0)) / (1 + B_PERM)))
mu, sd = permA.mean(0), permA.std(0, ddof=1)
ZA = (permA - mu) / sd
zA = (obsA - mu) / sd
main_ix = [IDS_A.index(t) for t, _, _ in A_TESTS]
maxzA = ZA[:, main_ix].max(1)
MAXT = {IDS_A[k]: (1 + (maxzA >= zA[k] - 1e-12).sum()) / (1 + B_PERM) for k in main_ix}
P(f'  maxT (A, {len(main_ix)} tests): null 95th pct of max z {np.percentile(maxzA, 95):.2f}')

# placebo A
pl = pd.read_csv(f'{OUT}/feat_placeboA.csv.gz')
plo = pd.read_csv(f'{SP}/ta/build/placebo_ta.csv.gz', usecols=['symbol', 'i', 'in_fo', 'qn_next', 'three_day'])
plo = plo[(plo.in_fo == True) & plo.qn_next.notna()][['symbol', 'i', 'three_day']]
pl = pl.merge(plo, on=['symbol', 'i'], how='left', validate='1:1')
pl = pl[pl.three_day.notna()].reset_index(drop=True)
py = pl.three_day.to_numpy(float)
pq_ = pl.qn_next.to_numpy(int)
PL_QMEAN = pd.Series(py).groupby(pq_).mean()
PMA = a_masks(pl)
PMA['RA1'] = ((pl.lag_pct < -10) & (pl.DQR >= 1.0)).to_numpy(bool)
PMA['RA2'] = ((pl.lag_pct < -10) & (pl.ACC > 0)).to_numpy(bool)
P(f'  placebo A days {len(pl)}, mean 3-day {py.mean():+.3f}%')
rngp = np.random.default_rng(7)


def placebo_a(t):
    s = A_SIGN[t]
    pm = PMA[t]
    if pm.sum() == 0:
        return {}
    pools = {q: s * py[pm & (pq_ == q)] for q in np.unique(pq_[pm])}
    m = MA[t]
    q_tr = qn[m]
    keep = np.isin(q_tr, list(pools))
    pnl = s * y[m][keep]
    qk = q_tr[keep]
    n = int(keep.sum())
    if n == 0:
        return {}
    nq = pd.Series(qk).value_counts().sort_index()
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
    return {'pl_n': int(pm.sum()), 'pl_sig_avg': pl_sig, 'pl_excess': e_pl, 'DiD': e_res - e_pl,
            'placebo_p': (1 + (e_draw >= e_res - 1e-12).sum()) / (1 + B_PL)}


rowsA = []
for t, _, _ in ALL_A:
    r = describe_a(t, MA[t])
    r['luck_p'] = LUCK[t]
    r['maxT_within'] = MAXT.get(t, np.nan)
    if t in A_SIGN and t not in ('LAGRULE', 'LAG_ALONE'):
        r.update(placebo_a(t))
    rowsA.append(r)
TA = pd.DataFrame(rowsA)

# =================================================================== TRADE B
ses = pd.read_csv(f'{DATA}/sessions.csv')
days = ses.day.tolist()
T = len(days)
ret = pd.read_csv(f'{DATA}/returns.csv', index_col=0)
SYMS = ret.columns.tolist()
SYM = {s: j for j, s in enumerate(SYMS)}
R = ret.to_numpy(float)
PX = np.cumprod(1.0 + np.nan_to_num(R), axis=0)
CVALID = np.cumsum(~np.isnan(R), axis=0)
NIFTY = pd.read_csv(f'{DATA}/index_close.csv', index_col=0)['Nifty 50'].to_numpy(float)


def hedged(j_sym, k, off):
    """20-session Nifty-hedged gross % from close k+off; tradable flag (k+off+21 exists, <= 2 blanks)."""
    e = k + off
    okk = e + 21 <= T - 1
    ee = np.where(okk, e, 0)
    okk &= (21 - (CVALID[np.minimum(ee + 21, T - 1), j_sym] - CVALID[ee, j_sym])) <= 2
    g = ((PX[np.minimum(ee + 20, T - 1), j_sym] / PX[ee, j_sym] - 1) -
         (NIFTY[np.minimum(ee + 20, T - 1)] / NIFTY[ee] - 1)) * 100
    return np.where(okk, g, np.nan), okk


jD = D.symbol.map(SYM).to_numpy(int)
kD = D.i_react.to_numpy(int)
VGj, TRj = {}, {}
for off in (0, 1, 2):
    VGj[off], TRj[off] = hedged(jD, kD, off)
tb = (D.tradable_B == True).to_numpy()
chk = np.abs(VGj[0][tb] - D.vsN_H20.to_numpy(float)[tb])
P(f'\nTRADE B: tradable_B {tb.sum()}; own entry-k hedged return vs outcomes vsN_H20: max |diff| {np.nanmax(chk):.2e}; '
  f'own tradable flag == tradable_B on {np.mean(TRj[0] == tb) * 100:.2f}%')
assert np.nanmax(chk) < 1e-3   # outcomes.csv is stored rounded (max diff 5e-5 pp)
BU = tb & TRj[1] & TRj[2]
P(f'  tradable at entries k, k+1, k+2: {BU.sum()} (tradable_B {tb.sum()})')
Wm = (D.W == True).to_numpy() & tb
WRm = Wm & (D.cut_rsi14 > 50).to_numpy()
QN = D.qn.to_numpy(int)
XB = {off: VGj[off] - CB for off in (0, 1, 2)}
P(f'  W {Wm.sum()} entry k {np.nanmean(XB[0][Wm]):+.3f}% [documented +1.45]; WR {WRm.sum()} '
  f'{np.nanmean(XB[0][WRm]):+.3f}% [documented +2.42]')
assert Wm.sum() == 392 and WRm.sum() == 232
for off in (1, 2):
    for lab, m in (('W', Wm), ('WR', WRm)):
        mm = m & TRj[off]
        P(f'  {lab} entry close k+{off}: n {mm.sum()} mean vsN_net {XB[off][mm].mean():+.3f}%')

# DPK split point: median DPK of the quarter's plain winners (tradable at k+1) - same threshold for W and WR tests
mW1 = Wm & TRj[1] & D.DPK.notna().to_numpy()
D['DPK_med'] = D.qn.map(D[mW1].groupby('qn').DPK.median())
P('  DPK split points (median of the quarter\'s winners):', D[mW1].groupby('qn').DPK.median().round(1).to_dict())
B_TESTS = []
for pool_lab, pool in (('W', Wm), ('WR', WRm)):
    for fe, (off, fn, cols) in B_FEATS.items():
        elig = pool & TRj[off] & D[cols].notna().all(1).to_numpy()
        sig = elig & fn(D).fillna(False).to_numpy(bool)
        B_TESTS.append((f'{pool_lab}_{fe}', pool_lab, fe, off, sig, elig))


def tq_(s):
    s = s.dropna()
    return s.mean() / (s.std(ddof=1) / np.sqrt(len(s))) if len(s) > 2 and s.std(ddof=1) > 0 else np.nan


rngb = np.random.default_rng(20261011)


def luck_b(si, pi, vals):
    tot = np.zeros(NDRAW_B)
    kt = 0
    for q in np.unique(QN[si]):
        k = int((QN[si] == q).sum())
        pq = pi[QN[pi] == q]
        v = vals[pq]
        if k == len(pq):
            tot += v.sum()
        else:
            for c0 in range(0, NDRAW_B, 5000):
                c1 = min(NDRAW_B, c0 + 5000)
                pick = np.argpartition(rngb.random((c1 - c0, len(pq))), k - 1, axis=1)[:, :k]
                tot[c0:c1] += v[pick].sum(1)
        kt += k
    return tot / kt


rowsB, pqB, tradesB, DPAR = [], [], [], {}
for name, lab, fe, off, sig, par in B_TESTS:
    v = XB[off]
    si, pi = np.where(sig)[0], np.where(par)[0]
    n = len(si)
    pm = pd.Series(v[pi]).groupby(QN[pi]).mean()
    dpar = v[si] - pm.reindex(QN[si]).to_numpy()
    x = v[si]
    q = QN[si]
    f14, l8 = q <= 13, q >= 14
    sq = pd.Series(x).groupby(q).mean()
    keep = np.ones(n, bool)
    keep[np.argsort(-x)[:5]] = False
    r = dict(test=name, trade='B', pool=lab, feature=fe, entry=f'k+{off}' if off else 'k', label=B_LABEL[fe], n=n,
             parent_n=len(pi), avg=x.mean(), parent_avg=v[pi].mean(), d_par=dpar.mean(), q_with=len(sq),
             q_pos=int((sq > 0).sum()), n_h1=int(f14.sum()), net_h1=x[f14].mean() if f14.any() else np.nan,
             dpar_h1=dpar[f14].mean() if f14.any() else np.nan, n_h2=int(l8.sum()),
             net_h2=x[l8].mean() if l8.any() else np.nan, dpar_h2=dpar[l8].mean() if l8.any() else np.nan,
             net_wo_best5=x[keep].mean() if n > 5 else np.nan, dpar_wo_best5=dpar[keep].mean() if n > 5 else np.nan,
             t_q_dpar=tq_(pd.Series(dpar).groupby(q).mean()))
    draws = luck_b(si, pi, v)
    r['luck_p'] = (1 + (draws >= x.mean() - 1e-12).sum()) / (1 + NDRAW_B)
    rowsB.append(r)
    DPAR[name] = (si, dpar)
    for qq in sorted(set(QN[pi])):
        mq = q == qq
        pqB.append(dict(test=name, qn=qq, results_for=PERIOD[qq], n=int(mq.sum()),
                        avg=x[mq].mean() if mq.any() else np.nan, parent_n=int((QN[pi] == qq).sum()),
                        parent_avg=pm.get(qq, np.nan)))
    for i_, dd in zip(si, dpar):
        tradesB.append(dict(test=name, symbol=D.symbol[i_], qn=QN[i_], results_for=D.results_for[i_],
                            entry=r['entry'], XN=D.XN[i_], cut_rsi14=D.cut_rsi14[i_], feature=D[B_FEATS[fe][2][0]][i_],
                            vsN_net=v[i_], d_par=dd))
TB = pd.DataFrame(rowsB)

# maxT within B: joint permutations within quarter x stratum over rows tradable at k, k+1 and k+2
strat = np.where(WRm, 0, np.where(Wm, 1, 2))
Uix = np.flatnonzero(BU)
block = QN[Uix] * 3 + strat[Uix]
o0 = np.argsort(block, kind='stable')
Uo = Uix[o0]
bs = block[o0]
NTB = len(B_TESTS)
obsB = np.zeros(NTB)
MB = np.zeros((NTB, len(Uo)))
OFF = np.zeros(NTB, int)
for t, (name, lab, fe, off, sig, par) in enumerate(B_TESTS):
    s_ = sig[Uo]
    MB[t, s_] = 1.0 / max(1, s_.sum())
    OFF[t] = off
    obsB[t] = XB[off][Uo][s_].mean()
VU = {off: XB[off][Uo] for off in (0, 1, 2)}
permB = np.zeros((NPERM_B, NTB))
for c0 in range(0, NPERM_B, 500):
    c1 = min(NPERM_B, c0 + 500)
    idx = np.argsort(bs[None, :] + rngb.random((c1 - c0, len(bs))), axis=1)
    for off in (0, 1, 2):
        tt = np.flatnonzero(OFF == off)
        permB[c0:c1, tt] = VU[off][idx] @ MB[tt].T
mub, sdb = permB.mean(0), permB.std(0, ddof=1)
zB = (obsB - mub) / sdb
maxzB = ((permB - mub) / sdb).max(1)
TB['maxT_within'] = [(1 + (maxzB >= zB[t] - 1e-12).sum()) / (1 + NPERM_B) for t in range(NTB)]
P(f'  maxT (B, {NTB} tests): null 95th pct of max z {np.percentile(maxzB, 95):.2f}; universe rows {len(Uo)}')

# placebo B (quiet days)
qd = pd.read_csv(f'{OUT}/feat_placeboB.csv.gz')
qd = qd[qd.no_result_k22 == True].reset_index(drop=True)
qj = qd.symbol.map(SYM).to_numpy(int)
qk = qd.i.to_numpy(int)
QX, QT = {}, {}
for off in (0, 1, 2):
    g, okk = hedged(qj, qk, off)
    QX[off], QT[off] = g - CB, okk
QW = (qd.W == True).to_numpy()
QWR = QW & (qd.m2_rsi14 > 50).to_numpy()
QM = qd.day.str[:7].to_numpy()
mq1 = QW & QT[1] & qd.DPK.notna().to_numpy()
qd['DPK_med'] = pd.Series(QM).map(pd.Series(qd.DPK.to_numpy()[mq1]).groupby(QM[mq1]).median()).to_numpy()
for off in (0, 1, 2):
    P(f'  quiet winners entry k+{off}: n {(QW & QT[off]).sum()} mean {QX[off][QW & QT[off]].mean():+.3f}%; '
      f'RSI winners n {(QWR & QT[off]).sum()} mean {QX[off][QWR & QT[off]].mean():+.3f}%')
rngq = np.random.default_rng(17)
plB = {}
for name, lab, fe, off, sig, par in B_TESTS:
    off_, fn, cols = B_FEATS[fe]
    qpool = (QW if lab == 'W' else QWR) & QT[off] & qd[cols].notna().all(1).to_numpy()
    qs = qpool & fn(qd).fillna(False).to_numpy(bool)
    v = QX[off]
    pmm = pd.Series(v[qpool]).groupby(QM[qpool]).mean()
    dq = v[qs] - pmm.reindex(QM[qs]).to_numpy()
    r = TB.loc[TB.test == name].iloc[0]
    res = dict(pl_n=int(qs.sum()), pl_sig_avg=v[qs].mean() if qs.any() else np.nan,
               pl_excess=dq.mean() if qs.any() else np.nan)
    res['DiD'] = r.d_par - res['pl_excess']
    if qs.sum() >= 2:
        dr = dq[rngq.integers(0, len(dq), size=(B_PL, r.n))].mean(1)
        res['placebo_p'] = (1 + (dr >= r.d_par - 1e-12).sum()) / (1 + B_PL)
    else:
        res['placebo_p'] = np.nan
    plB[name] = res
for c in ['pl_n', 'pl_sig_avg', 'pl_excess', 'DiD', 'placebo_p']:
    TB[c] = TB.test.map(lambda t: plB[t][c])

# =================================================================== family-wide multiple testing
main = pd.concat([TA[TA.test.isin([t for t, _, _ in A_TESTS])].assign(excess_or_dpar=lambda d: d.excess),
                  TB.assign(excess_or_dpar=lambda d: d.d_par)], ignore_index=True)
main['holm_p'] = holm(main.luck_p.to_numpy())
main['maxT_family'] = np.minimum(1.0, 2 * main.maxT_within)
main['n_family'] = len(main)


def verdict(r):
    if r.trade == 'A':
        halves = (r.excess_h1 > 0) and (r.excess_h2 > 0) and (r.net_h1 > 0) and (r.net_h2 > 0)
        wo5 = (r.net_wo_best5 > 0) and (r.excess_wo_best5 > 0)
        plc = (r.DiD > 0) and (r.placebo_p < 0.10)
    else:
        halves = (r.dpar_h1 > 0) and (r.dpar_h2 > 0) and (r.net_h1 > 0) and (r.net_h2 > 0)
        wo5 = (r.net_wo_best5 > 0) and (r.dpar_wo_best5 > 0)
        plc = (r.DiD > 0) and (r.placebo_p < 0.10) and (r.pl_n >= 30)
    crit = [('n<30', r.n >= 30), ('halves', halves), ('Holm', r.holm_p < 0.10), ('placebo', plc), ('w/o best 5', wo5)]
    fails = [k for k, ok_ in crit if not ok_]
    if not fails:
        return 'WORKS', ''
    if fails == ['Holm'] and r.luck_p < 0.05:
        return 'WATCH', 'Holm'
    return 'NO', ','.join(fails)


vv = main.apply(verdict, axis=1)
main['verdict'] = [v[0] for v in vv]
main['fails'] = [v[1] for v in vv]
main.to_csv(f'{OUT}/tests.csv', index=False, float_format='%.4f')

# =================================================================== replacement family (A)
rr_rows = []
lag_avail = {'RA1': A.DQR.notna().to_numpy(), 'RA2': A.ACC.notna().to_numpy()}
rngr = np.random.default_rng(13)
rep = TA[TA.test.isin(['RA1', 'RA2'])].copy()
rep['holm_p_within2'] = holm(rep.luck_p.to_numpy())
for t in ['RA1', 'RA2']:
    bm = LAGm & lag_avail[t]
    yin, yout = y[bm & MA[t]], y[bm & ~MA[t]]
    ya = y[bm]
    k = len(yin)
    sel = np.argsort(rngr.random((B_SPLIT, len(ya))), axis=1)[:, :k]
    s_in = ya[sel].sum(1)
    dperm = s_in / k - (ya.sum() - s_in) / (len(ya) - k)
    rep.loc[rep.test == t, 'overlap_with_85'] = int((MA[t] & LRm).sum())
    rep.loc[rep.test == t, 'in_minus_out_within_lag'] = yin.mean() - yout.mean()
    rep.loc[rep.test == t, 'adds_p_1s'] = (1 + (dperm >= yin.mean() - yout.mean() - 1e-12).sum()) / (1 + B_SPLIT)
rep['rule_avg'] = y[LRm].mean()
rep['lag_alone_n'] = int(LAGm.sum())
rep['lag_alone_avg'] = y[LAGm].mean()
rep.to_csv(f'{OUT}/replacement.csv', index=False, float_format='%.4f')

# =================================================================== lag-rule splits
SPLITS = [  # id, label, IN mask, availability columns, prediction
    ('LS1', 'ACC > 0 (5-day delivery % above 60-day avg)', A.ACC > 0, ['ACC'], 'IN better'),
    ('LS2', 'delivery qty 5/60 >= 1.0', A.DQR >= 1.0, ['DQR'], 'IN better'),
    ('LS3', 'delivery qty 5/60 >= 1.5', A.DQR >= 1.5, ['DQR'], 'IN better'),
    ('LS4', 'last published day delivery % above its 60-day avg (DPL > 0)', A.DPL > 0, ['DPL'], 'IN better'),
    ('LS5', 'ACC top quintile of the quarter', A.rank_ACC > 80, ['rank_ACC'], 'IN better'),
    ('LS6', 'price down + delivery up (PR5 < 0, ACC > 0)', (A.PR5 < 0) & (A.ACC > 0), ['PR5', 'ACC'], 'IN better'),
    ('LS7', '60-day delivery % level above the quarter median (rank_DP60 > 50)', A.rank_DP60 > 50, ['rank_DP60'],
     'IN better'),
]
rngs = np.random.default_rng(11)
srows = []
for sid, lab, mk, cols, pred in SPLITS:
    av = LRm & A[cols].notna().all(1).to_numpy()
    mk = mk.fillna(False).to_numpy(bool)
    yin, yout = y[av & mk], y[av & ~mk]
    r = dict(split=sid, label=lab, pred=pred, n_avail=int(av.sum()), n_in=len(yin), n_out=len(yout),
             avg_in=yin.mean() if len(yin) else np.nan, avg_out=yout.mean() if len(yout) else np.nan)
    r['net_in'] = r['avg_in'] - CA
    r['net_out'] = r['avg_out'] - CA
    for hh, hm in (('h1', qn <= 13), ('h2', qn >= 14)):
        a_in, a_out = y[av & mk & hm], y[av & ~mk & hm]
        r[f'n_in_{hh}'], r[f'avg_in_{hh}'] = len(a_in), a_in.mean() if len(a_in) else np.nan
        r[f'n_out_{hh}'], r[f'avg_out_{hh}'] = len(a_out), a_out.mean() if len(a_out) else np.nan
    r['diff'] = r['avg_in'] - r['avg_out']
    if len(yin) and len(yout):
        ya = y[av]
        k = len(yin)
        sel = np.argsort(rngs.random((B_SPLIT, len(ya))), axis=1)[:, :k]
        s_in = ya[sel].sum(1)
        dperm = s_in / k - (ya.sum() - s_in) / (len(ya) - k)
        r['perm_p_2s'] = (1 + (np.abs(dperm) >= abs(r['diff']) - 1e-12).sum()) / (1 + B_SPLIT)
    else:
        r['perm_p_2s'] = np.nan
    r['tested'] = (len(yin) >= 5) and (len(yout) >= 5)
    if len(yin) > 5:
        r['net_in_wo_best5'] = np.sort(yin)[::-1][5:].mean() - CA
    srows.append(r)
SPL = pd.DataFrame(srows)
tm = SPL.tested.to_numpy(bool)
SPL['holm_p'] = np.nan
SPL.loc[tm, 'holm_p'] = holm(SPL.perm_p_2s[tm].to_numpy())
SPL['separates'] = ((SPL.avg_in_h1 - SPL.avg_out_h1 > 0) & (SPL.avg_in_h2 - SPL.avg_out_h2 > 0) & (SPL.holm_p < 0.10)
                    & (SPL.net_in_wo_best5 > 0))
SPL.to_csv(f'{OUT}/lag_rule_splits.csv', index=False, float_format='%.4f')

# =================================================================== per-quarter, trades
pqA = []
for t in IDS_A:
    m = MA[t]
    for q in QS:
        mm = m & (qn == q)
        pqA.append(dict(test=t, qn=q, results_for=PERIOD[q], n=int(mm.sum()),
                        avg=A_SIGN[t] * y[mm].mean() if mm.any() else np.nan, parent_avg=A_SIGN[t] * QMEAN[q]))
pd.concat([pd.DataFrame(pqA), pd.DataFrame(pqB)]).to_csv(f'{OUT}/per_quarter.csv', index=False, float_format='%.4f')
trA = []
for t in IDS_A:
    m = MA[t]
    g = A.loc[m, ['symbol', 'qn', 'results_for', 'lag21', 'vol_ratio_5_60', 'ACC', 'DQR', 'DPL', 'PR5', 'three_day']]
    g.insert(0, 'test', t)
    g['pnl_net'] = A_SIGN[t] * g.three_day - CA
    trA.append(g)
pd.concat(trA).to_csv(f'{OUT}/trades_A.csv', index=False, float_format='%.4f')
pd.DataFrame(tradesB).to_csv(f'{OUT}/trades_B.csv', index=False, float_format='%.4f')

# =================================================================== tables
P('\nMAIN FAMILY')
pd.set_option('display.width', 260)
P(main[['test', 'n', 'avg', 'excess_or_dpar', 'q_pos', 'q_with', 'n_h1', 'net_h1', 'n_h2', 'net_h2', 'net_wo_best5',
        'luck_p', 'holm_p', 'maxT_family', 'pl_n', 'pl_excess', 'DiD', 'placebo_p', 'verdict', 'fails']]
  .round(3).to_string(index=False))


def table_a(df):
    L = ['| test | dir | signal (at cutoff close, delivery to cutoff-1) | n | avg gross | net | vs all F&O (excess) | '
         'q+ / q | first14 n, net, excess | last8 n, net, excess | w/o best5 net | luck p | Holm p | maxT p | '
         'placebo days n, excess | DiD | placebo p | verdict |', '|' + '---|' * 18]
    for r in df.itertuples():
        L.append(f'| {r.test} | {r.dir} | {r.label} | {r.n} | {fx(r.avg)} | {fx(r.net)} | {fx(r.excess)} | '
                 f'{r.q_pos}/{r.q_with} | {r.n_h1}, {fx(r.net_h1)}, {fx(r.excess_h1)} | {r.n_h2}, {fx(r.net_h2)}, '
                 f'{fx(r.excess_h2)} | {fx(r.net_wo_best5)} | {r.luck_p:.4f} | {fx(r.holm_p, 3, False)} | '
                 f'{fx(r.maxT_family, 3, False)} | {int(r.pl_n) if np.isfinite(r.pl_n) else "n/a"}, {fx(r.pl_excess)} | '
                 f'{fx(r.DiD)} | {fx(r.placebo_p, 4, False)} | {r.verdict}{" (" + r.fails + ")" if r.fails else ""} |')
    return '\n'.join(L)


def table_b(df):
    L = ['| test | entry | signal | n (parent) | avg vsN_net | parent avg | gain vs parent | q+ / q | '
         'first14 n, net, gain | last8 n, net, gain | w/o best5 net, gain | luck p | Holm p | maxT p | '
         'quiet n, gain | DiD | placebo p | verdict |', '|' + '---|' * 18]
    for r in df.itertuples():
        L.append(f'| {r.test} | {r.entry} | {r.label} | {r.n} ({r.parent_n}) | {fx(r.avg)} | {fx(r.parent_avg)} | '
                 f'{fx(r.d_par)} | {r.q_pos}/{r.q_with} | {r.n_h1}, {fx(r.net_h1)}, {fx(r.dpar_h1)} | {r.n_h2}, '
                 f'{fx(r.net_h2)}, {fx(r.dpar_h2)} | {fx(r.net_wo_best5)}, {fx(r.dpar_wo_best5)} | {r.luck_p:.4f} | '
                 f'{fx(r.holm_p, 3, False)} | {fx(r.maxT_family, 3, False)} | {int(r.pl_n)}, {fx(r.pl_excess)} | '
                 f'{fx(r.DiD)} | {fx(r.placebo_p, 4, False)} | {r.verdict}{" (" + r.fails + ")" if r.fails else ""} |')
    return '\n'.join(L)


def table_splits(df):
    L = ['| split of the 85 lag-rule trades | n IN / OUT | IN avg (net) | OUT avg (net) | IN - OUT | '
         'IN first14 n, avg | IN last8 n, avg | OUT first14 avg | OUT last8 avg | IN w/o best5 net | perm p (2-sided) | '
         'Holm p | separates |', '|' + '---|' * 13]
    for r in df.itertuples():
        L.append(f'| {r.split} {r.label} | {r.n_in} / {r.n_out} | {fx(r.avg_in)} ({fx(r.net_in)}) | {fx(r.avg_out)} '
                 f'({fx(r.net_out)}) | {fx(r.diff)} | {r.n_in_h1}, {fx(r.avg_in_h1)} | {r.n_in_h2}, {fx(r.avg_in_h2)} | '
                 f'{fx(r.avg_out_h1)} | {fx(r.avg_out_h2)} | {fx(getattr(r, "net_in_wo_best5", np.nan))} | '
                 f'{fx(r.perm_p_2s, 4, False)} | {fx(r.holm_p, 3, False)} | {"yes" if r.separates else "no"} |')
    return '\n'.join(L)


def table_rep(df):
    L = ['| test | signal | n | avg gross | net | q+ / q | first14 net | last8 net | w/o best5 net | luck p | '
         'Holm p (2) | placebo DiD, p | overlap with 85 | IN-OUT within lag<-10 (p) | verdict vs rule +2.13 |',
         '|' + '---|' * 15]
    for r in df.itertuples():
        works = (r.n >= 30 and r.excess_h1 > 0 and r.excess_h2 > 0 and r.net_h1 > 0 and r.net_h2 > 0 and
                 r.holm_p_within2 < 0.10 and r.DiD > 0 and r.placebo_p < 0.10 and r.net_wo_best5 > 0 and
                 r.excess_wo_best5 > 0)
        vrd = ('CAN REPLACE' if works and r.avg >= r.rule_avg else 'WORKS, below rule' if works else 'NO')
        L.append(f'| {r.test} | {r.label} | {r.n} | {fx(r.avg)} | {fx(r.net)} | {r.q_pos}/{r.q_with} | '
                 f'{fx(r.net_h1)} | {fx(r.net_h2)} | {fx(r.net_wo_best5)} | {r.luck_p:.4f} | '
                 f'{r.holm_p_within2:.3f} | {fx(r.DiD)}, {r.placebo_p:.4f} | {int(r.overlap_with_85)} | '
                 f'{fx(r.in_minus_out_within_lag)} ({r.adds_p_1s:.4f}) | {vrd} |')
    return '\n'.join(L)


tA = table_a(main[main.trade == 'A'])
tB = table_b(main[main.trade == 'B'])
tS = table_splits(SPL)
tR = table_rep(rep)
open(f'{OUT}/table_A.md', 'w').write(tA + '\n\nREPLACEMENT (separate family of 2)\n\n' + tR + '\n')
open(f'{OUT}/table_B.md', 'w').write(tB + '\n')
open(f'{OUT}/lag_rule_splits.md', 'w').write(tS + '\n')
P('\nTABLE A\n' + tA + '\n\nREPLACEMENT\n' + tR + '\n\nLAG-RULE SPLITS\n' + tS + '\n\nTABLE B\n' + tB)
P('\nreference: lag rule 85', f'{y[LRm].mean():+.3f}', '; lag alone', int(LAGm.sum()), f'{y[LAGm].mean():+.3f}')
# =================================================================== pre-registered diagnostics (descriptive)
diag = []
# D1: trade A signals using the cutoff day's own delivery file (published after the cutoff close: NOT tradable)
A_c0 = A.copy()
for c in ['ACC', 'DQR', 'DPL', 'PR5', 'rank_ACC', 'rank_DQR', 'rank_DPL']:
    A_c0[c] = A[c + '_c0']
A_c0['rank_DP60'] = A.rank_DP60
MC0 = a_masks(A_c0)
for t, s_, lab in A_TESTS:
    r = describe_a(t, MC0[t])
    diag.append(dict(diag='D1_cutoff_day_file_not_tradable', test=t, n=r['n'], avg=r.get('avg'), net=r.get('net'),
                     gain=r.get('excess'), gain_h1=r.get('excess_h1'), gain_h2=r.get('excess_h2')))
# D2: DPK split with a point-in-time threshold = median DPK of all plain winners of EARLIER quarters (qn >= 1)
medW = D[mW1].groupby('qn').DPK.apply(list)
prior = {}
acc_ = []
for q in sorted(D.qn.unique()):
    prior[q] = np.median(acc_) if acc_ else np.nan
    acc_ += medW.get(q, [])
thr = D.qn.map(prior).to_numpy(float)
for lab, pool in (('W', Wm), ('WR', WRm)):
    par = pool & TRj[1] & D.DPK.notna().to_numpy() & np.isfinite(thr)
    v = XB[1]
    pm = pd.Series(v[par]).groupby(QN[par]).mean()
    for side, sg in (('HI', D.DPK.to_numpy() >= thr), ('LO', D.DPK.to_numpy() < thr)):
        si = par & sg
        dp_ = v[si] - pm.reindex(QN[si]).to_numpy()
        diag.append(dict(diag='D2_DPK_prior_quarters_median', test=f'{lab}_DPK_{side}', n=int(si.sum()),
                         avg=v[si].mean(), net=v[si].mean(), gain=dp_.mean(), gain_h1=dp_[QN[si] <= 13].mean(),
                         gain_h2=dp_[QN[si] >= 14].mean()))
# D3: cost of waiting for the delivery file: winners entered at k, k+1, k+2 (results and quiet days)
for lab, pool, qpool in (('W', Wm, QW), ('WR', WRm, QWR)):
    for off in (0, 1, 2):
        mm = pool & TRj[off]
        diag.append(dict(diag='D3_entry_delay', test=f'{lab}_entry_k+{off}', n=int(mm.sum()), avg=XB[off][mm].mean(),
                         net=XB[off][mm].mean(), gain=np.nan, gain_h1=XB[off][mm & (QN <= 13)].mean(),
                         gain_h2=XB[off][mm & (QN >= 14)].mean()))
        qm = qpool & QT[off]
        diag.append(dict(diag='D3_entry_delay_quiet', test=f'quiet_{lab}_entry_k+{off}', n=int(qm.sum()),
                         avg=QX[off][qm].mean(), net=QX[off][qm].mean(), gain=np.nan, gain_h1=np.nan, gain_h2=np.nan))
# D4: XN-tercile control for any WORKS / WATCH B test
for r in main[(main.trade == 'B') & main.verdict.isin(['WORKS', 'WATCH'])].itertuples():
    name, lab, fe, off, sig, par = [t for t in B_TESTS if t[0] == r.test][0]
    v = XB[off]
    xn = D.XN.to_numpy(float)
    tt = np.full(len(D), -1)
    tt[np.where(par)[0]] = pd.qcut(pd.Series(xn[par]), 3, labels=False).to_numpy()
    cell = QN * 10 + tt
    pm = pd.Series(v[par]).groupby(cell[par]).mean()
    dp_ = v[sig] - pm.reindex(cell[sig]).to_numpy()
    diag.append(dict(diag='D4_XN_tercile_control', test=r.test, n=int(sig.sum()), avg=v[sig].mean(), net=v[sig].mean(),
                     gain=np.nanmean(dp_), gain_h1=np.nanmean(dp_[QN[sig] <= 13]), gain_h2=np.nanmean(dp_[QN[sig] >= 14])))
DG = pd.DataFrame(diag)
DG.to_csv(f'{OUT}/diagnostics.csv', index=False, float_format='%.4f')
P('\nDIAGNOSTICS (descriptive; cannot change a verdict)')
P(DG.round(3).to_string(index=False))
P('VERDICTS:', main.verdict.value_counts().to_dict())
P(main[main.luck_p < 0.05][['test', 'n', 'avg', 'excess_or_dpar', 'luck_p', 'holm_p', 'DiD', 'placebo_p', 'verdict',
                            'fails']].round(4).to_string(index=False))
LOG.close()
