"""Step 3: stress tests of S1 / S3 / W_NEAR52H. Own code; reads only vb_tradable.csv / vb_history.csv (built by build.py)
plus the raw price files for the placebo and the shifted-entry checks."""
import numpy as np, pandas as pd

SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
D = SP + '/sector_lab/data'
OUT = SP + '/perf/verify_B_post_results'
t = pd.read_csv(f'{OUT}/vb_tradable.csv')
p = pd.read_csv(f'{OUT}/vb_panel.csv')
h = pd.read_csv(f'{OUT}/vb_history.csv')
rng = np.random.default_rng(91)
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a); print(s); LOG.append(s)


t['year'] = t.reaction_day_s.str[:4].astype(int)
t['first14'] = t.qn <= 13
eligS = t.mean_drift_4.notna()
eligN = t.W & t.dist_52wh.notna()
CANDS = {'S1_DRIFT4_Q5': (t.S1, eligS), 'S3_CONSIST_DRIFT': (t.S3 & eligS, eligS), 'W_NEAR52H': (t.NEAR, eligN)}


def gain(sel, par, df=t):
    pm = df[par].groupby('qn').vsN_net.mean()
    x = df[sel]
    return x.vsN_net - x.qn.map(pm), x


def summ(sel, par, df=t):
    d, x = gain(sel, par, df)
    if len(x) == 0:
        return dict(n=0)
    qm = d.groupby(x.qn).mean()
    return dict(n=len(x), avg=round(x.vsN_net.mean(), 2), gain=round(d.mean(), 2), q_dpos=f'{(qm > 0).sum()}/{len(qm)}',
                t_q=round(qm.mean() / qm.std() * np.sqrt(len(qm)), 2) if len(qm) > 2 else np.nan)


def luck(sel, par, df=t, ndraw=20000):
    x = df[sel]
    obs = x.vsN_net.mean()
    tot = np.zeros(ndraw)
    for q, nq in x.groupby('qn').size().items():
        pool = df[par & (df.qn == q)].vsN_net.to_numpy()
        idx = np.argsort(rng.random((ndraw, len(pool))), axis=1)[:, :nq]
        tot += pool[idx].sum(1)
    m = tot / len(x)
    return (1 + (m >= obs).sum()) / (1 + ndraw)


# ------------------------------------------------------------------ 1. basic + luck p
P('=== 1. recomputed + own luck p (20,000 same-quarter random picks from the parent) ===')
for nm, (sel, par) in CANDS.items():
    P(nm, summ(sel, par), 'luck p', round(luck(sel, par), 5))

# ------------------------------------------------------------------ 2. leave-one-quarter-out, w/o best 5/10
P('\n=== 2. leave-one-quarter-out (gain), without best 5 / 10 trades ===')
for nm, (sel, par) in CANDS.items():
    d, x = gain(sel, par)
    lo = []
    for q in sorted(x.qn.unique()):
        lo.append((q, d[x.qn != q].mean(), x.vsN_net[x.qn != q].mean()))
    lo = pd.DataFrame(lo, columns=['qn', 'gain', 'avg'])
    w = lo.loc[lo.gain.idxmin()]
    P(f'{nm}: LOQO gain min {w.gain:+.2f} (drop qn {int(w.qn)}), max {lo.gain.max():+.2f}; avg min {lo.avg.min():+.2f}')
    for nb in (5, 10, 20):
        keep = x.vsN_net.rank(ascending=False, method='first') > nb
        keepd = d.rank(ascending=False, method='first') > nb
        P(f'   w/o best {nb:2d} by vsN_net: avg {x.vsN_net[keep].mean():+.2f} gain {d[keep].mean():+.2f}   '
          f'| w/o best {nb} by gain: gain {d[keepd].mean():+.2f}')
    # drop the best quarter and the best 2 quarters by per-quarter gain sum
    qs = d.groupby(x.qn).sum().sort_values(ascending=False)
    for nq in (1, 2, 3):
        kk = ~x.qn.isin(qs.index[:nq])
        P(f'   w/o best {nq} quarter(s) by gain contribution {list(qs.index[:nq])}: gain {d[kk].mean():+.2f} avg {x.vsN_net[kk].mean():+.2f} n {kk.sum()}')

