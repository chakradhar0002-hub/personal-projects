#!/usr/bin/env python3
"""CORPORATE NEWS FLOW family: run exactly the tests of prereg.txt (refuses to run if its sha256 differs from
prereg.sha256).
usage: python3 run_tests.py OUT SP     (OUT = .../more_signals/news; writes only into OUT)
Percent units. Trade A: three_day (close i_cut -> close i_p1), cost 0.17. Trade B: 20-session Nifty-hedged return from
the close of the reaction day k, cost 0.19."""
import hashlib
import sys

import numpy as np
import pandas as pd

OUT, SP = sys.argv[1], sys.argv[2]
DATA = f'{SP}/sector_lab/data'
F = f'{SP}/perf/features'
W_ = f'{OUT}/work'
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
    m = {
        'A01': df.RDCHG > 7, 'A02': df.RDCHG < -7, 'A03': df.LEADCHG <= -7, 'A04': df.LEADCHG >= 7,
        'A05': df.LEAD <= 7, 'A06': df.NEWSR >= 1.5, 'A07': df.NEWSR <= 0.5, 'A08': df.PR30 >= 1,
        'A09': df.ORDER30 >= 1, 'A10': df.ACQ30 >= 1, 'A11': df.CALLPRE == 0, 'A12': df.BIZ_RX > 0,
        'A13': df.BIZ_RX < 0, 'A14': df.PROMBUY90 >= 1, 'A15': df.PROMSELL90 >= 1, 'A16': df.HOLDBUY90 >= 1,
        'A17': df.HOLDSELL90 >= 1,
        # diagnostics D1
        'D1_CRUP90': df.CRUP90 >= 1, 'D1_PROMBUY30': df.PROMBUY30 >= 1, 'D1_PROMSELL30': df.PROMSELL30 >= 1,
    }
    return {k: v.fillna(False).to_numpy(bool) for k, v in m.items()}


A_TESTS = [
    ('A01', -1, 'LATE: results date > 7 days later than the same quarter last year', ['RDCHG'], 'stock-quarter'),
    ('A02', +1, 'EARLY: results date > 7 days earlier than last year', ['RDCHG'], 'stock-quarter'),
    ('A03', -1, 'NOTICE_SHORT: intimation lead time >= 7 days shorter than the stock\'s habit', ['LEADCHG'],
     'stock-quarter'),
    ('A04', +1, 'NOTICE_LONG: lead time >= 7 days longer than habit', ['LEADCHG'], 'stock-quarter'),
    ('A05', -1, 'NOTICE_MIN: lead time <= 7 days (near the legal minimum)', ['LEAD'], 'stock-quarter'),
    ('A06', +1, 'NEWS_HI: 30-day news flow >= 1.5x the stock\'s norm', ['NEWSR'], 'same feature'),
    ('A07', -1, 'NEWS_LO: 30-day news flow <= 0.5x norm (silence)', ['NEWSR'], 'same feature'),
    ('A08', +1, 'PRESS: press release(s) in the 30 days before the cutoff', ['PR30'], 'same feature'),
    ('A09', +1, 'ORDER: order win(s) in the 30 days before', ['ORDER30'], 'same feature'),
    ('A10', -1, 'ACQ: acquisition announcement(s) in the 30 days before', ['ACQ30'], 'same feature'),
    ('A11', -1, 'NOCALL: no earnings call / analyst meet announced in the 21 days before', ['CALLPRE'],
     'stock-quarter'),
    ('A12', +1, 'BIZ_UP: business update(s) in 45 days, market reaction > 0', ['BIZ_N45'], 'same feature'),
    ('A13', -1, 'BIZ_DOWN: business update(s), market reaction < 0', ['BIZ_N45'], 'same feature'),
    ('A14', +1, 'PROM_BUY: promoter acquisition (SAST Reg 29) in the 90 days before', ['PROMBUY90'], 'same feature'),
    ('A15', -1, 'PROM_SELL: promoter sale in the 90 days before', ['PROMSELL90'], 'same feature'),
    ('A16', +1, 'HOLD_BUY: large non-promoter holder buying in 90 days', ['HOLDBUY90'], 'same feature'),
    ('A17', -1, 'HOLD_SELL: large non-promoter holder selling in 90 days', ['HOLDSELL90'], 'same feature'),
]
A_SIGN = {t: s for t, s, _, _, _ in A_TESTS}
A_LABEL = {t: l for t, _, l, _, _ in A_TESTS}
A_AVAIL = {t: c for t, _, _, c, _ in A_TESTS}
A_PLTYPE = {t: p for t, _, _, _, p in A_TESTS}
D1 = [('D1_CRUP90', +1, 'credit-rating upgrade in the 90 days before (diagnostic)'),
      ('D1_PROMBUY30', +1, 'promoter acquisition in the 30 days before (diagnostic)'),
      ('D1_PROMSELL30', -1, 'promoter sale in the 30 days before (diagnostic)')]
