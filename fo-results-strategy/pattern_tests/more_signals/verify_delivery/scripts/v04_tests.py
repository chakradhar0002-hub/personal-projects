#!/usr/bin/env python3
"""Verifier: recompute the 26 main tests, the lag-rule splits and the replacement tests of the delivery family from
own features (own_feat.csv from v03_features.py), with own luck p and Holm. usage: python3 -P v04_tests.py SCRATCH OUTDIR
"""
import sys

import numpy as np
import pandas as pd

SP, OUT = sys.argv[1], sys.argv[2]
D = f'{SP}/more_signals/delivery'
LOG = open(f'{OUT}/v04_tests.log', 'w')


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.write(s + '\n')


f = pd.read_csv(f'{OUT}/own_feat.csv')
f = f[f.three_day.notna()].reset_index(drop=True) if False else f
QN = f.qn.to_numpy(int)
H1 = QN <= 13
y3 = f.three_day.to_numpy(float)           # project convention (sum of the three daily returns), %
okA = np.isfinite(y3)
rng = np.random.default_rng(20261011)
NPERM = 20000

# ---------------------------------------------------------------- trade A
qmean = pd.Series(y3).groupby(QN).transform('mean').to_numpy()


def perm_p_A(mask, sign):
    """within-quarter permutation of three_day among all F&O results; statistic = mean signed P&L of the picks"""
    obs = np.nanmean(sign * y3[mask])
    cnt = 0
    tot = 0
    for q in np.unique(QN[mask]):
        pass
    # build per-quarter samples: sum of k random picks
    sims = np.zeros(NPERM)
    for q in np.unique(QN):
        pool = y3[(QN == q) & okA]
        kq = int((mask & (QN == q) & okA).sum())
        if kq == 0:
            continue
        idx = np.argsort(rng.random((NPERM, len(pool))), axis=1)[:, :kq]
        sims += (sign * pool[idx]).sum(1)
    sims /= (mask & okA).sum()
    return (1 + np.sum(sims >= obs - 1e-12)) / (1 + NPERM)


def summ_A(lab, mask, sign, cost=0.17):
    m = mask & okA
    pnl = sign * y3[m]
    ex = sign * (y3[m] - qmean[m])
    net = pnl - cost
    qq = QN[m]
    qnet = pd.Series(net).groupby(qq).mean()
    srt = np.argsort(-pnl)
    wo5 = np.delete(net, srt[:5]).mean()
    wo5x = np.delete(ex, srt[:5]).mean()
    h1, h2 = H1[m], ~H1[m]
    return dict(test=lab, n=int(m.sum()), gross=pnl.mean(), net=net.mean(), excess=ex.mean(),
                q_pos=f'{int((qnet > 0).sum())}/{len(qnet)}', n_h1=int(h1.sum()), net_h1=net[h1].mean(),
                ex_h1=ex[h1].mean(), n_h2=int(h2.sum()), net_h2=net[h2].mean(), ex_h2=ex[h2].mean(),
                net_wo5=wo5, ex_wo5=wo5x, luck_p=perm_p_A(mask, sign))


r = f
A_TESTS = [
    ('A01', r.ACC > 0, 1), ('A02', r.rank_ACC > 80, 1), ('A03', r.rank_ACC <= 20, -1), ('A04', r.DQR >= 1.5, 1),
    ('A05', r.rank_DQR > 80, 1), ('A06', r.rank_DPL > 80, 1), ('A07', (r.PR5 < 0) & (r.ACC > 0), 1),
    ('A08', (r.PR5 > 0) & (r.ACC > 0), 1), ('A09', (r.PR5 > 0) & (r.ACC < 0), -1), ('A10', r.rank_DP60 > 80, 1)]
rows = []
for lab, msk, sg in A_TESTS:
    rows.append(summ_A(lab, msk.to_numpy(bool), sg))
TA = pd.DataFrame(rows)

