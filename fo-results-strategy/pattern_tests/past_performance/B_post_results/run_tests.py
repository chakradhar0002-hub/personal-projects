#!/usr/bin/env python3
"""Trade B (post-results winner drift, 20 sessions, Nifty-hedged) split by past performance.
Implements prereg.txt exactly (refuses to run if its sha256 differs from prereg.sha256).
Writes only into this folder. Percent units (1.2 = +1.2%)."""
import hashlib
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
F = f'{SP}/perf/features'
DATA = f'{SP}/sector_lab/data'
LOG = open(f'{HERE}/run.log', 'w')
NDRAW, NPERM, SEED = 20000, 10000, 20261009
C_NET = 0.19
rng = np.random.default_rng(SEED)


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    LOG.write(s + '\n')
    LOG.flush()


# ------------------------------------------------------------------ pre-registration hash
h = hashlib.sha256(open(f'{HERE}/prereg.txt', 'rb').read()).hexdigest()
logged = open(f'{HERE}/prereg.sha256').read().split()[0]
P(f'prereg.txt sha256 {h}  logged {logged}  match={h == logged}')
assert h == logged, 'prereg.txt changed after it was hashed'

# ------------------------------------------------------------------ results data
pan = pd.read_csv(f'{F}/panel.csv')
out = pd.read_csv(f'{F}/outcomes.csv')
d = pan.merge(out[['symbol', 'qn', 'raw_H20', 'nifty_H20', 'tradable_B', 'vsN_H20', 'vsN_net_H20']],
              on=['symbol', 'qn'], validate='1:1')
d = d[d.tradable_B].reset_index(drop=True)
assert d.vsN_net_H20.notna().all()
d['label'] = 'Results for ' + d.period + ' (' + d.quarter + ')'
QN = d.qn.to_numpy(int)
X = d.vsN_net_H20.to_numpy(float)          # long net
VG = d.vsN_H20.to_numpy(float)             # gross stock - Nifty
W = (d.W == True).to_numpy()
RH = (d.cut_rsi14 > 50).to_numpy()
WR = W & RH
P(f'tradable F&O results {len(d)}; W {W.sum()} mean {X[W].mean():+.3f}; WR {WR.sum()} mean {X[WR].mean():+.3f}; '
  f'ALL mean {X.mean():+.3f}   [documented W 392 +1.45, WR 232 +2.42]')
assert W.sum() == 392 and WR.sum() == 232
assert abs(X[W].mean() - 1.45) < 0.01 and abs(X[WR].mean() - 2.42) < 0.01

med4 = pan.groupby('qn').mean_drift_4_B.median()          # thresholds over ALL F&O results of the quarter (features)
q80 = pan.groupby('qn').mean_drift_4_B.quantile(0.8)
q20 = pan.groupby('qn').mean_drift_4_B.quantile(0.2)


def feats(df, med, p80, p20, sfx='_B'):
    """feature name -> (signal mask, eligible mask) using the pre-registered definitions."""
    g = lambda c: df[c + sfx] if (c + sfx) in df.columns else df[c]
    f = {}
    pw, nw4, pd20 = g('prev1_winner'), g('n_winner_4'), g('prev1_drift20')
    f['REPEAT1'] = (pw == 1, pw.notna())
    f['REPEAT4'] = (nw4 >= 2, nw4.notna())
    f['FIRSTTIME4'] = (nw4 == 0, nw4.notna())
    f['PREVWIN_RAN'] = ((pw == 1) & (pd20 > 0), pw.notna() & ((pw == 0) | pd20.notna()))
    md4 = g('mean_drift_4')
    f['DRIFT4_TOP'] = (md4 >= med, md4.notna())
    f['DRIFT4_BOT'] = (md4 < med, md4.notna())
    for L in (63, 126, 252):
        c = g(f'rank_vsN_{L}')
        f[f'MOM{L}_TOP'] = (c > 50, c.notna())
        f[f'MOM{L}_BOT'] = (c <= 50, c.notna())
    c = g('dist_52wh')
    f['NEAR52H'] = (c >= -5, c.notna())
    f['FAR52H'] = (c < -5, c.notna())
    c = g('vsSec_252')
    f['SEC252_UP'] = (c > 0, c.notna())
    f['SEC252_DN'] = (c <= 0, c.notna())
    # standalone
    f['DRIFT4_Q5'] = (md4 >= p80, md4.notna())
    f['DRIFT4_Q1'] = (md4 <= p20, md4.notna())
    npd = g('n_pos_drift_4')
    nd = g('n_drift_4')
    f['CONSIST_DRIFT'] = (npd >= 3, nd == 4)
    return {k: (np.asarray(s.fillna(False), bool) & np.asarray(e, bool), np.asarray(e, bool)) for k, (s, e) in f.items()}


