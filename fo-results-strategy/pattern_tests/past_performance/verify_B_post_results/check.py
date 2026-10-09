"""Step 1-2: look-ahead checks and recomputation of S1 / S3 / W_NEAR52H (n, avg vsN_net, gain vs same-quarter parent),
compared with the authors' feature panel and trades.csv. Own code."""
import numpy as np, pandas as pd

SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = SP + '/perf/verify_B_post_results'
p = pd.read_csv(f'{OUT}/vb_panel.csv')
au = pd.read_csv(f'{SP}/perf/features/panel.csv')
at = pd.read_csv(f'{SP}/perf/B_post_results/trades.csv')
ao = pd.read_csv(f'{SP}/perf/features/outcomes.csv')
P = print

# ------------------------------------------------------------ feature agreement with the authors' panel
m = p.merge(au[['symbol', 'qn', 'n_prev_B', 'n_drift_4_B', 'n_pos_drift_4_B', 'mean_drift_4_B', 'dist_52wh_B', 'XN']],
            on=['symbol', 'qn'], suffixes=('', '_au'), validate='1:1')
P('rows matched', len(m))
for a, b in [('n_prev', 'n_prev_B'), ('n_drift_4', 'n_drift_4_B'), ('n_pos_drift_4', 'n_pos_drift_4_B'),
             ('mean_drift_4', 'mean_drift_4_B'), ('dist_52wh', 'dist_52wh_B'), ('XN', 'XN_au')]:
    x, y = m[a].to_numpy(float), m[b].to_numpy(float)
    nanx, nany = np.isnan(x), np.isnan(y)
    both = ~nanx & ~nany
    P(f'  {a:14s} NaN mine {nanx.sum():4d} theirs {nany.sum():4d} NaN-pattern differ {(nanx != nany).sum():3d} '
      f'max abs diff {np.max(np.abs(x[both] - y[both])) if both.any() else np.nan:.2e}')
mo = p.merge(ao[['symbol', 'qn', 'vsN_net_H20', 'tradable_B']], on=['symbol', 'qn'])
P('  vsN_net max abs diff', np.nanmax(np.abs(mo.vsN_net - mo.vsN_net_H20)), ' tradable equal', (mo.tradable == mo.tradable_B).all())

# ------------------------------------------------------------ look-ahead checks
P('\nLOOK-AHEAD CHECKS')
el = p[p.n_prev >= 4]
P('  rows with n_prev>=4:', len(el), ' all 4 drifts known (exit < k):', int((el.n_drift_4 == 4).sum()),
  ' fewer:', int((el.n_drift_4 < 4).sum()))
P('  rows where a "last 4" item has qn >= current (impossible by construction): 0 [guard in build.py]')
# per quarter: latest exit used by any row vs the quarter's first decision session (k) among F&O rows
qq = p.groupby('qn').agg(first_k=('i_react', 'min'), last_k=('i_react', 'max'), max_exit=('max_exit_used', 'max'))
qq['exit_before_first_k'] = qq.max_exit < qq.first_k
P(qq.to_string())
bad = p[p.max_exit_used >= p.i_react]
P('  rows using a drift whose exit >= own k:', len(bad))
# authors' alternative claim: within-quarter percentiles use only values known at the quarter's first decision
# also: is any row's 'last 4' containing a result whose reaction day is AFTER the quarter's first decision?
# (that would make the quarter percentile depend on not-yet-reported results)
h = pd.read_csv(f'{OUT}/vb_history.csv')
cnt = 0
for q, g in p[p.n_prev >= 4].groupby('qn'):
    fk = g.i_react.min()
    for _, r in g.iterrows():
        hh = h[(h.symbol == r.symbol) & (h.i_react < r.i_react) & (h.i_p1 < r.i_react) & (h.qn < r.qn)].tail(4)
        if (hh.exit20 >= fk).any() and (hh.exit20 < r.i_react).any():
            cnt += 1
P('  rows whose last-4 drifts include one ending on/after the quarter\'s first decision:', cnt)

# ------------------------------------------------------------ recompute the 3 candidates
t = p[p.tradable].copy()


def q_pct(s, frac):  # quarter percentile over ALL in_fo rows of the quarter with the feature (not only tradable)
    return p.groupby('qn')[s].quantile(frac)


