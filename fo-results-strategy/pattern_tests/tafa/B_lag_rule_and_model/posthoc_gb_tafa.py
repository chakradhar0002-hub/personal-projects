"""POST-HOC (not pre-registered, not counted): what drives the nearest miss of Part 2, A|TAFA|GB|top10
(182 trades, +1.35% gross; failed the AUC-vs-null test and the family-wise null). Concentration in the best trades,
median, per-quarter means, the same model's TA-only / FA-only twins, and the spread of the shuffled-label null."""
import os  # LAB_ROOT: scratch folder with ta/, fa/, report/, sector_lab/data; REPO_ROOT: this repo
import numpy as np, pandas as pd
HERE = os.environ.get('LAB_ROOT', 'lab') + "/tafa/B_lag_rule_and_model"
R = pd.read_csv(f"{HERE}/part2_rows.csv")
QN, Y = R.qn.to_numpy(), R.three_day.to_numpy()
LAG = (R.lag_pct < -10).to_numpy(); S85 = LAG & (R.vol_ratio_5_60 >= 1.0).to_numpy()
EVQ = range(8, 22)
def picks(score, k):
    pk = np.zeros(len(R), bool)
    for q in EVQ:
        past = (QN >= 6) & (QN < q) & ~np.isnan(score)
        thr = np.quantile(score[past], 1 - k)
        pk[QN == q] = score[QN == q] > thr
    return pk
for fs in ("TAFA", "TA", "FA"):
    sc = np.load(f"{HERE}/scores/A_{fs}_GB_r0.npz")["score"]
    pk = picks(sc, 0.10)
    y = np.sort(Y[pk])[::-1]
    print(f"GB {fs} top10: n {pk.sum()}, mean {Y[pk].mean():.2f}, median {np.median(Y[pk]):.2f}, "
          f"best 5 sum {y[:5].sum():.1f} of total {y.sum():.1f}, without best 5 {y[5:].mean():.2f}, "
          f"without best 10 {y[10:].mean():.2f}, without worst 5 {y[:-5].mean():.2f}, "
          f"winsorised at +-10% {np.clip(Y[pk], -10, 10).mean():.2f}; all events winsorised {np.clip(Y[QN >= 8], -10, 10).mean():.2f}")
sc = np.load(f"{HERE}/scores/A_TAFA_GB_r0.npz")["score"]
pk = picks(sc, 0.10)
d = R[pk].assign(score=sc[pk]).sort_values("three_day", ascending=False)
print("\nbest 8 and worst 5 trades:")
print(pd.concat([d.head(8), d.tail(5)])[["symbol", "quarter", "qn", "lag_pct", "vol_ratio_5_60", "three_day", "take_profit", "score"]].round(2).to_string(index=False))
g = d.groupby("qn").three_day.agg(["size", "mean", "median"])
g["all_events_mean"] = R[R.qn >= 8].groupby("qn").three_day.mean()
print("\nper quarter:\n", g.round(2).to_string())
nm = []
for r in range(1, 31):
    s0 = np.load(f"{HERE}/scores/A_TAFA_GB_r{r}.npz")["score"]
    nm.append(Y[picks(s0, 0.10)].mean())
nm = np.array(nm)
print(f"\nshuffled-label null means (30 runs): mean {nm.mean():.2f}, sd {nm.std():.2f}, max {nm.max():.2f}, "
      f"sorted top 5 {np.sort(nm)[-5:].round(2)}")
