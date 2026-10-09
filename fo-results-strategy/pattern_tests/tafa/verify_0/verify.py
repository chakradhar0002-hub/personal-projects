"""VERIFIER analysis of candidate X8 (lag rule AND good fundamentals AND oversold count >= 3), on the independent
rebuild (rebuilt_events.csv, s85_joined.csv). Neighbour grid fixed here BEFORE running (textbook neighbours only):
  TA: count >= 2 / 3 / 4 with base thresholds; base count >= 3 with all six thresholds loosened
      (RSI14<35, RSI2<15, %K<25, %B<0.05 (i.e. within 1.5sd band replaced by pctb_15<0), CCI<-75, MFI<25) and tightened
      (RSI14<25, RSI2<5, %K<15, below 2.5sd band, CCI<-150, MFI<15); sample-sd Bollinger.
  FA: growth > 0 (base) / > 5% / > 10%; only PAT growth; only sales growth; only no-loss; no-loss dropped.
Everything reported, none chosen.
"""
import os  # LAB_ROOT: scratch folder with ta/, fa/, report/, sector_lab/data; REPO_ROOT: this repo
import numpy as np, pandas as pd, pickle
from collections import defaultdict
SCR = os.environ.get('LAB_ROOT', 'lab') + ""
OUT = f"{SCR}/tafa/verify_0"
COST = 0.17
rng = np.random.default_rng(99)
X = pd.read_csv(f"{OUT}/rebuilt_events.csv")
X = X[X.three_day.notna()].reset_index(drop=True)


def oscount(d, t):
    return ((d.rsi14 < t["rsi14"]).astype(int) + (d.rsi2 < t["rsi2"]) + (d.stochk < t["stoch"])
            + (d[t["bbcol"]] < 0) + (d.cci < t["cci"]) + (d.mfi < t["mfi"]))


BASE_T = dict(rsi14=30, rsi2=10, stoch=20, bbcol="pctb", cci=-100, mfi=20)
LOOSE_T = dict(rsi14=35, rsi2=15, stoch=25, bbcol="pctb_15", cci=-75, mfi=25)
TIGHT_T = dict(rsi14=25, rsi2=5, stoch=15, bbcol="pctb_25", cci=-150, mfi=15)
SAMP_T = dict(BASE_T, bbcol="pctb_s1")


def goodfund(d, g=0.0, use=("loss", "sales", "pat")):
    good = np.ones(len(d), bool); bad = np.zeros(len(d), bool)
    if "loss" in use:
        good &= (d.loss4 == 0).to_numpy(); bad |= (d.loss4 == 1).to_numpy()
    if "sales" in use:
        good &= (d.sales_yoy > g).to_numpy(); bad |= (d.sales_yoy <= g).to_numpy()
    if "pat" in use:
        good &= (d.pat_yoy > g).to_numpy(); bad |= (d.pat_yoy <= g).to_numpy()
    return np.where(good, 1, np.where(bad, 0, -1))


X["os"] = oscount(X, BASE_T)
X["gf"] = goodfund(X)
X["S85"] = (X.lag < -10) & (X.vol >= 1.0)
X["S44"] = (X.lag < -10) & (X.vol >= 1.3)
S = X[X.S85].reset_index(drop=True)


def stats(d, label):
    y = d.three_day.to_numpy()
    if len(y) == 0:
        return {"rule": label, "n": 0}
    q = d.qn.to_numpy()
    qm = pd.Series(y).groupby(q).mean()
    ys = np.sort(y)
    best_q = qm.idxmax()
    return {"rule": label, "n": len(y), "mean": y.mean(), "net": y.mean() - COST, "tp": d.tp3.mean(),
            "up%": 100 * (y > 0).mean(), "q": f"{(qm > 0).sum()}/{len(qm)}",
            "n14": int((q <= 13).sum()), "f14": y[q <= 13].mean() if (q <= 13).any() else np.nan,
            "n8": int((q >= 14).sum()), "l8": y[q >= 14].mean() if (q >= 14).any() else np.nan,
            "xb5": ys[:-5].mean() if len(y) > 5 else np.nan, "xbestq": y[q != best_q].mean(),
            "median": np.median(y)}