FEAT_W = ['REPEAT1', 'REPEAT4', 'FIRSTTIME4', 'PREVWIN_RAN', 'DRIFT4_TOP', 'DRIFT4_BOT', 'MOM63_TOP', 'MOM63_BOT',
          'MOM126_TOP', 'MOM126_BOT', 'MOM252_TOP', 'MOM252_BOT', 'NEAR52H', 'FAR52H', 'SEC252_UP', 'SEC252_DN']
FR = feats(d, d.qn.map(med4), d.qn.map(q80), d.qn.map(q20))
TESTS = []          # name, pool label, feature, direction, signal mask, parent mask
for lab, pool in (('W', W), ('WR', WR)):
    for fe in FEAT_W:
        s, e = FR[fe]
        TESTS.append((f'{lab}_{fe}', lab, fe, 1, s & pool, e & pool))
ALLT = np.ones(len(d), bool)
TESTS.append(('S1_DRIFT4_Q5', 'ALL', 'DRIFT4_Q5', 1, FR['DRIFT4_Q5'][0], FR['DRIFT4_Q5'][1]))
TESTS.append(('S2_DRIFT4_Q1', 'ALL', 'DRIFT4_Q1', -1, FR['DRIFT4_Q1'][0], FR['DRIFT4_Q1'][1]))
TESTS.append(('S3_CONSIST_DRIFT', 'ALL', 'CONSIST_DRIFT', 1, FR['CONSIST_DRIFT'][0], FR['CONSIST_DRIFT'][1]))
assert len(TESTS) == 35
for t in TESTS:
    assert not (t[4] & ~t[5]).any()


def dirx(dr):
    return X if dr == 1 else -VG - C_NET


def qmean_map(vals, mask, q):
    return pd.Series(vals[mask]).groupby(q[mask]).mean()


def tq(s):
    s = s.dropna()
    return s.mean() / (s.std(ddof=1) / np.sqrt(len(s))) if len(s) > 2 and s.std(ddof=1) > 0 else np.nan


def luck(si, pi, vals, ndraw=NDRAW):
    tot = np.zeros(ndraw)
    kt = 0
    for q in np.unique(QN[si]):
        k = int((QN[si] == q).sum())
        pq = pi[QN[pi] == q]
        n = len(pq)
        assert n >= k
        v = vals[pq]
        if k == n:
            tot += v.sum()
        else:
            for c0 in range(0, ndraw, 5000):
                c1 = min(ndraw, c0 + 5000)
                pick = np.argpartition(rng.random((c1 - c0, n)), k - 1, axis=1)[:, :k]
                tot[c0:c1] += v[pick].sum(1)
        kt += k
    return tot / kt


