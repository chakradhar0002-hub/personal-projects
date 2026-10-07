"""Search for a pre-results rule whose picks average >= 2% in the three-day window in every quarter.

Protocol (fixed before looking):
- Rules are 1 or 2 conditions "feature >= t" / "feature <= t", t = deciles of the feature in the training quarters.
- A quarter passes if the rule picks >= MIN_PICKS stocks and their average three-day return is >= TARGET.
- Rules are ranked on the TRAINING quarters (the first 14: Q4 FY21 - Q1 FY25) only; the HOLDOUT quarters
  (the last 8: Q2 FY25 - Q1 FY27) are reported for the top rules but never used to choose.
- Luck check: the same search on three-day returns shuffled within each quarter (no real link to the features).
  If shuffled data finds rules about as good, the real "best rule" is luck.

    python3 search22.py features22.csv OUT_DIR [N_SHUFFLES] [MIN_PICKS] [--no-trade-ok]

--no-trade-ok: a quarter with fewer than MIN_PICKS picks is "no trade" (neither pass nor fail); rules must trade in at
least half the training quarters and are ranked by passes minus failures.
"""
import csv, json, sys
import numpy as np
import pandas as pd

NO_TRADE_OK = "--no-trade-ok" in sys.argv
args = [a for a in sys.argv[1:] if not a.startswith("--")]
FEAT, OUT = args[0], args[1]
N_SHUFFLES = int(args[2]) if len(args) > 2 else 20
MIN_PICKS = int(args[3]) if len(args) > 3 else 3
TARGET, TRAIN_Q, TOP = 0.02, 14, 30
NOT_FEATURES = {"symbol", "quarter", "qn", "results_date", "cutoff", "industry", "fin_type", "timing", "three_day",
                "excess_nifty", "in_fo", "after_close"}       # results time is often not known in advance

d = pd.read_csv(FEAT)
d = d[d["three_day"].notna()].reset_index(drop=True)
feats = [c for c in d.columns if c not in NOT_FEATURES and d[c].dtype.kind in "fi" and d[c].notna().mean() > 0.5]
nq = int(d["qn"].max()) + 1
train = d["qn"] < TRAIN_Q
Q = np.zeros((len(d), nq), dtype=np.float32)
Q[np.arange(len(d)), d["qn"].values] = 1

# condition masks
conds, masks = [], []
for f in feats:
    x = d[f].values.astype(float)
    qs = np.nanquantile(x[train.values], np.linspace(0.1, 0.9, 9))
    for t in np.unique(qs):
        for op in (">=", "<="):
            m = (x >= t) if op == ">=" else (x <= t)
            m &= ~np.isnan(x)
            if 0.02 < m.mean() < 0.98:
                conds.append((f, op, float(t)))
                masks.append(m)
M = np.array(masks, dtype=np.float32)          # conditions x events
print("features", len(feats), "conditions", len(conds), "events", len(d), "quarters", nq, flush=True)


