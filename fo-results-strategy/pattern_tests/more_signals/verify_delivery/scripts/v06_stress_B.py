#!/usr/bin/env python3
"""Verifier stress tests for trade-B delivery candidates (W_DQK_HI, WR_DQK_HI), own code.
usage: python3 -P v06_stress_B.py SCRATCH OUTDIR"""
import sys

import numpy as np
import pandas as pd

SP, OUT = sys.argv[1], sys.argv[2]
DATA = f'{SP}/sector_lab/data'
LOG = open(f'{OUT}/v06_stress_B.log', 'w')
pd.set_option('display.width', 250)


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.write(s + '\n')


ses = pd.read_csv(f'{DATA}/sessions.csv')
days = ses.day.to_numpy()
T = len(days)
ret = pd.read_csv(f'{DATA}/returns.csv', index_col=0)
SY = ret.columns.tolist()
SJ = {s: j for j, s in enumerate(SY)}
S = len(SY)
R = ret.to_numpy(float)
NC = pd.read_csv(f'{DATA}/index_close.csv', usecols=['day', 'Nifty 50']).set_index('day')['Nifty 50'].reindex(days).to_numpy(float)
NR = np.r_[np.nan, NC[1:] / NC[:-1] - 1]
Mz = np.load(f'{OUT}/own_mats.npz')
DQL, DQA, SF = Mz['DQL'], Mz['DQA'], Mz['SF']
eqp = pd.read_csv(f'{SP}/more_signals/delivery/downloads/delivery_eq.csv', usecols=['day', 'symbol', 'ttl_trd_qnty'])
f = pd.read_csv(f'{OUT}/own_feat_stress.csv')
QN = f.qn.to_numpy(int)
H1 = QN <= 13
j = f.symbol.map(SJ).to_numpy(int)
k = f.i_react.to_numpy(int)
rng = np.random.default_rng(9)
first_q = f.groupby('symbol').qn.min()
early = f.symbol.map(first_q).to_numpy() <= 1
btr = pd.read_csv(f'{SP}/perf/B_post_results/trades.csv')
hab = set(zip(btr[btr.test == 'S1_DRIFT4_Q5'].symbol, btr[btr.test == 'S1_DRIFT4_Q5'].qn))
HAB = np.array([(s, q) in hab for s, q in zip(f.symbol, f.qn)])
XN = f.XN.to_numpy(float)
W = XN > 4
WR = W & (f.cut_rsi14.to_numpy(float) > 50)
TR = {0: f.tradable_B.to_numpy(bool), 1: f.trad_k1.to_numpy(bool)}
Y = {0: f.vsN_net_H20.to_numpy(float), 1: f.vsN_net_k1.to_numpy(float)}
DQK = f.DQK.to_numpy(float)

# total traded quantity ratio on day k (known at the close of k, unlike delivery): own, from NSE traded qty x own SF
LR = np.log1p(np.nan_to_num(R))
TQ = np.full((T, S), np.nan)
cur_map = {}
# reuse delivery_panel style mapping via own_feat? simpler: the study-independent mapping in v03 is not saved for TQ,
# so rebuild TQ quickly with the same forward ticker rule
sc = pd.read_csv(f'{SP}/symbolchange.csv', header=None, names=['co', 'old', 'new', 'date'], dtype=str)
for c in sc:
    sc[c] = sc[c].str.strip()
sc['d'] = pd.to_datetime(sc.date, format='%d-%b-%Y', errors='coerce').dt.strftime('%Y-%m-%d')
FWD = {}
for o, n, d in zip(sc.old, sc.new, sc.d):
    if isinstance(d, str):
        FWD.setdefault(o, []).append((d, n))


def fwd(s, d):
    for _ in range(10):
        c = [(dd, n) for dd, n in FWD.get(s, []) if dd > d]
        if not c:
            return s
        s = min(c)[1]
    return s


DIX = {d: i for i, d in enumerate(days)}
u = eqp[['symbol', 'day']].drop_duplicates()
mp = {(s, d): fwd(s, d) for s, d in zip(u.symbol, u.day)}
eqp['cur'] = [mp[(s, d)] for s, d in zip(eqp.symbol, eqp.day)]
eqp = eqp[eqp.cur.isin(SJ) & eqp.day.isin(DIX)]
TQ[eqp.day.map(DIX).to_numpy(int), eqp.cur.map(SJ).to_numpy(int)] = eqp.ttl_trd_qnty.to_numpy(float)
TQA = TQ * SF
VK = np.array([TQA[kk, jj] / np.nanmean(TQA[kk - 60:kk, jj]) if np.isfinite(TQA[kk - 60:kk, jj]).sum() >= 40 else np.nan
               for kk, jj in zip(k, j)])
f['VK'] = VK


