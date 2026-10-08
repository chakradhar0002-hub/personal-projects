#!/usr/bin/env python3
"""ADDED AFTER (see PREREGISTRATION.txt, X1-X3). Reads only trades.csv / results_tests.csv from this folder."""
import os
import numpy as np
import pandas as pd
from scipy import stats as sst

HERE = os.path.dirname(os.path.abspath(__file__))
NREP = 10000
rng = np.random.default_rng(20261009)
WINS = [(e, h) for e in (0, 1) for h in (5, 10, 20)]
LOG = open(os.path.join(HERE, 'addendum.log'), 'w')


def P_(s):
    print(s); LOG.write(s + '\n'); LOG.flush()


t = pd.read_csv(os.path.join(HERE, 'trades.csv'))
assert t.tradable.all()
RAW = t[[f'raw_E{e}H{h}' for e, h in WINS]].values
NIF = t[[f'nif_E{e}H{h}' for e, h in WINS]].values
VSN = RAW - NIF
QN = t.qn.values
FIRST = QN <= 13
XN = t.XN
E_PAT = t.rq_pat_yoy_pct.notna()
E_SUR = t.rq_pat_surprise_vs_trend_pp.notna() & t.surp_P80.notna()
E_M = t.MCHG.notna()
E_P2L = t.rq_profit_to_loss_yoy.notna()
ALLT = pd.Series(True, index=t.index)
FLIP = [('S1_WEAK', E_PAT, ALLT), ('S2_MARGIN_DN', E_M, ALLT), ('S3_PROFIT2LOSS', E_P2L, ALLT),
        ('S4_SURP_BOT', E_SUR, ALLT), ('I2_WEAK_XNpos', E_PAT, XN > 0), ('I5_SURPBOT_XNpos', E_SUR, XN > 0)]
# note: 6 short signals listed in the brief + S4; the 7th short-type test family member is none (S1..S4, I2, I5 = 6)


def luck(si, pi, vals):
    tot = np.zeros((NREP, vals.shape[1])); kt = 0
    for q in np.unique(QN[si]):
        k = int((QN[si] == q).sum()); pq = pi[QN[pi] == q]; n = len(pq); v = vals[pq]
        if k == n:
            tot += v.sum(0)
        else:
            for c0 in range(0, NREP, 2000):
                c1 = min(NREP, c0 + 2000)
                pick = np.argpartition(rng.random((c1 - c0, n)), k - 1, axis=1)[:, :k]
                tot[c0:c1] += v[pick].sum(1)
        kt += k
    return tot / kt


vsn_long = VSN - 0.19
raw_long = RAW - 0.17
rows = []
for name, el, bu in FLIP:
    sig = t[name].values.astype(bool)
    si = np.where(sig)[0]
    pi = np.where(el.values & bu.values)[0]
    rp = luck(si, pi, vsn_long)
    for j, (e, h) in enumerate(WINS):
        x = vsn_long[si, j]; q = QN[si]; fh = FIRST[si]
        qm = pd.Series(x).groupby(q).mean()
        tq = qm.mean() / (qm.std(ddof=1) / np.sqrt(len(qm)))
        srt = np.sort(x)
        rows.append(dict(test=name + '_FLIPPED_LONG', entry=f'E{e}', H=h, n=len(x), raw_net=raw_long[si, j].mean(),
                         vsN_net=x.mean(), nq=len(qm), q_pos=int((qm > 0).sum()), t_q=tq,
                         vsN_net_first14=x[fh].mean(), vsN_net_last8=x[~fh].mean(),
                         raw_net_first14=raw_long[si, j][fh].mean(), raw_net_last8=raw_long[si, j][~fh].mean(),
                         vsN_net_wo_best5=srt[:-5].mean(), pool_vsN_net=vsn_long[pi, j].mean(),
                         p_luck=(1 + (rp[:, j] >= x.mean()).sum()) / (1 + NREP)))
a = pd.DataFrame(rows)
main = pd.read_csv(os.path.join(HERE, 'results_tests.csv'))
allp = np.r_[main.p_luck.values, a.p_luck.values]


