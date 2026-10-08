"""Extra check ADDED AFTER the main run (not pre-registered): joint null for all 44 screens at once.

Shuffle three_day (and tp3) within each quarter across all in_fo results (keeps the quarter effect, breaks any link
between fundamentals and the outcome), recompute every screen's excess vs its eligible pool, 5,000 times.
Gives (1) a Westfall-Young max-|z| family-wise p for each screen (accounts for overlap between screens),
(2) how many screens reach |z| >= 1.96 by chance, versus the number observed.
Output: out/joint_null.csv
"""
import os  # LAB_ROOT: scratch folder with report/, search22/, sector_lab/data, fa/; REPO_ROOT: this repo
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
DATA = os.environ.get('LAB_ROOT', 'lab') + ""
sys.path.insert(0, str(HERE))
import screens  # noqa: E402

panel = pd.read_csv(f"{DATA}/fa/build/fa_panel.csv").merge(pd.read_csv(OUT / "extra_features.csv"), on=["symbol", "quarter"], validate="1:1")
U = panel[(panel.in_fo == True) & panel.three_day.notna()].reset_index(drop=True)
qn = U.qn.to_numpy()
S = screens.build_flags(U)
ids = list(S)
n = len(U)
W = np.zeros((len(S), n))
for j, (m, e, side, lab) in enumerate(S.values()):
    K = m.sum()
    W[j, m] += 1.0 / K
    for q in np.unique(qn[m]):
        kq = (m & (qn == q)).sum()
        pool = e & (qn == q)
        W[j, pool] -= kq / (K * pool.sum())
P = 5000
rng = np.random.default_rng(7)
groups = [np.where(qn == q)[0] for q in np.unique(qn)]
out = {}
for col in ("three_day", "tp3"):
    y = U[col].to_numpy(float)
    obs = W @ y
    Y = np.empty((n, P))
    for p in range(P):
        yy = y.copy()
        for g in groups:
            yy[g] = y[rng.permutation(g)]
        Y[:, p] = yy
    E = W @ Y                                   # screens x perms
    sd = E.std(axis=1, ddof=1)
    z, zs = obs / sd, E / sd[:, None]
    maxz = np.abs(zs).max(axis=0)
    out[f"{col}_excess"] = obs
    out[f"{col}_z"] = z
    out[f"{col}_p_single"] = (1 + (np.abs(zs) >= np.abs(z)[:, None]).sum(axis=1)) / (P + 1)
    out[f"{col}_p_maxT"] = (1 + (maxz[None, :] >= np.abs(z)[:, None]).sum(axis=1)) / (P + 1)
    cnt = (np.abs(zs) >= 1.96).sum(axis=0)
    print(f"{col}: observed screens with |z|>=1.96: {(np.abs(z) >= 1.96).sum()}; under the joint null median "
          f"{np.median(cnt):.0f}, 90th pct {np.percentile(cnt, 90):.0f}, P(count >= observed) "
          f"{np.mean(cnt >= (np.abs(z) >= 1.96).sum()):.2f}; max|z| observed {np.abs(z).max():.2f}, "
          f"null 95th pct of max|z| {np.percentile(maxz, 95):.2f}")
res = pd.DataFrame(out, index=ids)
res.index.name = "id"
res.to_csv(OUT / "joint_null.csv")
print(res.sort_values("three_day_p_single").head(10).round(3).to_string())
