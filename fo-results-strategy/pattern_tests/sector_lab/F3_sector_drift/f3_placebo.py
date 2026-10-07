#!/usr/bin/env python3
"""
F3 placebo / control checks (pre-registered in f3_sector_drift.py header; not counted
as variants). Uses the trade builder and features of the main script.

PL0  unconditional baseline: (i) every F&O result, buy at reaction close, H=20;
     (ii) random subsets of ALL F&O results with the same count per quarter as the
     base B3 (2000 reps) -> how often does a random pick match B3?
PL1  non-results big up days: stock beats Nifty by >4% on a session outside
     [i_cut, i_react+5] of all its results, F&O at the time (in_fo of its most
     recent results event), buy at close, hold 20, no overlapping trades per stock.
     Grouped by calendar quarter of entry.
PL2  random subsets of base winners (same count per quarter as the variant),
     2000 reps, for every subset variant (A3, BC1-5, C1-4, B5) at its horizon.
PL3  random peers for D1/D2 (stocks of OTHER groups with the same status), 300 reps.
PL4  random stock->sector map for A1 (H=20), 300 reps.
Also: base B3 t with clustering by reaction date (indicative only: 20-day windows
of nearby dates overlap, so the quarter t is the honest one).
"""
import os  # SECTOR_LAB: folder holding data/ from sector_lab_data.py
import sys
sys.path.append('/root/.local/lib/python3.11/site-packages')
import importlib.util
import numpy as np
import pandas as pd

