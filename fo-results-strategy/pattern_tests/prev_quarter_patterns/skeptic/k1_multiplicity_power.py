"""k1: count every test, corrections across all of them, a global maxT over every directional statistic under ONE
within-quarter shuffle of x, and power / minimum detectable effects."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from scipy import stats
from common import *

B = 5000
rng = np.random.default_rng(20261020)
A = pd.read_csv(os.path.join(RES, 'all_tests.csv'))
print(f'== 1. tests in all_tests.csv: {len(A)}')
print(A.family.value_counts().to_string())
dirf = ['A1', 'A2', 'B', 'C', 'C-global', 'C-streak', 'C-streak-global', 'C-alt', 'D']
A['dir'] = A.family.isin(dirf)


def bh(p):
    p = np.asarray(p, float); m = len(p); o = np.argsort(p)
    q = np.empty(m); run = 1.0
    for r in range(m - 1, -1, -1):
        i = o[r]; run = min(run, p[i] * m / (r + 1)); q[i] = run
    return q


for name, sub in [('all 84', A), ('directional', A[A.dir]), ('magnitude', A[~A.dir])]:
    hh, bb = holm(sub.p), bh(sub.p)
    print(f'{name}: {len(sub)} tests; raw p<0.05 {int((sub.p < 0.05).sum())} (chance {0.05 * len(sub):.1f}); '
          f'Holm<0.05 {int((hh < 0.05).sum())}; BH q<0.05 {int((bb < 0.05).sum())}; BH q<0.10 {int((bb < 0.10).sum())}')
    s = sub.assign(holm=hh, bh=bb).sort_values('p').head(6)
    for _, r in s.iterrows():
        print(f'   {r.id:14s} obs {r.obs:+.4f} n {r.n} p {fpv(r.p)} Holm-{name} {r.holm:.3f} BH {r.bh:.3f}')
# confirmed-rule components across all directional
d = A[A.dir]
print(f'directional: first-14q raw p<0.05 {int((d.p_first < 0.05).sum())}/{len(d)}, last-8q raw p<0.05 '
      f'{int((d.p_last < 0.05).sum())}/{len(d)}; same sign both halves {int((np.sign(d.obs_first) == np.sign(d.obs_last)).sum())}/{len(d)}')
both = d[(d.p_first < 0.05) & (d.p_last < 0.05) & (np.sign(d.obs_first) == np.sign(d.obs_last))]
print('directional tests with raw p<0.05 in BOTH halves, same sign:', both.id.tolist())
print('descriptive extra p values also printed in run.log (not in any family): A2 x-diff 8 + share-up diff 8, streak trend 1, '
      'vol60/vol60_ex context 2, partial vol60_ex 8, H luck p 2 -> 29 more; plus the after-the-fact lag-1 split (no p)')

# ------------------------------------------------------------------ global maxT over every directional statistic
F = load()
F['qn'] = F.qn.astype(int)
ICF = [f'h{k}' for k in LAGS] + ['l1_dm1', 'l1_rd', 'l1_dp1', 'n_up4', 'n_up8', 'mean_h2', 'mean_h4', 'mean_h8', 'best4', 'worst4']
SEQ = {L: sorted(F[f'seq{L}'].dropna().unique()) for L in (2, 3, 4)}
ST = [-4, -3, -2, -1, 1, 2, 3, 4]
names = ([f'IC {f}' for f in ICF] + [f'A2 lag{k}' for k in LAGS] + [f'C {p}' for L in (2, 3, 4) for p in SEQ[L]] +
         [f'Cglob{L}' for L in (2, 3, 4)] + [f'S{s:+d}' for s in ST] + ['Sglob'])
NS = len(names)
qs = sorted(F.qn.unique())
x_all = F.x.to_numpy(); qn = F.qn.to_numpy()
qmean_y = F.groupby('qn').y.mean()


def stats_from(xv):
    """all directional statistics for an outcome vector xv (same row order as F). Works on (B, n) arrays too."""
    pass


# Precompute, per quarter, permutations; accumulate numerators for each statistic.
obs = np.zeros(NS); null = np.zeros((B, NS))
# IC: mean over quarters with >= 20
icq = {f: 0 for f in ICF}
# group stats: pooled sums
grp_defs = []   # (name, mask of rows) for pooled mean x / A2 up-down
for k in LAGS:
    h = F[f'h{k}'].to_numpy()
    grp_defs.append(('A2', k, ~np.isnan(h) & (h > 0), ~np.isnan(h) & (h <= 0)))
pat_masks = []
for L in (2, 3, 4):
    s = F[f'seq{L}']
    for p in SEQ[L]:
        pat_masks.append((s == p).to_numpy())
st = F.streak.to_numpy()
st_masks = [(st == v) for v in ST]
seq_have = {L: F[f'seq{L}'].notna().to_numpy() for L in (2, 3, 4)}
st_have = ~np.isnan(st)

# containers for pooled sums: for each mask, sum of x over mask (obs and null)
def pooled_setup():
    return np.zeros(B + 1)

mask_list = []
for _, k, up, dn in grp_defs:
    mask_list += [up, dn]
mask_list += pat_masks + st_masks
for L in (2, 3, 4):
    mask_list.append(seq_have[L])
mask_list.append(st_have)
M = np.array(mask_list)                       # (nm, n)
sums = np.zeros((B + 1, len(mask_list))); sq_cache = None
ic_obs = np.zeros(len(ICF)); ic_null = np.zeros((B, len(ICF))); ic_nq = np.zeros(len(ICF))
for q in qs:
    rows = np.flatnonzero(qn == q)
    xq = x_all[rows]
    P = np.vstack([np.arange(len(rows))] + [rng.permutation(len(rows)) for _ in range(B)])   # (B+1, nq), row 0 = obs
    Xp = xq[P]                                                                              # (B+1, nq)
    sums += Xp @ M[:, rows].T.astype(float)
    for j, f in enumerate(ICF):
        fv = F[f].to_numpy()[rows]
        m = ~np.isnan(fv)
        if m.sum() < 20:
            continue
        a = rank(fv[m]); a = a - a.mean()
        Y = Xp[:, m]
        R = np.argsort(np.argsort(Y, axis=1), axis=1).astype(float) + 1
        R = R - R.mean(axis=1, keepdims=True)
        c = (R @ a) / np.sqrt((a ** 2).sum() * (R ** 2).sum(axis=1))
        ic_obs[j] += c[0]; ic_null[:, j] += c[1:]; ic_nq[j] += 1
ic_obs /= ic_nq; ic_null /= ic_nq
cnt = M.sum(axis=1).astype(float)
means = sums / cnt                              # (B+1, nm) pooled mean x per mask
col = 0; S = np.zeros((B + 1, NS))
S[:, :len(ICF)] = np.vstack([ic_obs, ic_null]); col = len(ICF)
qm_y = {q: qmean_y[q] for q in qs}
# A2: y = x + quarter mean y; diff of pooled y means = diff of pooled x means + diff of pooled quarter means (constant)
qmy = F.qn.map(qmean_y).to_numpy()
for i, (_, k, up, dn) in enumerate(grp_defs):
    const = qmy[up].mean() - qmy[dn].mean()
    S[:, col] = means[:, 2 * i] - means[:, 2 * i + 1] + const; col += 1
base = 2 * len(grp_defs)
for i in range(len(pat_masks)):
    S[:, col] = means[:, base + i]; col += 1
# global SS per length: sum_p n_p (mean_p - mean_subset)^2
off = base
for L in (2, 3, 4):
    pass
pi = 0; ss_cols = []
for L in (2, 3, 4):
    npat = len(SEQ[L])
    sub_mean = means[:, base + len(pat_masks) + len(st_masks) + (L - 2)]
    ss = np.zeros(B + 1)
    for j in range(npat):
        ss += cnt[base + pi + j] * (means[:, base + pi + j] - sub_mean) ** 2
    pi += npat
    S[:, col] = ss; ss_cols.append(col); col += 1
sbase = base + len(pat_masks)
for i in range(len(st_masks)):
    S[:, col] = means[:, sbase + i]; col += 1
sub_mean = means[:, -1]; ss = np.zeros(B + 1)
for i in range(len(st_masks)):
    ss += cnt[sbase + i] * (means[:, sbase + i] - sub_mean) ** 2
S[:, col] = ss; ss_cols.append(col); col += 1
assert col == NS
obsS, nullS = S[0], S[1:]
mu, sd = nullS.mean(0), nullS.std(0)
Z = (nullS - mu) / sd; zo = (obsS - mu) / sd
one = np.zeros(NS, bool); one[ss_cols] = True
Za = np.where(one, Z, np.abs(Z)); zoa = np.where(one, zo, np.abs(zo))
mx = Za.max(1)
p_ind = np.array([(1 + np.sum(Za[:, j] >= zoa[j] - 1e-12)) / (B + 1) for j in range(NS)])
p_glob = np.array([(1 + np.sum(mx >= zoa[j] - 1e-12)) / (B + 1) for j in range(NS)])
print(f'\n== 1b. ONE within-quarter shuffle of x, all {NS} directional statistics (the 68 family tests; C-alt = C3 UDU/DUD '
      f'are inside C) -> global maxT. 95th pct of max |z| under the null: {np.quantile(mx, 0.95):.2f}')
o = np.argsort(-zoa)
for j in o[:10]:
    print(f'   {names[j]:12s} obs {obsS[j]:+.4f} z {zo[j]:+.2f} p(single) {fpv(p_ind[j])} global maxT p {p_glob[j]:.3f}')
# ICs only (18) as a subfamily
icz = np.abs(Z[:, :len(ICF)]); mxi = icz.max(1)
print(f'   IC-only family (18 features: A1 8, B 3, D 7): 95th pct max|z| {np.quantile(mxi, 0.95):.2f}; best4 maxT-18 p '
      f'{(1 + np.sum(mxi >= abs(zo[ICF.index("best4")]) - 1e-12)) / (B + 1):.3f}; mean_h8 '
      f'{(1 + np.sum(mxi >= abs(zo[ICF.index("mean_h8")]) - 1e-12)) / (B + 1):.3f}')
# check matches the repo's single p values
for f in ('h1', 'h3', 'best4', 'mean_h8'):
    j = ICF.index(f)
    print(f'   check {f}: IC {ic_obs[j]:+.4f} null sd {sd[j]:.4f} p {fpv(p_ind[j])}')

# ------------------------------------------------------------------ power
print('\n== 2. power / smallest detectable effect (normal approx with the permutation null sd; homogeneous true IC)')
from scipy.stats import norm
sdx = F.x.std()
print(f'sd of x {sdx:.2f}; a true IC rho moves the favoured fifth by about rho*sd*1.40 = {1.40 * sdx:.2f}*rho points '
      f'(IC 0.03 -> {0.03 * 1.40 * sdx:+.2f}, 0.05 -> {0.05 * 1.40 * sdx:+.2f}, 0.08 -> {0.08 * 1.40 * sdx:+.2f})')
# null sd per half for lag features from fresh shuffles (first 14 q / last 8 q)
half = {'first': F.qn <= 13, 'last': F.qn >= 14}
sdh = {}
for hn, m in half.items():
    sub = F[m]
    o_, n_, _ = perm_ic_multi(sub, [f'h{k}' for k in LAGS], 'x', B=1000, seed=7)
    sdh[hn] = n_.std(0)
    zc = np.quantile(np.abs((n_ - n_.mean(0)) / n_.std(0)).max(1), 0.95)
    sdh[hn + '_zc'] = zc
print(f'maxT-8 critical |z| first 14 q {sdh["first_zc"]:.2f}; last 8 q single test 1.96')
print('lag | null sd all / first / last | MDE80 single test | MDE80 maxT-8 (all q) | P(CONFIRM) at IC 0.03 / 0.05 / 0.08 / 0.10 | IC giving 80% confirm | observed IC, 95% CI (quarter t)')
zc_all = np.quantile(np.abs(Z[:, :8]).max(1), 0.95)
for k in LAGS:
    j = k - 1
    s_all, s1, s2 = sd[j], sdh['first'][j], sdh['last'][j]
    mde1 = (1.96 + 0.84) * s_all; mde8 = (zc_all + 0.84) * s_all
    pc = lambda r: (1 - norm.cdf(sdh['first_zc'] - r / s1)) * (1 - norm.cdf(1.96 - r / s2))
    grid = np.linspace(0, 0.3, 3001); r80 = grid[np.argmax([pc(r) >= 0.8 for r in grid])]
    ics = ic_q(F, f'h{k}', 'x'); v = np.array([c for _, c, _ in ics]); se = v.std(ddof=1) / np.sqrt(len(v))
    tc = stats.t.ppf(0.975, len(v) - 1)
    print(f'  {k} | {s_all:.4f} / {s1:.4f} / {s2:.4f} | {mde1:.3f} | {mde8:.3f} | {pc(0.03):.2f} / {pc(0.05):.2f} / {pc(0.08):.2f} / {pc(0.10):.2f} | '
          f'{r80:.3f} | {v.mean():+.3f} [{v.mean() - tc * se:+.3f}, {v.mean() + tc * se:+.3f}]')
# pattern means
print('pattern means: null sd of mean x and the MDE (80% power, Holm within its length) vs observed')
for L, mlen in ((3, 8), (4, 16)):
    for p in ('U' * L, 'D' * L):
        n = int((F[f'seq{L}'] == p).sum()); s = sdx / np.sqrt(n)
        zc = norm.ppf(1 - 0.025 / mlen)
        print(f'   {p}: n {n}, sd {s:.2f}, MDE80 single {(2.80) * s:.2f} pts, MDE80 Holm-{mlen} {(zc + 0.84) * s:.2f} pts, '
              f'observed {F.loc[F[f"seq{L}"] == p, "x"].mean():+.2f}')

# ------------------------------------------------------------------ omnibus: how many directional statistics reach |z|>1.96?
cnt_null = (Za >= 1.96).sum(1); cnt_obs = int((zoa >= 1.96).sum())
print(f'\n== omnibus count: directional statistics with |z| >= 1.96: observed {cnt_obs} of {NS}; null mean {cnt_null.mean():.1f}, '
      f'95th pct {np.quantile(cnt_null, 0.95):.0f}, p {(1 + (cnt_null >= cnt_obs).sum()) / (B + 1):.3f}')
# effective number of tests (Li & Ji) from the null correlation of the 66 statistics
ev_ = np.linalg.eigvalsh(np.corrcoef(Z.T)); ev_ = np.abs(ev_)
meff = np.sum((ev_ >= 1) + (ev_ - np.floor(ev_)))
print(f'   effective number of independent directional tests (Li-Ji) about {meff:.1f}; Sidak on best single p 0.003 -> '
      f'{1 - (1 - 0.003) ** meff:.3f}')
print('   the statistics with |z| >= 1.96: ' + ', '.join(f'{names[j]} ({zo[j]:+.2f})' for j in o if zoa[j] >= 1.96))
# omnibus without the track-record cluster (UUU / UUUU / S+4 / S+3 and D features and lag 3/4 that load on pp_last4)
keep = [j for j, n in enumerate(names) if not any(t in n for t in ('UUU', 'S+4', 'S+3', 'n_up', 'mean_h4', 'mean_h8', 'best4', 'worst4'))]
cn = (Za[:, keep] >= 1.96).sum(1); co = int((zoa[keep] >= 1.96).sum())
print(f'   without the track-record cluster ({len(keep)} statistics): observed {co}, null mean {cn.mean():.1f}, p {(1 + (cn >= co).sum()) / (B + 1):.3f}')