# ------------------------------------------------------------------ 3. by year
P('\n=== 3. by calendar year of the reaction day / by quarter ===')
for nm, (sel, par) in CANDS.items():
    d, x = gain(sel, par)
    by = pd.DataFrame({'y': x.year, 'd': d, 'v': x.vsN_net}).groupby('y').agg(n=('d', 'size'), avg=('v', 'mean'),
                                                                          gain=('d', 'mean'), gsum=('d', 'sum'))
    by['share_of_total_gain'] = by.gsum / by.gsum.sum()
    P(nm); P(by.round(2).to_string())
    if nm == 'S1_DRIFT4_Q5':
        pq = pd.DataFrame({'qn': x.qn, 'rf': x.results_for, 'd': d, 'v': x.vsN_net}).groupby(['qn', 'rf']).agg(
            n=('d', 'size'), avg=('v', 'mean'), gain=('d', 'mean'))
        P(pq.round(2).to_string())
        pq.round(3).to_csv(f'{OUT}/S1_per_quarter.csv')

# ------------------------------------------------------------------ 4. nearby cut-offs / definitions for S1
P('\n=== 4. S1 nearby cut-offs and definitions (gain vs eligible parent, first14 | last8) ===')


def halves(sel, par):
    d, x = gain(sel, par)
    f = x.qn <= 13
    return f'n {len(x):4d} avg {x.vsN_net.mean():+.2f} gain {d.mean():+.2f} | f14 {d[f].mean():+.2f} l8 {d[~f].mean():+.2f} | ' \
           f'l8 avg {x.vsN_net[~f].mean():+.2f} | q+ {(d.groupby(x.qn).mean() > 0).sum()}/{x.qn.nunique()}'


for frac in (0.5, 0.6, 0.67, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95):
    th = p.groupby('qn').mean_drift_4.quantile(frac)
    P(f'  top {100 - frac * 100:4.0f}% mean_drift_4: ', halves(t.mean_drift_4 >= t.qn.map(th), eligS))
for lo_, hi_ in ((0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0)):
    a = t.qn.map(p.groupby('qn').mean_drift_4.quantile(lo_)); b = t.qn.map(p.groupby('qn').mean_drift_4.quantile(hi_))
    sel = (t.mean_drift_4 >= a) & ((t.mean_drift_4 < b) if hi_ < 1 else True)
    P(f'  quintile {lo_:.1f}-{hi_:.1f}:            ', halves(sel & eligS, eligS))
for th in (0, 2, 3, 4, 5, 6, 8):
    P(f'  fixed mean_drift_4 > {th}:           ', halves(t.mean_drift_4 > th, eligS))
for col in ('mean_drift_3', 'mean_drift_6', 'mean_drift_8', 'mean_drift_all', 'median_drift_4'):
    th = p.groupby('qn')[col].quantile(0.8)
    el = t[col].notna()
    P(f'  top 20% {col:15s}:      ', halves(t[col] >= t.qn.map(th), el), f' (parent: {col} known)')
# strictly causal threshold: previous quarter's 80th percentile
thp = p.groupby('qn').mean_drift_4.quantile(0.8).shift(1)
P('  prev-quarter 80th pct threshold:  ', halves(t.mean_drift_4 >= t.qn.map(thp), eligS & t.qn.map(thp).notna()))
# rank among stocks that already reported in the quarter (expanding, strictly causal in time order)
t = t.sort_values(['qn', 'i_react']).copy()
t['S1_exp'] = False
for q, g in t[eligS.reindex(t.index)].groupby('qn'):
    vals = p[(p.qn == q) & p.mean_drift_4.notna()]
    for i, r in g.iterrows():
        known = vals[vals.i_react <= r.i_react].mean_drift_4  # reported up to today (incl. itself)
        if len(known) >= 20:
            t.loc[i, 'S1_exp'] = r.mean_drift_4 >= known.quantile(0.8)
t = t.sort_index()
P('  expanding within-quarter 80th pct (>=20 reported):', halves(t.S1_exp, eligS))