wmean_q = qmean_map(X, W, QN)
rows, pq_rows, trade_rows, DPAR = [], [], [], {}
for name, lab, fe, dr, sig, par in TESTS:
    v = dirx(dr)
    si, pi = np.where(sig)[0], np.where(par)[0]
    n = len(si)
    pm = qmean_map(v, par, QN)
    dpar = v[si] - pm.reindex(QN[si]).to_numpy()
    DPAR[name] = (si, dpar)
    x = v[si]
    q = QN[si]
    f14, l8 = q <= 13, q >= 14
    sq = pd.Series(x).groupby(q).mean()
    dq = pd.Series(dpar).groupby(q).mean()
    order = np.argsort(-x)
    keep = np.ones(n, bool)
    keep[order[:5]] = False
    r = dict(test=name, pool=lab, feature=fe, direction='long' if dr == 1 else 'short', n=n, parent_n=len(pi),
             mean_vsN_net=x.mean(), parent_mean=v[pi].mean(), up_pct=100 * (x > 0).mean(),
             q_with=len(sq), q_pos=int((sq > 0).sum()), t_q=tq(sq),
             d_par=dpar.mean(), q_dpos=int((dq > 0).sum()), t_dq=tq(dq),
             n_f14=int(f14.sum()), mean_f14=x[f14].mean() if f14.any() else np.nan,
             d_f14=dpar[f14].mean() if f14.any() else np.nan,
             q_pos_f14=int((sq[sq.index <= 13] > 0).sum()), q_f14=int((sq.index <= 13).sum()),
             n_l8=int(l8.sum()), mean_l8=x[l8].mean() if l8.any() else np.nan,
             d_l8=dpar[l8].mean() if l8.any() else np.nan,
             q_pos_l8=int((sq[sq.index >= 14] > 0).sum()), q_l8=int((sq.index >= 14).sum()),
             mean_wo5=x[keep].mean() if n > 5 else np.nan, d_wo5=dpar[keep].mean() if n > 5 else np.nan)
    if lab in ('W', 'WR'):
        r['d_W'] = (x - wmean_q.reindex(q).to_numpy()).mean()
    draws = luck(si, pi, v)
    r['luck_p'] = (1 + (draws >= x.mean() - 1e-12).sum()) / (1 + NDRAW)
    r['luck_mean'], r['luck_p95'] = draws.mean(), np.percentile(draws, 95)
    rows.append(r)
    for qq in sorted(set(QN[pi])):
        mq = (q == qq)
        pq_rows.append(dict(test=name, qn=qq, results_for=d.label[QN == qq].iloc[0], n=int(mq.sum()),
                            mean_vsN_net=x[mq].mean() if mq.any() else np.nan, parent_n=int((QN[pi] == qq).sum()),
                            parent_mean=pm.get(qq, np.nan), d_par=dpar[mq].mean() if mq.any() else np.nan))
    for i_, dd in zip(si, dpar):
        trade_rows.append(dict(test=name, symbol=d.symbol[i_], qn=QN[i_], results_for=d.label[i_],
                               reaction_day=d.reaction_day[i_], XN=d.XN[i_], cut_rsi14=d.cut_rsi14[i_],
                               vsN_net=dirx(dr)[i_], d_par=dd))
res = pd.DataFrame(rows)


def holm(p):
    p = np.asarray(p, float)
    o = np.argsort(p)
    m = len(p)
    adj = np.empty(m)
    run = 0
    for r_, i in enumerate(o):
        run = max(run, (m - r_) * p[i])
        adj[i] = min(1, run)
    return adj


res['holm_p'] = holm(res.luck_p)

# ------------------------------------------------------------------ maxT (Westfall-Young)
strat = np.where(WR, 0, np.where(W, 1, 2))
block = QN * 3 + strat
order0 = np.argsort(block, kind='stable')
bs = block[order0]
VGs = VG[order0]
NT = len(TESTS)
M = np.zeros((NT, len(d)))
sgn = np.zeros(NT)
for t, (name, lab, fe, dr, sig, par) in enumerate(TESTS):
    M[t, np.where(sig[order0])[0]] = 1.0 / sig.sum()
    sgn[t] = dr
obs = np.array([sgn[t] * (M[t] @ VGs) - C_NET for t in range(NT)])
assert np.allclose(obs, res.mean_vsN_net.to_numpy())
perm_stats = np.zeros((NPERM, NT))
for c0 in range(0, NPERM, 500):
    c1 = min(NPERM, c0 + 500)
    keys = bs[None, :] + rng.random((c1 - c0, len(bs)))
    idx = np.argsort(keys, axis=1)
    Vp = VGs[idx]
    perm_stats[c0:c1] = (Vp @ M.T) * sgn[None, :] - C_NET
mu, sd = perm_stats.mean(0), perm_stats.std(0, ddof=1)
Zp = (perm_stats - mu) / sd
z_obs = (obs - mu) / sd
maxz = Zp.max(1)
res['z_perm'] = z_obs
res['p_perm_single'] = [(1 + (perm_stats[:, t] >= obs[t] - 1e-12).sum()) / (1 + NPERM) for t in range(NT)]
res['p_maxT'] = [(1 + (maxz >= z_obs[t]).sum()) / (1 + NPERM) for t in range(NT)]
P(f'maxT: null 95th pct of max z over {NT} tests {np.percentile(maxz, 95):.2f}; observed max z {z_obs.max():.2f}')

