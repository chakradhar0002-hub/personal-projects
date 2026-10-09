#!/usr/bin/env python3
"""Independent re-computation (plain pandas, no code shared with run_tests.py) of key numbers:
S1/S3 and a few W/WR tests (n, mean, gain vs parent, halves, w/o best 5), the S1 luck p by a different sampler, the
quiet-day track record for a random sample of quiet stock-days (merge-based), and quiet-day outcomes."""
import numpy as np
import pandas as pd

SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
HERE = f'{SP}/perf/B_post_results'
F = f'{SP}/perf/features'
LOG = open(f'{HERE}/verify.log', 'w')


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    LOG.write(s + '\n')


res = pd.read_csv(f'{HERE}/results_tests.csv').set_index('test')
p = pd.read_csv(f'{F}/panel.csv').merge(pd.read_csv(f'{F}/outcomes.csv')[['symbol', 'qn', 'vsN_H20', 'tradable_B']],
                                        on=['symbol', 'qn'])
p = p[p.tradable_B]
p['x'] = p.vsN_H20 - 0.19
thr = p.groupby('qn').mean_drift_4_B.quantile([0.2, 0.5, 0.8]).unstack()
p = p.join(thr, on='qn')


def check(name, sub, par, short=False):
    s = p[sub].copy()
    pr = p[par].copy()
    if short:
        s['x'] = -s.vsN_H20 - 0.19
        pr['x'] = -pr.vsN_H20 - 0.19
    pm = pr.groupby('qn').x.mean()
    s['dp'] = s.x - s.qn.map(pm)
    s5 = s.sort_values('x', ascending=False).iloc[5:]
    mine = dict(n=len(s), mean=s.x.mean(), d=s.dp.mean(), d14=s[s.qn <= 13].dp.mean(), d8=s[s.qn >= 14].dp.mean(),
                wo5=s5.x.mean(), dwo5=s5.dp.mean())
    r = res.loc[name]
    theirs = dict(n=r.n, mean=r.mean_vsN_net, d=r.d_par, d14=r.d_f14, d8=r.d_l8, wo5=r.mean_wo5, dwo5=r.d_wo5)
    okk = all(abs(mine[k] - theirs[k]) < 1e-3 for k in mine)
    P(f'{name:18s} ' + ' '.join(f'{k}={mine[k]:+.3f}' for k in mine) + f'  match={okk}')
    return s, pr


W = p.W == True
WR = W & (p.cut_rsi14 > 50)
e4 = p.mean_drift_4_B.notna()
s1, par1 = check('S1_DRIFT4_Q5', e4 & (p.mean_drift_4_B >= p[0.8]), e4)
check('S2_DRIFT4_Q1', e4 & (p.mean_drift_4_B <= p[0.2]), e4, short=True)
check('S3_CONSIST_DRIFT', (p.n_drift_4_B == 4) & (p.n_pos_drift_4_B >= 3), p.n_drift_4_B == 4)
check('W_NEAR52H', W & (p.dist_52wh_B >= -5), W & p.dist_52wh_B.notna())
check('WR_MOM126_BOT', WR & (p.rank_vsN_126_B <= 50), WR & p.rank_vsN_126_B.notna())
check('W_DRIFT4_TOP', W & e4 & (p.mean_drift_4_B >= p[0.5]), W & e4)
check('W_REPEAT1', W & (p.prev1_winner_B == 1), W & p.prev1_winner_B.notna())
check('WR_SEC252_DN', WR & (p.vsSec_252_B <= 0), WR & p.vsSec_252_B.notna())

# S1 luck p with a different sampler (python loop, rng.choice), 4,000 draws
rng = np.random.default_rng(7)
obs = s1.x.mean()
cnt = s1.groupby('qn').size()
pools = {q: par1[par1.qn == q].x.to_numpy() for q in cnt.index}
draws = np.array([np.concatenate([rng.choice(pools[q], k, replace=False) for q, k in cnt.items()]).mean()
                  for _ in range(4000)])