# ------------------------------------------------------------------ 5. survivorship / joiners
P('\n=== 5. survivorship: in F&O by qn 1 vs later joiners (parent restricted to the same group) ===')
early = t.first_fo_qn <= 1
for nm, (sel, par) in CANDS.items():
    P(nm)
    P('   early (first in F&O by qn<=1): ', summ(sel & early, par & early), ' | vs full parent', summ(sel & early, par))
    P('   later joiners:                 ', summ(sel & ~early, par & ~early), ' | vs full parent', summ(sel & ~early, par))
    P('   qn 17-21 only (universe ~ full 2025-26 list):', summ(sel & (t.qn >= 17), par & (t.qn >= 17)))
P('S1 trades by group:', t[t.S1].groupby(early[t.S1]).size().to_dict(), ' (True = early)')

# ------------------------------------------------------------------ 6. concentration: stocks, sectors
P('\n=== 6. concentration ===')
for nm, (sel, par) in list(CANDS.items())[:2]:
    d, x = gain(sel, par)
    vc = x.symbol.value_counts()
    P(nm, 'trades', len(x), 'stocks', len(vc), 'top 10:', vc.head(10).to_dict())
    bysym = pd.DataFrame({'s': x.symbol, 'd': d}).groupby('s').d.agg(['size', 'sum', 'mean']).sort_values('sum', ascending=False)
    P('   top 10 stocks by gain contribution:', bysym.head(10).round(1).to_dict('index'))
    P(f'   share of total gain from top 5 / 10 contributors: {bysym["sum"].head(5).sum() / bysym["sum"].sum():.2f} / '
      f'{bysym["sum"].head(10).sum() / bysym["sum"].sum():.2f}')
    for ntop in (5, 10, 20):
        drop = vc.index[:ntop]
        P(f'   w/o {ntop} most frequent stocks (dropped from trades AND parent): ',
          summ(sel & ~t.symbol.isin(drop), par & ~t.symbol.isin(drop)))
    drop = bysym.index[:10]
    P('   w/o 10 biggest gain contributors (trades and parent):', summ(sel & ~t.symbol.isin(drop), par & ~t.symbol.isin(drop)))
    # stock-cluster bootstrap of the pooled gain
    syms = vc.index.to_numpy()
    g_by = {s: d[x.symbol == s].to_numpy() for s in syms}
    bs = []
    for _ in range(5000):
        pick = rng.choice(syms, len(syms), replace=True)
        arr = np.concatenate([g_by[s] for s in pick])
        bs.append(arr.mean())
    bs = np.array(bs)
    P(f'   stock-cluster bootstrap of gain: 5th pct {np.percentile(bs, 5):+.2f}, 2.5th {np.percentile(bs, 2.5):+.2f}, '
      f'P(gain<=0) {np.mean(bs <= 0):.3f}')
    # quarter x stock two-way: quarter-cluster bootstrap
    qs = x.qn.unique()
    g_q = {q: d[x.qn == q].to_numpy() for q in qs}
    bq = np.array([np.concatenate([g_q[q] for q in rng.choice(qs, len(qs), replace=True)]).mean() for _ in range(5000)])
    P(f'   quarter-cluster bootstrap of gain: 5th pct {np.percentile(bq, 5):+.2f}, P(gain<=0) {np.mean(bq <= 0):.3f}')
    # within quarter x sector cells
    for cell in ('industry', 'sector_index'):
        pm = t[par].groupby(['qn', cell]).vsN_net.mean()
        dd = x.vsN_net.to_numpy() - pm.reindex(pd.MultiIndex.from_arrays([x.qn, x[cell]])).to_numpy()
        P(f'   gain within quarter x {cell}: {np.nanmean(dd):+.2f} (n {np.isfinite(dd).sum()}); '
          f'f14 {np.nanmean(dd[x.qn.to_numpy() <= 13]):+.2f} l8 {np.nanmean(dd[x.qn.to_numpy() > 13]):+.2f}')
    P('   trades by sector_index:', x.sector_index.value_counts().head(8).to_dict())

