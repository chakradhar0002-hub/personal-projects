"""POST-HOC (not pre-registered; written after fa_on_lag.py showed no split working): do the fixed cut points hide a
continuous relation? Spearman rank correlation of each raw fundamental with three_day inside S85 and S44 (known rows),
p from 10,000 within-quarter shuffles of the outcome, Holm over the pre-results features. Counted as extra tests.

    python3 posthoc_ranks.py    (writes posthoc_ranks.csv, posthoc.log)
"""
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import rankdata

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.dirname(os.path.dirname(HERE))
NPERM = 10000
rng = np.random.default_rng(7)

F = pd.read_csv(f"{SCR}/fa/build/fa_panel.csv")
E0 = pd.read_csv(f"{SCR}/ta/build/events_ta.csv", usecols=["symbol", "quarter", "lag_pct", "vol_ratio_5_60"])
E = F.merge(E0, on=["symbol", "quarter"])
E = E[(E.in_fo == True) & E.three_day.notna()].reset_index(drop=True)
E["margin_chg_pp"] = np.where(E.fin_type == "Company", E.l1_ebitda_margin_chg_yoy_pp, E.l1_net_margin_chg_yoy_pp)
E["debt_equity_co"] = np.where(E.fin_type == "Company", E.debt_equity, np.nan)
PRE = ["roe_pct", "debt_equity_co", "l1_pat_yoy_pct", "l1_sales_yoy_pct", "pat_yoy_accel_pp", "sales_yoy_accel_pp",
       "margin_chg_pp", "pe_vs_own3y_pct", "pe_vs_peers_pct", "earnings_yield_pct", "piotroski_frac", "log_mcap"]
POST = ["rq_sales_yoy_pct", "rq_pat_yoy_pct", "rq_pat_surprise_vs_trend_pp"]


def wq_spearman(x, y, q):
    """Spearman rho and within-quarter shuffle p (two-sided)."""
    rx, ry = rankdata(x), rankdata(y)
    rho = np.corrcoef(rx, ry)[0, 1]
    o = np.argsort(q, kind="stable")
    rx, ry, q = rx[o], ry[o], q[o]
    idx = np.argsort(q[None, :] + rng.random((NPERM, len(q))), axis=1)
    Ry = ry[idx]
    rxc = rx - rx.mean()
    rp = ((Ry - Ry.mean(1, keepdims=True)) * rxc).sum(1) / (np.sqrt((rxc ** 2).sum()) * Ry.std(1) * np.sqrt(len(q)))
    return rho, (np.sum(np.abs(rp) >= abs(rho) - 1e-12) + 1) / (NPERM + 1)


def holm(p):
    p = np.asarray(p, float)
    o = np.argsort(p)
    adj, run = np.empty(len(p)), 0
    for r_, i in enumerate(o):
        run = max(run, (len(p) - r_) * p[i])
        adj[i] = min(1, run)
    return adj


rows = []
for base, v in (("S85", 1.0), ("S44", 1.3)):
    m = (E.lag_pct < -10) & (E.vol_ratio_5_60 >= v)
    d = E[m]
    for fam, feats in (("pre", PRE), ("post", POST)):
        part = []
        for f in feats:
            k = d[f].notna().to_numpy()
            x, y, q = d[f].to_numpy(float)[k], d.three_day.to_numpy()[k], d.qn.to_numpy()[k]
            rho, p = wq_spearman(x, y, q)
            f14, l8 = q <= 13, q >= 14
            r14 = np.corrcoef(rankdata(x[f14]), rankdata(y[f14]))[0, 1] if f14.sum() > 4 else np.nan
            r8 = np.corrcoef(rankdata(x[l8]), rankdata(y[l8]))[0, 1] if l8.sum() > 4 else np.nan
            part.append({"base": base, "family": fam, "feature": f, "n": int(k.sum()), "rho": rho, "p_perm": p,
                         "rho_f14": r14, "n_f14": int(f14.sum()), "rho_l8": r8, "n_l8": int(l8.sum())})
        part = pd.DataFrame(part)
        part["p_holm"] = holm(part.p_perm)
        rows.append(part)
R = pd.concat(rows)
R.to_csv(f"{HERE}/posthoc_ranks.csv", index=False, float_format="%.4f")
with open(f"{HERE}/posthoc.log", "w") as fh:
    fh.write(R.round(3).to_string(index=False) + "\n")
print(R.round(3).to_string(index=False))
