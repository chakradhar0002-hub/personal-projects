#!/usr/bin/env python3
"""Verifier analysis of the candidate W & GOOD & RSI(14)>50, E0 H20, Nifty-hedged, from raw_events.csv (build_raw.py).

Pre-registered by the verifier BEFORE running (textbook neighbours only, all counted and printed):
  TA neighbours : RSI(14) > 40, 45, 50, 55, 60; RSI band 50-70; close > SMA50 at cutoff; close > SMA200 at cutoff
  FA neighbours : GOOD (25/15 or margin +2pp); 20/10 or +1pp; 30/20 or +3pp; profit+sales part only; margin part only
  Winner cut    : XN > 3, 4, 5, 6
  Horizon       : 5, 10, 15, 20, 30 sessions
  Luck parents  : (a) winners eligible for GOOD and RSI (the candidate's pool); (b) winners & GOOD (does RSI add?);
                  (c) winners & RSI>50 (does GOOD add?); (d) all eligible in_fo results (is it more than a winner effect?)
                  20,000 random same-size per-quarter picks each, one-sided.
Costs: hedged net = vsN gross - 0.19 (0.17 stock + 0.02 Nifty hedge); unhedged net = raw - 0.17.
"""
import os  # LAB_ROOT: scratch folder with ta/, fa/, report/, sector_lab/data; REPO_ROOT: this repo
import numpy as np
import pandas as pd

OUT = os.environ.get('LAB_ROOT', 'lab') + "/tafa/verify_1"
rng = np.random.default_rng(7)
df = pd.read_csv(f"{OUT}/raw_events.csv")
Z = np.load(f"{OUT}/raw_daily.npz", allow_pickle=True)
R, TRADED, NIFTY = Z["R"], Z["TRADED"], Z["NIFTY"]
syms = list(Z["syms"])
SYM = {s: j for j, s in enumerate(syms)}

# SMA50 / SMA200 ratio at the cutoff on traded days from the cumulative-return index
T, N = R.shape
S50 = np.full((T, N), np.nan)
S200 = np.full((T, N), np.nan)
for j in range(N):
    rows = np.flatnonzero(TRADED[:, j])
    if len(rows) < 60:
        continue
    r = np.nan_to_num(R[rows, j]); r[0] = 0
    c = pd.Series(np.cumprod(1 + r))
    S50[rows, j] = (c / c.rolling(50).mean() - 1).to_numpy()
    S200[rows, j] = (c / c.rolling(200).mean() - 1).to_numpy()
S50 = pd.DataFrame(S50).ffill().to_numpy()
S200 = pd.DataFrame(S200).ffill().to_numpy()
jj = df.symbol.map(SYM).to_numpy(int)
df["c_vs_sma50"] = S50[df.i_cut.to_numpy(int), jj]
df["c_vs_sma200"] = S200[df.i_cut.to_numpy(int), jj]

df = df[df.tradable].reset_index(drop=True)
# one basis per computation (preferred basis if it has Q and Q-4, else the other basis) - build_raw.py *_1b fields
for c in ("pat_yoy", "sales_yoy", "mchg_pp"):
    df[c] = df[c + "_1b"]
pat, sal, mc = df.pat_yoy, df.sales_yoy, df.mchg_pp
E_GOOD = (pat.notna() & sal.notna()) | mc.notna()
E_RSI = df.rsi_cut.notna()
QN = df.qn.to_numpy()
FIRST = QN <= 13
for H in (5, 10, 15, 20, 30):
    df[f"v{H}"] = df[f"raw_H{H}"] - df[f"nif_H{H}"] - 0.19


def good(p=25, s=15, m=2, parts="both"):
    a = (pat > p) & (sal > s)
    b = mc > m
    return {"both": a | b, "ps": a, "m": b}[parts]


def stats(mask, col="v20"):
    x = df.loc[mask, col].to_numpy()
    q = QN[mask]
    qm = pd.Series(x).groupby(q).mean()
    s = np.sort(x)
    best_q = qm.idxmax() if len(qm) else None
    return dict(n=len(x), net=x.mean(), up=(x > 0).mean() * 100, nq=len(qm), qpos=int((qm > 0).sum()),
                t_q=qm.mean() / (qm.std(ddof=1) / np.sqrt(len(qm))) if len(qm) > 2 else np.nan,
                first14=x[FIRST[mask]].mean(), last8=x[~FIRST[mask]].mean(),
                wo_best5=s[:-5].mean() if len(s) > 5 else np.nan,
                wo_best_q=x[q != best_q].mean() if best_q is not None else np.nan, best_q=best_q)


def luck(mask, pool, col="v20", nd=20000):
    x = df.loc[mask, col].to_numpy()
    tot = np.zeros(nd)
    kt = 0
    for q in np.unique(QN[mask]):
        k = int((mask & (QN == q)).sum())
        pv = df.loc[pool & (QN == q), col].to_numpy()
        n = len(pv)
        if k == n:
            tot += pv.sum()
        else:
            pick = np.argpartition(rng.random((nd, n)), k - 1, axis=1)[:, :k]
            tot += pv[pick].sum(1)
        kt += k
    d = tot / kt
    return (1 + (d >= x.mean()).sum()) / (1 + nd), d.mean()


def dq_t(mask, pool, col="v20"):
    """per-quarter difference subset - pool mean, t across quarters"""
    a = df.loc[mask].groupby("qn")[col].mean()
    b = df.loc[pool].groupby("qn")[col].mean().reindex(a.index)
    d = a - b
    return d.mean(), d.mean() / (d.std(ddof=1) / np.sqrt(len(d))), int((d > 0).sum()), len(d)


