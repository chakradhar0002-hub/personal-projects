#!/usr/bin/env python3
"""
F3 addendum -- ADDED AFTER seeing the main and placebo results. CHECKS ONLY: no new
tradable variant is introduced (variant count stays 35). Purpose: describe the
candidates that crossed |t|>=2.5 (B5, BC5) and the two closest sector refinements
(A1, BC3) against more placebos, and test how results-specific the base drift is.

K1  random F&O results with the same per-quarter counts (2000 reps) for B3, A1, B5, BC3, BC5
K2  B3 minus PL1 (non-results XN>4 days) by calendar quarter, first 14 vs last 8
    calendar quarters; same for XN>6 (B5 vs non-results XN>6 days).
K3  robustness: median quarter, mean without the best quarter, leave-one-quarter-out min t
K4  BC5 composition: no group vs group with <2 reported peers; position in season.
K5  (COUNTED as variant #36) prior-work reproduction: events.next20 starts at the
    Day+1 close (i_p1), not at the reaction close. For during-market results that is
    one session later than the brief's rule. Same winners (XN>4%), entry at the Day+1
    close, hold 20 sessions (= events.next20 / next20_vs_nifty), costs as main.
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
rng = np.random.default_rng(4242)
log = open(f'{OUT}/run_addendum.txt', 'w')


def P_(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    log.write(s + '\n')


def qser(t, col='net_vsN'):
    return t.groupby('qn')[col].mean()


def tstat(q):
    return q.mean() / (q.std(ddof=1) / np.sqrt(len(q)))


T = pd.read_csv(f'{OUT}/trades.csv')
fo = m.fo
allfo = m.build(fo, 20)
pools = {q: allfo[allfo.qn == q].net_vsN.values for q in allfo.qn.unique()}
cands = ['B3 XN>4 H20', 'A1 XS>4 H20', 'B5 XN>6 H20', 'BC3 PS>2 H20', 'BC5 n<2 H20']
rows = []
P_('K1 random F&O results, same per-quarter counts (2000 reps), hedged vs Nifty')
for v in cands:
    t = T[T.label == v]
    q = qser(t)
    obs_m, obs_t = q.mean(), tstat(q)
    c = t.groupby('qn').size()
    sim = []
    for r in range(2000):
        qs = {qq: rng.choice(pools[qq], size=n, replace=False).mean() for qq, n in c.items()}
        s = pd.Series(qs)
        sim.append((s.mean(), tstat(s), s[s.index < 14].mean(), s[s.index >= 14].mean()))
    sim = np.array(sim)
    pm = (sim[:, 0] >= obs_m).mean()
    pt = (sim[:, 1] >= obs_t).mean()
    pr = ((sim[:, 1] >= 2.5) & (sim[:, 2] > 0) & (sim[:, 3] > 0)).mean()
    # K3 robustness
    med = q.median()
    nobest = q.drop(q.idxmax()).mean()
    loo = min(tstat(q.drop(k)) for k in q.index)
    P_(f'  {v:14s} obs {obs_m*100:5.2f} t {obs_t:4.2f} | random mean {sim[:,0].mean()*100:5.2f} 95% {np.percentile(sim[:,0],95)*100:5.2f} '
       f'p(q_avg) {pm:.4f} p(t) {pt:.4f} random promising-like {pr:.4f} | median q {med*100:.2f}, '
       f'mean w/o best q {nobest*100:.2f}, LOO min t {loo:.2f}')
    rows.append(dict(variant=v, obs_q_avg=obs_m * 100, obs_t=obs_t, rand_mean=sim[:, 0].mean() * 100,
                     rand_p95=np.percentile(sim[:, 0], 95) * 100, p_q_avg=pm, p_t=pt, rand_promising_like=pr,
                     median_q=med * 100, mean_wo_best_q=nobest * 100, loo_min_t=loo))
pd.DataFrame(rows).to_csv(f'{OUT}/addendum_random_results.csv', index=False)

# K2 results-specific part of the drift
P_('\nK2 results drift minus non-results big-up-day drift (calendar quarters)')
pl1 = pd.read_csv(f'{OUT}/pl1_nonresults_trades.csv')
R, nret = m.R, m.nret


def nonres(th):
    """same construction as PL1 (f3_placebo.py) with threshold th"""
    if th == 0.04:
        return pl1
    first_i = int(fo.i_react.min())
    last_i = m.NS - 21
    evs = m.ev.sort_values('i_cut')
    out = []
    for sym, k in m.SYM.items():
        e = evs[evs.symbol == sym]
        if len(e) == 0:
            continue
        excl = np.zeros(m.NS, bool)
        for a, z in zip(e.i_cut, e.i_react):
            excl[a:z + 6] = True
        status = np.zeros(m.NS, bool)
        ic = e.i_cut.values
        ff = e.in_fo.values.astype(bool)
        for j in range(len(e)):
            status[ic[j]:(ic[j + 1] if j + 1 < len(e) else m.NS)] = ff[j]
        status[:ic[0]] = ff[0]
        x = R[:, k] - nret
        nxt = 0
        for i in range(first_i, last_i):
            if i < nxt or excl[i] or not status[i] or np.isnan(R[i, k]) or not (x[i] > th):
                continue
            raw, nb = m.stock_hold(sym, i, 20)
            if np.isnan(raw) or nb > 2:
                continue
            nf, _ = m.index_hold('Nifty 50', i, 20)
            out.append(dict(symbol=sym, i=i, day=m.ses.day.iloc[i], raw=raw, nifty=nf))
            nxt = i + 21
    d = pd.DataFrame(out)
    d['net_vsN'] = d.raw - d.nifty - m.COST - m.HEDGE
    return d


for v, th in (('B3 XN>4 H20', 0.04), ('B5 XN>6 H20', 0.06)):
    nr = nonres(th).copy()
    nr['per'] = pd.PeriodIndex(nr.day, freq='Q').astype(str)
    t = T[T.label == v].copy()
    t['per'] = pd.PeriodIndex(m.ses.day.iloc[t.i_entry].values, freq='Q').astype(str)
    a = t.groupby('per').net_vsN.mean()
    b = nr.groupby('per').net_vsN.mean()
    d = (a - b).dropna().sort_index()
    f, l = d.iloc[:14], d.iloc[14:]
    P_(f'  {v}: non-results n={len(nr)} q_avg {b.mean()*100:.2f} (t {tstat(b):.2f}); results q_avg (cal.) {a.mean()*100:.2f}; '
       f'difference {d.mean()*100:.2f} t {tstat(d):.2f}; first 14 cal. q {f.mean()*100:.2f}, last {len(l)} {l.mean()*100:.2f}')
    P_(f'     non-results drift first 14 cal. q {b.sort_index().iloc[:14].mean()*100:.2f}, last {len(b)-14} {b.sort_index().iloc[14:].mean()*100:.2f}')

# K4 BC5 composition
W = fo[fo.XN > m.T4].copy()
bc5 = W[W.PS.isna()]
P_('\nK4 BC5 composition')
P_(f'  no group: {bc5.grp.isna().sum()}, group with <2 reported peers: {bc5.grp.notna().sum()} of {len(bc5)}')
# season position: rank of reaction day within the quarter (fraction of F&O results already out)
frac = []
for w in W.itertuples():
    qq = fo[fo.qn == w.qn]
    frac.append((qq.i_react < w.i_react).mean())
W['season_frac'] = frac
P_(f'  share of quarter F&O results already out at reaction day: BC5 median {W.loc[W.PS.isna(),"season_frac"].median():.2f}, '
   f'other winners median {W.loc[W.PS.notna(),"season_frac"].median():.2f}')
tb = T[T.label == 'B3 XN>4 H20'].copy()
tb = tb.merge(W[['symbol', 'qn', 'grp', 'PS']], on=['symbol', 'qn'])
for nm, sub in (('BC5 no group', tb[tb.grp.isna()]), ('BC5 group, <2 peers', tb[tb.grp.notna() & tb.PS.isna()])):
    q = qser(sub)
    P_(f'  {nm}: n={len(sub)} q_avg {q.mean()*100:.2f} t {tstat(q):.2f} nq {len(q)}')

# K5 prior-work definition (entry at Day+1 close)
P_('\nK5 (variant #36) winners XN>4%, entry at Day+1 close (events.next20), hold 20')
Wk = fo[fo.XN > m.T4].copy()
tk = m.build(Wk, 20, entry_col='i_p1', label='K5 XN>4 H20 entry Day+1 close')
ev20 = Wk.set_index(['symbol', 'qn']).next20
chk = (tk.set_index(['symbol', 'qn']).raw - ev20).abs().max()
for col in ('net_raw', 'net_vsN', 'net_vsS'):
    q = qser(tk, col)
    P_(f'  {col}: trade avg {tk[col].mean()*100:.2f} q_avg {q.mean()*100:.2f} t {tstat(q):.2f} '
       f'first14 {q[q.index<14].mean()*100:.2f} last8 {q[q.index>=14].mean()*100:.2f} qpos {(q>0).sum()}/{len(q)}')
P_(f'  max |raw - events.next20| = {chk:.2e}; during-market/non-trading/before-open winners: {(Wk.i_react==Wk.i_rd).sum()} of {len(Wk)}')
first15 = tk[tk.qn < 15]
q15 = qser(first15, 'net_raw')
P_(f'  first 15 quarters only (prior study span?): raw trade avg {first15.net_raw.mean()*100:.2f}, q_avg {q15.mean()*100:.2f}, qpos {(q15>0).sum()}/{len(q15)}')
s5 = m.summarize(tk, 'K5 XN>4 H20 entry Day+1 close', 20)
pd.DataFrame([s5]).to_csv(f'{OUT}/addendum_K5_summary.csv', index=False)
log.close()