# ------------------------------------------------------------------ quiet-day placebo
ses = pd.read_csv(f'{DATA}/sessions.csv')
days = ses.day.tolist()
T = len(days)
ret = pd.read_csv(f'{DATA}/returns.csv', index_col=0)
SYMS = ret.columns.tolist()
SYM = {s: j for j, s in enumerate(SYMS)}
R = ret.to_numpy(float)
PX = np.cumprod(1.0 + np.nan_to_num(R), axis=0)
CVALID = np.cumsum(~np.isnan(R), axis=0)
FIRST = np.array([np.argmax(np.isfinite(R[:, j])) for j in range(R.shape[1])])
ixc = pd.read_csv(f'{DATA}/index_close.csv', index_col=0)
NIFTY = ixc['Nifty 50'].to_numpy(float)
MAXBLANK = {21: 2, 63: 3, 126: 6, 252: 12}


def stock_ret_vec(js, i, L):
    js = np.asarray(js, int)
    outv = (PX[i, js] / PX[i - L, js] - 1) * 100 if i - L >= 0 else np.full(len(js), np.nan)
    bad = (i - L < FIRST[js]) | (i - L < 0)
    if i - L >= 0:
        bad |= (L - (CVALID[i, js] - CVALID[i - L, js])) > MAXBLANK[L]
    return np.where(bad, np.nan, outv)


def index_ret(arr, i, L):
    if i - L < 0 or not (np.isfinite(arr[i]) and np.isfinite(arr[i - L])):
        return np.nan
    return (arr[i] / arr[i - L] - 1) * 100


qd = pd.read_csv(f'{SP}/tafa/C_post_results/quiet_days.csv.gz',
                 usecols=['symbol', 'i', 'day', 'qn_prev', 'XN', 'm2_rsi14', 'W'])
jx = qd.symbol.map(SYM).to_numpy(int)
k = qd.i.to_numpy(int)
ok = k + 21 <= T - 1
kk = np.where(ok, k, 0)
ok &= (21 - (CVALID[np.minimum(kk + 21, T - 1), jx] - CVALID[kk, jx])) <= 2
qd = qd[ok].reset_index(drop=True)
jx, k = jx[ok], k[ok]
qd['vsN_net'] = ((PX[k + 20, jx] / PX[k, jx] - 1) - (NIFTY[k + 20] / NIFTY[k] - 1)) * 100 - C_NET
qd['vsN_g'] = qd.vsN_net + C_NET
qd['month'] = qd.day.str[:7]
P(f'quiet stock-days with complete 20-session outcome: {len(qd)}; quiet winners {int(qd.W.sum())}; '
  f'quiet RSI winners {int((qd.W & (qd.m2_rsi14 > 50)).sum())}')

# track record at quiet day k (history.csv; strictly before k)
hist = pd.read_csv(f'{F}/history.csv')
HG = {s: g.sort_values('qn') for s, g in hist.groupby('symbol')}
trk = {c: np.full(len(qd), np.nan) for c in ['prev1_winner', 'prev1_drift20', 'n_winner_4', 'mean_drift_4',
                                              'n_pos_drift_4', 'n_drift_4', 'n_prev']}
for s, idx in qd.groupby('symbol').groups.items():
    g = HG[s]
    tde, xne, dre = g.h_td_end.to_numpy(), g.h_xn_end.to_numpy(), g.h_dr_end.to_numpy()
    xn, dr = g.h_xn.to_numpy(float), g.h_dr.to_numpy(float)
    for r_ in idx:
        kk_ = qd.i.iat[r_]
        kn = np.flatnonzero((tde < kk_) & (xne < kk_))[::-1]          # most recent first (sorted by qn)
        trk['n_prev'][r_] = len(kn)
        if len(kn) == 0:
            continue
        drk = np.where(dre[kn] < kk_, dr[kn], np.nan)
        assert np.all(xne[kn] < kk_) and np.all(dre[kn][np.isfinite(drk)] < kk_)
        trk['prev1_winner'][r_] = float(xn[kn[0]] > 4) if np.isfinite(xn[kn[0]]) else np.nan
        trk['prev1_drift20'][r_] = drk[0]
        if len(kn) >= 4:
            x4, d4 = xn[kn[:4]], drk[:4]
            trk['n_winner_4'][r_] = float((x4[np.isfinite(x4)] > 4).sum()) if np.isfinite(x4).any() else np.nan
            fd = d4[np.isfinite(d4)]
            trk['n_drift_4'][r_] = len(fd)
            trk['n_pos_drift_4'][r_] = float((fd > 0).sum()) if len(fd) else np.nan
            trk['mean_drift_4'][r_] = fd.mean() if len(fd) else np.nan