for t, s, l in D1:
    A_SIGN[t], A_LABEL[t] = s, l

B_FEATS = {
    'EVENT_K': (lambda d: d.EVENT_K >= 1, ['EVENT_K'], 'other material news on k-1 / k besides the results'),
    'NEWS_LO': (lambda d: d.NEWSR < 1, ['NEWSR'], 'pre-results news flow below the stock\'s norm (NEWSR < 1)'),
    'NEWS_HI': (lambda d: d.NEWSR >= 1, ['NEWSR'], 'pre-results news flow at/above norm (NEWSR >= 1)'),
    'NOCALL': (lambda d: d.CALLPRE == 0, ['CALLPRE'], 'no call / analyst meet announced before the results'),
    'CALL': (lambda d: d.CALLPRE >= 1, ['CALLPRE'], 'call / analyst meet announced before the results'),
    'EARLY': (lambda d: d.RDCHG < -7, ['RDCHG'], 'early reporter (> 7 days earlier than last year)'),
    'LATE': (lambda d: d.RDCHG > 7, ['RDCHG'], 'late reporter (> 7 days later; worse expected)'),
    'PROMBUY90': (lambda d: d.PROMBUY90 >= 1, ['PROMBUY90'], 'promoter acquisition in the 90 days before the cutoff'),
    'HOLDBUY90': (lambda d: d.HOLDBUY90 >= 1, ['HOLDBUY90'], 'large holder buying in the 90 days before the cutoff'),
    'BUSY': (lambda d: d.BUSY_K >= 15, ['BUSY_K'], '>= 15 results share the reaction day (distraction)'),
    'ORDER_K': (lambda d: d.ORDER_K >= 1, ['ORDER_K'], 'order win on k-1 / k'),
}
B_MAIN = [('W', 'EVENT_K'), ('W', 'NEWS_LO'), ('W', 'NEWS_HI'), ('W', 'NOCALL'), ('W', 'CALL'), ('W', 'EARLY'),
          ('WR', 'NEWS_LO'), ('WR', 'NEWS_HI'), ('WR', 'NOCALL'), ('WR', 'CALL')]
B_DIAG = [('WR', 'EVENT_K'), ('WR', 'EARLY'), ('W', 'LATE'), ('W', 'PROMBUY90'), ('WR', 'PROMBUY90'),
          ('W', 'HOLDBUY90'), ('WR', 'HOLDBUY90'), ('W', 'BUSY'), ('WR', 'BUSY'), ('W', 'ORDER_K')]
B_PLTYPE = {'EVENT_K': 'same feature (quiet day k-1/k)', 'NEWS_LO': 'same feature (k-2)',
            'NEWS_HI': 'same feature (k-2)', 'NOCALL': 'stock-type (qn_prev)', 'CALL': 'stock-type (qn_prev)',
            'EARLY': 'stock-type (qn_prev)'}

# =================================================================== TRADE A
fr = pd.read_csv(f'{W_}/feat_results.csv')
out = pd.read_csv(f'{F}/outcomes.csv')
D = fr.merge(out[['symbol', 'qn', 'three_day', 'tradable_B', 'raw_H20', 'nifty_H20', 'vsN_H20', 'vsN_net_H20']],
             on=['symbol', 'qn'], how='left', validate='1:1')