# ------------------------------------------------------------------ 7. momentum control and reaction split for S1
P('\n=== 7. S1 controls ===')
d, x = gain(t.S1, eligS)
for col, nb in (('vsN_252', 5), ('vsN_63', 5)):
    el = eligS & t[col].notna()
    t['_b'] = t[el].groupby('qn')[col].transform(lambda s: pd.qcut(s.rank(method='first'), nb, labels=False))
    pm = t[el].groupby(['qn', '_b']).vsN_net.mean()
    xx = t[t.S1 & el]
    dd = xx.vsN_net.to_numpy() - pm.reindex(pd.MultiIndex.from_arrays([xx.qn, xx._b])).to_numpy()
    P(f'   gain within quarter x {col} quintile: {np.nanmean(dd):+.2f} n {len(dd)}; f14 {np.nanmean(dd[xx.qn.to_numpy() <= 13]):+.2f} '
      f'l8 {np.nanmean(dd[xx.qn.to_numpy() > 13]):+.2f}')
    P(f'   S1 share in top {col} quintile: {(xx._b == nb - 1).mean():.2f}')
for lab, m_ in (('XN<=0', t.XN <= 0), ('0<XN<=4', (t.XN > 0) & (t.XN <= 4)), ('XN>4', t.XN > 4)):
    P(f'   S1 & {lab:8s}: vs same-reaction parent', summ(t.S1 & m_, eligS & m_), '| l8:', summ(t.S1 & m_ & (t.qn > 13), eligS & m_ & (t.qn > 13)))
P('   S1 & W vs all W (eligible):', summ(t.S1 & t.W, eligS & t.W))

# ------------------------------------------------------------------ 8. shifted entries (same stocks, same quarter, later / earlier)
P('\n=== 8. same S1 flag, entry shifted away from the results (is it a results effect or a stock trait?) ===')
ses = pd.read_csv(f'{D}/sessions.csv')
ret = pd.read_csv(f'{D}/returns.csv', index_col=0)
ixc = pd.read_csv(f'{D}/index_close.csv', index_col=0, usecols=['day', 'Nifty 50'])
NS = len(ses)
R = ret.to_numpy(float); PX = np.cumprod(1 + np.nan_to_num(R), axis=0); VAL = ~np.isnan(R)
NIF = ixc['Nifty 50'].to_numpy(float)
SYM = {s: j for j, s in enumerate(ret.columns)}


def hedged(j, k0, H=20):
    j = np.asarray(j, int); k0 = np.asarray(k0, int)
    ok = (k0 >= 0) & (k0 + H <= NS - 1)
    kk = np.where(ok, k0, 0); ii = kk + np.where(ok, H, 0)
    v = ((PX[ii, j] / PX[kk, j]) - (NIF[ii] / NIF[kk])) * 100 - 0.19
    bl = np.zeros(len(kk), int)
    for s_ in range(1, H + 1):
        bl += ~VAL[np.minimum(kk + s_, NS - 1), j]
    return np.where(ok & (bl <= 2), v, np.nan)


jj = t.symbol.map(SYM).to_numpy(int)
for lab, k0 in (('pre: cutoff-20 -> cutoff (before results)', t.i_cut.to_numpy() - 20),
                ('results: k -> k+20 (the trade)', t.i_react.to_numpy()),
                ('k+20 -> k+40', t.i_react.to_numpy() + 20), ('k+40 -> k+60', t.i_react.to_numpy() + 40)):
    tt = t.copy(); tt['vsN_net'] = hedged(jj, k0)
    if lab.startswith('pre'):  # only rows whose track record was fully known at the window start
        okr = (tt.max_exit_used < k0)
    else:
        okr = pd.Series(True, index=tt.index)
    ok = tt.vsN_net.notna() & okr
    d_, x_ = gain(tt.S1 & ok, eligS & ok, tt)
    f = x_.qn <= 13
    P(f'  {lab:45s} n {len(x_)} avg {x_.vsN_net.mean():+.2f} gain {d_.mean():+.2f} | f14 {d_[f].mean():+.2f} l8 {d_[~f].mean():+.2f}')

