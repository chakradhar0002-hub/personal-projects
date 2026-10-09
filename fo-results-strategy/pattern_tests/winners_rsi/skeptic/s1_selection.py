#!/usr/bin/env python3
"""S1. Selection / winner's curse for the W_RSI_HI H20 pick.

The rule was the best (highest permutation z) of 117 pre-registered tests, 108 of which were FA / TA subsets of the
plain winners. Here (own code):
  (a) family-wise maxT (Westfall-Young, one-sided) under within-quarter permutation of the outcome rows (H5, H10, H20
      carried jointly) among the 392 winners, for nested families: TA singles at H20 (4), TA singles x 3 holds (12),
      every TA-involving subset at H20 (30), all 36 subsets at H20, all 108 part-2 tests.
  (b) what the BEST test's d_W looks like under the global null (expected max) vs the observed d_W.
  (c) bootstrap winner's-curse bias correction (quarter-cluster bootstrap; re-select the best test in every resample,
      bias = its resample d_W - its full-sample d_W).
  (d) empirical-Bayes shrinkage of d_W across the 36 H20 subsets, and a skeptical-prior posterior.
d_W = per-trade mean of (subset trade - mean of the eligible winners of the same quarter), the pre-registered measure.
"""
import numpy as np
import pandas as pd

from common import HERE, Log, sg

L = Log('s1_selection.log')
rng = np.random.default_rng(20261009)
NPERM = 20000
NBOOT = 5000

P = pd.read_csv(f'{HERE}/panel.csv.gz')
W = P[P.W].reset_index(drop=True)
n = len(W)
Y = W[['vsN_H5', 'vsN_H10', 'vsN_H20']].to_numpy(float)
QN = W.qn.to_numpy(int)
HS = (5, 10, 20)

# ---------------------------------------------------------------- subsets (exactly the pre-registered part 2 list)
B = lambda c: W[c].fillna(False).astype(bool).to_numpy()
FEAT = {'GOOD': ('GOOD', 'E_GOOD'), 'BAD': ('BAD', 'E_BAD'), 'Q_HI': ('Q_HI', 'E_QHI'), 'Q_LO': ('Q_LO', 'E_QLO'),
        'CHEAP': ('CHEAP', 'E_PE'), 'EXP': ('EXP', 'E_PE'), 'UP200': ('UP200', 'E_S200'),
        'DN200': ('DN200', 'E_S200'), 'RSI_HI': ('RSI_HI', 'E_RSI'), 'RSI_LO': ('RSI_LO', 'E_RSI')}
TA = ['UP200', 'DN200', 'RSI_HI', 'RSI_LO']
FAF = ['GOOD', 'BAD', 'Q_HI', 'Q_LO', 'CHEAP', 'EXP']
subsets = [[f] for f in FAF + TA] + [[a, b] for a in FAF for b in TA] + [['GOOD', 'UP200', 'RSI_HI'],
                                                                       ['BAD', 'DN200', 'RSI_LO']]
names, MEM, ELIG, isTA = [], [], [], []
for s in subsets:
    m = np.ones(n, bool)
    e = np.ones(n, bool)
    for f in s:
        m &= B(FEAT[f][0])
        e &= B(FEAT[f][1])
    names.append('W_' + '&'.join(s) if len(s) < 3 else ('W_ALL_BULL' if s[0] == 'GOOD' else 'W_ALL_BEAR'))
    MEM.append(m & e)
    ELIG.append(e)
    isTA.append(any(f in TA for f in s))
MEM, ELIG = np.array(MEM), np.array(ELIG)
NT = len(names)
assert NT == 36
assert MEM[names.index('W_RSI_HI')].sum() == 232

# quarter one-hot
Qs = np.unique(QN)
QM = (QN[None, :] == Qs[:, None]).astype(float)          # (22, n)