assert len(D) == 3280
PERIOD = D.groupby('qn').results_for.first()
A = D[D.three_day.notna()].reset_index(drop=True)
P(f'TRADE A: F&O results with three_day {len(A)} of 3280')
y = A.three_day.to_numpy(float)
qn = A.qn.to_numpy(int)
N = len(A)
QS = np.unique(qn)
QMEAN = pd.Series(y).groupby(qn).mean()
P(f'  all F&O results mean three_day {y.mean():+.3f}% (documented +0.04%)')
MA = a_masks(A)
LRm = ((A.in_fo_events == True) & (A.lag21 < -10) & (A.vol_ratio_5_60 >= 1.0)).to_numpy(bool)
P(f'  lag rule trades {LRm.sum()}, mean {y[LRm].mean():+.3f}% [documented 85, +2.13%]')
assert LRm.sum() == 85 and abs(y[LRm].mean() - 2.13) < 0.01
rp = pd.read_csv(__import__('os').environ.get('REPO_ROOT', '.') + '/results/lag10_volume/trades.csv',
                 usecols=['symbol', 'qn'])
assert set(zip(rp.symbol, rp.qn)) == set(zip(A.symbol[LRm], A.qn[LRm]))
IDS_A = [t for t, *_ in A_TESTS] + [t for t, _, _ in D1]


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
    r['quarters'] = f'{q.min()}-{q.max()}'
    for hh, hm in (('h1', q <= 13), ('h2', q >= 14)):
        r[f'n_{hh}'] = int(hm.sum())
        r[f'net_{hh}'] = pnl[hm].mean() - CA if hm.any() else np.nan
        r[f'excess_{hh}'] = (pnl[hm] - base[hm]).mean() if hm.any() else np.nan
    o = np.argsort(-pnl)[:5]
    r['net_wo_best5'] = np.delete(pnl, o).mean() - CA if n > 5 else np.nan
    r['excess_wo_best5'] = (np.delete(pnl, o) - np.delete(base, o)).mean() if n > 5 else np.nan
    return r


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
main_ix = [IDS_A.index(t) for t, *_ in A_TESTS]
maxzA = ZA[:, main_ix].max(1)
MAXT = {IDS_A[k]: (1 + (maxzA >= zA[k] - 1e-12).sum()) / (1 + B_PERM) for k in main_ix}
P(f'  maxT (A, {len(main_ix)} tests): null 95th pct of max z {np.percentile(maxzA, 95):.2f}')

# placebo A
pl = pd.read_csv(f'{W_}/feat_placeboA.csv.gz')
plo = pd.read_csv(f'{SP}/ta/build/placebo_ta.csv.gz', usecols=['symbol', 'i', 'in_fo', 'qn_next', 'three_day'])
plo = plo[(plo.in_fo == True) & plo.qn_next.notna()][['symbol', 'i', 'three_day']]
pl = pl.merge(plo, on=['symbol', 'i'], how='left', validate='1:1')
pl = pl[pl.three_day.notna()].reset_index(drop=True)
py = pl.three_day.to_numpy(float)
pq_ = pl.qn_next.to_numpy(int)
PL_QMEAN = pd.Series(py).groupby(pq_).mean()
PMA = a_masks(pl)
P(f'  placebo A days {len(pl)}, mean 3-day {py.mean():+.3f}%')
rngp = np.random.default_rng(7)


def placebo_a(t):
    s = A_SIGN[t]
    pm = PMA[t]
    if pm.sum() == 0:
        return {'pl_n': 0}
    pools = {q: s * py[pm & (pq_ == q)] for q in np.unique(pq_[pm])}
    m = MA[t]
    q_tr = qn[m]
    keep = np.isin(q_tr, list(pools))
    pnl = s * y[m][keep]
    qk = q_tr[keep]
    n = int(keep.sum())
    if n == 0:
        return {'pl_n': int(pm.sum())}
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
            'placebo_p': (1 + (e_draw >= e_res - 1e-12).sum()) / (1 + B_PL), 'pl_trades_used': n}