def bstat(sig, pool, lag, cut=None):
    par = pool & TR[lag] & np.isfinite(Y[lag]) & np.isfinite(DQK)
    m = par & sig
    y = Y[lag]
    pm = pd.Series(y[par]).groupby(QN[par]).mean()
    dpar = y[m] - pd.Series(QN[m]).map(pm).to_numpy()
    srt = np.argsort(-y[m])
    return dict(n=int(m.sum()), net=y[m].mean(), parent=y[par].mean(), gain=dpar.mean(), g_h1=dpar[H1[m]].mean(),
                g_h2=dpar[~H1[m]].mean(), net_wo5=np.delete(y[m], srt[:5]).mean(), g_wo5=np.delete(dpar, srt[:5]).mean(),
                net_wo10=np.delete(y[m], srt[:10]).mean(), g_wo10=np.delete(dpar, srt[:10]).mean()), dpar, m


def fmt(d):
    return ' '.join(f'{a} {b:+.3f}' if isinstance(b, float) else f'{a} {b}' for a, b in d.items())


f['year'] = f.cutoff.str[:4].astype(int)
for plab, pool in [('W', W), ('WR', WR)]:
    P('=' * 100)
    P(f'{plab}_DQK_HI: reaction-day delivery qty >= 3x 60-day avg, buy close k+1')
    P('=' * 100)
    sig = DQK >= 3
    st, dpar, m = bstat(sig, pool, 1)
    P('base:', fmt(st))
    lo = []
    for q in range(22):
        mm = m & (QN != q)
        lo.append(dpar[(QN[m] != q)].mean())
    P(f'LOQO gain min {np.min(lo):+.3f} (drop qn {int(np.argmin(lo))}) max {np.max(lo):+.3f} (drop qn {int(np.argmax(lo))})')
    g = pd.DataFrame({'yr': f.year[m].to_numpy(), 'g': dpar}).groupby('yr').g.agg(['size', 'mean'])
    P('by year (n, gain):', ', '.join(f'{yr}: {int(r["size"])} {r["mean"]:+.2f}' for yr, r in g.iterrows()))
    d = pd.DataFrame({'s': f.symbol[m].to_numpy(), 'g': dpar}).groupby('s').g.agg(['sum', 'size'])
    idx = rng.integers(0, len(d), (5000, len(d)))
    bm = d['sum'].to_numpy()[idx].sum(1) / d['size'].to_numpy()[idx].sum(1)
    P(f'symbol-cluster bootstrap: {len(d)} symbols, P(gain <= 0) {np.mean(bm <= 0):.3f}')
    for c in (1.5, 2, 2.5, 3, 3.5, 4, 5, 6):
        s2, _, _ = bstat(DQK >= c, pool, 1)
        P(f'   DQK >= {c:<4}', fmt(s2))
    # same trades bought at k
    s0, d0, m0 = bstat(sig, pool, 0)
    P('same signal bought at close k (NOT tradable: day-k delivery file comes after the close):', fmt(s0))
    sp, _, _ = bstat(np.ones(len(f), bool), pool, 0)
    P(f'parent bought at k: n {sp["n"]} net {sp["net"]:+.3f}  -> {plab}_DQK_HI at k+1 minus parent at k: {st["net"] - sp["net"]:+.3f}')
    # total-volume ratio on day k (known at close k)
    for c in (2, 3, 4):
        sv1, _, _ = bstat(VK >= c, pool, 1)
        sv0, _, _ = bstat(VK >= c, pool, 0)
        P(f'   total volume on k >= {c}x: bought k   ', fmt(sv0))
        P(f'   total volume on k >= {c}x: bought k+1 ', fmt(sv1))
    P(f'   corr(DQK, VK) among {plab}: {np.corrcoef(np.log(DQK[pool & np.isfinite(VK)]), np.log(VK[pool & np.isfinite(VK)]))[0, 1]:+.3f}')
    # DQK within VK: does delivery add to total volume?
    for a_lab, am in [('VK>=3', VK >= 3), ('VK<3', VK < 3)]:
        for b_lab, bm_ in [('DQK>=3', DQK >= 3), ('DQK<3', DQK < 3)]:
            s3, _, _ = bstat(am & bm_, pool, 1)
            P(f'   {a_lab} & {b_lab} (k+1): n {s3["n"]} net {s3["net"]:+.3f} gain {s3["gain"]:+.3f}')
    # XN control
    par = pool & TR[1] & np.isfinite(Y[1]) & np.isfinite(DQK)
    dfp = pd.DataFrame({'qn': QN[par], 'XN': XN[par], 'y': Y[1][par], 'sig': sig[par], 'sym': f.symbol[par].to_numpy()})
    dfp['xt'] = dfp.groupby('qn').XN.transform(lambda s: pd.qcut(s.rank(method='first'), 3, labels=False) if len(s) >= 3 else 0)
    dfp['cell'] = dfp.groupby(['qn', 'xt']).y.transform('mean')
    P(f'XN control: gain within quarter x XN tercile {(dfp.y - dfp.cell)[dfp.sig].mean():+.3f} (n {int(dfp.sig.sum())})')
    Xd = pd.get_dummies(dfp.qn.astype(str), drop_first=True).astype(float)
    Xd['sig'] = dfp.sig.astype(float)
    Xd['XN'] = dfp.XN
    Xd['c'] = 1.0
    Xv = Xd.to_numpy(float)
    b, *_ = np.linalg.lstsq(Xv, dfp.y.to_numpy(), rcond=None)
    res = dfp.y.to_numpy() - Xv @ b
    XtXi = np.linalg.pinv(Xv.T @ Xv)
    meat = np.zeros((Xv.shape[1],) * 2)
    for s_ in dfp.sym.unique():
        mm = (dfp.sym == s_).to_numpy()
        gg = Xv[mm].T @ res[mm]
        meat += np.outer(gg, gg)
    V = XtXi @ meat @ XtXi
    ii = list(Xd.columns).index('sig')
    P(f'OLS vsN_net(k+1) ~ DQK_HI + XN + quarter FE: coef {b[ii]:+.3f}, symbol-clustered t {b[ii] / np.sqrt(V[ii, ii]):.2f}')
    # XN size comparator at k
    for c in (6, 7, 8):
        sx, _, _ = bstat(XN > c, pool, 0)
        P(f'   comparator: {plab} with XN > {c} bought at k:', fmt(sx))
    # overlaps
    P(f'overlap: with RSI>50 winners {int((m & WR).sum())}/{int(m.sum())}; with habitual drifters {int((m & HAB).sum())}')
    if plab == 'W':
        s4, _, _ = bstat(sig, W & ~WR, 1)
        P('   DQK_HI among winners with RSI <= 50 (k+1):', fmt(s4))
        s5, _, _ = bstat(sig, W & ~HAB, 1)
        P('   DQK_HI among winners that are not habitual drifters (k+1):', fmt(s5))
    s6, _, _ = bstat(sig, pool & early, 1)
    s7, _, _ = bstat(sig, pool & ~early, 1)
    P('survivorship: in F&O by qn 1:', fmt(s6))
    P('              later joiners  :', fmt(s7))