def dW_all(Yv, mem=MEM, elig=ELIG, qm=QM, w=None):
    """d_W for every test and horizon. Yv (n, 3) [or (b, n, 3)]. w: optional per-trade weights (bootstrap counts)."""
    if w is None:
        w = np.ones(Yv.shape[0])
    # eligible-pool mean per quarter per test: sum_q(elig * w * y) / sum_q(elig * w)
    EW = elig * w[None, :]                                  # (T, n)
    num = np.einsum('tn,qn,nh->tqh', EW, qm, Yv)
    den = np.einsum('tn,qn->tq', EW, qm)
    with np.errstate(invalid='ignore', divide='ignore'):
        pm = num / den[:, :, None]                          # (T, q, h)
    pm = np.nan_to_num(pm)
    MW = mem * w[None, :]
    sub_sum = MW @ Yv                                       # (T, h)
    cnt_q = np.einsum('tn,qn->tq', MW, qm)                  # members per quarter
    base = np.einsum('tq,tqh->th', cnt_q, pm)
    ntot = MW.sum(1)[:, None]
    return (sub_sum - base) / ntot, sub_sum / ntot


D_obs, M_obs = dW_all(Y)
irsi = names.index('W_RSI_HI')
L(f"observed W_RSI_HI: mean H5/H10/H20 {M_obs[irsi].round(3)}, d_W {D_obs[irsi].round(3)}")

# quarter-cluster SE of d_W (per test, H20)
se_dW = np.zeros((NT, 3))
for t in range(NT):
    for h in range(3):
        pmq = {}
        y = Y[:, h]
        for q in Qs:
            e = ELIG[t] & (QN == q)
            pmq[q] = y[e].mean() if e.any() else np.nan
        m = MEM[t]
        dev = y[m] - np.array([pmq[q] for q in QN[m]])
        sq = pd.Series(dev).groupby(QN[m]).sum()
        nq = pd.Series(dev).groupby(QN[m]).size()
        dd = dev.mean()
        G = len(sq)
        se_dW[t, h] = np.sqrt(G / (G - 1) * ((sq - nq * dd) ** 2).sum()) / m.sum()

# ---------------------------------------------------------------- (a) permutation null
L(f"\n(a) within-quarter permutation of outcome rows among the {n} winners ({NPERM:,} perms)")
qidx = [np.flatnonzero(QN == q) for q in Qs]
D_perm = np.empty((NPERM, NT, 3), np.float32)
M_perm = np.empty((NPERM, NT, 3), np.float32)
for b in range(NPERM):
    perm = np.arange(n)
    for ix in qidx:
        perm[ix] = ix[rng.permutation(len(ix))]
    d_, m_ = dW_all(Y[perm])
    D_perm[b] = d_
    M_perm[b] = m_
mu, sd = M_perm.mean(0), M_perm.std(0)
Z_obs = (M_obs - mu) / sd
Z_perm = (M_perm - mu) / sd
p_single = (1 + (M_perm >= M_obs - 1e-12).sum(0)) / (1 + NPERM)
L(f"W_RSI_HI H20: z {Z_obs[irsi, 2]:.3f}, single-test p {p_single[irsi, 2]:.4f}")
rank = pd.DataFrame({'test': np.repeat(names, 3), 'H': np.tile(HS, NT), 'n': np.repeat(MEM.sum(1), 3),
                     'mean': M_obs.ravel(), 'dW': D_obs.ravel(), 'se_dW_q': se_dW.ravel(), 'z_perm': Z_obs.ravel(),
                     'p_single': p_single.ravel()}).sort_values('z_perm', ascending=False)
L('top 10 of the 108 part-2 tests by permutation z:')
L(rank.head(10).round(4).to_string(index=False))
rank.to_csv(f'{HERE}/s1_part2_tests.csv', index=False, float_format='%.5f')