P(f'S1 luck re-check: obs {obs:+.3f}, random mean {draws.mean():+.3f}, sd {draws.std():.3f}, z {(obs - draws.mean()) / draws.std():.2f}, '
  f'p = {(1 + (draws >= obs).sum()) / 4001:.5f}  (run_tests {res.loc["S1_DRIFT4_Q5", "luck_p"]:.5f})')

# quiet-day track record by merge (random 3,000 quiet rows) and quiet outcomes
qf = pd.read_csv(f'{HERE}/quiet_features.csv.gz')
h = pd.read_csv(f'{F}/history.csv')
smp = qf.sample(3000, random_state=3)
bad = 0
for r in smp.itertuples():
    g = h[(h.symbol == r.symbol) & (h.h_td_end < r.i) & (h.h_xn_end < r.i)].sort_values('qn').tail(4)
    if len(g) < 4:
        if not np.isnan(r.mean_drift_4):
            bad += 1
        continue
    dr = g.h_dr[g.h_dr_end < r.i]
    m = dr.mean() if len(dr) else np.nan
    if not ((np.isnan(m) and np.isnan(r.mean_drift_4)) or abs(m - r.mean_drift_4) < 1e-4):
        bad += 1
P(f'quiet mean_drift_4 merge re-check on 3,000 random quiet stock-days: mismatches {bad}')
ses = pd.read_csv(f'{SP}/sector_lab/data/sessions.csv')
ret = pd.read_csv(f'{SP}/sector_lab/data/returns.csv', index_col=0)
ixc = pd.read_csv(f'{SP}/sector_lab/data/index_close.csv', index_col=0)
nif = ixc['Nifty 50'].to_numpy()
qo = pd.read_csv(f'{SP}/tafa/C_post_results/quiet_days.csv.gz', usecols=['symbol', 'i'])
sm2 = qf.sample(300, random_state=5)
mx = 0
pl = pd.read_csv(f'{HERE}/placebo.csv').set_index('test')
# recompute quiet outcome for sampled rows and the S1 quiet subset mean from scratch
vals = []
for r in qf.itertuples():
    pass
for r in sm2.itertuples():
    rr = ret[r.symbol].to_numpy()[r.i + 1:r.i + 21]
    stock = np.prod(1 + np.nan_to_num(rr)) - 1
    vals.append(((stock - (nif[r.i + 20] / nif[r.i] - 1)) * 100 - 0.19))
sm2 = sm2.assign(v=vals)
P(f'quiet outcomes recomputed for 300 rows: mean {np.mean(vals):+.3f} (no stored outcome to compare; used below)')
# S1 quiet placebo from scratch (all quiet rows)
R = ret.to_numpy(float)
SYM = {s: j for j, s in enumerate(ret.columns)}
PX = np.cumprod(1 + np.nan_to_num(R), axis=0)
j = qf.symbol.map(SYM).to_numpy(int)
i = qf.i.to_numpy(int)
qf['v'] = ((PX[i + 20, j] / PX[i, j] - 1) - (nif[i + 20] / nif[i] - 1)) * 100 - 0.19
chk = sm2[['symbol', 'i', 'v']].merge(qf[['symbol', 'i', 'v']], on=['symbol', 'i'], suffixes=('', '_vec'))
P(f'quiet outcome loop vs vectorised: max abs diff {(chk.v - chk.v_vec).abs().max():.2e}')
qf['month'] = qf.day.str[:7]
e = qf.mean_drift_4.notna()
q80m = qf[e].groupby('month').mean_drift_4.quantile(0.8)
top = e & (qf.mean_drift_4 >= qf.month.map(q80m))
pm = qf[e].groupby('month').v.mean()
dq = (qf[top].v - qf[top].month.map(pm)).mean()
P(f'S1 quiet placebo from scratch: n={int(top.sum())} mean={qf[top].v.mean():+.3f} gain vs month={dq:+.3f}  '
  f'(run_tests n={int(pl.loc["S1_DRIFT4_Q5", "quiet_n"])} gain={pl.loc["S1_DRIFT4_Q5", "quiet_d"]:+.3f})')
LOG.close()
