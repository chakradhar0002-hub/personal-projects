"""Results-winner drift: after a stock beats Nifty by more than a threshold on its reaction day, buy at that close and
hold 20 sessions. Excess returns over Nifty 50 (a Nifty-futures hedge), after costs. Only events where the stock had
F&O options at the time (so stocks are not counted before they joined F&O).

    python3 drift.py OUT_panel_features.csv OUT_DIR
"""
import math, sys
import numpy as np
import pandas as pd

FEAT, OUT = sys.argv[1], sys.argv[2]
d = pd.read_csv(FEAT)
COST = 0.0015 + 0.0002          # stock-future round trip + Nifty-future hedge
THRESHOLD, HOLD = 0.04, 20      # fixed rule; 3% and 5% shown as a sensitivity check


def tstat(s):
    s = pd.Series(s).dropna()
    return s.mean() / s.std(ddof=1) * math.sqrt(len(s)) if len(s) > 2 else float("nan")


def hold_ret(frame, first, last):
    cols = [f"x{k}" for k in range(first, last + 1)]
    return frame[cols].sum(axis=1, min_count=len(cols))


fo = d[d["opt_expiry"].notna()].copy()
fo["q_avg20"] = fo.groupby("qn")["post20"].transform("mean")        # the average F&O stock that quarter

rows = []
for thr in (0.03, 0.04, 0.05):
    for side, name in ((1, "long winners"), (-1, "short losers")):
        x = fo[(fo["react"] * side) > thr].dropna(subset=["post20"])
        ret = side * x["post20"] - COST
        vs_avg = side * (x["post20"] - x["q_avg20"])
        pq = ret.groupby(x["qn"]).mean()
        pq_avg = vs_avg.groupby(x["qn"]).mean()
        rows.append({"rule": f"{name}, reaction beyond {thr:.0%}", "trades": len(x), "avg_after_cost": ret.mean(),
                     "median": ret.median(), "win_rate": (ret > 0).mean(), "in_sample_avg": pq[pq.index < 9].mean(),
                     "out_of_sample_avg": pq[pq.index >= 9].mean(), "quarters_positive": f"{int((pq > 0).sum())}/{len(pq)}",
                     "t_by_quarter": tstat(pq), "vs_average_stock": vs_avg.mean(), "vs_average_stock_t": tstat(pq_avg)})
grid = pd.DataFrame(rows)

x = fo[fo["react"] > THRESHOLD].dropna(subset=["post20"]).copy()
x["ret"] = x["post20"] - COST
x["ret_enter_next_day"] = hold_ret(x, 2, HOLD) - COST
by_q = x.groupby(["qn", "quarter"]).agg(trades=("ret", "size"), avg=("ret", "mean"), median=("ret", "median"),
                                         win_rate=("ret", lambda s: (s > 0).mean())).reset_index()
path = {h: hold_ret(x, 1, h).mean() for h in (1, 2, 3, 5, 10, 15, 20)}
# positions open at once: a trade is open from the session after its reaction day to 20 sessions later
opens = pd.Series(0, index=range(int(x["R"].min()), int(x["R"].max()) + HOLD + 1))
for r in x["R"].astype(int):
    opens.loc[r + 1:r + HOLD] += 1

grid.to_csv(f"{OUT}/drift_rules.csv", index=False)
by_q.to_csv(f"{OUT}/drift_by_quarter.csv", index=False)
x[["symbol", "quarter", "results_date", "reaction_day", "timing", "industry", "react", "post20", "ret", "ret_enter_next_day"]] \
    .sort_values("reaction_day").to_csv(f"{OUT}/drift_trades.csv", index=False)
pd.set_option("display.width", 250, "display.max_columns", 30)
print(grid.round(4).to_string())
print(by_q.round(4).to_string())
print(f"rule: trades {len(x)}, avg {x['ret'].mean():.4f}, median {x['ret'].median():.4f}, sd {x['ret'].std():.4f}, "
      f"p10 {x['ret'].quantile(.1):.4f}, p90 {x['ret'].quantile(.9):.4f}, worst {x['ret'].min():.4f}, best {x['ret'].max():.4f}, "
      f"win {(x['ret'] > 0).mean():.3f}; enter next day {x['ret_enter_next_day'].mean():.4f}")
print("avg excess after N sessions:", {h: round(v * 100, 2) for h, v in path.items()})
print("open positions: max", int(opens.max()), "median while any open", int(opens[opens > 0].median()))