fam = {
    'TA singles, H20 (4)': [(t, 2) for t in range(NT) if names[t] in ['W_' + x for x in TA]],
    'TA singles, H5/10/20 (12)': [(t, h) for t in range(NT) if names[t] in ['W_' + x for x in TA] for h in range(3)],
    'all TA-involving subsets, H20 (30)': [(t, 2) for t in range(NT) if isTA[t]],
    'all 36 subsets, H20 (36)': [(t, 2) for t in range(NT)],
    'all TA-involving subsets x 3 holds (90)': [(t, h) for t in range(NT) if isTA[t] for h in range(3)],
    'all part-2 tests (108)': [(t, h) for t in range(NT) for h in range(3)],
}
rows = []
for fname, ids in fam.items():
    tt = np.array([i for i, _ in ids])
    hh = np.array([h for _, h in ids])
    zmax = Z_perm[:, tt, hh].max(1)
    p_fw = (1 + (zmax >= Z_obs[irsi, 2] - 1e-9).sum()) / (1 + NPERM)
    # expected d_W of the best test under the global null (selected by max z)
    sel = Z_perm[:, tt, hh].argmax(1)
    dsel = D_perm[np.arange(NPERM), tt[sel], hh[sel]]
    msel = M_perm[np.arange(NPERM), tt[sel], hh[sel]]
    # same, restricted to H20 selections (d_W in H20 units)
    rows.append(dict(family=fname, k=len(ids), z_obs=Z_obs[irsi, 2], max_z_null_mean=zmax.mean(),
                     max_z_null_p95=np.percentile(zmax, 95), p_familywise=p_fw,
                     null_best_dW_mean=dsel.mean(), null_best_dW_p50=np.median(dsel),
                     null_best_dW_p90=np.percentile(dsel, 90), null_best_sel_H20_share=(hh[sel] == 2).mean()))
FW = pd.DataFrame(rows)
L('\nfamily-wise maxT p for W_RSI_HI H20 (z_obs %.2f), and the d_W the BEST test shows under the global null:'
  % Z_obs[irsi, 2])
L(FW.round(4).to_string(index=False))
FW.to_csv(f'{HERE}/s1_familywise.csv', index=False, float_format='%.5f')

# ---------------------------------------------------------------- (c) bootstrap winner's-curse correction
L(f"\n(c) bootstrap bias correction (resample the 22 quarters with replacement, {NBOOT:,} resamples; "
  f"select the max-z test in each resample; bias = resample d_W - full-sample d_W of that test)")
sd_null = sd                                       # per-test null sd of the subset mean (fixed scale for selection)
bc_rows = []
BOOT = []
for b in range(NBOOT):
    qs = rng.choice(Qs, len(Qs), replace=True)
    cnt = pd.Series(qs).value_counts()
    w = np.zeros(n)
    for q, c in cnt.items():
        w[QN == q] = c
    d_, m_ = dW_all(Y, w=w)
    BOOT.append((d_, m_))
BD = np.array([x[0] for x in BOOT])
BM = np.array([x[1] for x in BOOT])
for fname, ids in fam.items():
    tt = np.array([i for i, _ in ids])
    hh = np.array([h for _, h in ids])
    # selection statistic in the bootstrap world: d_W standardised by its null sd of the subset mean
    zb = BD[:, tt, hh] / sd_null[tt, hh]
    zb = np.nan_to_num(zb, nan=-np.inf)
    sel = zb.argmax(1)
    bias = BD[np.arange(NBOOT), tt[sel], hh[sel]] - D_obs[tt[sel], hh[sel]]
    # the observed pick (in the real data, select by the same statistic)
    z0 = D_obs[tt, hh] / sd_null[tt, hh]
    s0 = z0.argmax()
    picked = f"{names[tt[s0]]} H{HS[hh[s0]]}"
    # z-scale version (fair when the tests have very different precision): bias in z units, mapped back to
    # W_RSI_HI's own scale (its null sd of d_W)
    sdD = D_perm.std(0)
    zbd = np.nan_to_num(BD[:, tt, hh] / sdD[tt, hh], nan=-np.inf)
    seld = zbd.argmax(1)
    bias_z = zbd[np.arange(NBOOT), seld] - (D_obs[tt, hh] / sdD[tt, hh])[seld]
    bc_rows.append(dict(family=fname, k=len(ids), picked=picked, dW_picked=D_obs[tt[s0], hh[s0]],
                        mean_bias=bias.mean(), dW_corrected=D_obs[tt[s0], hh[s0]] - bias.mean(),
                        z_obs=D_obs[irsi, 2] / sdD[irsi, 2], mean_bias_z=bias_z.mean(),
                        rsi_hi_corrected_zscale=(D_obs[irsi, 2] / sdD[irsi, 2] - bias_z.mean()) * sdD[irsi, 2],
                        rsi_hi_selected_share=((tt[seld] == irsi) & (hh[seld] == 2)).mean()))