# ------------------------------------------------------------------ 9. placebo on quiet days (own track record + outcome)
P('\n=== 9. placebo: quiet stock-days (tafa quiet_days list: symbol, session i) with OWN track record and outcome ===')
q = pd.read_csv(f'{SP}/tafa/C_post_results/quiet_days.csv.gz', usecols=['symbol', 'i', 'day'])
q['j'] = q.symbol.map(SYM).astype(int)
q['vsN_net'] = hedged(q.j, q.i)
# require the same tradability as results (k+21 exists, <=2 blanks): approximate with hedged() blanks<=2 over 20 sessions
q = q[q.vsN_net.notna() & (q.i + 21 <= NS - 1)].copy()
hh = h.sort_values(['symbol', 'i_react'])
md4 = np.full(len(q), np.nan)
for s, g in q.groupby('symbol'):
    hs = hh[hh.symbol == s]
    ip1, irc, ex, dr = hs.i_p1.to_numpy(), hs.i_react.to_numpy(), hs.exit20.to_numpy(), hs.drift20.to_numpy()
    for ii_, i in zip(g.index, g.i.to_numpy()):
        pr = np.where((ip1 < i) & (irc < i))[0]
        if len(pr) >= 4:
            l4 = pr[-4:]
            kn = l4[ex[l4] < i]
            if len(kn):
                md4[q.index.get_loc(ii_)] = dr[kn].mean()
q['mean_drift_4'] = md4
q['month'] = q.day.str[:7]
qe = q[q.mean_drift_4.notna()].copy()
qe['top'] = qe.mean_drift_4 >= qe.groupby('month').mean_drift_4.transform(lambda s: s.quantile(0.8))
mm = qe.groupby('month').vsN_net.transform('mean')
qe['d'] = qe.vsN_net - mm
x_ = qe[qe.top]
mon = x_.groupby('month').d.mean()
P(f'  quiet days with mean_drift_4: {len(qe)}; top-quintile n {len(x_)}, avg {x_.vsN_net.mean():+.2f}, gain vs month {x_.d.mean():+.2f}, '
  f'month-clustered t {mon.mean() / mon.std() * np.sqrt(len(mon)):.2f}, months+ {(mon > 0).sum()}/{len(mon)}')
for lab, m_ in (('2021-2023', x_.day < '2024'), ('2024-2026', x_.day >= '2024'), ('Jul 2024 on', x_.day >= '2024-07')):
    P(f'    {lab}: n {m_.sum()} gain {x_.d[m_].mean():+.2f}')
# quiet days restricted to the same stock-quarters as S1 trades: quiet days of S1 stocks between k+21 and next result
P('  quiet-day gain when the stock was an S1 pick at its latest result (entry on quiet days after that drift window):')
s1 = t[t.S1][['symbol', 'i_react']]
qq = qe.merge(s1, on='symbol')
qq = qq[(qq.i > qq.i_react + 20) & (qq.i <= qq.i_react + 60)]
P(f'    n {len(qq)} stock-days, gain vs month {qq.d.mean():+.2f}')
qe[['symbol', 'i', 'day', 'mean_drift_4', 'vsN_net', 'top', 'd']].to_csv(f'{OUT}/vb_quiet.csv.gz', index=False,
                                                                        float_format='%.5g', compression='gzip')

# ------------------------------------------------------------------ 10. overlap with other rules
P('\n=== 10. overlap ===')
lag = pd.read_csv(__import__('os').environ.get('REPO_ROOT', '.') + '/results/lag10_volume/trades.csv')
ov = t[t.S1].merge(lag[['symbol', 'qn']], on=['symbol', 'qn'])
P(f'  S1 trades that are also among the 85 trade-A lag10+volume trades (same symbol-quarter): {len(ov)}; '
  f'their S1 avg {ov.vsN_net.mean():+.2f}' if len(ov) else '  none')
P(f'  S1 & W: {int((t.S1 & t.W).sum())}; S1 & XN<=4: {int((t.S1 & ~t.W).sum())}')
# concurrency
ev = t[t.S1]
occ = np.zeros(NS, int)
for k0 in ev.i_react:
    occ[k0 + 1:k0 + 21] += 1
P(f'  max concurrent S1 positions {occ.max()}, median over sessions with any {np.median(occ[occ > 0]):.0f}')

open(f'{OUT}/stress.log', 'w').write('\n'.join(LOG) + '\n')
