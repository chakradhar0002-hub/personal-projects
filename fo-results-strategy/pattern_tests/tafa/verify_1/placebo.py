#!/usr/bin/env python3
"""Verifier placebo for the TA part (and the TA+FA cell) on NON-results days, built from raw_daily.npz / raw_events.csv.

Quiet day k for a stock: traded at k; no result session (i_rd or i_react of ANY of its events) in [k-10, k+20];
its most recent event before k (i_react < k) was in_fo; k+21 exists, <= 2 blank returns in k+1..k+21.
Quiet "winner": stock return at k - Nifty return at k > 4%. TA state at k-2 (same lag as cutoff vs reaction:
cutoff = result session - 2). FA = GOOD flag of the stock's most recent result with i_react < k (already public).
Outcome = 20-session Nifty-hedged return from close k, net of 0.19. SE clustered by calendar month.
Also: results-day comparison of RSI split on ALL results (not only winners).
"""
import os  # LAB_ROOT: scratch folder with ta/, fa/, report/, sector_lab/data; REPO_ROOT: this repo
import numpy as np
import pandas as pd

SP = os.environ.get('LAB_ROOT', 'lab') + ""
OUT = f"{SP}/tafa/verify_1"
Z = np.load(f"{OUT}/raw_daily.npz", allow_pickle=True)
R, TRADED, RSI, NIFTY = Z["R"], Z["TRADED"], Z["RSI"], Z["NIFTY"]
syms = list(Z["syms"])
SYM = {s: j for j, s in enumerate(syms)}
T, N = R.shape
RSI_ff = pd.DataFrame(RSI).ffill().to_numpy()
days = pd.read_csv(f"{SP}/sector_lab/data/sessions.csv").day.to_numpy()
ev = pd.read_csv(f"{SP}/sector_lab/data/events.csv")
a = pd.read_csv(f"{OUT}/analysis_rows.csv")          # in_fo events with my fundamentals (one basis)
a["GOOD"] = ((a.pat_yoy > 25) & (a.sales_yoy > 15)) | (a.mchg_pp > 2)
good_map = {(r.symbol, r.qn): bool(r.GOOD) for r in a.itertuples()}
nret = np.r_[np.nan, NIFTY[1:] / NIFTY[:-1] - 1]

rows = []
for s, g in ev.groupby("symbol"):
    j = SYM[s]
    g = g.sort_values("i_react")
    block = np.zeros(T + 40, bool)
    for c in ("i_rd", "i_react"):
        block[g[c].to_numpy(int)] = True
    cb = np.r_[0, np.cumsum(block)]
    for k in range(12, T - 22):
        if not TRADED[k, j] or not np.isfinite(R[k, j]):
            continue
        xn = (R[k, j] - nret[k]) * 100
        if xn <= 4:
            continue
        if cb[k + 21] - cb[max(k - 10, 0)] != 0:
            continue
        prev = g[g.i_react < k]
        if prev.empty or not bool(prev.in_fo.iloc[-1]):
            continue
        if (~np.isfinite(R[k + 1:k + 22, j])).sum() > 2:
            continue
        stk = np.prod(1 + np.nan_to_num(R[k + 1:k + 21, j])) - 1
        nif = NIFTY[k + 20] / NIFTY[k] - 1
        stk5 = np.prod(1 + np.nan_to_num(R[k + 1:k + 6, j])) - 1
        nif5 = NIFTY[k + 5] / NIFTY[k] - 1
        lastq = int(prev.qn.iloc[-1])
        rows.append(dict(symbol=s, k=k, month=days[k][:7], xn=xn, rsi_m2=RSI_ff[k - 2, j],
                         good_last=good_map.get((s, lastq), np.nan), v20=(stk - nif) * 100 - 0.19,
                         v5=(stk5 - nif5) * 100 - 0.19))
q = pd.DataFrame(rows)
q.to_csv(f"{OUT}/placebo_quiet_winners.csv", index=False, float_format="%.5g")
print(f"quiet-day winners: {len(q)}  ({q.month.min()}..{q.month.max()}), symbols {q.symbol.nunique()}")


def cm(x, cl):
    x = np.asarray(x, float)
    d = pd.DataFrame({"x": x - x.mean(), "c": np.asarray(cl)})
    s = d.groupby("c").x.sum()
    return x.mean(), np.sqrt((s ** 2).sum()) / len(x)


def diff(m1, m0, col):
    """difference of means m1 - m0 with month-clustered SE (stacked regression on an indicator)"""
    x = q.loc[m1 | m0, col].to_numpy()
    z = m1[m1 | m0].to_numpy().astype(float)
    cl = q.loc[m1 | m0, "month"].to_numpy()
    X = np.column_stack([np.ones_like(z), z])
    b = np.linalg.lstsq(X, x, rcond=None)[0]
    e = x - X @ b
    XtXi = np.linalg.inv(X.T @ X)
    meat = np.zeros((2, 2))
    for c in np.unique(cl):
        m = cl == c
        u = X[m].T @ e[m]
        meat += np.outer(u, u)
    V = XtXi @ meat @ XtXi
    return b[1], np.sqrt(V[1, 1])


hi = q.rsi_m2 > 50
gd = q.good_last == True
known = q.good_last.notna()
for col in ("v20", "v5"):
    print(f"\n-- {col} (hedged, net 0.19)")
    for nm, m in [("all quiet winners", pd.Series(True, index=q.index)), ("RSI>50", hi), ("RSI<=50", ~hi),
                  ("last GOOD", gd), ("last GOOD & RSI>50", gd & hi), ("RSI>60", q.rsi_m2 > 60),
                  ("RSI>70", q.rsi_m2 > 70)]:
        mn, se = cm(q.loc[m, col], q.month[m])
        print(f"   {nm:22s} n {int(m.sum()):5d} mean {mn:+.2f} (se {se:.2f})")
    d, se = diff(hi, ~hi, col)
    print(f"   RSI>50 minus RSI<=50: {d:+.2f} (se {se:.2f}, t {d / se:.2f})")
    d, se = diff(gd & hi & known, known & ~(gd & hi), col)
    print(f"   GOOD&RSI>50 minus other quiet winners (FA known): {d:+.2f} (se {se:.2f}, t {d / se:.2f})")

# results days: RSI split among ALL in_fo results and among winners (from analysis_rows)
print("\nresults days (H20 hedged net):")
for nm, m in [("all results RSI>50", a.rsi_cut > 50), ("all results RSI<=50", a.rsi_cut <= 50),
              ("non-winners RSI>50", (a.XN <= 4) & (a.rsi_cut > 50)), ("non-winners RSI<=50", (a.XN <= 4) & (a.rsi_cut <= 50)),
              ("winners RSI>50", (a.XN > 4) & (a.rsi_cut > 50)), ("winners RSI<=50", (a.XN > 4) & (a.rsi_cut <= 50))]:
    print(f"   {nm:22s} n {int(m.sum()):5d} mean {a.loc[m, 'v20'].mean():+.2f}")