BC = pd.DataFrame(bc_rows)
L(BC.round(3).to_string(index=False))
BC.to_csv(f'{HERE}/s1_bootstrap_bias.csv', index=False, float_format='%.5f')
# plain bootstrap CI of W_RSI_HI d_W H20 and mean
ci = np.percentile(BD[:, irsi, 2], [5, 50, 95])
ci_m = np.percentile(BM[:, irsi, 2], [5, 50, 95])
L(f"quarter bootstrap W_RSI_HI H20: d_W 90% [{ci[0]:+.2f}, {ci[2]:+.2f}] (P(d_W<=0) {(BD[:, irsi, 2] <= 0).mean():.3f}); "
  f"mean 90% [{ci_m[0]:+.2f}, {ci_m[2]:+.2f}]")

# ---------------------------------------------------------------- (d) shrinkage
L('\n(d) empirical-Bayes shrinkage of d_W (H20) across subsets (normal-normal, method of moments)')
for lab, sel in [('36 subsets H20', np.arange(NT)), ('10 singles H20', np.arange(10))]:
    d = D_obs[sel, 2]
    s = se_dW[sel, 2]
    tau2 = max(0.0, np.var(d, ddof=1) - np.mean(s ** 2))
    mu0 = np.average(d, weights=1 / (s ** 2 + tau2)) if tau2 > 0 else np.average(d, weights=1 / s ** 2)
    shr = tau2 / (tau2 + se_dW[irsi, 2] ** 2)
    post = mu0 + shr * (D_obs[irsi, 2] - mu0)
    L(f"  {lab}: sd(d_W) across tests {np.std(d, ddof=1):.3f}, mean se^2 {np.mean(s ** 2):.3f} -> tau {np.sqrt(tau2):.3f}; "
      f"grand mean {mu0:+.3f}; W_RSI_HI d_W {D_obs[irsi, 2]:+.3f} (se {se_dW[irsi, 2]:.3f}) -> shrunk {post:+.3f} "
      f"(weight on own estimate {shr:.2f})")
for tau in (0.25, 0.5, 1.0):
    se = se_dW[irsi, 2]
    w_ = tau ** 2 / (tau ** 2 + se ** 2)
    L(f"  skeptical prior d_W ~ N(0, {tau}^2): posterior mean {w_ * D_obs[irsi, 2]:+.3f} "
      f"(sd {np.sqrt(w_) * se:.3f})")
L(f"note: d_W of W_RSI_HI H20 {D_obs[irsi, 2]:+.3f} is the same-quarter gap to ALL winners; the pooled gap "
  f"main - all winners is {M_obs[irsi, 2] - Y[:, 2].mean():+.3f} (between-quarter composition adds "
  f"{M_obs[irsi, 2] - Y[:, 2].mean() - D_obs[irsi, 2]:+.3f})")
np.save(f'{HERE}/s1_dw_boot.npy', BD[:, irsi, :])