def split(d, lab, name):
    k = lab >= 0
    t, f = d[lab == 1], d[lab == 0]
    a, b = stats(t, name), stats(f, name + " [other side]")
    D = t.three_day.mean() - f.three_day.mean()
    return a, b, D


rows = []
x8 = np.where(S.gf == -1, -1, ((S.gf == 1) & (S.os >= 3)).astype(int))
S["x8"] = x8
a, b, D = split(S, x8, "X8 base (S85)")
print("=== BASE on the independent rebuild")
print(pd.DataFrame([a, b]).round(2).to_string(index=False), "\n D =", round(D, 2))
print("trades without ADANIPORTS Q3 FY23:", round(S[(S.x8 == 1) & ~((S.symbol == "ADANIPORTS") & (S.quarter == "Q3 FY23"))].three_day.mean(), 2))
print("share of the summed return from ADANIPORTS:", round(19.09 / S[S.x8 == 1].three_day.sum(), 3))
print("net after cost of the take-profit version:", round(S[S.x8 == 1].tp3.mean() - COST, 2))
print("parent S85 mean", round(S.three_day.mean(), 2), "known-FA S85 mean", round(S[S.x8 >= 0].three_day.mean(), 2))
print("per-quarter means of X8 trades:")
print(S[S.x8 == 1].groupby("qn").three_day.agg(["size", "mean"]).round(2).T.to_string())

# leave one quarter out
print("\n=== LEAVE ONE QUARTER OUT (mean of X8 trades, D vs other known S85 trades)")
lo = []
for q in sorted(S[S.x8 == 1].qn.unique()):
    m = S.qn != q
    t, f = S[m & (S.x8 == 1)], S[m & (S.x8 == 0)]
    lo.append((q, len(t), t.three_day.mean(), t.three_day.mean() - f.three_day.mean()))
lo = pd.DataFrame(lo, columns=["dropped_qn", "n", "mean", "D"])
print(lo.round(2).to_string(index=False))
print("LOQO min mean", round(lo["mean"].min(), 2), "min D", round(lo.D.min(), 2))

# 2x2 and volume bands
print("\n=== 2x2 cells (known FA) and volume bands")
K = S[S.gf >= 0]
print(K.groupby([K.gf, K.os >= 3]).three_day.agg(["size", "mean"]).round(2))
for band, m in (("vol 1.0-1.3", S.vol < 1.3), ("vol >= 1.3", S.vol >= 1.3)):
    t, f = S[m & (S.x8 == 1)], S[m & (S.x8 == 0)]
    print(f"{band}: X8 {len(t)} {t.three_day.mean():.2f} | other {len(f)} {f.three_day.mean():.2f}")

# neighbours
print("\n=== NEIGHBOURING THRESHOLDS (S85)")
var = []
TA_V = [("os>=3 base", BASE_T, 3), ("os>=2", BASE_T, 2), ("os>=4", BASE_T, 4), ("os>=3 loose levels", LOOSE_T, 3),
        ("os>=3 tight levels", TIGHT_T, 3), ("os>=3 sample-sd BB", SAMP_T, 3)]
FA_V = [("gf base", dict()), ("growth>5%", dict(g=5.0)), ("growth>10%", dict(g=10.0)),
        ("loss+PAT only", dict(use=("loss", "pat"))), ("loss+sales only", dict(use=("loss", "sales"))),
        ("no-loss only", dict(use=("loss",))), ("growth only (no loss test)", dict(use=("sales", "pat")))]
for tn, tt, k in TA_V:
    osk = oscount(S, tt) >= k
    for fnm, fk in FA_V:
        gf = goodfund(S, **fk)
        lab = np.where(gf == -1, -1, ((gf == 1) & osk).astype(int))
        a, b, D = split(S, lab, f"{tn} & {fnm}")
        var.append({**a, "D": D, "other_n": b["n"], "other_mean": b.get("mean")})