for c, v in trk.items():
    qd[c] = v
# within-month thresholds over all quiet stock-days
qd['med4'] = qd.groupby('month').mean_drift_4.transform('median')
qd['p80'] = qd.groupby('month').mean_drift_4.transform(lambda s: s.quantile(0.8))
qd['p20'] = qd.groupby('month').mean_drift_4.transform(lambda s: s.quantile(0.2))

# price performance at quiet k (winners only: W/WR placebo)
ohl = pd.read_csv(f'{SP}/ta/build/adjusted_ohlcv.csv.gz', usecols=['day', 'symbol', 'high', 'close'])
DIX = {dd: i for i, dd in enumerate(days)}
ohl = ohl[ohl.symbol.isin(SYM)]
HI = np.full((T, len(SYMS)), np.nan)
CL = np.full((T, len(SYMS)), np.nan)
ii_, jj_ = ohl.day.map(DIX).to_numpy(int), ohl.symbol.map(SYM).to_numpy(int)
HI[ii_, jj_], CL[ii_, jj_] = ohl.high.to_numpy(float), ohl.close.to_numpy(float)
QWI = np.flatnonzero(qd.W.to_numpy(bool))
qj = qd.symbol.map(SYM).to_numpy(int)
D52q = np.full(len(qd), np.nan)
for j in np.unique(qj[QWI]):
    rows_ = np.flatnonzero(np.isfinite(CL[:, j]))
    hh = pd.Series(HI[rows_, j]).rolling(250, min_periods=250).max().to_numpy()
    dcol = np.full(T, np.nan)
    dcol[rows_] = (CL[rows_, j] / hh - 1) * 100
    sel = QWI[qj[QWI] == j]
    D52q[sel] = dcol[qd.i.to_numpy(int)[sel]]
qd['dist_52wh'] = D52q
ev = pd.read_csv(f'{DATA}/events.csv', usecols=['symbol', 'qn', 'sector_index'])
secmap = dict(zip(zip(ev.symbol, ev.qn), ev.sector_index))
FOSET = {q: pan.symbol[pan.qn == q].map(SYM).to_numpy(int) for q in pan.qn.unique()}
for L in (63, 126, 252):
    qd[f'rank_vsN_{L}'] = np.nan
qd['vsSec_252'] = np.nan
for (qp, i), g in qd.iloc[QWI].groupby(['qn_prev', 'i']):
    js = FOSET.get(qp)
    if js is None:
        continue
    for L in (63, 126, 252):
        allr = stock_ret_vec(js, i, L)
        for r_ in g.index:
            j = qj[r_]
            mine = stock_ret_vec([j], i, L)[0]
            if not np.isfinite(mine):
                continue
            pool_r = allr[js != j]
            pool_r = np.r_[pool_r[np.isfinite(pool_r)], mine]
            qd.at[r_, f'rank_vsN_{L}'] = pd.Series(pool_r).rank(pct=True).iloc[-1] * 100
    for r_ in g.index:
        sx = secmap.get((qd.symbol.iat[r_], qp))
        if isinstance(sx, str) and sx in ixc.columns:
            qd.at[r_, 'vsSec_252'] = stock_ret_vec([qj[r_]], i, 252)[0] - index_ret(ixc[sx].to_numpy(float), i, 252)
P(f'quiet winners with rank_vsN_252 {int(qd.rank_vsN_252.notna().sum())}, dist_52wh {int(qd.dist_52wh.notna().sum())}, '
  f'vsSec_252 {int(qd.vsSec_252.notna().sum())}; quiet days with mean_drift_4 {int(qd.mean_drift_4.notna().sum())}')
qd.drop(columns=['vsN_net', 'vsN_g']).to_csv(f'{HERE}/quiet_features.csv.gz', index=False, float_format='%.6g',
                                             compression='gzip')

FQ = feats(qd, qd.med4, qd.p80, qd.p20, sfx='')
QW = qd.W.to_numpy(bool)
QWR = QW & (qd.m2_rsi14 > 50).to_numpy()
QALL = np.ones(len(qd), bool)
QX = qd.vsN_net.to_numpy(float)
QVG = qd.vsN_g.to_numpy(float)
QM = qd.month.to_numpy()