rowsA = []
for t in IDS_A:
    r = describe_a(t, MA[t])
    r['luck_p'] = LUCK[t]
    r['maxT_within'] = MAXT.get(t, np.nan)
    r['placebo_type'] = A_PLTYPE.get(t, 'same feature')
    r.update(placebo_a(t))
    rowsA.append(r)
TA = pd.DataFrame(rowsA)

# =================================================================== TRADE B
ses = pd.read_csv(f'{DATA}/sessions.csv')
days = ses.day.tolist()
T = len(days)
ret = pd.read_csv(f'{DATA}/returns.csv', index_col=0)
SYM = {s: j for j, s in enumerate(ret.columns)}
R = ret.to_numpy(float)
PX = np.cumprod(1.0 + np.nan_to_num(R), axis=0)
CVALID = np.cumsum(~np.isnan(R), axis=0)
NIFTY = pd.read_csv(f'{DATA}/index_close.csv', index_col=0)['Nifty 50'].to_numpy(float)


def hedged(j_sym, e):
    """20-session Nifty-hedged gross % from close e; tradable flag (e+21 exists, <= 2 blanks in e+1..e+21)."""
    okk = e + 21 <= T - 1
    ee = np.where(okk, e, 0)
    okk &= (21 - (CVALID[np.minimum(ee + 21, T - 1), j_sym] - CVALID[ee, j_sym])) <= 2
    g = ((PX[np.minimum(ee + 20, T - 1), j_sym] / PX[ee, j_sym] - 1) -
         (NIFTY[np.minimum(ee + 20, T - 1)] / NIFTY[ee] - 1)) * 100
    return np.where(okk, g, np.nan), okk


jD = D.symbol.map(SYM).to_numpy(int)
VG, TRk = hedged(jD, D.i_react.to_numpy(int))
tb = (D.tradable_B == True).to_numpy()
chk = np.abs(VG[tb] - D.vsN_H20.to_numpy(float)[tb])
P(f'\nTRADE B: tradable_B {tb.sum()}; own hedged return vs outcomes vsN_H20: max |diff| {np.nanmax(chk):.2e}; '
  f'own tradable flag == tradable_B on {np.mean(TRk == tb) * 100:.2f}%')
assert np.nanmax(chk) < 1e-3
XB = D.vsN_net_H20.to_numpy(float)
Wm = (D.W == True).to_numpy() & tb
WRm = Wm & (D.cut_rsi14 > 50).to_numpy()
QN = D.qn.to_numpy(int)
P(f'  W {Wm.sum()} mean vsN_net {np.nanmean(XB[Wm]):+.3f}% [documented +1.45]; WR {WRm.sum()} '
  f'{np.nanmean(XB[WRm]):+.3f}% [documented +2.42]')
assert Wm.sum() == 392 and WRm.sum() == 232
POOL = {'W': Wm, 'WR': WRm}


def b_sets(lst):
    o = []
    for pool_lab, fe in lst:
        fn, cols, lab = B_FEATS[fe]
        elig = POOL[pool_lab] & D[cols].notna().all(1).to_numpy()
        sig = elig & fn(D).fillna(False).to_numpy(bool)
        o.append((f'{pool_lab}_{fe}', pool_lab, fe, sig, elig))
    return o


B_TESTS = b_sets(B_MAIN)
B_DIAGS = b_sets(B_DIAG)


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


def describe_b(name, lab, fe, sig, par):
    v = XB
    si, pi = np.where(sig)[0], np.where(par)[0]
    n = len(si)
    r = dict(test=name, trade='B', pool=lab, feature=fe, entry='k', label=B_FEATS[fe][2], n=n, parent_n=len(pi))
    if n == 0:
        return r, si, np.array([])
    pm = pd.Series(v[pi]).groupby(QN[pi]).mean()
    dpar = v[si] - pm.reindex(QN[si]).to_numpy()
    x = v[si]
    q = QN[si]
    f14, l8 = q <= 13, q >= 14
    sq = pd.Series(x).groupby(q).mean()
    keep = np.ones(n, bool)
    keep[np.argsort(-x)[:5]] = False
    r.update(avg=x.mean(), parent_avg=v[pi].mean(), d_par=dpar.mean(), q_with=len(sq),
             q_pos=int((sq > 0).sum()), n_h1=int(f14.sum()), net_h1=x[f14].mean() if f14.any() else np.nan,
             dpar_h1=dpar[f14].mean() if f14.any() else np.nan, n_h2=int(l8.sum()),
             net_h2=x[l8].mean() if l8.any() else np.nan, dpar_h2=dpar[l8].mean() if l8.any() else np.nan,
             net_wo_best5=x[keep].mean() if n > 5 else np.nan, dpar_wo_best5=dpar[keep].mean() if n > 5 else np.nan,
             t_q_dpar=tq_(pd.Series(dpar).groupby(q).mean()))
    draws = luck_b(si, pi, v)
    r['luck_p'] = (1 + (draws >= x.mean() - 1e-12).sum()) / (1 + NDRAW_B)
    return r, si, dpar