pd.set_option("display.width", 250, "display.max_columns", 40, "display.max_rows", 200)
W = (df.XN > 4)
G = good() & E_GOOD
RH = df.rsi_cut > 50
CAND = W & G & RH
ELIG = W & E_GOOD & E_RSI
print("=== CANDIDATE rebuilt from raw: W & GOOD & RSI>50, H20")
s = stats(CAND)
x = df.loc[CAND]
print(f"n {s['n']}; raw gross {x.raw_H20.mean():+.2f}  raw net {x.raw_H20.mean() - 0.17:+.2f}  vsN gross "
      f"{(x.raw_H20 - x.nif_H20).mean():+.2f}  vsN net {s['net']:+.2f}  TP(+3% hedged) net {(x.tp_hedged_H20 - 0.19).mean():+.2f}")
print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in s.items()})
# leave one quarter out
lo = [df.loc[CAND & (QN != q), "v20"].mean() for q in np.unique(QN[CAND])]
print(f"leave-one-quarter-out mean range {min(lo):+.2f} .. {max(lo):+.2f}")
pq = df.loc[CAND].groupby("qn").v20.agg(["size", "mean"]).round(2)
pw = df.loc[W].groupby("qn").v20.mean().round(2)
pq["all_winners"] = pw
print(pq.T.to_string())

print("\n=== references (H20 vsN net)")
for nm, m in [("all in_fo results", np.ones(len(df), bool)), ("plain winners", W), ("winners eligible", ELIG),
              ("winners & GOOD", W & G), ("winners & RSI>50", W & RH & E_RSI), ("winners & RSI<=50", W & ~RH & E_RSI),
              ("winners & GOOD & RSI<=50", W & G & ~RH), ("winners & notGOOD & RSI>50", W & E_GOOD & ~G & RH),
              ("winners & notGOOD & RSI<=50", W & E_GOOD & ~G & ~RH)]:
    s_ = stats(m)
    print(f"  {nm:30s} n {s_['n']:4d} net {s_['net']:+.2f} first14 {s_['first14']:+.2f} last8 {s_['last8']:+.2f} "
          f"q+ {s_['qpos']}/{s_['nq']} wo_best5 {s_['wo_best5']:+.2f}")

print("\n=== LUCK (H20) vs random same-size per-quarter picks")
for nm, pool in [("winners eligible (candidate pool)", ELIG), ("winners & GOOD (does RSI add?)", W & G & E_RSI),
                 ("winners & RSI>50 (does GOOD add?)", W & RH & E_GOOD),
                 ("all eligible in_fo results", E_GOOD & E_RSI)]:
    p, rm = luck(CAND, pool)
    dm, t, qp, nq = dq_t(CAND, pool)
    print(f"  {nm:38s} pool n {int(pool.sum()):4d} pool mean {df.loc[pool, 'v20'].mean():+.2f} random mean {rm:+.2f} "
          f"p {p:.4f}; per-quarter gain {dm:+.2f} t {t:.2f} ({qp}/{nq} quarters better)")
for H in (5, 10, 15, 30):
    p, rm = luck(CAND, ELIG, col=f"v{H}")
    s_ = stats(CAND, f"v{H}")
    print(f"  H{H}: net {s_['net']:+.2f} winners-elig {df.loc[ELIG, f'v{H}'].mean():+.2f} p {p:.4f} "
          f"first14 {s_['first14']:+.2f} last8 {s_['last8']:+.2f}")

print("\n=== ROBUSTNESS GRID (H20 vsN net; p vs random picks from winners(XN cut) eligible)")
TA = {"RSI>40": df.rsi_cut > 40, "RSI>45": df.rsi_cut > 45, "RSI>50": RH, "RSI>55": df.rsi_cut > 55,
      "RSI>60": df.rsi_cut > 60, "RSI 50-70": (df.rsi_cut > 50) & (df.rsi_cut <= 70),
      "C>SMA50": df.c_vs_sma50 > 0, "C>SMA200": df.c_vs_sma200 > 0, "noTA": pd.Series(True, index=df.index)}
FA = {"GOOD25/15|2": good(), "GOOD20/10|1": good(20, 10, 1), "GOOD30/20|3": good(30, 20, 3),
      "PAT25&SAL15 only": good(parts="ps"), "MARGIN+2 only": good(parts="m"), "noFA": pd.Series(True, index=df.index)}
rows = []
for wc in (3, 4, 5, 6):
    Wc = df.XN > wc
    pool = Wc & E_GOOD & E_RSI
    for tn, tm in TA.items():
        for fn, fm in FA.items():
            m = pool & tm & fm
            if m.sum() < 15:
                continue
            s_ = stats(m)
            p, _ = luck(m, pool, nd=4000) if m.sum() < pool.sum() else (np.nan, np.nan)
            rows.append(dict(win=wc, TA=tn, FA=fn, n=s_["n"], net=s_["net"], pool=df.loc[pool, "v20"].mean(),
                             gain=s_["net"] - df.loc[pool, "v20"].mean(), first14=s_["first14"], last8=s_["last8"],
                             qpos=f"{s_['qpos']}/{s_['nq']}", wo5=s_["wo_best5"], p=p))
g = pd.DataFrame(rows)
g.to_csv(f"{OUT}/grid.csv", index=False, float_format="%.3f")
print(g[g.win == 4].round(2).to_string(index=False))
print("\nwinner cut 3/5/6, FA = GOOD25/15|2:")
print(g[(g.win != 4) & (g.FA == "GOOD25/15|2")].round(2).to_string(index=False))
print("\nFA effect at fixed TA (winners XN>4, RSI>50): GOOD vs not-GOOD")
print(g[(g.win == 4) & (g.TA == "RSI>50")][["FA", "n", "net", "gain", "p"]].round(3).to_string(index=False))
df.to_csv(f"{OUT}/analysis_rows.csv", index=False, float_format="%.5g")