def clus(x, cl):
    x = np.asarray(x, float)
    if len(x) < 2:
        return np.nan
    s = pd.DataFrame({'x': x - x.mean(), 'c': cl}).groupby('c').x.sum()
    return np.sqrt((s ** 2).sum()) / len(x)


pl_rows = []
for name, lab, fe, dr, sig, par in TESTS:
    qpool = {'W': QW, 'WR': QWR, 'ALL': QALL}[lab]
    qs, qe = FQ[fe]
    qs, qe = qs & qpool, qe & qpool
    v = QX if dr == 1 else -QVG - C_NET
    pmm = pd.Series(v[qe]).groupby(QM[qe]).mean()
    dq = v[qs] - pmm.reindex(QM[qs]).to_numpy()
    r = res.loc[res.test == name].iloc[0]
    pl_rows.append(dict(test=name, quiet_parent_n=int(qe.sum()), quiet_n=int(qs.sum()),
                        quiet_mean=v[qs].mean() if qs.any() else np.nan,
                        quiet_parent_mean=v[qe].mean() if qe.any() else np.nan,
                        quiet_d=dq.mean() if qs.any() else np.nan, quiet_d_se=clus(dq, QM[qs]) if qs.any() else np.nan,
                        results_d_par=r.d_par, placebo_excess=r.d_par - (dq.mean() if qs.any() else np.nan),
                        results_mean=r.mean_vsN_net))
for lab, m in (('REF_quiet_winners', QW), ('REF_quiet_RSI_winners', QWR), ('REF_all_quiet_days', QALL)):
    pl_rows.append(dict(test=lab, quiet_n=int(m.sum()), quiet_mean=QX[m].mean(), quiet_d_se=clus(QX[m], QM[m])))
pl = pd.DataFrame(pl_rows)
pl.to_csv(f'{HERE}/placebo.csv', index=False, float_format='%.4f')
res = res.merge(pl[['test', 'quiet_n', 'quiet_mean', 'quiet_d', 'quiet_d_se', 'placebo_excess']], on='test', how='left')


# ------------------------------------------------------------------ verdicts
def verdict(r):
    a = r.n >= 30
    b = (r.d_f14 > 0) and (r.d_l8 > 0) and (r.mean_f14 > 0) and (r.mean_l8 > 0)
    c = r.holm_p < 0.10
    dpl = (r.quiet_n >= 30) and (r.placebo_excess > 0)
    e = (r.d_wo5 > 0) and (r.mean_wo5 > 0)
    fails = [s for s, okk in (('n<30', a), ('halves', b), ('Holm', c), ('placebo', dpl), ('w/o best 5', e)) if not okk]
    if not fails:
        return 'WORKS', ''
    if a and b and dpl and e and r.luck_p < 0.05:
        return 'WATCH', 'Holm'
    return 'NO', ','.join(fails)


vv = res.apply(verdict, axis=1)
res['verdict'] = [x[0] for x in vv]
res['fails'] = [x[1] for x in vv]
res.to_csv(f'{HERE}/results_tests.csv', index=False, float_format='%.4f')
pd.DataFrame(pq_rows).to_csv(f'{HERE}/per_quarter.csv', index=False, float_format='%.4f')
pd.DataFrame(trade_rows).to_csv(f'{HERE}/trades.csv', index=False, float_format='%.4f')

# ------------------------------------------------------------------ reference rows
P('\nREFERENCE (tradable F&O results, 20-session vsN_net):')
for lab, m in (('plain winners W', W), ('winners RSI>50 WR', WR), ('all results', ALLT)):
    sq = pd.Series(X[m]).groupby(QN[m]).mean()
    P(f'  {lab:20s} n={m.sum():4d} mean {X[m].mean():+.2f}  q+ {int((sq > 0).sum())}/{len(sq)}  '
      f'first14 {X[m & (QN <= 13)].mean():+.2f}  last8 {X[m & (QN >= 14)].mean():+.2f}')
for lab, m in (('quiet winners', QW), ('quiet RSI winners', QWR), ('all quiet days', QALL)):
    P(f'  {lab:20s} n={m.sum():5d} mean {QX[m].mean():+.2f} (month-clustered SE {clus(QX[m], QM[m]):.2f})')