V = pd.DataFrame(var)
print(V[["rule", "n", "mean", "net", "tp", "q", "f14", "l8", "xb5", "xbestq", "D", "other_n", "other_mean"]].round(2).to_string(index=False))
V.to_csv(f"{OUT}/neighbours.csv", index=False)
print("neighbour grid: median mean", round(V["mean"].median(), 2), "; median D", round(V.D.median(), 2),
      "; share D > 1pp", round((V.D > 1).mean(), 2), "; share xb5 > S85 xb5 (1.36)", round((V.xb5 > 1.36).mean(), 2))

# S44
S4 = X[X.S44].reset_index(drop=True)
lab4 = np.where(S4.gf == -1, -1, ((S4.gf == 1) & (S4.os >= 3)).astype(int))
a, b, D = split(S4, lab4, "X8 on S44")
print("\n=== S44\n", pd.DataFrame([a, b]).round(2).to_string(index=False), " D", round(D, 2))

# luck
print("\n=== LUCK")


def rand_picks(pool, sel_q, n=20000):
    tot, k_all = np.zeros(n), 0
    for q, k in sel_q.items():
        y = pool[pool.qn == q].three_day.to_numpy()
        if len(y) < k:
            continue
        pick = np.argsort(rng.random((n, len(y))), axis=1)[:, :k]
        tot += y[pick].sum(1); k_all += k
    return tot / k_all


sel = S[S.x8 == 1]
obs = sel.three_day.mean()
sel_q = sel.groupby("qn").size()
for nm, pool in (("S85 parent (85)", S), ("S85 known-FA (78)", S[S.x8 >= 0]), ("all in_fo results", X),
                 ("lag<-10 any volume", X[X.lag < -10])):
    r = rand_picks(pool, sel_q)
    print(f"random same-size-per-quarter picks from {nm}: mean {r.mean():.2f}, 95th pct {np.percentile(r, 95):.2f}, "
          f"p(>= {obs:.2f}) {(np.sum(r >= obs) + 1) / (len(r) + 1):.4f}")
# within-quarter permutation of the label among known S85
K = S[S.x8 >= 0].reset_index(drop=True)
y, q, lab = K.three_day.to_numpy(), K.qn.to_numpy(), (K.x8 == 1).to_numpy()
D0 = y[lab].mean() - y[~lab].mean()
NP = 20000
Dp = np.empty(NP)
order = np.argsort(q, kind="stable"); y, q, lab = y[order], q[order], lab[order]
for i in range(NP):
    idx = np.argsort(q + rng.random(len(q)), kind="stable")
    ll = lab[idx]
    Dp[i] = y[ll].mean() - y[~ll].mean()
print(f"within-quarter permutation: D {D0:.2f}, one-sided p {(np.sum(Dp >= D0) + 1) / (NP + 1):.4f}, "
      f"two-sided p {(np.sum(np.abs(Dp) >= abs(D0)) + 1) / (NP + 1):.4f}")
# bootstrap CI of the mean (quarter-cluster)
qs = sel.qn.unique()
bm = []
for i in range(5000):
    pickq = rng.choice(qs, len(qs))
    yy = np.concatenate([sel[sel.qn == z].three_day.to_numpy() for z in pickq])
    bm.append(yy.mean())
print(f"quarter-cluster bootstrap 90% CI of the X8 mean: {np.percentile(bm, 5):.2f} .. {np.percentile(bm, 95):.2f}")
bd = []
for i in range(5000):
    ii = rng.integers(0, len(K), len(K))
    kk = K.iloc[ii]
    t = kk[kk.x8 == 1].three_day; f = kk[kk.x8 == 0].three_day
    if len(t) and len(f):
        bd.append(t.mean() - f.mean())
print(f"bootstrap 90% CI of D: {np.percentile(bd, 5):.2f} .. {np.percentile(bd, 95):.2f}")
S.to_csv(f"{OUT}/s85_verified.csv", index=False)
X.to_csv(f"{OUT}/infos_verified.csv", index=False)
