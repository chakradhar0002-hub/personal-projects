"""Quarter-by-quarter check of "lagged Nifty by more than 10% over the month AND above-average volume" before results.

Signal at the cutoff close (2 sessions before the result session), stocks in F&O at the time:
  - lag: the stock's 21-session return minus the Nifty 50 21-session return < -10%
  - volume: average traded volume of the last 5 sessions / average of the last 60 sessions (up to the cutoff) >= 1.0
Buy at the cutoff close; exit at the Day+1 close (3-day) or with the take-profit rule. Volume comes straight from the
NSE price table (as features22.py does); results with a bonus or split inside the 60 sessions are flagged, since
unadjusted volume jumps after them. Cross-checked against features22.py's volume_5d_vs_60d.

    python3 lag10_volume.py PACK_DIR nse_prices.db features22.csv OUT_DIR
"""
import sqlite3
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

PACK, DB, FEAT, OUT = sys.argv[1:5]
COST = 0.0017
VARIANTS = [("lag > 10%, volume >= 1.0x (main)", 0.10, 1.0), ("lag > 10%, volume < 1.0x (quiet)", 0.10, None),
            ("lag > 10%, volume >= 1.5x", 0.10, 1.5), ("lag > 15%, volume >= 1.0x", 0.15, 1.0),
            ("lag > 12%, volume >= 1.0x", 0.12, 1.0), ("lag > 8%, volume >= 1.0x", 0.08, 1.0),
            ("lag > 10%, volume >= 0.8x", 0.10, 0.8), ("lag > 10%, volume >= 1.2x", 0.10, 1.2)]

ev = pd.read_csv(f"{PACK}/events.csv")
sessions = pd.read_csv(f"{PACK}/sessions.csv").day.tolist()
R = pd.read_csv(f"{PACK}/returns.csv", index_col=0)
nifty = pd.read_csv(f"{PACK}/index_close.csv", index_col=0)["Nifty 50"].to_numpy()
ret, col = R.to_numpy(), {s: j for j, s in enumerate(R.columns)}
first = {s: int(np.argmax(~np.isnan(ret[:, j]))) for s, j in col.items()}
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
vol = defaultdict(dict)
for day, sym, v in con.execute("SELECT day, symbol, volume FROM px"):
    vol[sym][day] = v
ca_days = defaultdict(list)
for sym, ex, kind in con.execute("SELECT symbol, ex_date, kind FROM ca WHERE kind IN ('bonus', 'split')"):
    ca_days[sym].append(ex)


def avg_volume(sym, c, n):
    vs = [vol[sym][sessions[k]] for k in range(c - n + 1, c + 1) if k >= 0 and vol[sym].get(sessions[k])]
    return np.mean(vs) if vs else np.nan


rows = []
for e in ev.itertuples():
    j, c = col.get(e.symbol), e.i_cut
    if j is None or pd.isna(e.three_day) or c < 60 or first[e.symbol] > c - 21:
        continue
    n1m = nifty[c] / nifty[c - 21] - 1
    d1, d2, d3 = (np.nan_to_num(ret[i, j]) for i in (e.i_m1, e.i_rd, e.i_p1))
    rows.append({"symbol": e.symbol, "quarter": e.quarter, "qn": e.qn, "period": e.period, "cutoff": e.cutoff,
                 "in_fo": e.in_fo, "industry": e.industry, "vs_nifty_1m": np.nanprod(1 + ret[c - 20:c + 1, j]) - 1 - n1m,
                 "volume_ratio": avg_volume(e.symbol, c, 5) / avg_volume(e.symbol, c, 60),
                 "split_in_window": any(sessions[c - 59] <= x <= sessions[c] for x in ca_days[e.symbol]),
                 "three_day": d1 + d2 + d3, "take_profit": d1 if d1 > 0.03 else (d1 + d2 if d1 + d2 > 0.03 else d1 + d2 + d3)})
d = pd.DataFrame(rows)

f = pd.read_csv(FEAT)[["symbol", "quarter", "volume_5d_vs_60d", "vs_nifty_1m"]]
m = d.merge(f, on=["symbol", "quarter"], suffixes=("", "_f")).dropna(subset=["volume_ratio", "volume_5d_vs_60d"])
print(f"check volume ratio: {len(m)} rows, max difference {np.abs(m.volume_ratio - m.volume_5d_vs_60d).max():.2e}; "
      f"check lag: max difference {np.abs(m.vs_nifty_1m - m.vs_nifty_1m_f).max():.2e}")

fo = d[d.in_fo == True]
QUARTERS = d.drop_duplicates("qn").sort_values("qn").set_index("qn")[["quarter", "period"]]
all_fo = fo.groupby("qn").three_day.mean().rename("all_fo_avg")


def pick(lag, vmin):
    x = fo[fo.vs_nifty_1m < -lag]
    return x[x.volume_ratio >= vmin] if vmin is not None else x[x.volume_ratio < 1.0]


S = []
for name, lag, vmin in VARIANTS:
    x = pick(lag, vmin)
    for ex in ("three_day", "take_profit"):
        q = x.groupby("qn")[ex].mean()
        p = x[ex]
        S.append({"rule": name, "exit": ex, "trades": len(x), "up_pct": 100 * (p > 0).mean(), "avg_pct": 100 * p.mean(),
                  "avg_after_cost_pct": 100 * (p.mean() - COST), "median_pct": 100 * p.median(),
                  "worst_pct": 100 * p.min(), "best_pct": 100 * p.max(), "quarters_with_trades": len(q),
                  "quarters_positive": int((q > 0).sum()), "quarters_at_2pct": int((q >= 0.02).sum()),
                  "first14_avg_pct": 100 * p[x.qn < 14].mean(), "last8_avg_pct": 100 * p[x.qn >= 14].mean(),
                  "without_best5_pct": 100 * p.sort_values().iloc[:-5].mean(), "split_in_window": int(x.split_in_window.sum())})
S = pd.DataFrame(S)
S.to_csv(f"{OUT}/summary.csv", index=False)

main = pick(0.10, 1.0).sort_values(["qn", "cutoff", "symbol"])
main.to_csv(f"{OUT}/trades.csv", index=False)
g3, gt = main.groupby("qn").three_day, main.groupby("qn").take_profit
quiet = pick(0.10, None).groupby("qn").three_day
tq = QUARTERS.join(pd.DataFrame({"trades": g3.size(), "up": g3.apply(lambda s: int((s > 0).sum())), "avg": g3.mean(),
                                 "avg_tp": gt.mean(), "worst": g3.min(), "best": g3.max(),
                                 "quiet_trades": quiet.size(), "quiet_avg": quiet.mean()})).join(all_fo)
tq[["trades", "up", "quiet_trades"]] = tq[["trades", "up", "quiet_trades"]].fillna(0).astype(int)
tq["stocks"] = main.groupby("qn").apply(lambda g: ", ".join(f"{s} {100 * v:+.1f}" for s, v in zip(g.symbol, g.three_day)))
tq.to_csv(f"{OUT}/per_quarter.csv")
pd.set_option("display.width", 250, "display.max_columns", 30, "display.max_colwidth", 140)
print(S.round(2).to_string())
print(tq.round(4).to_string())
by_stock = main.groupby("symbol").three_day.agg(["size", "mean"]).sort_values("size", ascending=False)
print("most frequent stocks:", by_stock.head(8).round(4).to_dict("index"))