# ------------------------------------------------------------------ table
def f2(x, nd=2, sign=True):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return 'n/a'
    return f'{x:+.{nd}f}' if sign else f'{x:.{nd}f}'


hdr = ('| test | n (parent) | avg vsN_net | gain vs parent | q+ / q | d>0 q | first14 n, avg, gain | last8 n, avg, gain '
       '| w/o best5 avg, gain | luck p | Holm p | maxT p | placebo quiet n, gain | excess | verdict |')
sep = '|' + '---|' * 15
lines = [hdr, sep]
for r in res.itertuples():
    lines.append(f'| {r.test} | {r.n} ({r.parent_n}) | {f2(r.mean_vsN_net)} | {f2(r.d_par)} | {r.q_pos}/{r.q_with} | '
                 f'{r.q_dpos}/{r.q_with} | {r.n_f14}, {f2(r.mean_f14)}, {f2(r.d_f14)} | {r.n_l8}, {f2(r.mean_l8)}, '
                 f'{f2(r.d_l8)} | {f2(r.mean_wo5)}, {f2(r.d_wo5)} | {r.luck_p:.4f} | {r.holm_p:.3f} | {r.p_maxT:.3f} | '
                 f'{int(r.quiet_n)}, {f2(r.quiet_d)} | {f2(r.placebo_excess)} | {r.verdict}{" (" + r.fails + ")" if r.fails else ""} |')
TABLE = '\n'.join(lines)
P('\nALL 35 PRE-REGISTERED TESTS (vsN_net = 20-session Nifty-hedged net %, gain = same-quarter difference vs parent)')
P(TABLE)
open(f'{HERE}/table.txt', 'w').write(TABLE + '\n')

# ------------------------------------------------------------------ diagnostics
diag = []
# D1: price-performance splits at the cutoff (_A)
FA_ = feats(d, d.qn.map(med4), d.qn.map(q80), d.qn.map(q20), sfx='_A')
for lab, pool in (('W', W), ('WR', WR)):
    for fe in ['MOM63_TOP', 'MOM63_BOT', 'MOM126_TOP', 'MOM126_BOT', 'MOM252_TOP', 'MOM252_BOT', 'NEAR52H', 'FAR52H',
               'SEC252_UP', 'SEC252_DN']:
        s, e = FA_[fe]
        s, e = s & pool, e & pool
        pm = qmean_map(X, e, QN)
        dp = X[s] - pm.reindex(QN[s]).to_numpy()
        diag.append(dict(diag='D1_at_cutoff_A', test=f'{lab}_{fe}_A', n=int(s.sum()), mean_vsN_net=X[s].mean(),
                         d_par=dp.mean(), d_f14=dp[QN[s] <= 13].mean(), d_l8=dp[QN[s] >= 14].mean()))
# D2: XN-tercile control for WORKS / WATCH
for r in res[res.verdict.isin(['WORKS', 'WATCH'])].itertuples():
    name, lab, fe, dr, sig, par = [t for t in TESTS if t[0] == r.test][0]
    v = dirx(dr)
    xn = d.XN.to_numpy(float)
    terc = pd.qcut(pd.Series(xn[par]), 3, labels=False)
    tt = np.full(len(d), -1)
    tt[np.where(par)[0]] = terc.to_numpy()
    cell = QN * 10 + tt
    pm = pd.Series(v[par]).groupby(cell[par]).mean()
    dp = v[sig] - pm.reindex(cell[sig]).to_numpy()
    diag.append(dict(diag='D2_XN_tercile_control', test=r.test, n=int(sig.sum()), mean_vsN_net=v[sig].mean(),
                     d_par=dp.mean(), d_f14=dp[QN[sig] <= 13].mean(), d_l8=dp[QN[sig] >= 14].mean()))
dg = pd.DataFrame(diag)
dg.to_csv(f'{HERE}/diagnostics.csv', index=False, float_format='%.4f')
P('\nDIAGNOSTICS (descriptive; cannot change a verdict)')
P(dg.round(2).to_string(index=False))
P('\nVERDICT COUNTS:', res.verdict.value_counts().to_dict())
P('Tests with raw luck p < 0.05:', res[res.luck_p < 0.05][['test', 'n', 'mean_vsN_net', 'd_par', 'luck_p', 'holm_p',
                                                         'p_maxT', 'placebo_excess', 'verdict', 'fails']].round(4).to_string(index=False))
LOG.close()