def evaluate(y):
    """Best single and pair rules for outcome vector y. Returns DataFrame of top rules with per-quarter stats."""
    Y = Q * y[:, None]
    tq = slice(0, TRAIN_Q)
    best = []

    def score(cnt, sm):
        mean = np.divide(sm, cnt, out=np.full_like(sm, np.nan), where=cnt > 0)
        traded = cnt >= MIN_PICKS
        ok = traded & (mean >= TARGET)
        if NO_TRADE_OK:
            fails = (traded & ~ok)[:, tq].sum(axis=1)
            n_traded = traded[:, tq].sum(axis=1)
            tr_pass = np.where(n_traded >= TRAIN_Q / 2, ok[:, tq].sum(axis=1) - fails, -99)
            worst = np.where(traded[:, tq], mean[:, tq], 9).min(axis=1)
        else:
            tr_pass = ok[:, tq].sum(axis=1)
            worst = np.where(traded[:, tq], mean[:, tq], -1).min(axis=1)
        return mean, ok, tr_pass, worst

    # singles
    cnt, sm = M @ Q, M @ Y
    mean, ok, tr_pass, worst = score(cnt, sm)
    for i in range(len(conds)):
        best.append((tr_pass[i], worst[i], (i,)))
    # pairs (i < j)
    for i in range(len(conds)):
        P = M[i + 1:] * M[i]
        cnt, sm = P @ Q, P @ Y
        mean, ok, tr_pass, worst = score(cnt, sm)
        keep = np.argsort(-(tr_pass * 10 + worst))[:50]
        for k in keep:
            best.append((tr_pass[k], worst[k], (i, i + 1 + k)))
    best.sort(key=lambda b: (-b[0], -b[1]))
    rows = []
    for tp, w, idx in best[:TOP]:
        m = np.prod([M[i] for i in idx], axis=0).astype(bool)
        cnt, sm = m @ Q, (m * y) @ Q
        mean = np.divide(sm, cnt, out=np.full_like(sm, np.nan, dtype=float), where=cnt > 0)
        traded = cnt >= MIN_PICKS
        ok = traded & (mean >= TARGET)
        rows.append({"rule": " AND ".join(f"{conds[i][0]} {conds[i][1]} {conds[i][2]:.4g}" for i in idx),
                     "train_score": int(tp), "train_quarters_pass": int(ok[:TRAIN_Q].sum()),
                     "train_quarters_traded": int(traded[:TRAIN_Q].sum()), "train_worst_quarter": float(w),
                     "holdout_quarters_pass": int(ok[TRAIN_Q:].sum()), "holdout_quarters_traded": int(traded[TRAIN_Q:].sum()),
                     "holdout_quarters": nq - TRAIN_Q,
                     "picks_total": int(cnt.sum()), "picks_per_quarter_min": int(cnt.min()),
                     "train_avg": float(sm[:TRAIN_Q].sum() / max(cnt[:TRAIN_Q].sum(), 1)),
                     "holdout_avg": float(sm[TRAIN_Q:].sum() / max(cnt[TRAIN_Q:].sum(), 1)),
                     "per_quarter_avg": [None if np.isnan(v) else round(float(v), 4) for v in mean],
                     "per_quarter_picks": [int(v) for v in cnt]})
    return pd.DataFrame(rows)


y = d["three_day"].values.astype(np.float32)
real = evaluate(y)
TAG = f"min{MIN_PICKS}" + ("_notrade" if NO_TRADE_OK else "")
real.to_csv(f"{OUT}/search_top_rules_{TAG}.csv", index=False)
base = d.groupby("qn")["three_day"].mean()
print("all stocks: quarters with average >= 2%:", int((base >= TARGET).sum()), "of", nq,
      "| per quarter:", [round(v * 100, 2) for v in base.values], flush=True)
pd.set_option("display.width", 250, "display.max_colwidth", 90)
print(real.drop(columns=["per_quarter_avg", "per_quarter_picks"]).head(15).to_string(), flush=True)

# luck check: shuffle three-day returns within each quarter, search again
rng = np.random.default_rng(0)
null = []
for s in range(N_SHUFFLES):
    ys = y.copy()
    for q in range(nq):
        idx = np.where(d["qn"].values == q)[0]
        ys[idx] = rng.permutation(ys[idx])
    r = evaluate(ys).iloc[0]
    null.append({"shuffle": s, "best_train_pass": int(r["train_score"]), "its_holdout_pass": int(r["holdout_quarters_pass"]),
                 "its_train_avg": r["train_avg"], "its_holdout_avg": r["holdout_avg"], "rule": r["rule"]})
    print("shuffle", s, null[-1], flush=True)
null = pd.DataFrame(null)
null.to_csv(f"{OUT}/search_shuffled_best_{TAG}.csv", index=False)
top = real.iloc[0]
summary = {"settings": {"min_picks": MIN_PICKS, "no_trade_ok": NO_TRADE_OK, "target": TARGET, "train_quarters": TRAIN_Q},
           "best_rule": top["rule"], "train_score": int(top["train_score"]), "train_pass": int(top["train_quarters_pass"]),
           "train_traded": int(top["train_quarters_traded"]), "holdout_pass": int(top["holdout_quarters_pass"]),
           "holdout_traded": int(top["holdout_quarters_traded"]),
           "train_avg": top["train_avg"], "holdout_avg": top["holdout_avg"],
           "shuffled_best_train_pass_median": float(null["best_train_pass"].median()),
           "shuffled_best_train_pass_max": int(null["best_train_pass"].max()),
           "share_of_shuffles_at_least_as_good": float((null["best_train_pass"] >= top["train_score"]).mean()),
           "shuffled_holdout_pass_median": float(null["its_holdout_pass"].median())}
json.dump(summary, open(f"{OUT}/search_summary_{TAG}.json", "w"), indent=1)
print(json.dumps(summary, indent=1))
