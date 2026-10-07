"""Walk-forward score: for each quarter, fit a ridge regression of the three-day return on the pre-results features
using ONLY earlier quarters, score this quarter's stocks, and buy every stock whose score is above a threshold also
set from earlier quarters (top X% of past scores) - a rule you could follow on the day, without knowing the stocks
that report later. Features are scaled by their distribution in earlier quarters only. Every quarter's result is
out-of-sample. Luck check: rerun with three-day returns shuffled within quarters.

    python3 walkforward22.py features22.csv OUT_DIR [N_SHUFFLES]
"""
import json, sys
import numpy as np
import pandas as pd

FEAT, OUT = sys.argv[1], sys.argv[2]
N_SHUFFLES = int(sys.argv[3]) if len(sys.argv) > 3 else 50
TARGET, FIRST_TEST, ALPHA = 0.02, int(sys.argv[4]) if len(sys.argv) > 4 else 6, 50.0
NOT_FEATURES = {"symbol", "quarter", "qn", "results_date", "cutoff", "industry", "fin_type", "timing", "three_day",
                "excess_nifty", "in_fo", "after_close"}       # results time is often not known in advance

d = pd.read_csv(FEAT)
d = d[d["three_day"].notna()].reset_index(drop=True)
feats = [c for c in d.columns if c not in NOT_FEATURES and d[c].dtype.kind in "fi" and d[c].notna().mean() > 0.5]
RAW = d[feats].astype(float).values
qn = d["qn"].values
nq = qn.max() + 1
KS = (2.5, 5, 10, 20)          # buy if the score is in the top K% of scores seen in earlier quarters


def scaled(tr, rows):
    """Percentile of each feature against the training rows' distribution (missing -> 0.5), centred."""
    out = np.empty((rows.sum(), RAW.shape[1]))
    for j in range(RAW.shape[1]):
        ref = np.sort(RAW[tr, j][~np.isnan(RAW[tr, j])])
        x = RAW[rows, j]
        p = np.searchsorted(ref, x, side="right") / max(len(ref), 1)
        p[np.isnan(x)] = 0.5
        out[:, j] = p
    return out - 0.5


def run(y):
    out = {k: [] for k in KS}
    for q in range(FIRST_TEST, nq):
        tr, te = qn < q, qn == q
        A = scaled(tr, tr)
        w = np.linalg.solve(A.T @ A + ALPHA * np.eye(A.shape[1]), A.T @ (y[tr] - y[tr].mean()))
        s_tr, s_te = A @ w, scaled(tr, te) @ w
        for k in KS:
            pick = s_te >= np.quantile(s_tr, 1 - k / 100)
            out[k].append((float(y[te][pick].mean()) if pick.sum() else float("nan"), int(pick.sum())))
    return out


y = d["three_day"].values.astype(float)
real = run(y)
base = [float(y[qn == q].mean()) for q in range(FIRST_TEST, nq)]
rows = []
for k in KS:
    v = np.array([m for m, _ in real[k]])
    n = np.array([c for _, c in real[k]])
    ok = (n >= 3) & (np.nan_to_num(v, nan=-1) >= TARGET)
    rows.append({"top_pct": k, "test_quarters": len(v), "quarters_at_2pct_with_3_picks": int(ok.sum()),
                 "avg_per_quarter": float(np.nanmean(v)), "trades": int(n.sum()), "quarters_without_picks": int((n == 0).sum()),
                 "worst_quarter": float(np.nanmin(v)), "quarters_beat_all_stocks": int((np.nan_to_num(v, nan=-1) > np.array(base)).sum()),
                 "per_quarter": [None if np.isnan(x) else round(x, 4) for x in v], "picks": [int(c) for c in n]})
res = pd.DataFrame(rows)
res.to_csv(f"{OUT}/walkforward_real.csv", index=False)
print("all stocks per test quarter:", [round(b * 100, 2) for b in base])
print(res.drop(columns=["per_quarter"]).to_string())

rng = np.random.default_rng(1)
null = {k: [] for k in KS}
for s in range(N_SHUFFLES):
    ys = y.copy()
    for q in range(nq):
        idx = np.where(qn == q)[0]
        ys[idx] = rng.permutation(ys[idx])
    r = run(ys)
    for k in KS:
        v = np.array([m for m, _ in r[k]])
        n = np.array([c for _, c in r[k]])
        null[k].append((int(((n >= 3) & (np.nan_to_num(v, nan=-1) >= TARGET)).sum()), float(np.nanmean(v))))
summary = {}
for k in KS:
    real_hits, real_avg = rows[KS.index(k)]["quarters_at_2pct_with_3_picks"], rows[KS.index(k)]["avg_per_quarter"]
    nh = np.array([h for h, _ in null[k]])
    na = np.array([a for _, a in null[k]])
    summary[f"top{k}pct"] = {"real_quarters_at_2pct": real_hits, "real_avg": round(real_avg, 4),
                          "shuffled_quarters_at_2pct_median": float(np.median(nh)), "shuffled_avg_median": round(float(np.median(na)), 4),
                          "p_value_avg": float((na >= real_avg).mean()), "p_value_hits": float((nh >= real_hits).mean())}
json.dump(summary, open(f"{OUT}/walkforward_summary.json", "w"), indent=1)
print(json.dumps(summary, indent=1))