# -------- own quiet-day placebo for B
P('\n' + '=' * 100)
P('OWN PLACEBO B: quiet stock-days of F&O stocks, XN_k = stock - Nifty > 4%, no result session of the stock in [k-10, k+22];')
P('               DQK on day k, buy close k+1, 20 sessions, short Nifty, net 0.19; gain vs quiet winners of the same month')
P('=' * 100)
ev = pd.read_csv(f'{DATA}/events.csv', usecols=['symbol', 'i_rd', 'i_react'])
BL = np.zeros((T, S), bool)
for s_, a, b_ in zip(ev.symbol, ev.i_rd, ev.i_react):
    if s_ in SJ:
        for x in (a, b_):
            if np.isfinite(x):
                x = int(x)
                BL[max(0, x - 22):x + 11, SJ[s_]] = True     # k in [r-22, r+10]  <=> r in [k-10, k+22]
INF = np.zeros((T, S), bool)
for s_, rd in zip(f.symbol, f.i_rd):
    INF[max(0, rd - 70):rd + 70, SJ[s_]] = True
XNm = (R - NR[:, None]) * 100
CR = np.vstack([np.zeros((1, S)), np.cumsum(LR, 0)])
NANC = np.vstack([np.zeros((1, S)), np.cumsum(~np.isfinite(R), 0)])
cand = np.where((XNm > 4) & INF & ~BL)
rows = []
for kk, jj in zip(*cand):
    a = kk + 1
    b_ = a + 20
    if kk < 1320 or b_ >= T or not np.isfinite(DQL[kk, jj]):
        continue
    if NANC[b_ + 1, jj] - NANC[a + 1, jj] > 2:
        continue
    y = (np.exp(CR[b_ + 1, jj] - CR[a + 1, jj]) - 1) * 100 - (NC[b_] / NC[a] - 1) * 100 - 0.19
    rows.append((kk, jj, days[kk][:7], XNm[kk, jj], DQL[kk, jj], y))
qd = pd.DataFrame(rows, columns=['k', 'j', 'month', 'XN', 'DQK', 'y'])
qd['pm'] = qd.groupby('month').y.transform('mean')
sg = qd.DQK >= 3
qg = (qd.y - qd.pm)[sg]
P(f'quiet winners {len(qd)} (k from session 1320), DQK >= 3: {int(sg.sum())}; quiet net all {qd.y.mean():+.3f}, DQK_HI {qd.y[sg].mean():+.3f}, '
  f'quiet gain {qg.mean():+.3f}')
stW, _, _ = bstat(DQK >= 3, W, 1)
P(f'results W_DQK_HI gain {stW["gain"]:+.3f} -> DiD {stW["gain"] - qg.mean():+.3f}; placebo p (draws of {stW["n"]} quiet gains >= results gain): '
  f'{np.mean(rng.choice(qg.to_numpy(), (10000, stW["n"])).mean(1) >= stW["gain"]):.4f}')
for c in (2, 4):
    s_ = qd.DQK >= c
    P(f'   quiet DQK >= {c}: n {int(s_.sum())} gain {(qd.y - qd.pm)[s_].mean():+.3f}')
qd.to_csv(f'{OUT}/own_placebo_B.csv.gz', index=False, compression='gzip', float_format='%.5g')
LOG.close()