rowsB, pqB, tradesB = [], [], []
for name, lab, fe, sig, par in B_TESTS:
    r, si, dpar = describe_b(name, lab, fe, sig, par)
    rowsB.append(r)
    pi = np.where(par)[0]
    pm = pd.Series(XB[pi]).groupby(QN[pi]).mean()
    for qq in sorted(set(QN[pi])):
        mq = QN[si] == qq
        pqB.append(dict(test=name, qn=qq, results_for=PERIOD[qq], n=int(mq.sum()),
                        avg=XB[si][mq].mean() if mq.any() else np.nan, parent_n=int((QN[pi] == qq).sum()),
                        parent_avg=pm.get(qq, np.nan)))
    for i_, dd in zip(si, dpar):
        tradesB.append(dict(test=name, symbol=D.symbol[i_], qn=QN[i_], results_for=D.results_for[i_],
                            XN=D.XN[i_], cut_rsi14=D.cut_rsi14[i_], feature=D[B_FEATS[fe][1][0]][i_],
                            vsN_net=XB[i_], d_par=dd))
TB = pd.DataFrame(rowsB)

# maxT within B: joint permutations within quarter x stratum over rows tradable at k
strat = np.where(WRm, 0, np.where(Wm, 1, 2))
Uix = np.flatnonzero(tb)
block = QN[Uix] * 3 + strat[Uix]
o0 = np.argsort(block, kind='stable')
Uo = Uix[o0]
bs = block[o0]
NTB = len(B_TESTS)
obsB = np.zeros(NTB)
MB = np.zeros((NTB, len(Uo)))
for t, (name, lab, fe, sig, par) in enumerate(B_TESTS):
    s_ = sig[Uo]
    MB[t, s_] = 1.0 / max(1, s_.sum())
    obsB[t] = XB[Uo][s_].mean()
VU = XB[Uo]
permB = np.zeros((NPERM_B, NTB))
for c0 in range(0, NPERM_B, 500):
    c1 = min(NPERM_B, c0 + 500)
    idx = np.argsort(bs[None, :] + rngb.random((c1 - c0, len(bs))), axis=1)
    permB[c0:c1] = VU[idx] @ MB.T
mub, sdb = permB.mean(0), permB.std(0, ddof=1)
zB = (obsB - mub) / sdb
maxzB = ((permB - mub) / sdb).max(1)
TB['maxT_within'] = [(1 + (maxzB >= zB[t] - 1e-12).sum()) / (1 + NPERM_B) for t in range(NTB)]
P(f'  maxT (B, {NTB} tests): null 95th pct of max z {np.percentile(maxzB, 95):.2f}; universe rows {len(Uo)}')

# placebo B (quiet days)
qd = pd.read_csv(f'{W_}/feat_placeboB.csv.gz')
qd = qd[qd.no_result_k22 == True].reset_index(drop=True)
QX, QT = hedged(qd.symbol.map(SYM).to_numpy(int), qd.i.to_numpy(int))
QX = QX - CB
QW = (qd.W == True).to_numpy()
QWR = QW & (qd.m2_rsi14 > 50).to_numpy()
QPOOL = {'W': QW, 'WR': QWR}
QM = qd.day.str[:7].to_numpy()
P(f'  quiet winners: n {(QW & QT).sum()} mean {QX[QW & QT].mean():+.3f}%; RSI winners n {(QWR & QT).sum()} '
  f'mean {QX[QWR & QT].mean():+.3f}%')
