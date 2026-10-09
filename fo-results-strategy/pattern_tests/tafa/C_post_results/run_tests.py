#!/usr/bin/env python3
"""Post-results TA + FA combinations - runs exactly the 117 tests in PREREGISTRATION.txt (same folder).

Needs features.csv and quiet_days.csv.gz from features.py (features only). This script is the first to compute any
forward return. Read-only inputs: scratchpad/sector_lab/data/*.csv. Writes only into this folder.
"""
import hashlib
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.environ.get('LAB_ROOT', os.path.abspath(os.path.join(HERE, '..', '..')))  # scratch data folder
DATA = f'{SP}/sector_lab/data'
NDRAW = 20000
NPERM = 10000
SEED = 20261009
HS = (5, 10, 20)
C_STK, C_HEDGE = 0.17, 0.02
LOG = open(f'{HERE}/run.log', 'w')


def P_(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    LOG.write(s + '\n')
    LOG.flush()


P_('PREREGISTRATION.txt sha256', hashlib.sha256(open(f'{HERE}/PREREGISTRATION.txt', 'rb').read()).hexdigest())
rng = np.random.default_rng(SEED)

# ------------------------------------------------------------------ prices
ses = pd.read_csv(f'{DATA}/sessions.csv')
ret = pd.read_csv(f'{DATA}/returns.csv', index_col=0)
ixc = pd.read_csv(f'{DATA}/index_close.csv', index_col=0, usecols=['day', 'Nifty 50'])
assert (ret.index == ses.day).all() and (ixc.index == ses.day).all()
NS = len(ses)
SYM = {s: k for k, s in enumerate(ret.columns)}
R = ret.to_numpy(float)
PX = np.cumprod(1.0 + np.nan_to_num(R), axis=0)
CVALID = np.cumsum(~np.isnan(R), axis=0)
NIFTY = ixc['Nifty 50'].to_numpy(float)


def outcomes(sym, k):
    """raw[n,3], nif[n,3] (percent, k -> k+H), hedged TP long / short [n,3], tradable flag."""
    jx = np.array([SYM[s] for s in sym])
    k = np.asarray(k, int)
    n = len(k)
    raw, nif = np.full((n, 3), np.nan), np.full((n, 3), np.nan)
    tpl, tps = np.full((n, 3), np.nan), np.full((n, 3), np.nan)
    ok = (k + 21 <= NS - 1)
    kk = np.where(ok, k, 0)
    blanks = 21 - (CVALID[np.minimum(kk + 21, NS - 1), jx] - CVALID[kk, jx])
    ok &= blanks <= 2
    path = np.full((n, 20), np.nan)
    for t in range(1, 21):
        ii = np.minimum(kk + t, NS - 1)
        path[:, t - 1] = ((PX[ii, jx] / PX[kk, jx] - 1) - (NIFTY[ii] / NIFTY[kk] - 1)) * 100
    for c, H in enumerate(HS):
        ii = np.minimum(kk + H, NS - 1)
        raw[:, c] = (PX[ii, jx] / PX[kk, jx] - 1) * 100
        nif[:, c] = (NIFTY[ii] / NIFTY[kk] - 1) * 100
        p = path[:, :H]
        for sgn, out in ((1, tpl), (-1, tps)):
            hit = sgn * p > 3
            first = np.where(hit.any(1), hit.argmax(1), H - 1)
            out[:, c] = sgn * p[np.arange(n), first]
    for a in (raw, nif, tpl, tps):
        a[~ok] = np.nan
    return raw, nif, tpl, tps, ok


# ------------------------------------------------------------------ results
f = pd.read_csv(f'{HERE}/features.csv')
raw, nif, tpl, tps, ok = outcomes(f.symbol, f.i_react)
ok &= f.XN.notna().to_numpy()
P_(f'in_fo results {len(f)}, tradable {ok.sum()}')
f = f[ok].reset_index(drop=True)
raw, nif, tpl, tps = raw[ok], nif[ok], tpl[ok], tps[ok]
VSN = raw - nif
QN = f.qn.to_numpy()
FIRST = QN <= 13
W = f.W.to_numpy()
B = {c: f[c].to_numpy(bool) for c in f.columns if f[c].dtype == bool}

# reproduction of the documented plain winner drift
x = VSN[W, 2] - 0.19
qm = pd.Series(x).groupby(QN[W]).mean()
P_(f'REPRO plain winner drift E0 H20 vsN net: n={W.sum()} mean={x.mean():+.2f}% q_pos={int((qm > 0).sum())}/{len(qm)} '
   f't={qm.mean() / (qm.std() / np.sqrt(len(qm))):.2f}   [documented 392, +1.45%, 15/22]')


def dnet(d):
    """direction-adjusted nets: raw_net, vsN_net, tp_net, raw_gross, vsN_gross, tp_gross"""
    tp = tpl if d == 1 else tps
    return d * raw - C_STK, d * VSN - C_STK - C_HEDGE, tp - C_STK - C_HEDGE, d * raw, d * VSN, tp


# ------------------------------------------------------------------ test list
TESTS = []   # (name, part, direction, sig mask, {pool name: mask}, primary pool names, secondary pool name)
e1 = B['E_GOOD'] & B['E_TA_RX']
TESTS.append(('P1_GOOD_BREAKOUT_VOL', 1, 1, B['GOOD'] & B['BREAKOUT_VOL'] & e1,
              {'TA': B['BREAKOUT_VOL'] & e1, 'FA': B['GOOD'] & e1, 'ALL': e1}, ['TA', 'FA'], 'ALL'))
TESTS.append(('P2_GOOD_BELOW50', 1, 1, B['GOOD'] & B['BELOW50'] & e1,
              {'TA': B['BELOW50'] & e1, 'FA': B['GOOD'] & e1, 'ALL': e1}, ['TA', 'FA'], 'ALL'))
e3 = B['E_BAD'] & B['E_TA_RX']
TESTS.append(('P3_BAD_BRKDN_VOL', 1, -1, B['BAD'] & B['BRKDN_VOL'] & e3,
              {'TA': B['BRKDN_VOL'] & e3, 'FA': B['BAD'] & e3, 'ALL': e3}, ['TA', 'FA'], 'ALL'))
ELIG = {'GOOD': 'E_GOOD', 'BAD': 'E_BAD', 'Q_HI': 'E_QHI', 'Q_LO': 'E_QLO', 'CHEAP': 'E_PE', 'EXP': 'E_PE',
        'UP200': 'E_S200', 'DN200': 'E_S200', 'RSI_HI': 'E_RSI', 'RSI_LO': 'E_RSI'}
FA_ = ['GOOD', 'BAD', 'Q_HI', 'Q_LO', 'CHEAP', 'EXP']
TA_ = ['UP200', 'DN200', 'RSI_HI', 'RSI_LO']
SUBS = [[c] for c in FA_ + TA_] + [[a, b] for a in FA_ for b in TA_] + \
       [['GOOD', 'UP200', 'RSI_HI'], ['BAD', 'DN200', 'RSI_LO']]
for parts in SUBS:
    name = {('GOOD', 'UP200', 'RSI_HI'): 'ALL_BULL', ('BAD', 'DN200', 'RSI_LO'): 'ALL_BEAR'}.get(tuple(parts),
                                                                                              '&'.join(parts))
    el = W.copy()
    sg = W.copy()
    for c in parts:
        el &= B[ELIG[c]]
        sg &= B[c]
    TESTS.append(('W_' + name, 2, 1, sg, {'W_ELIG': el, 'W_ALL': W}, ['W_ELIG'], 'W_ALL'))
assert len(TESTS) == 39


def luck(si, pi, vals, ndraw=NDRAW):
    """pooled means of random same-size per-quarter picks (without replacement) from pool rows pi"""
    tot = np.zeros((ndraw, vals.shape[1]))
    kt = 0
    for q in np.unique(QN[si]):
        k = int((QN[si] == q).sum())
        pq = pi[QN[pi] == q]
        n = len(pq)
        assert n >= k, (q, n, k)
        v = vals[pq]
        if k == n:
            tot += v.sum(0)
        else:
            for c0 in range(0, ndraw, 4000):
                c1 = min(ndraw, c0 + 4000)
                pick = np.argpartition(rng.random((c1 - c0, n)), k - 1, axis=1)[:, :k]
                tot[c0:c1] += v[pick].sum(1)
        kt += k
    return tot / kt


def qstats(x, q):
    s = pd.Series(x).groupby(q).mean()
    t = s.mean() / (s.std(ddof=1) / np.sqrt(len(s))) if len(s) > 1 and s.std(ddof=1) > 0 else np.nan
    return s, t


rows, pq_rows, trade_flags = [], [], {}
for name, part, d, sig, pools, prim, sec in TESTS:
    rawn, vsnn, tpn, rawg, vsng, tpg = dnet(d)
    si = np.where(sig)[0]
    trade_flags[name] = sig.astype(int)
    pv = {}
    for pn_, pm in pools.items():
        assert not (sig & ~pm).any(), (name, pn_)
        rd_ = luck(si, np.where(pm)[0], vsnn)
        pv[pn_] = rd_
    for c, H in enumerate(HS):
        x = vsnn[si, c]
        q = QN[si]
        fh = FIRST[si]
        qm, t = qstats(x, q)
        wmean_q = pd.Series(VSN[W, c] - C_STK - C_HEDGE).groupby(QN[W]).mean()   # plain winners, LONG, always
        dW = x - wmean_q.reindex(q).to_numpy()
        dq = qm - wmean_q.reindex(qm.index)
        tdq = dq.mean() / (dq.std(ddof=1) / np.sqrt(len(dq))) if len(dq) > 1 else np.nan
        srt = np.sort(x)
        act = x.mean()
        ps = {pn_: (1 + (pv[pn_][:, c] >= act).sum()) / (1 + NDRAW) for pn_ in pools}
        row = dict(test=name, part=part, side='long' if d == 1 else 'short', H=H, n=len(x),
                   n_first14=int(fh.sum()), n_last8=int((~fh).sum()),
                   raw_gross=rawg[si, c].mean(), raw_net=rawn[si, c].mean(),
                   vsN_gross=vsng[si, c].mean(), vsN_net=act, tp_gross=tpg[si, c].mean(), tp_net=tpn[si, c].mean(),
                   up_pct=(x > 0).mean() * 100, nq=len(qm), q_pos=int((qm > 0).sum()), t_q=t,
                   vsN_net_first14=x[fh].mean() if fh.any() else np.nan,
                   vsN_net_last8=x[~fh].mean() if (~fh).any() else np.nan,
                   qpos_first14=f'{int((qm[qm.index <= 13] > 0).sum())}/{int((qm.index <= 13).sum())}',
                   qpos_last8=f'{int((qm[qm.index >= 14] > 0).sum())}/{int((qm.index >= 14).sum())}',
                   raw_net_first14=rawn[si, c][fh].mean() if fh.any() else np.nan,
                   raw_net_last8=rawn[si, c][~fh].mean() if (~fh).any() else np.nan,
                   vsN_net_wo_best5=srt[:-5].mean() if len(srt) > 5 else np.nan,
                   dW=dW.mean(), dW_first14=dW[fh].mean() if fh.any() else np.nan,
                   dW_last8=dW[~fh].mean() if (~fh).any() else np.nan, t_dW_q=tdq,
                   dW_qpos=f'{int((dq > 0).sum())}/{len(dq)}')
        for pn_ in pools:
            row[f'pool_{pn_}_n'] = int(pools[pn_].sum())
            row[f'pool_{pn_}_mean'] = vsnn[pools[pn_], c].mean()
            row[f'rand_{pn_}_mean'] = pv[pn_][:, c].mean()
            row[f'p_{pn_}'] = ps[pn_]
        row['p_primary'] = max(ps[p] for p in prim)
        row['p_secondary'] = ps[sec]
        rows.append(row)
        for qq in qm.index:
            mq = q == qq
            pq_rows.append(dict(test=name, H=H, qn=qq, n=int(mq.sum()), vsN_net=x[mq].mean(), raw_net=rawn[si, c][mq].mean(),
                                plain_winners_vsN_net=wmean_q.get(qq, np.nan)))
res = pd.DataFrame(rows)


def holm(p):
    p = np.asarray(p, float)
    o = np.argsort(p)
    m = len(p)
    adj = np.empty(m)
    run = 0.0
    for r, i in enumerate(o):
        run = max(run, (m - r) * p[i])
        adj[i] = min(1.0, run)
    return adj


res['p_holm117'] = holm(res.p_primary)
res['p_holm_part'] = np.nan
for pt in (1, 2):
    m = res.part == pt
    res.loc[m, 'p_holm_part'] = holm(res.p_primary[m])

# ------------------------------------------------------------------ Westfall-Young max-z (joint permutation)
P_('\nWestfall-Young: joint permutations within quarter x winner stratum ...')
grp = QN * 2 + W.astype(int)
groups = [np.where(grp == g)[0] for g in np.unique(grp)]
sigM = np.column_stack([t[3] for t in TESTS]).astype(float)        # rows x 39
dirs = np.array([t[2] for t in TESTS], float)
nsig = sigM.sum(0)
# direction-adjusted with cost: long mean(vsN) - 0.19 ; short mean(-vsN) - 0.19
obs_true = np.zeros((39, 3))
for c in range(3):
    m = (sigM.T @ VSN[:, c]) / nsig
    obs_true[:, c] = dirs * m - C_STK - C_HEDGE
PERM = np.zeros((NPERM, 39, 3))
CH = 500
for c0 in range(0, NPERM, CH):
    m_ = min(CH, NPERM - c0)
    idx = np.empty((m_, len(VSN)), int)
    for g in groups:
        if len(g) == 1:
            idx[:, g] = g
        else:
            idx[:, g] = g[np.argsort(rng.random((m_, len(g))), axis=1)]
    for c in range(3):
        Yp = VSN[idx, c]                                            # m_ x rows
        PERM[c0:c0 + m_, :, c] = dirs[None, :] * (Yp @ sigM) / nsig[None, :] - C_STK - C_HEDGE
mu, sd = PERM.mean(0), PERM.std(0)
Z = (PERM - mu) / sd
zobs = (obs_true - mu) / sd
# map tests x H to res rows (res ordered by test then H)
order = [(t[0], H) for t in TESTS for H in HS]
assert list(zip(res.test, res.H)) == order
zflat = zobs.reshape(-1)                                            # test-major, H-minor = same order
Zflat = Z.reshape(NPERM, -1)
maxz = Zflat.max(1)
res['z_perm'] = zflat
res['p_perm_single'] = [(1 + (Zflat[:, i] >= zflat[i]).sum()) / (1 + NPERM) for i in range(len(zflat))]
res['p_westfall_young'] = [(1 + (maxz >= zflat[i]).sum()) / (1 + NPERM) for i in range(len(zflat))]
assert np.allclose(obs_true.reshape(-1), res.vsN_net.values, atol=1e-9)
P_(f'  null 95th pct of max z over 117 tests: {np.percentile(maxz, 95):.2f}; observed max z {zflat.max():.2f}; '
   f'tests with single perm p < 0.05: {(res.p_perm_single < 0.05).sum()} (expected ~{0.05 * 117:.1f}); '
   f'under the joint null P(count >= observed) = '
   f'{np.mean((Zflat >= 1.645).sum(1) >= (res.p_perm_single < 0.05).sum()):.3f}')

# ------------------------------------------------------------------ placebo (quiet days)
qd = pd.read_csv(f'{HERE}/quiet_days.csv.gz')
qraw, qnif, qtpl, qtps, qok = outcomes(qd.symbol, qd.i)
qd = qd[qok].reset_index(drop=True)
qraw, qnif = qraw[qok], qnif[qok]
QV = qraw - qnif
qd['month'] = qd.day.str[:7]
P_(f'\nquiet days with complete 20-session outcome: {len(qd)}; quiet winners {int(qd.W.sum())}')


def clus_mean(x, cl):
    """mean and month-clustered SE"""
    x = np.asarray(x, float)
    df = pd.DataFrame({'x': x - x.mean(), 'c': cl})
    s = df.groupby('c').x.sum()
    return x.mean(), np.sqrt((s ** 2).sum()) / len(x) if len(x) > 1 else np.nan


QB = {c: qd[c].to_numpy(bool) for c in qd.columns if qd[c].dtype == bool}
QB['GOOD'], QB['BAD'] = QB['L_GOOD'], QB['L_BAD']
pl_rows = []
for name, sig_ta, sig_fa, d in [('P1_GOOD_BREAKOUT_VOL', 'BREAKOUT_VOL', 'GOOD', 1), ('P2_GOOD_BELOW50', 'BELOW50', 'GOOD', 1),
                                ('P3_BAD_BRKDN_VOL', 'BRKDN_VOL', 'BAD', -1)]:
    for lab, m in [('TA_only', QB[sig_ta]), ('TA+last_FA', QB[sig_ta] & QB[sig_fa])]:
        for c, H in enumerate(HS):
            x = d * QV[m, c] - C_STK - C_HEDGE
            mn, se = clus_mean(x, qd.month[m])
            r_ = res[(res.test == name) & (res.H == H)].iloc[0]
            pl_rows.append(dict(test=name, placebo=lab, H=H, n=int(m.sum()), placebo_vsN_net=mn, se_month=se,
                                results_vsN_net=r_.vsN_net, results_minus_placebo=r_.vsN_net - mn))
QW = QB['W']
for name, part, d, sig, pools, prim, sec in TESTS[3:]:
    parts = name[2:].split('&')
    parts = {'ALL_BULL': ['GOOD', 'UP200', 'RSI_HI'], 'ALL_BEAR': ['BAD', 'DN200', 'RSI_LO']}.get(name[2:], parts)
    if any(p not in QB for p in parts):
        continue
    m = QW.copy()
    for p in parts:
        m &= QB[p]
    for c, H in enumerate(HS):
        allw = pd.Series(QV[QW, c] - 0.19).groupby(qd.month[QW].to_numpy()).mean()
        x = QV[m, c] - 0.19
        dd = x - allw.reindex(qd.month[m]).to_numpy()
        mn, se = clus_mean(x, qd.month[m])
        dm, dse = clus_mean(dd, qd.month[m])
        r_ = res[(res.test == name) & (res.H == H)].iloc[0]
        pl_rows.append(dict(test=name, placebo='quiet-day winners', H=H, n=int(m.sum()), placebo_vsN_net=mn, se_month=se,
                            placebo_d_vs_all_quiet_winners=dm, se_d=dse, results_vsN_net=r_.vsN_net,
                            results_dW=r_.dW, results_minus_placebo=r_.vsN_net - mn))
for c, H in enumerate(HS):
    x = QV[QW, c] - 0.19
    mn, se = clus_mean(x, qd.month[QW])
    pl_rows.append(dict(test='REF_all_quiet_winners', placebo='quiet-day winners', H=H, n=int(QW.sum()),
                        placebo_vsN_net=mn, se_month=se))
    x = QV[:, c] - 0.19
    mn, se = clus_mean(x, qd.month)
    pl_rows.append(dict(test='REF_all_quiet_days', placebo='quiet days', H=H, n=len(x), placebo_vsN_net=mn, se_month=se))
pl = pd.DataFrame(pl_rows)
pl.to_csv(f'{HERE}/placebo.csv', index=False, float_format='%.4f')
plc = pl[pl.placebo == 'TA+last_FA'].set_index(['test', 'H']).placebo_vsN_net

# ------------------------------------------------------------------ verdicts


def verdict(r):
    if r.part == 1:
        pc = plc.get((r.test, r.H), np.nan)
        base = (r.n >= 30) and (r.vsN_net_first14 > 0) and (r.vsN_net_last8 > 0) and (r.t_q >= 2.0) \
            and (r.vsN_net_wo_best5 > 0) and (r.vsN_net > pc)
    else:
        base = (r.n >= 30) and (r.dW_first14 > 0) and (r.dW_last8 > 0) and (r.vsN_net_first14 > 0) \
            and (r.vsN_net_last8 > 0) and (r.t_dW_q >= 2.0) and (r.vsN_net_wo_best5 > 0)
    if base and r.p_holm117 < 0.05:
        return 'SURVIVES' if r.part == 1 else 'BEATS_PLAIN_DRIFT'
    if base and r.p_primary < 0.05:
        return 'WATCH'
    return 'NO'


res['verdict'] = res.apply(verdict, axis=1)
res.to_csv(f'{HERE}/results_tests.csv', index=False, float_format='%.4f')
pd.DataFrame(pq_rows).to_csv(f'{HERE}/per_quarter.csv', index=False, float_format='%.4f')
tr = f[['symbol', 'quarter', 'qn', 'reaction_day', 'i_react', 'XN', 'W', 'GOOD', 'BAD', 'Q_HI', 'Q_LO', 'CHEAP', 'EXP',
        'UP200', 'DN200', 'RSI_HI', 'RSI_LO', 'BREAKOUT_VOL', 'BELOW50', 'BRKDN_VOL']].copy()
for c, H in enumerate(HS):
    tr[f'raw_H{H}'] = raw[:, c]
    tr[f'nifty_H{H}'] = nif[:, c]
    tr[f'tp_long_hedged_H{H}'] = tpl[:, c]
    tr[f'tp_short_hedged_H{H}'] = tps[:, c]
for k_, v_ in trade_flags.items():
    tr[k_] = v_
tr.to_csv(f'{HERE}/trades.csv', index=False, float_format='%.4f')

# references
ref = []
for nm, m, d in [('ALL_results', np.ones(len(f), bool), 1), ('PLAIN_WINNERS_XN4', W, 1),
                 ('GOOD_all', B['GOOD'], 1), ('BAD_all_short', B['BAD'], -1), ('BREAKOUT_VOL_all', B['BREAKOUT_VOL'], 1),
                 ('BELOW50_all', B['BELOW50'], 1), ('BRKDN_VOL_all_short', B['BRKDN_VOL'], -1)]:
    rawn, vsnn, tpn, rawg, vsng, tpg = dnet(d)
    for c, H in enumerate(HS):
        x = vsnn[m, c]
        qm, t = qstats(x, QN[m])
        fh = FIRST[m]
        ref.append(dict(ref=nm, H=H, n=int(m.sum()), raw_gross=rawg[m, c].mean(), raw_net=rawn[m, c].mean(),
                        vsN_gross=vsng[m, c].mean(), vsN_net=x.mean(), tp_net=tpn[m, c].mean(), up_pct=(x > 0).mean() * 100,
                        nq=len(qm), q_pos=int((qm > 0).sum()), t_q=t, vsN_net_first14=x[fh].mean(),
                        vsN_net_last8=x[~fh].mean(), wo_best5=np.sort(x)[:-5].mean()))
ref = pd.DataFrame(ref)
ref.to_csv(f'{HERE}/references.csv', index=False, float_format='%.4f')

# ------------------------------------------------------------------ print
pd.set_option('display.width', 300, 'display.max_rows', 300, 'display.max_columns', 60)
P_('\nREFERENCES (direction-adjusted; percent):')
P_(ref.round(2).to_string(index=False))
cols1 = ['test', 'H', 'n', 'raw_gross', 'raw_net', 'vsN_gross', 'vsN_net', 'tp_net', 'up_pct', 'nq', 'q_pos', 't_q',
         'vsN_net_first14', 'vsN_net_last8', 'vsN_net_wo_best5', 'pool_TA_mean', 'pool_FA_mean', 'pool_ALL_mean',
         'p_TA', 'p_FA', 'p_ALL', 'p_primary', 'p_holm117', 'p_westfall_young', 'dW', 'verdict']
P_('\nPART 1 - FA + TA combinations on all results (E0; vsN = Nifty-hedged; net = -0.19; shorts sign-flipped):')
P_(res[res.part == 1][cols1].round(3).to_string(index=False))
P_('\nPART 1 placebo (quiet days):')
P_(pl[pl.test.str.startswith('P')].round(3).to_string(index=False))
cols2 = ['test', 'H', 'n', 'raw_net', 'vsN_gross', 'vsN_net', 'tp_net', 'up_pct', 'nq', 'q_pos', 'vsN_net_first14',
         'vsN_net_last8', 'vsN_net_wo_best5', 'dW', 'dW_first14', 'dW_last8', 't_dW_q', 'dW_qpos', 'pool_W_ELIG_mean',
         'p_W_ELIG', 'p_W_ALL', 'p_holm117', 'p_westfall_young', 'verdict']
for H in HS:
    P_(f'\nPART 2 - plain winner subsets, H{H} (dW = vs all plain winners of the same quarter):')
    P_(res[(res.part == 2) & (res.H == H)][cols2].round(3).to_string(index=False))
P_('\nPART 2 placebo (quiet-day winners; d = vs all quiet-day winners of the same month):')
P_(pl[pl.placebo == 'quiet-day winners'].round(3).to_string(index=False))
P_('\nVerdicts:', res.verdict.value_counts().to_dict())
P_(f'Nominal primary p < 0.05: {(res.p_primary < 0.05).sum()} of 117 (expected by chance ~5.9); '
   f'min Holm {res.p_holm117.min():.3f}; min Westfall-Young {res.p_westfall_young.min():.3f}')
P_('Smallest 12 primary p:')
P_(res.nsmallest(12, 'p_primary')[['test', 'H', 'n', 'vsN_net', 'dW', 't_q', 't_dW_q', 'p_primary', 'p_holm117',
                                    'p_westfall_young', 'verdict']].round(4).to_string(index=False))