# ---------------------------------------------------------------- trade B
XN = f.XN.to_numpy(float)
Wm = (XN > 4)
WRm = Wm & (f.cut_rsi14.to_numpy(float) > 50)
TR = {0: f.tradable_B.to_numpy(bool), 1: f.trad_k1.to_numpy(bool), 2: f.trad_k2.to_numpy(bool)}
YB = {0: f.vsN_net_H20.to_numpy(float), 1: f.vsN_net_k1.to_numpy(float), 2: f.vsN_net_k2.to_numpy(float)}
mW1 = Wm & TR[1] & f.DPK.notna().to_numpy()
dpk_med = f.qn.map(f[mW1].groupby('qn').DPK.median()).to_numpy(float)
DPK = f.DPK.to_numpy(float)
FEAT = {
    'ACCPRE_HI': (0, f.ACC_pre.to_numpy() > 0, f.ACC_pre.notna().to_numpy()),
    'ACCPRE_LO': (0, f.ACC_pre.to_numpy() <= 0, f.ACC_pre.notna().to_numpy()),
    'DPK_HI': (1, DPK >= dpk_med, np.isfinite(DPK) & np.isfinite(dpk_med)),
    'DPK_LO': (1, DPK < dpk_med, np.isfinite(DPK) & np.isfinite(dpk_med)),
    'DQK_HI': (1, f.DQK.to_numpy() >= 3, f.DQK.notna().to_numpy()),
    'DQK_LO': (1, f.DQK.to_numpy() < 3, f.DQK.notna().to_numpy()),
    'DPK1_HI': (2, f.DPK1.to_numpy() > 0, f.DPK1.notna().to_numpy()),
    'DPK1_LO': (2, f.DPK1.to_numpy() <= 0, f.DPK1.notna().to_numpy())}


def b_stats(lab, pool, lag, sig, known):
    par = pool & TR[lag] & known & np.isfinite(YB[lag])
    m = par & sig
    y = YB[lag]
    pm = pd.Series(y[par]).groupby(QN[par]).mean()
    dpar = y[m] - pd.Series(QN[m]).map(pm).to_numpy()
    obs = y[m].mean()
    sims = np.zeros(NPERM)
    for q in np.unique(QN[m]):
        pl = y[par & (QN == q)]
        kq = int((m & (QN == q)).sum())
        idx = np.argsort(rng.random((NPERM, len(pl))), axis=1)[:, :kq]
        sims += pl[idx].sum(1)
    sims /= m.sum()
    p = (1 + np.sum(sims >= obs - 1e-12)) / (1 + NPERM)
    srt = np.argsort(-y[m])
    h1 = H1[m]
    qv = pd.Series(y[m]).groupby(QN[m]).mean()
    return dict(test=lab, entry=f'k+{lag}', n=int(m.sum()), parent_n=int(par.sum()), net=obs, parent=y[par].mean(),
                gain=dpar.mean(), q_pos=f'{int((qv > 0).sum())}/{len(qv)}', n_h1=int(h1.sum()), net_h1=y[m][h1].mean(),
                gain_h1=dpar[h1].mean(), n_h2=int((~h1).sum()), net_h2=y[m][~h1].mean(), gain_h2=dpar[~h1].mean(),
                net_wo5=np.delete(y[m], srt[:5]).mean(), gain_wo5=np.delete(dpar, srt[:5]).mean(), luck_p=p)


rows = []
for pl_lab, pool in [('W', Wm), ('WR', WRm)]:
    for fl, (lag, sig, known) in FEAT.items():
        rows.append(b_stats(f'{pl_lab}_{fl}', pool, lag, sig, known))
TB = pd.DataFrame(rows)

# Holm over 26
allp = pd.concat([TA[['test', 'luck_p']], TB[['test', 'luck_p']]], ignore_index=True)
o = np.argsort(allp.luck_p.to_numpy())
m_ = len(allp)
adj = np.empty(m_)
run = 0
for rank_, ix in enumerate(o):
    run = max(run, (m_ - rank_) * allp.luck_p.iloc[ix])
    adj[ix] = min(1, run)
