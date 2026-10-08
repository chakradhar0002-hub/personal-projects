#!/usr/bin/env python3
"""Post-results fundamental drift - runs exactly the tests in PREREGISTRATION.txt (same folder).

Read-only inputs: ../build/fa_panel.csv and ../../sector_lab/data/*.csv. Writes only into this folder.
"""
import os
import sys
import numpy as np
import pandas as pd
from scipy import stats as sst

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.abspath(os.path.join(HERE, '..', '..'))
PANEL = os.path.join(SCR, 'fa', 'build', 'fa_panel.csv')
DATA = os.path.join(SCR, 'sector_lab', 'data')
OUT = HERE
NREP = 10000
SEED = 20261008
C_STK = 0.17
C_HEDGE = 0.02
ENTRIES = (0, 1)
HORIZONS = (5, 10, 20)
WINS = [(e, h) for e in ENTRIES for h in HORIZONS]          # 6 windows, column order everywhere
LOG = open(os.path.join(OUT, 'run.log'), 'w')


def P_(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    LOG.write(s + '\n')
    LOG.flush()


# ------------------------------------------------------------------ load prices
ses = pd.read_csv(f'{DATA}/sessions.csv')
ret = pd.read_csv(f'{DATA}/returns.csv', index_col=0)
ixc = pd.read_csv(f'{DATA}/index_close.csv', index_col=0)
ev = pd.read_csv(f'{DATA}/events.csv')
assert (ret.index == ses.day).all() and (ixc.index == ses.day).all()
NS = len(ses)
SYM = {s: k for k, s in enumerate(ret.columns)}
R = ret.values
R0 = np.nan_to_num(R, nan=0.0)
PX = np.cumprod(1.0 + R0, axis=0)
VALID = ~np.isnan(R)
CVALID = np.cumsum(VALID, axis=0)
NIFTY = ixc['Nifty 50'].values
nret = np.r_[np.nan, NIFTY[1:] / NIFTY[:-1] - 1]

# ------------------------------------------------------------------ panel
pn = pd.read_csv(PANEL)
f = pn[pn.in_fo == True].copy()
P_(f'panel in_fo rows: {len(f)}')
f = f.merge(ev[['symbol', 'qn', 'i_react', 'reaction_day']].rename(columns={'reaction_day': 'rd_ev'}),
            on=['symbol', 'qn'], how='left')
assert f.i_react.notna().all()
f['i_react'] = f.i_react.astype(int)
assert (ses.day.values[f.i_react.values] == f.reaction_day.values).all(), 'reaction day mismatch'
assert (f.rd_ev == f.reaction_day).all()

# XN and windows
xn, ok, nbl = [], [], []
OUTC = {k: [] for k in ['raw', 'nif']}
raw_m = np.full((len(f), 6), np.nan)
nif_m = np.full((len(f), 6), np.nan)
for r, (s, i) in enumerate(zip(f.symbol, f.i_react)):
    k = SYM.get(s)
    if k is None:
        xn.append(np.nan); ok.append(False); nbl.append(99); continue
    x = (R[i, k] - nret[i]) * 100 if not np.isnan(R[i, k]) else np.nan
    xn.append(x)
    iend = i + 21
    if iend >= NS or np.isnan(x):
        ok.append(False); nbl.append(99); continue
    blanks = 21 - (CVALID[iend, k] - CVALID[i, k])
    nbl.append(blanks)
    ok.append(blanks <= 2)
    for j, (e, h) in enumerate(WINS):
        i0, i1 = i + e, i + e + h
        raw_m[r, j] = (PX[i1, k] / PX[i0, k] - 1) * 100
        nif_m[r, j] = (NIFTY[i1] / NIFTY[i0] - 1) * 100
f['XN'] = xn
f['tradable'] = ok
f['blanks21'] = nbl
d = (f.XN - f.react_excess_nifty).abs()
P_(f'XN vs panel react_excess_nifty: max abs diff {d.max():.2e} (n={d.notna().sum()})')
P_(f'tradable: {f.tradable.sum()} of {len(f)}; not tradable: XN missing {f.XN.isna().sum()}, '
   f'end of data {((f.i_react + 21) >= NS).sum()}, >2 blanks {((f.blanks21 > 2) & (f.blanks21 < 99)).sum()}')
for j, (e, h) in enumerate(WINS):
    f[f'raw_E{e}H{h}'] = raw_m[:, j]
    f[f'nif_E{e}H{h}'] = nif_m[:, j]

# ------------------------------------------------------------------ signals
f['MCHG'] = np.where(f.fin_type == 'Company', f.rq_ebitda_margin_chg_yoy_pp, f.rq_net_margin_chg_yoy_pp)
# surprise cut-offs from earlier quarters only (all in_fo results, qn' < qn and reaction day earlier)
sv = f.rq_pat_surprise_vs_trend_pp.values
qn = f.qn.values
rdi = f.i_react.values
p80 = np.full(len(f), np.nan)
p20 = np.full(len(f), np.nan)
npool = np.zeros(len(f), int)
for r in range(len(f)):
    m = (qn < qn[r]) & (rdi < rdi[r]) & ~np.isnan(sv)
    npool[r] = m.sum()
    if npool[r] >= 50:
        p80[r] = np.percentile(sv[m], 80)
        p20[r] = np.percentile(sv[m], 20)
f['surp_P80'] = p80
f['surp_P20'] = p20
f['surp_pool_n'] = npool
cut = f.groupby('qn')[['surp_P80', 'surp_P20']].median()
P_('surprise cut-offs (median per qn, pp):\n' + cut.round(1).T.to_string())

pat, sal, sur = f.rq_pat_yoy_pct, f.rq_sales_yoy_pct, f.rq_pat_surprise_vs_trend_pp
E_STRONG = pat.notna() & sal.notna()
E_PAT = pat.notna()
E_SUR = sur.notna() & f.surp_P80.notna()
E_M = f.MCHG.notna()
E_L2P = f.rq_loss_to_profit_yoy.notna()
E_P2L = f.rq_profit_to_loss_yoy.notna()
STRONG = E_STRONG & (pat > 25) & (sal > 15)
WEAK = E_PAT & (pat < -25)
SURT = E_SUR & (sur > f.surp_P80)
SURB = E_SUR & (sur < f.surp_P20)
MUP = E_M & (f.MCHG > 2)
MDN = E_M & (f.MCHG < -2)
L2P = E_L2P & (f.rq_loss_to_profit_yoy == 1)
P2L = E_P2L & (f.rq_profit_to_loss_yoy == 1)
XN = f.XN
NEG, POS, W4 = XN < 0, XN > 0, XN > 4
T = f.tradable.values

# name, direction, signal mask, eligible mask, bucket mask (comparison pool = eligible & bucket)
ALLT = pd.Series(True, index=f.index)
SIGS = [
    ('L1_STRONG', 1, STRONG, E_STRONG, ALLT),
    ('L2_SURP_TOP', 1, SURT, E_SUR, ALLT),
    ('L3_MARGIN_UP', 1, MUP, E_M, ALLT),
    ('L4_TURNAROUND', 1, L2P, E_L2P, ALLT),
    ('S1_WEAK', -1, WEAK, E_PAT, ALLT),
    ('S2_MARGIN_DN', -1, MDN, E_M, ALLT),
    ('S3_PROFIT2LOSS', -1, P2L, E_P2L, ALLT),
    ('S4_SURP_BOT', -1, SURB, E_SUR, ALLT),
    ('I1_STRONG_XNneg', 1, STRONG & NEG, E_STRONG, NEG),
    ('I2_WEAK_XNpos', -1, WEAK & POS, E_PAT, POS),
    ('I3_STRONG_XN4', 1, STRONG & W4, E_STRONG, W4),
    ('I4_SURPTOP_XNneg', 1, SURT & NEG, E_SUR, NEG),
    ('I5_SURPBOT_XNpos', -1, SURB & POS, E_SUR, POS),
    ('I6_SURPTOP_XN4', 1, SURT & W4, E_SUR, W4),
]

RAW = f[[f'raw_E{e}H{h}' for e, h in WINS]].values
NIF = f[[f'nif_E{e}H{h}' for e, h in WINS]].values
VSN = RAW - NIF
QN = f.qn.values
FIRST = QN <= 13
rng = np.random.default_rng(SEED)


def nets(direction):
    return direction * RAW - C_STK, direction * VSN - C_STK - C_HEDGE


def qt(x, q):
    """quarter means, t across quarters, one-sided p (H1 > 0)"""
    s = pd.Series(x).groupby(q).mean()
    nq = len(s)
    if nq < 2 or s.std(ddof=1) == 0:
        return s, np.nan, np.nan
    t = s.mean() / (s.std(ddof=1) / np.sqrt(nq))
    return s, t, 1 - sst.t.cdf(t, nq - 1)


def luck(sig_idx, pool_idx, vals, nrep=NREP):
    """random same-size per-quarter picks from pool; returns (R, ncol) pooled means"""
    tot = np.zeros((nrep, vals.shape[1]))
    ktot = 0
    qs = np.unique(QN[sig_idx])
    for q in qs:
        k = int((QN[sig_idx] == q).sum())
        pi = pool_idx[QN[pool_idx] == q]
        n = len(pi)
        assert n >= k
        v = vals[pi]
        if k == n:
            tot += v.sum(0)
        else:
            for c0 in range(0, nrep, 2000):
                c1 = min(nrep, c0 + 2000)
                rr = rng.random((c1 - c0, n))
                pick = np.argpartition(rr, k - 1, axis=1)[:, :k]
                tot[c0:c1] += v[pick].sum(1)
        ktot += k
    return tot / ktot


rows, pq_rows = [], []
for name, dr, sig, elig, bucket in SIGS:
    sig_m = sig.values & T
    pool_m = elig.values & bucket.values & T
    unc_m = elig.values & T
    assert not (sig_m & ~pool_m).any()
    si = np.where(sig_m)[0]
    pi = np.where(pool_m)[0]
    ui = np.where(unc_m)[0]
    rawn, vsnn = nets(dr)
    rand_p = luck(si, pi, vsnn)                       # primary pool
    rand_u = luck(si, ui, vsnn) if name.startswith('I') else rand_p
    rand_raw = luck(si, pi, rawn)
    # pool means per quarter (for d)
    for j, (e, h) in enumerate(WINS):
        x = vsnn[si, j]
        xr = rawn[si, j]
        q = QN[si]
        fh = FIRST[si]
        qm, t, pt = qt(x, q)
        qmr, tr, ptr = qt(xr, q)
        poolq = pd.Series(vsnn[pi, j]).groupby(QN[pi]).mean()
        dq = qm - poolq.reindex(qm.index)
        dtr = x - poolq.reindex(q).values
        dts = dq.mean() / (dq.std(ddof=1) / np.sqrt(len(dq))) if len(dq) > 1 else np.nan
        srt = np.sort(x)
        act = x.mean()
        row = dict(test=name, side='long' if dr == 1 else 'short', entry=f'E{e}', H=h,
                   n=len(x), n_first14=int(fh.sum()), n_last8=int((~fh).sum()),
                   raw_gross=(dr * RAW[si, j]).mean(), raw_net=xr.mean(),
                   vsN_gross=(dr * VSN[si, j]).mean(), vsN_net=act,
                   win_pct=(x > 0).mean() * 100,
                   nq=len(qm), q_pos=int((qm > 0).sum()), t_q=t, p_t=pt,
                   vsN_net_first14=x[fh].mean() if fh.any() else np.nan,
                   vsN_net_last8=x[~fh].mean() if (~fh).any() else np.nan,
                   qpos_first14=f'{int((qm[qm.index <= 13] > 0).sum())}/{int((qm.index <= 13).sum())}',
                   qpos_last8=f'{int((qm[qm.index >= 14] > 0).sum())}/{int((qm.index >= 14).sum())}',
                   raw_net_first14=xr[fh].mean() if fh.any() else np.nan,
                   raw_net_last8=xr[~fh].mean() if (~fh).any() else np.nan,
                   t_q_raw=tr, q_pos_raw=int((qmr > 0).sum()),
                   vsN_net_wo_best5=srt[:-5].mean() if len(srt) > 5 else np.nan,
                   pool_n=len(pi), pool_vsN_net=vsnn[pi, j].mean(),
                   d_vs_pool=dtr.mean(), d_first14=dtr[fh].mean() if fh.any() else np.nan,
                   d_last8=dtr[~fh].mean() if (~fh).any() else np.nan, t_d=dts,
                   p_luck=(1 + (rand_p[:, j] >= act).sum()) / (1 + NREP),
                   p_luck_uncond=(1 + (rand_u[:, j] >= act).sum()) / (1 + NREP),
                   p_luck_raw=(1 + (rand_raw[:, j] >= xr.mean()).sum()) / (1 + NREP),
                   rand_mean=rand_p[:, j].mean())
        rows.append(row)
        for qq in qm.index:
            mq = q == qq
            pool_mq = QN[pi] == qq
            pq_rows.append(dict(test=name, entry=f'E{e}', H=h, qn=qq, n=int(mq.sum()), vsN_net=x[mq].mean(),
                                raw_net=xr[mq].mean(), pool_n=int(pool_mq.sum()),
                                pool_vsN_net=vsnn[pi[pool_mq], j].mean()))

res = pd.DataFrame(rows)


def holm(p):
    p = np.asarray(p, float)
    o = np.argsort(p)
    m = len(p)
    adj = np.empty(m)
    run = 0
    for r, i in enumerate(o):
        run = max(run, (m - r) * p[i])
        adj[i] = min(1.0, run)
    return adj


res['p_luck_holm'] = holm(res.p_luck.values)
res['p_t_holm'] = holm(res.p_t.fillna(1).values)
res['p_luck_raw_holm'] = holm(res.p_luck_raw.values)


def verdict(r):
    base = (r.n >= 30) and (r.vsN_net_first14 > 0) and (r.vsN_net_last8 > 0) and (r.t_q >= 2.0) \
        and (r.vsN_net_wo_best5 > 0)
    if base and r.p_luck_holm < 0.05:
        return 'SURVIVES'
    if base and r.p_luck < 0.05:
        return 'WATCH'
    return 'NO'


res['verdict'] = res.apply(verdict, axis=1)
res.to_csv(os.path.join(OUT, 'results_tests.csv'), index=False, float_format='%.4f')
pd.DataFrame(pq_rows).to_csv(os.path.join(OUT, 'per_quarter.csv'), index=False, float_format='%.4f')

# ------------------------------------------------------------------ references
ref_rows = []
for nm, m in [('ALL', np.ones(len(f), bool)), ('WIN_XN4', W4.values)]:
    mi = np.where(m & T)[0]
    rawn, vsnn = nets(1)
    for j, (e, h) in enumerate(WINS):
        x = vsnn[mi, j]
        qm, t, pt = qt(x, QN[mi])
        fh = FIRST[mi]
        ref_rows.append(dict(ref=nm, entry=f'E{e}', H=h, n=len(x), raw_gross=RAW[mi, j].mean(),
                             raw_net=rawn[mi, j].mean(), vsN_gross=VSN[mi, j].mean(), vsN_net=x.mean(),
                             nq=len(qm), q_pos=int((qm > 0).sum()), t_q=t,
                             vsN_net_first14=x[fh].mean(), vsN_net_last8=x[~fh].mean(),
                             raw_net_first14=rawn[mi, j][fh].mean(), raw_net_last8=rawn[mi, j][~fh].mean()))
ref = pd.DataFrame(ref_rows)
ref.to_csv(os.path.join(OUT, 'references.csv'), index=False, float_format='%.4f')

# reproduction of the documented winner drift (F3 convention: events.in_fo blank->True, H20 window only)
evx = ev.copy()
evx.loc[evx.in_fo.isna(), 'in_fo'] = True
evx['in_fo'] = evx.in_fo.astype(bool)
wr = []
for s, i, q, fo in zip(evx.symbol, evx.i_react, evx.qn, evx.in_fo):
    k = SYM.get(s)
    if k is None or not fo or np.isnan(R[i, k]):
        continue
    x = R[i, k] - nret[i]
    if x <= 0.04 or i + 20 >= NS:
        continue
    if 20 - (CVALID[i + 20, k] - CVALID[i, k]) > 2:
        continue
    wr.append((q, (PX[i + 20, k] / PX[i, k] - NIFTY[i + 20] / NIFTY[i]) * 100 - 0.19))
wr = pd.DataFrame(wr, columns=['qn', 'net'])
qm = wr.groupby('qn').net.mean()
P_(f'\nREPRO plain winner drift (F3 convention, E0 H20, vsN net): n={len(wr)} mean={wr.net.mean():+.2f}% '
   f'q_pos={int((qm > 0).sum())}/{len(qm)} t={qm.mean() / (qm.std() / np.sqrt(len(qm))):.2f}  '
   f'[documented: 392, +1.45%, 15/22, t 2.15]')

# ------------------------------------------------------------------ trades file
keep = ['symbol', 'quarter', 'qn', 'fin_type', 'industry', 'timing', 'results_date', 'reaction_day', 'i_react',
        'XN', 'rq_pat_yoy_pct', 'rq_sales_yoy_pct', 'MCHG', 'rq_pat_surprise_vs_trend_pp', 'surp_P80', 'surp_P20',
        'rq_loss_to_profit_yoy', 'rq_profit_to_loss_yoy', 'rq_xbrl_lag_days', 'tradable'] + \
       [f'raw_E{e}H{h}' for e, h in WINS] + [f'nif_E{e}H{h}' for e, h in WINS]
tr = f[keep].copy()
for name, dr, sig, elig, bucket in SIGS:
    tr[name] = (sig & f.tradable).astype(int)
tr.to_csv(os.path.join(OUT, 'trades.csv'), index=False, float_format='%.4f')

# ------------------------------------------------------------------ print
pd.set_option('display.width', 250)
P_('\nREFERENCES (long, all tradable in_fo results / plain winners XN>4):')
P_(ref.round(2).to_string(index=False))
P_('\nSIGNAL COUNTS (tradable): ' + ', '.join(f'{n}={int((s & f.tradable).sum())}' for n, _, s, _, _ in SIGS))
cols = ['test', 'entry', 'H', 'n', 'raw_net', 'vsN_net', 'win_pct', 'nq', 'q_pos', 't_q', 'vsN_net_first14',
        'vsN_net_last8', 'vsN_net_wo_best5', 'pool_vsN_net', 'd_vs_pool', 'd_first14', 'd_last8', 'p_luck',
        'p_luck_holm', 'p_t_holm', 'verdict']
P_('\nALL 84 PRIMARY TESTS (percent; vsN = Nifty-hedged; net after 0.17% + 0.02% hedge; shorts sign-flipped):')
P_(res[cols].round(3).to_string(index=False))
P_('\nInteraction tests, unconditional luck p (pool = all eligible results, secondary):')
P_(res[res.test.str.startswith('I')][['test', 'entry', 'H', 'n', 'vsN_net', 'p_luck', 'p_luck_uncond']]
   .round(4).to_string(index=False))
P_('\nRaw (unhedged) family: min p_luck_raw = %.4f, min Holm = %.4f' % (res.p_luck_raw.min(), res.p_luck_raw_holm.min()))
P_('\nVerdicts: ' + res.verdict.value_counts().to_dict().__repr__())
P_('Smallest 10 primary luck p:')
P_(res.nsmallest(10, 'p_luck')[['test', 'entry', 'H', 'n', 'vsN_net', 't_q', 'p_luck', 'p_luck_holm', 'verdict']]
   .round(4).to_string(index=False))