rngq = np.random.default_rng(17)


def placebo_b(name, lab, fe, dpar_mean, n_tr):
    fn, cols, _ = B_FEATS[fe]
    if not all(c in qd.columns for c in cols):
        return dict(pl_n=0, pl_sig_avg=np.nan, pl_excess=np.nan, DiD=np.nan, placebo_p=np.nan)
    qpool = QPOOL[lab] & QT & qd[cols].notna().all(1).to_numpy()
    qs = qpool & fn(qd).fillna(False).to_numpy(bool)
    v = QX
    pmm = pd.Series(v[qpool]).groupby(QM[qpool]).mean()
    dq = v[qs] - pmm.reindex(QM[qs]).to_numpy()
    res = dict(pl_n=int(qs.sum()), pl_sig_avg=v[qs].mean() if qs.any() else np.nan,
               pl_excess=dq.mean() if qs.any() else np.nan)
    res['DiD'] = dpar_mean - res['pl_excess']
    if qs.sum() >= 2 and n_tr > 0:
        dr = dq[rngq.integers(0, len(dq), size=(B_PL, n_tr))].mean(1)
        res['placebo_p'] = (1 + (dr >= dpar_mean - 1e-12).sum()) / (1 + B_PL)
    else:
        res['placebo_p'] = np.nan
    return res


plB = {}
for name, lab, fe, sig, par in B_TESTS:
    r = TB.loc[TB.test == name].iloc[0]
    plB[name] = placebo_b(name, lab, fe, r.d_par, int(r.n))
for c in ['pl_n', 'pl_sig_avg', 'pl_excess', 'DiD', 'placebo_p']:
    TB[c] = TB.test.map(lambda t: plB[t][c])
TB['placebo_type'] = TB.feature.map(B_PLTYPE)

# =================================================================== family-wide multiple testing
main = pd.concat([TA[TA.test.isin([t for t, *_ in A_TESTS])].assign(excess_or_dpar=lambda d: d.excess),
                  TB.assign(excess_or_dpar=lambda d: d.d_par)], ignore_index=True)
main['holm_p'] = holm(main.luck_p.to_numpy())
main['maxT_family'] = np.minimum(1.0, 2 * main.maxT_within)
main['n_family'] = len(main)
assert len(main) == 27


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

# =================================================================== lag-rule splits
rngs = np.random.default_rng(11)
srows = []
for t, s, lab, cols, _ in A_TESTS:
    av = LRm & A[cols].notna().all(1).to_numpy()
    mk = MA[t]
    yin, yout = y[av & mk], y[av & ~mk]
    r = dict(split=t, label=lab, pred='IN better' if s > 0 else 'IN worse', n_avail=int(av.sum()), n_in=len(yin),
             n_out=len(yout), avg_in=yin.mean() if len(yin) else np.nan, avg_out=yout.mean() if len(yout) else np.nan)
    r['net_in'] = r['avg_in'] - CA
    r['net_out'] = r['avg_out'] - CA
    for hh, hm in (('h1', qn <= 13), ('h2', qn >= 14)):
        a_in, a_out = y[av & mk & hm], y[av & ~mk & hm]
        r[f'n_in_{hh}'], r[f'avg_in_{hh}'] = len(a_in), a_in.mean() if len(a_in) else np.nan
        r[f'n_out_{hh}'], r[f'avg_out_{hh}'] = len(a_out), a_out.mean() if len(a_out) else np.nan
    r['diff'] = r['avg_in'] - r['avg_out']
    r['pred_diff'] = s * r['diff']
    r['tested'] = (len(yin) >= 5) and (len(yout) >= 5)
    if r['tested']:
        ya = y[av]
        k = len(yin)
        sel = np.argsort(rngs.random((B_SPLIT, len(ya))), axis=1)[:, :k]
        s_in = ya[sel].sum(1)
        dperm = s_in / k - (ya.sum() - s_in) / (len(ya) - k)
        r['perm_p_2s'] = (1 + (np.abs(dperm) >= abs(r['diff']) - 1e-12).sum()) / (1 + B_SPLIT)
    else:
        r['perm_p_2s'] = np.nan
    better = yin if s > 0 else yout
    r['better_side'] = 'IN' if s > 0 else 'OUT'
    r['better_net_wo_best5'] = np.sort(better)[::-1][5:].mean() - CA if len(better) > 5 else np.nan
    srows.append(r)