allp['holm'] = adj
TA = TA.merge(allp, on=['test', 'luck_p'])
TB = TB.merge(allp, on=['test', 'luck_p'])
th = pd.read_csv(f'{D}/tests.csv')
pd.set_option('display.width', 250)
P('TRADE A - own recomputation (three_day = project convention) vs study')
TA2 = TA.merge(th[['test', 'n', 'net', 'excess', 'luck_p', 'holm_p']], on='test', suffixes=('', '_study'))
P(TA2.round(4).to_string(index=False))
P('\nTRADE B - own recomputation vs study')
TB2 = TB.merge(th[['test', 'n', 'avg', 'd_par', 'luck_p', 'holm_p']], on='test', suffixes=('', '_study'))
P(TB2.round(4).to_string(index=False))
TA.to_csv(f'{OUT}/own_tests_A.csv', index=False)
TB.to_csv(f'{OUT}/own_tests_B.csv', index=False)

# ---------------------------------------------------------------- lag rule splits and replacement
lagm = (f.in_fo_events == True).to_numpy() & (f.lag21.to_numpy() < -10) & (f.vol_ratio_5_60.to_numpy() >= 1.0)
repo = pd.read_csv(__import__('os').environ.get('REPO_ROOT', '.') + '/results/lag10_volume/trades.csv')
rk = set(zip(repo.symbol, repo.qn))
mine_k = set(zip(f.symbol[lagm], f.qn[lagm]))
P(f'\nlag rule: own {lagm.sum()} trades, repo {len(rk)}, same set {mine_k == rk}; mean three_day {y3[lagm].mean():.3f}')
ra1 = (f.in_fo_events == True).to_numpy() & (f.lag21.to_numpy() < -10) & (f.DQR.to_numpy() >= 1.0)
ra2 = (f.in_fo_events == True).to_numpy() & (f.lag21.to_numpy() < -10) & (f.ACC.to_numpy() > 0)
for lab, msk in [('RA1', ra1), ('RA2', ra2)]:
    s = summ_A(lab, msk, 1)
    P(f"{lab}: n {s['n']} gross {s['gross']:+.3f} net {s['net']:+.3f} h1 {s['net_h1']:+.2f} h2 {s['net_h2']:+.2f} "
      f"wo5 {s['net_wo5']:+.2f} q+ {s['q_pos']} luck p {s['luck_p']:.4f}")
P(f'RA1 & lag rule {int((ra1 & lagm).sum())} avg {y3[ra1 & lagm].mean():+.3f}; RA1 only {int((ra1 & ~lagm).sum())} avg '
  f'{y3[ra1 & ~lagm].mean():+.3f}; lag only {int((~ra1 & lagm).sum())} avg {y3[~ra1 & lagm].mean():+.3f}')
P('\nlag-rule splits (IN avg, OUT avg, n)')
for lab, msk in [('LS1 ACC>0', f.ACC > 0), ('LS2 DQR>=1', f.DQR >= 1), ('LS3 DQR>=1.5', f.DQR >= 1.5),
                 ('LS4 DPL>0', f.DPL > 0), ('LS5 rank_ACC>80', f.rank_ACC > 80),
                 ('LS6 PR5<0&ACC>0', (f.PR5 < 0) & (f.ACC > 0)), ('LS7 rank_DP60>50', f.rank_DP60 > 50)]:
    mm = msk.to_numpy(bool)
    a, b = y3[lagm & mm], y3[lagm & ~mm]
    diff = a.mean() - b.mean()
    lab_all = np.r_[np.ones(len(a)), np.zeros(len(b))]
    yy = np.r_[a, b]
    pr = np.random.default_rng(11)
    sims = np.array([yy[pr.permutation(lab_all) == 1].mean() - yy[pr.permutation(lab_all) == 0].mean() if False else 0
                     for _ in range(1)])
    cnt = 0
    for _ in range(20000):
        pp = pr.permutation(len(yy))
        d_ = yy[pp[:len(a)]].mean() - yy[pp[len(a):]].mean()
        cnt += abs(d_) >= abs(diff) - 1e-12
    P(f'  {lab:18s} IN {len(a):3d} {a.mean():+.2f}  OUT {len(b):3d} {b.mean():+.2f}  IN-OUT {diff:+.2f}  perm p {(cnt + 1) / 20001:.4f}')
LOG.close()
