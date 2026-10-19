"""Skeptic 1: sanity, joint multiplicity over all 59 features, all reported p values, power of the tests."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
from scipy import stats


def multipletests(p, method):
    p = np.asarray(p, float); n = len(p); o = np.argsort(p)
    if method == 'holm':
        adj = np.maximum.accumulate((n - np.arange(n)) * p[o])
    else:
        adj = np.minimum.accumulate((n / np.arange(n, 0, -1) * p[o][::-1]))[::-1]
    out = np.empty(n); out[o] = np.minimum(adj, 1)
    return None, out

from common import *

df = load_events()
print('== sanity')
print('slope_sma_50 mean IC', round(ic_by_q(df, 'slope_sma_50').mean(), 4))
for a, b in [('slope_sma_50', 'my_slope_sma_50'), ('dist_sma_100', 'my_dist_sma_100'), ('dist_sma_50', 'my_dist_sma_50')]:
    print(f'  independent {b} vs repo {a}: max abs diff {np.abs(df[a] - df[b]).max():.2e}')
print('  three_day ties: n unique', df.three_day.nunique(), 'of', len(df), '; exact zeros', (df.three_day == 0).sum())
print('  lag-rule trades matched in events:', df.lag_trade.sum())

# ------------------------------------------------------------------ joint shuffle null over all 59 features
B = 10000
rng = np.random.default_rng(20261119)
qs = sorted(df.qn.unique())
first = [q for q in qs if q <= 13]
icsum = {h: np.zeros((B, 27)) for h in ('all', 'f14', 'l8')}
icobs = {h: np.zeros(27) for h in ('all', 'f14', 'l8')}
bsum = np.zeros((B, 32)); bobs = np.zeros(32); bnull = np.zeros(32); nsig = np.zeros(32)
bsum_h = {h: np.zeros((B, 32)) for h in ('f14', 'l8')}; bobs_h = {h: np.zeros(32) for h in ('f14', 'l8')}
bnull_h = {h: np.zeros(32) for h in ('f14', 'l8')}; nsig_h = {h: np.zeros(32) for h in ('f14', 'l8')}
for q in qs:
    g = df[df.qn == q]
    y = g.three_day.values
    R = np.column_stack([zr(g[f].values) for f in CONT])
    ry = zr(y)
    Bm = g[BINARY].values.astype(float)
    idx = np.argsort(rng.random((B, len(y))), axis=1)
    sim_ic = ry[idx] @ R
    sim_b = y[idx] @ Bm
    h = 'f14' if q <= 13 else 'l8'
    for hh in ('all', h):
        icsum[hh] += sim_ic
        icobs[hh] += ry @ R
    bsum += sim_b; bobs += y @ Bm; bnull += Bm.sum(0) * y.mean(); nsig += Bm.sum(0)
    bsum_h[h] += sim_b; bobs_h[h] += y @ Bm; bnull_h[h] += Bm.sum(0) * y.mean(); nsig_h[h] += Bm.sum(0)
nq = {'all': len(qs), 'f14': len(first), 'l8': len(qs) - len(first)}
for h in icsum:
    icsum[h] /= nq[h]; icobs[h] /= nq[h]
bm_sim = bsum / nsig; bm_obs = bobs / nsig; bm_null = bnull / nsig
zc_obs = icobs['all'] / icsum['all'].std(0)
zc_sim = icsum['all'] / icsum['all'].std(0)
zb_obs = (bm_obs - bm_null) / bm_sim.std(0)
zb_sim = (bm_sim - bm_null) / bm_sim.std(0)
zall_sim = np.abs(np.hstack([zc_sim, zb_sim]))
zall_obs = np.abs(np.hstack([zc_obs, zb_obs]))
names = CONT + BINARY
maxz = zall_sim.max(1)
joint = (1 + (maxz[:, None] >= zall_obs[None, :] - 1e-12).sum(0)) / (1 + B)
pind = (1 + (zall_sim >= zall_obs[None, :] - 1e-12).sum(0)) / (1 + B)
# maxT over continuous only, on raw |mean IC| (as the build)
mx = np.abs(icsum['all']).max(1)
maxt27 = (1 + (mx[:, None] >= np.abs(icobs['all'])[None, :] - 1e-12).sum(0)) / (1 + B)
order = np.argsort(-zall_obs)
print('\n== joint familywise over all 59 features (within-quarter shuffle of three_day, B=10,000, seed 20261119)')
print('feature, |z|, own p, maxT27 p (cont only), joint maxT59 p')
for j in order[:8]:
    m27 = maxt27[j] if j < 27 else np.nan
    print(f'  {names[j]:18s} |z| {zall_obs[j]:.2f}  p {pind[j]:.4f}  maxT27 {m27:.4f}  joint59 {joint[j]:.4f}')
print('  95% critical |z|: single 1.96-ish; max over 27 cont', round(np.quantile(np.abs(zc_sim).max(1), .95), 2),
      '; max over 59', round(np.quantile(maxz, .95), 2))
# count of unadjusted hits under the null
c_obs = (pind[:27] < 0.05).sum(); b_obs = (pind[27:] < 0.05).sum()
thr_c = np.quantile(np.abs(zc_sim), .95, axis=0); thr_b = np.quantile(np.abs(zb_sim), .95, axis=0)
cnt_c = (np.abs(zc_sim) > thr_c).sum(1); cnt_b = (np.abs(zb_sim) > thr_b).sum(1)
print(f'  unadjusted hits: continuous {c_obs} of 27 -> P(null count >= {c_obs}) = {(cnt_c >= c_obs).mean():.4f} '
      f'(null mean {cnt_c.mean():.2f}, 95th pct {np.quantile(cnt_c, .95):.0f}, 99th {np.quantile(cnt_c, .99):.0f})')
print(f'  unadjusted hits: binary {b_obs} of 32 -> P(null count >= {b_obs}) = {(cnt_b >= b_obs).mean():.4f} '
      f'(null mean {cnt_b.mean():.2f}, 95th pct {np.quantile(cnt_b, .95):.0f})')
# sign-agnostic global: is 26 of 27 negative unusual given correlation?
neg_sim = (icsum['all'] < 0).sum(1)
print(f'  26 of 27 mean ICs negative: P(null >= 26 same sign) = {((neg_sim >= 26) | (neg_sim <= 1)).mean():.4f}')
# global test: mean of the 27 ICs (one composite)
comp_obs = icobs['all'].mean(); comp_sim = icsum['all'].mean(1)
print(f'  average of all 27 mean ICs {comp_obs:+.4f}, shuffle p {(1 + (np.abs(comp_sim) >= abs(comp_obs)).sum()) / (1 + B):.4f}')

# ------------------------------------------------------------------ all reported p values
t1 = pd.read_csv(os.path.join(RES, 't1_continuous.csv'))
t2 = pd.read_csv(os.path.join(RES, 't2_binary.csv'))
ps = []
for _, r in t1.iterrows():
    for c in ['perm_p', 'p_first14', 'p_last8', 'pooled_rho_p', 'res_minus_placebo_p']:
        ps.append((r.feature, c, r[c]))
for _, r in t2.iterrows():
    for c in ['luck_p', 'p_first14', 'p_last8', 'res_minus_placebo_p']:
        ps.append((r.feature, c, r[c]))
P_ = pd.DataFrame(ps, columns=['feature', 'test', 'p']).dropna()
P_['holm'] = multipletests(P_.p, method='holm')[1]
P_['bh'] = multipletests(P_.p, method='fdr_bh')[1]
print(f'\n== all {len(P_)} p values in t1/t2 CSVs (5 per continuous, 4 per binary feature)')
print('  min raw p', P_.p.min(), '; min Holm', round(P_.holm.min(), 3), '; min BH q', round(P_.bh.min(), 3),
      '; raw p<0.05:', (P_.p < 0.05).sum(), f'(expected {0.05 * len(P_):.1f})')
print(P_.sort_values('p').head(6).to_string(index=False))
ov = pd.concat([t1[['feature', 'perm_p']].rename(columns={'perm_p': 'p'}), t2[['feature', 'luck_p']].rename(columns={'luck_p': 'p'})])
ov['holm'] = multipletests(ov.p, method='holm')[1]; ov['bh'] = multipletests(ov.p, method='fdr_bh')[1]
print('  59 overall p (perm/luck): min Holm', round(ov.holm.min(), 3), ' min BH q', round(ov.bh.min(), 3))
print('  slope_sma_50 Bonferroni over 59:', round(min(1, 0.0026 * 59), 3), '; over 59 + 44 earlier TA signals (103):', round(min(1, 0.0026 * 103), 3))

# ------------------------------------------------------------------ power
print('\n== power (null critical values from the shuffles; alternatives by injecting a Gaussian-copula link)')
sd_all = icsum['all'].std(0); sd_f = icsum['f14'].std(0); sd_l = icsum['l8'].std(0)
j = CONT.index('slope_sma_50')
print(f'  null sd of mean IC (slope_sma_50): all 22 q {sd_all[j]:.4f}, first 14 {sd_f[j]:.4f}, last 8 {sd_l[j]:.4f}')
print(f'  observed mean IC -0.052 -> 95% CI approx [{-0.052 - 1.96 * sd_all[j]:+.3f}, {-0.052 + 1.96 * sd_all[j]:+.3f}]')
crit_single = np.quantile(np.abs(icsum['all']), .95, axis=0)
crit_max = np.quantile(np.abs(icsum['all']).max(1), .95)
crit_max_f = np.quantile(np.abs(icsum['f14']).max(1), .95)
crit_l = np.quantile(np.abs(icsum['l8']), .95, axis=0)
print(f'  critical |mean IC|: single feature {crit_single[j]:.4f}; maxT27 all {crit_max:.4f}; maxT27 first14 {crit_max_f:.4f}; '
      f'last8 single {crit_l[j]:.4f}')
rng2 = np.random.default_rng(99)
G = {q: df[df.qn == q] for q in qs}
Rq = {q: np.column_stack([zr(G[q][f].values) for f in CONT]) for q in qs}
for target in ['slope_sma_50', 'dist_sma_50']:
    jt = CONT.index(target)
    nsc = {q: stats.norm.ppf((stats.rankdata(G[q][target].values) - 0.5) / len(G[q])) for q in qs}
    for c in [0.03, 0.05, 0.07, 0.09, 0.12]:
        NS = 400
        rej = np.zeros(4); real = []
        for s in range(NS):
            ic_all = np.zeros(27); ic_f = np.zeros(27); ic_l = np.zeros(27)
            for q in qs:
                yy = -c * nsc[q] + np.sqrt(1 - c * c) * rng2.standard_normal(len(nsc[q]))
                v = zr(yy) @ Rq[q]
                ic_all += v
                if q <= 13: ic_f += v
                else: ic_l += v
            ic_all /= 22; ic_f /= 14; ic_l /= 8
            real.append(ic_all[jt])
            r_single = abs(ic_all[jt]) >= crit_single[jt]
            r_max = abs(ic_all[jt]) >= crit_max
            r_conf = (abs(ic_f[jt]) >= crit_max_f) and (np.sign(ic_l[jt]) == np.sign(ic_f[jt])) and (abs(ic_l[jt]) >= crit_l[jt])
            r_any_conf = any((abs(ic_f[k]) >= crit_max_f) and (np.sign(ic_l[k]) == np.sign(ic_f[k])) and (abs(ic_l[k]) >= crit_l[k]) for k in range(27))
            rej += [r_single, r_max, r_conf, r_any_conf]
        rej /= NS
        print(f'  {target:13s} true mean IC {np.mean(real):+.3f}: power single-test {rej[0]:.2f}, maxT27 {rej[1]:.2f}, '
              f'confirm rule (this feature) {rej[2]:.2f}, confirm rule (any feature) {rej[3]:.2f}')
