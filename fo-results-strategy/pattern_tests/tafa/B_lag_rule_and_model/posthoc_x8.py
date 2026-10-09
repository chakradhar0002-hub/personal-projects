"""POST-HOC (not pre-registered, not counted for promotion): a closer look at the best-looking Part 1 pair,
X8 good fundamentals AND oversold count >= 3, which failed the adjustment (Holm 0.81, maxT 0.66).
(1) the volume bands 1.0-1.3x vs >= 1.3x (the check that rejected 'oversold >= 3' alone earlier);
(2) luck within the 85 trades (random same-size-per-quarter picks from the rule's own trades) and vs all in_fo results;
(3) per-quarter trades."""
import os  # LAB_ROOT: scratch folder with ta/, fa/, report/, sector_lab/data; REPO_ROOT: this repo
import numpy as np, pandas as pd
HERE = os.environ.get('LAB_ROOT', 'lab') + "/tafa/B_lag_rule_and_model"
T = pd.read_csv(f"{HERE}/part1_trades_S85_flags.csv")
rng = np.random.default_rng(7)
x = T["X8_goodfund&oversold3"]
hi = T.vol_ratio_5_60 >= 1.3
for band, m in (("vol 1.0-1.3x", ~hi), ("vol >= 1.3x", hi)):
    for lab, s in (("X8 true", x == 1), ("X8 false", x == 0), ("unknown", x == -1)):
        d = T[m & s]
        print(f"{band:13s} {lab:9s} n {len(d):3d} mean {d.three_day.mean():6.2f} tp {d.tp3.mean():6.2f}")
def luck(sel, pool_df, n=20000):
    obs = pool_df.three_day[sel].mean(); tot = np.zeros(n); k_all = 0
    for q, g in pool_df.groupby("qn"):
        k = int(sel[g.index].sum())
        if k == 0: continue
        y = g.three_day.to_numpy()
        pick = np.argsort(rng.random((n, len(y))), axis=1)[:, :k]
        tot += y[pick].sum(1); k_all += k
    r = tot / k_all
    return obs, r.mean(), (np.sum(r >= obs) + 1) / (n + 1)
o, rm, p = luck((x == 1).to_numpy(), T)
print(f"X8 true within the 85: mean {o:.2f}, random same-size-per-quarter picks from the 85 {rm:.2f}, p {p:.4f}")
R = pd.read_csv(f"{HERE}/part2_rows.csv")
R = R.merge(T[["symbol", "quarter", "X8_goodfund&oversold3"]], on=["symbol", "quarter"], how="left")
sel = (R["X8_goodfund&oversold3"] == 1).to_numpy()
o, rm, p = luck(sel, R)
print(f"X8 true vs all in_fo results: mean {o:.2f}, random picks {rm:.2f}, p {p:.4f}")
d = T[x == 1].sort_values(["qn", "symbol"])
print(d[["symbol", "quarter", "qn", "lag_pct", "vol_ratio_5_60", "three_day", "tp3"]].round(2).to_string(index=False))