thr80 = q_pct('mean_drift_4', 0.8)
t['S1'] = t.mean_drift_4 >= t.qn.map(thr80)
t['S3'] = t.n_pos_drift_4 >= 3
t['W'] = t.XN > 4
t['NEAR'] = t.W & (t.dist_52wh >= -5)
eligS = t.mean_drift_4.notna()


def stats(sel, par, name, df=t):
    x = df[sel]
    par_m = df[par].groupby('qn').vsN_net.mean()
    d = x.vsN_net - x.qn.map(par_m)
    f = x.qn <= 13
    qm = d.groupby(x.qn).mean()
    o = dict(test=name, n=len(x), parent_n=int(par.sum()), avg=x.vsN_net.mean(), gain=d.mean(),
             q_pos=int((x.groupby('qn').vsN_net.mean() > 0).sum()), q=x.qn.nunique(), q_dpos=int((qm > 0).sum()),
             t_q=qm.mean() / qm.std() * np.sqrt(len(qm)),
             n14=int(f.sum()), avg14=x.vsN_net[f].mean(), gain14=d[f].mean(),
             n8=int((~f).sum()), avg8=x.vsN_net[~f].mean(), gain8=d[~f].mean())
    return o, x.assign(d_par=d)


res = []
o, s1 = stats(t.S1, eligS, 'S1_DRIFT4_Q5'); res.append(o)
o, s3 = stats(t.S3 & eligS, eligS, 'S3_CONSIST_DRIFT'); res.append(o)
eligN = t.W & t.dist_52wh.notna()
o, nh = stats(t.NEAR, eligN, 'W_NEAR52H'); res.append(o)
R = pd.DataFrame(res)
P('\nRECOMPUTED'); P(R.round(3).to_string(index=False))
claimed = {'S1_DRIFT4_Q5': (569, 2804, 1.80, 1.11, 270, 2.88, 1.66, 299, 0.81, 0.62),
           'S3_CONSIST_DRIFT': (938, 2804, 1.17, 0.41, 501, 1.90, 0.53, 437, 0.34, 0.26),
           'W_NEAR52H': (176, 392, 2.42, 0.60, 101, 2.45, 0.08, 75, 2.38, 1.29)}
P('\nCOMPARE with claimed (n, parent, avg, gain, n14, avg14, gain14, n8, avg8, gain8)')
for _, r in R.iterrows():
    c = claimed[r.test]
    mine = (r.n, r.parent_n, r.avg, r.gain, r.n14, r.avg14, r.gain14, r.n8, r.avg8, r.gain8)
    diffs = [f'{a}->{b:.2f}' if isinstance(a, float) and abs(a - b) > 0.006 else (f'{a}->{b}' if not isinstance(a, float) and a != b else '')
             for a, b in zip(c, mine)]
    P(f'  {r.test}: claimed {c}\n      mine {tuple(round(v, 2) if isinstance(v, float) else v for v in mine)}  diffs: {[x for x in diffs if x]}')

# trade-level comparison with the authors' trades.csv
for name, df in [('S1_DRIFT4_Q5', s1), ('S3_CONSIST_DRIFT', s3), ('W_NEAR52H', nh)]:
    a = at[at.test == name][['symbol', 'qn', 'vsN_net', 'd_par']]
    mm = df[['symbol', 'qn', 'vsN_net', 'd_par']].merge(a, on=['symbol', 'qn'], how='outer', suffixes=('', '_au'), indicator=True)
    P(f'  {name}: trades mine-only {(mm._merge == "left_only").sum()}, theirs-only {(mm._merge == "right_only").sum()}, '
      f'max |vsN diff| {np.nanmax(np.abs(mm.vsN_net - mm.vsN_net_au)):.1e}, max |d_par diff| {np.nanmax(np.abs(mm.d_par - mm.d_par_au)):.1e}')
    if (mm._merge != 'both').any():
        P(mm[mm._merge != 'both'].head(10).to_string())

t.to_csv(f'{OUT}/vb_tradable.csv', index=False, float_format='%.6g')
s1.to_csv(f'{OUT}/vb_trades_S1.csv', index=False, float_format='%.5g')
R.to_csv(f'{OUT}/recomputed.csv', index=False, float_format='%.4f')