SPL = pd.DataFrame(srows)
tm = SPL.tested.to_numpy(bool)
SPL['holm_p'] = np.nan
SPL.loc[tm, 'holm_p'] = holm(SPL.perm_p_2s[tm].to_numpy())
sg = np.where(SPL.pred == 'IN better', 1, -1)
SPL['separates'] = (tm & (sg * (SPL.avg_in_h1 - SPL.avg_out_h1) > 0) & (sg * (SPL.avg_in_h2 - SPL.avg_out_h2) > 0)
                    & (SPL.holm_p < 0.10) & (SPL.better_net_wo_best5 > 0))
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
    g = A.loc[m, ['symbol', 'qn', 'results_for', 'lag21', 'vol_ratio_5_60', 'RDCHG', 'LEAD', 'LEADCHG', 'NEWS30',
                  'NEWSR', 'PR30', 'ORDER30', 'ACQ30', 'CALLPRE', 'BIZ_RX', 'PROMBUY90', 'PROMSELL90', 'HOLDBUY90',
                  'HOLDSELL90', 'three_day']].copy()
    g.insert(0, 'test', t)
    g['in_lag_rule'] = LRm[m]
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
    L = ['| test | dir | signal (known at 15:00 on the cutoff day) | n | avg gross | net | vs all F&O (excess) | '
         'q+ / q | first14 n, net, excess | last8 n, net, excess | w/o best5 net | luck p | Holm p | maxT p | '
         'placebo (type) n, excess | DiD | placebo p | verdict |', '|' + '---|' * 18]
    for r in df.itertuples():
        pln = int(r.pl_n) if np.isfinite(r.pl_n) else 'n/a'
        L.append(f'| {r.test} | {r.dir} | {r.label} | {r.n} | {fx(r.avg)} | {fx(r.net)} | {fx(r.excess)} | '
                 f'{r.q_pos}/{r.q_with} | {r.n_h1}, {fx(r.net_h1)}, {fx(r.excess_h1)} | {r.n_h2}, {fx(r.net_h2)}, '
                 f'{fx(r.excess_h2)} | {fx(r.net_wo_best5)} | {r.luck_p:.4f} | {fx(r.holm_p, 3, False)} | '
                 f'{fx(r.maxT_family, 3, False)} | ({r.placebo_type}) {pln}, {fx(r.pl_excess)} | '
                 f'{fx(r.DiD)} | {fx(r.placebo_p, 4, False)} | {r.verdict}{" (" + r.fails + ")" if r.fails else ""} |')
    return '\n'.join(L)


def table_b(df):
    L = ['| test | signal (known at 15:00 on reaction day k) | n (parent) | avg vsN_net | parent avg | gain vs parent | '
         'q+ / q | first14 n, net, gain | last8 n, net, gain | w/o best5 net, gain | luck p | Holm p | maxT p | '
         'quiet placebo (type) n, gain | DiD | placebo p | verdict |', '|' + '---|' * 17]
    for r in df.itertuples():
        L.append(f'| {r.test} | {r.label} | {r.n} ({r.parent_n}) | {fx(r.avg)} | {fx(r.parent_avg)} | '
                 f'{fx(r.d_par)} | {r.q_pos}/{r.q_with} | {r.n_h1}, {fx(r.net_h1)}, {fx(r.dpar_h1)} | {r.n_h2}, '
                 f'{fx(r.net_h2)}, {fx(r.dpar_h2)} | {fx(r.net_wo_best5)}, {fx(r.dpar_wo_best5)} | {r.luck_p:.4f} | '
                 f'{fx(r.holm_p, 3, False)} | {fx(r.maxT_family, 3, False)} | ({r.placebo_type}) {int(r.pl_n)}, '
                 f'{fx(r.pl_excess)} | {fx(r.DiD)} | {fx(r.placebo_p, 4, False)} | '
                 f'{r.verdict}{" (" + r.fails + ")" if r.fails else ""} |')
    return '\n'.join(L)


