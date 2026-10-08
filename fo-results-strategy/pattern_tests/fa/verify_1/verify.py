"""Adversarial check of 'lag rule + last quarter's sales YoY growth above the previous quarter's'.
    python3 verify.py  (needs accel_mine.csv from build_accel.py) -> verify.log, trades_mine.csv
"""
import os, sys
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.environ.get('LAB_ROOT', 'lab') + ""
REPO = os.environ.get('REPO_ROOT', '.') + "/results/lag10_volume"
COST = 0.17
rng = np.random.default_rng(11)
pd.set_option("display.width", 250, "display.max_columns", 50, "display.max_rows", 200)
log = open(f"{HERE}/verify.log", "w")
def P(*a):
    s = " ".join(str(x) for x in a)
    print(s); log.write(s + "\n")

A = pd.read_csv(f"{HERE}/accel_mine.csv")
T = pd.read_csv(f"{REPO}/trades.csv")
T13 = pd.read_csv(f"{REPO}/trades_vol13.csv")
F = pd.read_csv(f"{SCR}/fa/build/fa_panel.csv", usecols=["symbol", "quarter", "sales_yoy_accel_pp", "l1_sales_yoy_pct",
                                                        "l2_sales_yoy_pct"])
A = A.merge(F, on=["symbol", "quarter"], how="left")
A["inS85"] = pd.MultiIndex.from_frame(A[["symbol", "quarter"]]).isin(pd.MultiIndex.from_frame(T[["symbol", "quarter"]]))
A["inS44"] = pd.MultiIndex.from_frame(A[["symbol", "quarter"]]).isin(pd.MultiIndex.from_frame(T13[["symbol", "quarter"]]))
P("S85 found:", A.inS85.sum(), " S44 found:", A.inS44.sum())
S = A[A.inS85].merge(T[["symbol", "quarter", "three_day", "take_profit"]], on=["symbol", "quarter"], suffixes=("", "_ref"))
P("max |three_day - ref*100|", np.abs(S.three_day - 100 * S.three_day_ref).max(),
  " max |tp3 - ref*100|", np.abs(S.tp3 - 100 * S.take_profit).max())

# ---------------- (1) compare my label with the panel's
S["mine"] = np.where(S.accel.isna(), "unk", np.where(S.accel > 0, "T", "F"))
S["panel"] = np.where(S.sales_yoy_accel_pp.isna(), "unk", np.where(S.sales_yoy_accel_pp > 0, "T", "F"))
P("\nmy label vs panel label (S85):\n", pd.crosstab(S.mine, S.panel))
dif = S[(S.mine != S.panel)]
P("disagreements:\n", dif[["symbol", "quarter", "fin_type", "basis1", "same_basis", "y1", "y2", "accel",
                            "l1_sales_yoy_pct", "l2_sales_yoy_pct", "sales_yoy_accel_pp", "three_day"]].round(2).to_string())
both = S.accel.notna() & S.sales_yoy_accel_pp.notna()
P("max |accel mine - panel| where both:", np.abs(S.accel - S.sales_yoy_accel_pp)[both].max().round(3),
  " n large (>1pp):", (np.abs(S.accel - S.sales_yoy_accel_pp)[both] > 1).sum())
P("unknown rows (mine):\n", S[S.accel.isna()][["symbol", "quarter", "fin_type", "industry", "s1", "s2", "s5", "s6",
                                                  "three_day"]].round(1).to_string())
P("PIT: L1/L2 published before cutoff for all S85 rows:", S.pit_ok.all(), "; strict (date known):", S.pit_strict.sum(), "/", len(S))
P("mixed-basis rows among known S85:", (~S.same_basis[S.accel.notna()]).sum())
S.to_csv(f"{HERE}/trades_mine.csv", index=False, float_format="%.4f")


def stats(d, label):
    y = d.three_day.to_numpy(); q = d.qn.to_numpy()
    if len(y) == 0:
        return {"rule": label, "n": 0}
    qm = pd.Series(y).groupby(q).mean()
    ys = np.sort(y)
    bestq = qm.idxmax()
    return {"rule": label, "n": len(y), "mean": y.mean(), "net": y.mean() - COST, "tp": d.tp3.mean(),
            "up%": 100 * (y > 0).mean(), "q+": f"{(qm > 0).sum()}/{len(qm)}",
            "n14": (q <= 13).sum(), "f14": y[q <= 13].mean(), "n8": (q >= 14).sum(), "l8": y[q >= 14].mean(),
            "xb5": ys[:-5].mean() if len(y) > 5 else np.nan,
            "x_bestq": y[q != bestq].mean(), "median": np.median(y),
            "loqo_min": min(y[q != qq].mean() for qq in np.unique(q)),
            "loqo_max": max(y[q != qq].mean() for qq in np.unique(q))}


P("\n==== headline, my labels (S85) ====")
K = S[S.accel.notna()]
rows = [stats(S, "S85 all"), stats(K[K.accel > 0], "accel>0 (candidate)"), stats(K[K.accel <= 0], "accel<=0"),
        stats(S[S.accel.isna()], "unknown")]
P(pd.DataFrame(rows).round(2).to_string(index=False))
P("\nsame with the PANEL's labels:")
Kp = S[S.sales_yoy_accel_pp.notna()]
P(pd.DataFrame([stats(Kp[Kp.sales_yoy_accel_pp > 0], "panel accel>0"),
                stats(Kp[Kp.sales_yoy_accel_pp <= 0], "panel accel<=0")]).round(2).to_string(index=False))