def holm(p):
    o = np.argsort(p); m = len(p); adj = np.empty(m); run = 0
    for r, i in enumerate(o):
        run = max(run, (m - r) * p[i]); adj[i] = min(1, run)
    return adj


h = holm(allp)
a['p_luck_holm126'] = h[len(main):]
main_h126 = h[:len(main)]
P_(f'X1 note: there are 6 short-type signals (S1-S4, I2, I5) -> 36 flipped tests (the text said 42; 36 is the count).')
P_(f'Holm over {len(allp)} luck p: min adjusted (main) {main_h126.min():.3f}, min adjusted (flipped) {a.p_luck_holm126.min():.3f}')


def verdict(r):
    base = (r.n >= 30) and (r.vsN_net_first14 > 0) and (r.vsN_net_last8 > 0) and (r.t_q >= 2.0) and (r.vsN_net_wo_best5 > 0)
    return 'SURVIVES' if base and r.p_luck_holm126 < 0.05 else ('WATCH' if base and r.p_luck < 0.05 else 'NO')


a['verdict'] = a.apply(verdict, axis=1)
a.to_csv(os.path.join(HERE, 'addendum_flipped.csv'), index=False, float_format='%.4f')
pd.set_option('display.width', 250)
P_('\nX1 FLIPPED SHORT SIGNALS AS LONGS (post hoc):')
P_(a.round(3).to_string(index=False))

# X2 / X3: I3, I6 vs all plain winners
W = (XN > 4).values
P_('\nX2/X3 I3, I6 minus ALL plain winners (same quarter), per-quarter difference of vsN_net means:')
for name in ['I3_STRONG_XN4', 'I6_SURPTOP_XN4']:
    sig = t[name].values.astype(bool)
    for j, (e, h) in enumerate(WINS):
        s = pd.Series(vsn_long[sig, j]).groupby(QN[sig]).mean()
        w = pd.Series(vsn_long[W, j]).groupby(QN[W]).mean()
        d = (s - w.reindex(s.index))
        sr = pd.Series(raw_long[sig, j]).groupby(QN[sig]).mean()
        wr = pd.Series(raw_long[W, j]).groupby(QN[W]).mean()
        dr = (sr - wr.reindex(sr.index))
        tt = d.mean() / (d.std(ddof=1) / np.sqrt(len(d)))
        P_(f'  {name} E{e} H{h}: n={sig.sum()} mean d={d.mean():+.2f} t={tt:.2f} first14 d={d[d.index <= 13].mean():+.2f} '
           f'last8 d={d[d.index >= 14].mean():+.2f} quarters d>0 {int((d > 0).sum())}/{len(d)} | raw d first14 '
           f'{dr[dr.index <= 13].mean():+.2f} last8 {dr[dr.index >= 14].mean():+.2f}')
# per-quarter table for the headline E0 H20
j = WINS.index((0, 20))
pq = pd.DataFrame({'ALL_n': pd.Series(1, index=t.index).groupby(QN).sum(),
                   'ALL_vsN_net': pd.Series(vsn_long[:, j]).groupby(QN).mean(),
                   'WIN_n': pd.Series(W.astype(int)).groupby(QN).sum(),
                   'WIN_vsN_net': pd.Series(vsn_long[W, j]).groupby(QN[W]).mean()})
for name in ['L1_STRONG', 'I3_STRONG_XN4', 'I6_SURPTOP_XN4', 'S1_WEAK', 'I5_SURPBOT_XNpos']:
    sig = t[name].values.astype(bool)
    pq[name + '_n'] = pd.Series(sig.astype(int)).groupby(QN).sum()
    pq[name + '_long_vsN_net'] = pd.Series(vsn_long[sig, j]).groupby(QN[sig]).mean()
pq.to_csv(os.path.join(HERE, 'per_quarter_E0H20_headline.csv'), float_format='%.3f')
P_('\nPer quarter, E0 H20, LONG vsN_net (percent; S1/I5 shown as longs):')
P_(pq.round(2).to_string())