def table_splits(df):
    L = ['| split of the 85 lag-rule trades | prediction | n IN / OUT | IN avg (net) | OUT avg (net) | IN - OUT | '
         'IN first14 n, avg | IN last8 n, avg | OUT first14 avg | OUT last8 avg | better side w/o best5 net | '
         'perm p (2-sided) | Holm p | separates |', '|' + '---|' * 14]
    for r in df.itertuples():
        L.append(f'| {r.split} {r.label} | {r.pred} | {r.n_in} / {r.n_out} | {fx(r.avg_in)} ({fx(r.net_in)}) | '
                 f'{fx(r.avg_out)} ({fx(r.net_out)}) | {fx(r.diff)} | {r.n_in_h1}, {fx(r.avg_in_h1)} | '
                 f'{r.n_in_h2}, {fx(r.avg_in_h2)} | {fx(r.avg_out_h1)} | {fx(r.avg_out_h2)} | '
                 f'{fx(r.better_net_wo_best5)} | {fx(r.perm_p_2s, 4, False) if r.tested else "not tested (<5)"} | '
                 f'{fx(r.holm_p, 3, False)} | {"yes" if r.separates else "no"} |')
    return '\n'.join(L)


tA = table_a(main[main.trade == 'A'])
tB = table_b(main[main.trade == 'B'])
tS = table_splits(SPL)
open(f'{OUT}/table_A.md', 'w').write(tA + '\n')
open(f'{OUT}/table_B.md', 'w').write(tB + '\n')
open(f'{OUT}/lag_rule_splits.md', 'w').write(tS + '\n')
P('\nTABLE A\n' + tA + '\n\nLAG-RULE SPLITS\n' + tS + '\n\nTABLE B\n' + tB)

# =================================================================== pre-registered diagnostics (descriptive)
diag = []
for t, s, lab in D1:
    r = TA[TA.test == t].iloc[0]
    diag.append(dict(diag='D1', test=t, label=lab, n=r.n, avg=r.get('avg'), net=r.get('net'), gain=r.get('excess'),
                     gain_h1=r.get('excess_h1'), gain_h2=r.get('excess_h2'), luck_p=r.luck_p,
                     placebo_DiD=r.get('DiD'), placebo_p=r.get('placebo_p')))
for name, lab, fe, sig, par in B_DIAGS:
    r, si, dpar = describe_b(name, lab, fe, sig, par)
    pb = placebo_b(name, lab, fe, r.get('d_par', np.nan), int(r['n'])) if r['n'] else {}
    diag.append(dict(diag='D2', test=name, label=r['label'], n=r['n'], avg=r.get('avg'), net=r.get('avg'),
                     gain=r.get('d_par'), gain_h1=r.get('dpar_h1'), gain_h2=r.get('dpar_h2'), luck_p=r.get('luck_p'),
                     placebo_DiD=pb.get('DiD'), placebo_p=pb.get('placebo_p'), placebo_n=pb.get('pl_n')))
for r in main[(main.trade == 'A') & main.verdict.isin(['WORKS', 'WATCH'])].itertuples():
    m = MA[r.test]
    diag.append(dict(diag='D4', test=r.test, label='overlap with the 85 lag-rule trades', n=int((m & LRm).sum()),
                     avg=A_SIGN[r.test] * y[m & LRm].mean() if (m & LRm).any() else np.nan))
DG = pd.DataFrame(diag)
DG.to_csv(f'{OUT}/diagnostics.csv', index=False, float_format='%.4f')
P('\nDIAGNOSTICS (descriptive; cannot change a verdict)')
P(DG.round(3).to_string(index=False))
P('VERDICTS:', main.verdict.value_counts().to_dict())
P(main[main.luck_p < 0.05][['test', 'n', 'avg', 'excess_or_dpar', 'luck_p', 'holm_p', 'DiD', 'placebo_p', 'verdict',
                            'fails']].round(4).to_string(index=False))
LOG.close()