# per-quarter table
P("\nper quarter (accel>0 vs <=0):")
pq = K.assign(side=np.where(K.accel > 0, "T", "F")).groupby(["qn", "side"]).three_day.agg(["size", "mean"]).unstack()
P(pq.round(2).to_string())
P("T trades:\n", K[K.accel > 0].sort_values("three_day")[["symbol", "quarter", "qn", "y1", "y2", "accel", "three_day"]]
  .round(2).to_string(index=False))

# ---------------- (2) robustness: neighbouring cut-offs and variants
P("\n==== robustness ====")
rob = []
for c in (-10, -5, -2, 0, 2, 5, 10):
    rob.append(stats(K[K.accel > c], f"accel>{c}"))
rob.append(stats(K[(K.accel > 0) & K.same_basis], "accel>0 same basis only"))
rob.append(stats(K[(K.accel > 0) & (K.y1 > 0)], "accel>0 & L1 sales yoy>0"))
rob.append(stats(K[K.y1 > 0], "L1 sales yoy>0"))
rob.append(stats(K[K.y1 > 10], "L1 sales yoy>10"))
rob.append(stats(K[K.y1 > K.y1.median()], "L1 sales yoy > median of S85"))
nonfin = K[K.fin_type == "Company"]
rob.append(stats(nonfin[nonfin.accel > 0], "accel>0 non-financials"))
rob.append(stats(nonfin[nonfin.accel <= 0], "accel<=0 non-financials"))
fin = K[K.fin_type != "Company"]
rob.append(stats(fin[fin.accel > 0], "accel>0 financials"))
rob.append(stats(fin[fin.accel <= 0], "accel<=0 financials"))
# 1.3x volume base
K44 = A[A.inS44 & A.accel.notna()]
rob.append(stats(K44[K44.accel > 0], "S44 accel>0"))
rob.append(stats(K44[K44.accel <= 0], "S44 accel<=0"))
P(pd.DataFrame(rob).round(2).to_string(index=False))

# ---------------- (3) luck
y, q, lab = K.three_day.to_numpy(), K.qn.to_numpy(), (K.accel > 0).to_numpy()
D = y[lab].mean() - y[~lab].mean()
NP = 50000
Dp = np.empty(NP); Mp = np.empty(NP)
for i in range(NP):
    l2 = lab.copy()
    for qq in np.unique(q):
        ix = np.flatnonzero(q == qq)
        l2[ix] = rng.permutation(lab[ix])
    Dp[i] = y[l2].mean() - y[~l2].mean(); Mp[i] = y[l2].mean()
P(f"\nwithin-quarter permutation (known S85 rows): D = {D:.2f}, two-sided p = {(np.abs(Dp) >= abs(D) - 1e-12).mean():.3f},"
  f" one-sided p (T mean >= observed among random same-size per-quarter picks from S85-known) = {(Mp >= y[lab].mean() - 1e-12).mean():.3f}")
# vs random same-size per-quarter picks from ALL in_fo results (is the 37 just the lag rule?)
Y, QA = A.three_day.to_numpy(), A.qn.to_numpy()
tq = pd.Series(q[lab]).value_counts()
tot = np.zeros(20000)
for qq, k in tq.items():
    ix = np.flatnonzero(QA == qq)
    tot += np.array([Y[rng.choice(ix, k, replace=False)].sum() for _ in range(20000)])
rnd = tot / lab.sum()
P(f"vs random same-size per-quarter picks from all in_fo results: rule {y[lab].mean():.2f}, random mean {rnd.mean():.2f}, "
  f"p = {(rnd >= y[lab].mean()).mean():.4f}")
# same comparison for the parent: random same-size picks from the 85 lag-rule trades (any label)
ys, qs_ = S.three_day.to_numpy(), S.qn.to_numpy()
tot = np.zeros(20000)
for qq, k in tq.items():
    ix = np.flatnonzero(qs_ == qq)
    tot += np.array([ys[rng.choice(ix, k, replace=False)].sum() for _ in range(20000)])
rnd = tot / lab.sum()
P(f"vs random same-size per-quarter picks from the 85 lag-rule trades (incl. unknowns): random mean {rnd.mean():.2f}, "
  f"p = {(rnd >= y[lab].mean()).mean():.3f}")

# fundamental placebo: same split on all OTHER in_fo results in the same quarters
R = A[~A.inS85 & A.accel.notna() & A.qn.isin(np.unique(q))]
P(f"\nall other in_fo results, same quarters: accel>0 n={int((R.accel > 0).sum())} mean {R[R.accel > 0].three_day.mean():.3f}; "
  f"accel<=0 n={int((R.accel <= 0).sum())} mean {R[R.accel <= 0].three_day.mean():.3f}")
for nm, sub in (("first14", R[R.qn <= 13]), ("last8", R[R.qn >= 14])):
    P(f"  {nm}: T {sub[sub.accel > 0].three_day.mean():.3f}  F {sub[sub.accel <= 0].three_day.mean():.3f}")
# Bonferroni/Holm-type: B tried 75 things; 11 pre splits in main family
p2 = (np.abs(Dp) >= abs(D) - 1e-12).mean()
P(f"Bonferroni over the 11-split main family: {min(1, 11 * p2):.2f}; over 75 things: {min(1, 75 * p2):.2f}")