OUT = os.environ.get('SECTOR_LAB', 'sector_lab') + '/F3_sector_drift'
spec = importlib.util.spec_from_file_location('f3main', OUT + '/f3_sector_drift.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
rng = np.random.default_rng(777)
log = open(f'{OUT}/run_placebo.txt', 'w')


def P_(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    log.write(s + '\n')


fo = m.fo
W = fo[fo.XN > m.T4]
res = []


def qmean_t(qn, x):
    q = pd.Series(x).groupby(np.asarray(qn)).mean()
    n = len(q)
    mm = q.mean()
    t = mm / (q.std(ddof=1) / np.sqrt(n)) if n > 1 else np.nan
    f = q[q.index < 14].mean()
    l = q[q.index >= 14].mean()
    return mm, t, f, l


# ---------------------------------------------------------------- base trades at H=5,20
base = {H: m.build(W, H, label=f'B H{H}') for H in (5, 20)}
for H in (5, 20):
    b = base[H]
    b['i_react'] = b.i_entry
    mm, t, f, l = qmean_t(b.qn, b.net_vsN)
    P_(f'base H{H}: n={len(b)} q_avg={mm*100:.2f} t={t:.2f} first14={f*100:.2f} last8={l*100:.2f}')

# date-clustered t for B3
b = base[20]
dmean = b.groupby('i_entry').net_vsN.mean()
P_(f'B3 clustered by reaction date: {len(dmean)} dates, mean {dmean.mean()*100:.2f}, '
   f't {dmean.mean()/(dmean.std(ddof=1)/np.sqrt(len(dmean))):.2f} (overlapping windows -> optimistic)')

# ---------------------------------------------------------------- PL0
allfo = m.build(fo, 20, label='PL0 all F&O results H20')
mm, t, f, l = qmean_t(allfo.qn, allfo.net_vsN)
mr, tr_, fr, lr = qmean_t(allfo.qn, allfo.net_raw)
P_(f'\nPL0(i) all F&O results, H20: n={len(allfo)} vsN q_avg={mm*100:.2f} t={t:.2f} first14={f*100:.2f} '
   f'last8={l*100:.2f} | raw q_avg={mr*100:.2f} first14={fr*100:.2f} last8={lr*100:.2f}')
res.append(dict(check='PL0 all F&O results H20', n=len(allfo), q_avg=mm * 100, t=t, first14=f * 100, last8=l * 100))
allfo5 = m.build(fo, 5, label='PL0 H5')
mm5, t5, f5, l5 = qmean_t(allfo5.qn, allfo5.net_vsN)
P_(f'PL0(i) all F&O results, H5: vsN q_avg={mm5*100:.2f} t={t5:.2f}')

# PL0(ii) random subsets of all F&O results with B3's per-quarter counts
cnt = base[20].groupby('qn').size()
grp_all = {q: allfo[allfo.qn == q].net_vsN.values for q in cnt.index}
obs_m, obs_t, obs_f, obs_l = qmean_t(base[20].qn, base[20].net_vsN)
NR = 2000
sim = np.empty((NR, 4))
for r in range(NR):
    qs, xs = [], []
    for q, n in cnt.items():
        pool = grp_all[q]
        pick = rng.choice(pool, size=min(n, len(pool)), replace=False)
        qs += [q] * len(pick)
        xs += list(pick)
    sim[r] = qmean_t(qs, xs)
p_m = (sim[:, 0] >= obs_m).mean()
p_t = (sim[:, 1] >= obs_t).mean()
p_both = ((sim[:, 2] > 0) & (sim[:, 3] > 0) & (sim[:, 1] >= obs_t)).mean()
P_(f'PL0(ii) random F&O results, B3 counts: random q_avg mean {sim[:,0].mean()*100:.2f} '
   f'(95th pct {np.percentile(sim[:,0],95)*100:.2f}); P(random >= B3 q_avg {obs_m*100:.2f}) = {p_m:.4f}; '
   f'P(t>={obs_t:.2f}) = {p_t:.4f}; P(both halves>0 & t>=obs) = {p_both:.4f}')
res.append(dict(check='PL0(ii) random F&O results vs B3', n=len(base[20]), q_avg=sim[:, 0].mean() * 100,
                p_value=p_m, p_t=p_t))

# ---------------------------------------------------------------- PL1 non-results big up days
R, nret = m.R, m.nret
first_i = int(fo.i_react.min())
last_i = m.NS - 21
evs = m.ev.sort_values('i_cut')
rows = []
for sym, k in m.SYM.items():
    e = evs[evs.symbol == sym]
    if len(e) == 0:
        continue
    excl = np.zeros(m.NS, bool)
    for a, z in zip(e.i_cut, e.i_react):
        excl[a:z + 6] = True
    # F&O status = in_fo of most recent event with i_cut <= i (first event before that)
    status = np.zeros(m.NS, bool)
    ic = e.i_cut.values
    fo_flag = e.in_fo.values.astype(bool)
    for j in range(len(e)):
        a = ic[j]
        z = ic[j + 1] if j + 1 < len(e) else m.NS
        status[a:z] = fo_flag[j]
    status[:ic[0]] = fo_flag[0]
    x = R[:, k] - nret
    nxt = 0
    for i in range(first_i, last_i):
        if i < nxt or excl[i] or not status[i]:
            continue
        if np.isnan(R[i, k]) or not (x[i] > 0.04):
            continue
        raw, nb = m.stock_hold(sym, i, 20)
        if np.isnan(raw) or nb > 2:
            continue
        nf, _ = m.index_hold('Nifty 50', i, 20)
        rows.append(dict(symbol=sym, i=i, day=m.ses.day.iloc[i], raw=raw, nifty=nf))
        nxt = i + 21
pl1 = pd.DataFrame(rows)
pl1['net_vsN'] = pl1.raw - pl1.nifty - m.COST - m.HEDGE
pl1['per'] = pd.PeriodIndex(pl1.day, freq='Q').astype(str)
q = pl1.groupby('per').net_vsN.mean()
P_(f'\nPL1 non-results days with XN>4%, H20: n={len(pl1)} trade avg {pl1.net_vsN.mean()*100:.2f}, '
   f'{len(q)} calendar quarters, q_avg {q.mean()*100:.2f}, t {q.mean()/(q.std(ddof=1)/np.sqrt(len(q))):.2f}, '
   f'first half {q.iloc[:len(q)//2].mean()*100:.2f}, second half {q.iloc[len(q)//2:].mean()*100:.2f}')
pl1.to_csv(f'{OUT}/pl1_nonresults_trades.csv', index=False)
res.append(dict(check='PL1 non-results XN>4 H20', n=len(pl1), q_avg=q.mean() * 100,
                t=q.mean() / (q.std(ddof=1) / np.sqrt(len(q)))))
# same-period comparison: B3 by calendar quarter
b3 = base[20].copy()
b3['per'] = pd.PeriodIndex(m.ses.day.iloc[b3.i_entry].values, freq='Q').astype(str)
cmp_ = pd.DataFrame({'B3': b3.groupby('per').net_vsN.mean(), 'PL1': q}).dropna()
d = cmp_.B3 - cmp_.PL1
P_(f'B3 minus PL1 by calendar quarter ({len(d)} common quarters): {d.mean()*100:.2f}, t {d.mean()/(d.std(ddof=1)/np.sqrt(len(d))):.2f}')

# ---------------------------------------------------------------- PL2 random subsets of base winners
S = pd.read_csv(f'{OUT}/summary.csv')
T = pd.read_csv(f'{OUT}/trades.csv')
subset_vars = [v for v in S.variant if v.startswith(('A3', 'BC', 'C1', 'C2', 'C3', 'C4', 'B5'))]
P_('\nPL2 random subsets of base winners (2000 reps, same count per quarter)')
pl2 = []
for v in subset_vars:
    H = int(S.loc[S.variant == v, 'H'].iloc[0])
    t = T[T.label == v]
    obs = qmean_t(t.qn, t.net_vsN)
    bb = base[H]
    pools = {qq: bb[bb.qn == qq].net_vsN.values for qq in bb.qn.unique()}
    c = t.groupby('qn').size()
    sim = np.empty((NR, 4))
    for r in range(NR):
        qs, xs = [], []
        for qq, n in c.items():
            pick = rng.choice(pools[qq], size=n, replace=False)
            qs += [qq] * n
            xs += list(pick)
        sim[r] = qmean_t(qs, xs)
    p_m = (sim[:, 0] >= obs[0]).mean()
    p_t = (sim[:, 1] >= obs[1]).mean()
    p_all = ((sim[:, 1] >= obs[1]) & (sim[:, 2] > 0) & (sim[:, 3] > 0)).mean()
    d = dict(variant=v, H=H, n=len(t), obs_q_avg=obs[0] * 100, obs_t=obs[1], obs_first14=obs[2] * 100,
             obs_last8=obs[3] * 100, rand_q_avg_mean=sim[:, 0].mean() * 100,
             rand_q_avg_95=np.percentile(sim[:, 0], 95) * 100, p_q_avg=p_m, p_t=p_t, p_t_and_halves=p_all,
             rand_frac_promising_like=((np.abs(sim[:, 1]) >= 2.5) & (sim[:, 2] > 0) & (sim[:, 3] > 0)).mean())
    pl2.append(d)
    P_(f"  {v:22s} n={len(t):4d} obs q_avg {obs[0]*100:6.2f} t {obs[1]:5.2f} | random mean {d['rand_q_avg_mean']:5.2f} "
       f"95% {d['rand_q_avg_95']:5.2f} | p(q_avg) {p_m:.3f} p(t) {p_t:.3f} p(t&halves) {p_all:.3f} "
       f"| random 'promising-like' {d['rand_frac_promising_like']:.3f}")
pd.DataFrame(pl2).to_csv(f'{OUT}/placebo_random_subsets.csv', index=False)

# ---------------------------------------------------------------- PL3 random peers for D
P_('\nPL3 random peers for D (300 reps)')
lag = {'weak': pd.read_csv(f'{OUT}/laggards_weak.csv'), 'notyet': pd.read_csv(f'{OUT}/laggards_notyet.csv')}
fo_g = fo[fo.grp.notna()]
# precompute stock holding net_vsN for (symbol, i_entry, H) lazily
cache = {}


def nvsn(sym, i0, H):
    key = (sym, i0, H)
    if key not in cache:
        raw, nb = m.stock_hold(sym, i0, H)
        nf, _ = m.index_hold('Nifty 50', i0, H)
        cache[key] = np.nan if (np.isnan(raw) or nb > 2) else raw - nf - m.COST - m.HEDGE
    return cache[key]


Wg = W[W.grp.notna()].sort_values('i_react')
NR3 = 300
pl3 = []
for kind, nm in (('weak', 'D1'), ('notyet', 'D2')):
    # true count of peers per trigger before dedupe
    true_rows = []
    for w in Wg.itertuples():
        p = fo_g[(fo_g.qn == w.qn) & (fo_g.grp == w.grp) & (fo_g.symbol != w.symbol)]
        p = p[(p.i_react <= w.i_react) & (p.XN < 0)] if kind == 'weak' else p[p.i_react > w.i_react]
        oth = fo_g[(fo_g.qn == w.qn) & (fo_g.grp != w.grp) & (fo_g.symbol != w.symbol)]
        oth = oth[(oth.i_react <= w.i_react) & (oth.XN < 0)] if kind == 'weak' else oth[oth.i_react > w.i_react]
        true_rows.append((w.qn, w.i_react, len(p), oth.symbol.values))
    for H in (5, 20):
        t = T[T.label == f"{'D1 reported-weak peers' if kind=='weak' else 'D2 not-yet-reported peers'} H{H}"]
        obs = qmean_t(t.qn, t.net_vsN)
        sims = []
        for r in range(NR3):
            picks = []
            for qn, ir, n, oth in true_rows:
                if n == 0 or len(oth) == 0:
                    continue
                ch = rng.choice(oth, size=min(n, len(oth)), replace=False)
                picks += [(s, qn, ir) for s in ch]
            dfp = pd.DataFrame(picks, columns=['symbol', 'qn', 'i']).drop_duplicates(['symbol', 'qn'], keep='first')
            x = np.array([nvsn(s, i, H) for s, i in zip(dfp.symbol, dfp.i)])
            ok = ~np.isnan(x)
            sims.append(qmean_t(dfp.qn.values[ok], x[ok]))
        sims = np.array(sims)
        p_m = (sims[:, 0] >= obs[0]).mean()
        P_(f'  {nm} H{H}: obs q_avg {obs[0]*100:.2f} t {obs[1]:.2f} | random-peer mean {sims[:,0].mean()*100:.2f} '
           f'[5%,95%] [{np.percentile(sims[:,0],5)*100:.2f},{np.percentile(sims[:,0],95)*100:.2f}] p(random>=obs) {p_m:.3f}')
        pl3.append(dict(variant=f'{nm} H{H}', obs_q_avg=obs[0] * 100, obs_t=obs[1], rand_mean=sims[:, 0].mean() * 100,
                        rand_p5=np.percentile(sims[:, 0], 5) * 100, rand_p95=np.percentile(sims[:, 0], 95) * 100,
                        p_random_ge_obs=p_m))
pd.DataFrame(pl3).to_csv(f'{OUT}/placebo_random_peers.csv', index=False)

# ---------------------------------------------------------------- PL4 random sector map for A1
P_('\nPL4 random stock->sector map for A1 H20 (300 reps)')
t = T[T.label == 'A1 XS>4 H20']
obs = qmean_t(t.qn, t.net_vsN)
syms = fo.symbol.unique()
secmap = fo.groupby('symbol').sector_index.first()
rr = fo.r_react.values
ireact = fo.i_react.values
# daily sector return lookup with fallback
sec_d = {s: np.r_[np.nan, m.IDX[s][1:] / m.IDX[s][:-1] - 1] for s in m.SECTORS}
n500d = np.r_[np.nan, m.N500[1:] / m.N500[:-1] - 1]
NR4 = 300
sims = []
for r in range(NR4):
    perm = dict(zip(secmap.index, rng.permutation(secmap.values)))
    secs = fo.symbol.map(perm).values
    sd = np.array([sec_d[s][i] if not np.isnan(sec_d[s][i]) else n500d[i] for s, i in zip(secs, ireact)])
    sel = (rr - sd) > m.T4
    sub = fo[sel]
    x = np.array([nvsn(s, i, 20) for s, i in zip(sub.symbol, sub.i_react)])
    ok = ~np.isnan(x)
    sims.append(qmean_t(sub.qn.values[ok], x[ok]))
sims = np.array(sims)
P_(f'  A1: obs q_avg {obs[0]*100:.2f} t {obs[1]:.2f} | random-sector mean {sims[:,0].mean()*100:.2f} '
   f'[5%,95%] [{np.percentile(sims[:,0],5)*100:.2f},{np.percentile(sims[:,0],95)*100:.2f}] '
   f'p(random>=obs) {(sims[:,0]>=obs[0]).mean():.3f}; p(t>=obs) {(sims[:,1]>=obs[1]).mean():.3f}')
res.append(dict(check='PL4 A1 random sector map', n=len(t), q_avg=sims[:, 0].mean() * 100,
                p_value=(sims[:, 0] >= obs[0]).mean()))
pd.DataFrame(res).to_csv(f'{OUT}/placebo_misc.csv', index=False)
log.close()
