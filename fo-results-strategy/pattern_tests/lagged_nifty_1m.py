"""Quarter-by-quarter check of the rule "the stock lagged Nifty by more than 15% over the month before results".

Signal at the cutoff close (2 sessions before the result session): the stock's 21-session return minus the Nifty 50
21-session return < -15%. Buy at the cutoff close; exit at the Day+1 close (3-day) or with the take-profit rule (Day-1
close if Day-1 > +3%, else Result-day close if Day-1 + Result day > +3%, else Day+1 close). Returns are sums of daily
returns, as in the rest of the project. Built from the data pack (sector_lab_data.py) and cross-checked against
features22.py's columns.

    python3 lagged_nifty_1m.py PACK_DIR features22.csv OUT_DIR
"""
import sys
import numpy as np
import pandas as pd

PACK, FEAT, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
COST = 0.0017
THRESHOLDS = (-0.10, -0.12, -0.15, -0.20)
MAIN = -0.15

ev = pd.read_csv(f"{PACK}/events.csv")
R = pd.read_csv(f"{PACK}/returns.csv", index_col=0)
nifty = pd.read_csv(f"{PACK}/index_close.csv", index_col=0)["Nifty 50"].to_numpy()
ret = R.to_numpy()
col = {s: j for j, s in enumerate(R.columns)}
first = {s: int(np.argmax(~np.isnan(ret[:, j]))) for s, j in col.items()}

rows = []
for e in ev.itertuples():
    j, c = col.get(e.symbol), e.i_cut
    if j is None or pd.isna(e.three_day) or c < 21 or first[e.symbol] > c - 21:
        continue
    stock_1m = np.nanprod(1 + ret[c - 20:c + 1, j]) - 1
    d1, d2, d3 = (np.nan_to_num(ret[i, j]) for i in (e.i_m1, e.i_rd, e.i_p1))
    rows.append({"symbol": e.symbol, "company": e.company, "quarter": e.quarter, "qn": e.qn, "period": e.period,
                 "cutoff": e.cutoff, "results_date": e.results_date, "in_fo": e.in_fo, "industry": e.industry,
                 "stock_1m": stock_1m, "nifty_1m": nifty[c] / nifty[c - 21] - 1,
                 "vs_nifty_1m": stock_1m - (nifty[c] / nifty[c - 21] - 1),
                 "day_m1": d1, "result_day": d2, "day_p1": d3, "three_day": d1 + d2 + d3,
                 "take_profit": d1 if d1 > 0.03 else (d1 + d2 if d1 + d2 > 0.03 else d1 + d2 + d3)})
d = pd.DataFrame(rows)

# cross-check against the feature file built by features22.py
f = pd.read_csv(FEAT)[["symbol", "quarter", "vs_nifty_1m", "three_day", "tp3"]]
m = d.merge(f, on=["symbol", "quarter"], suffixes=("", "_f"))
for a, b in (("vs_nifty_1m", "vs_nifty_1m_f"), ("three_day", "three_day_f"), ("take_profit", "tp3")):
    ok = m[[a, b]].dropna()
    print(f"check {a}: {len(ok)} rows, max difference {np.abs(ok[a] - ok[b]).max():.2e}")

QUARTERS = d.drop_duplicates("qn").sort_values("qn")[["qn", "quarter", "period"]]


def per_quarter(x, exit_col):
    g = x.groupby("qn")[exit_col]
    t = QUARTERS.set_index("qn").join(pd.DataFrame({"trades": g.size(), "up": g.apply(lambda s: int((s > 0).sum())),
                                                    "avg": g.mean(), "best": g.max(), "worst": g.min()}))
    t["trades"] = t.trades.fillna(0).astype(int)
    t["up"] = t.up.fillna(0).astype(int)
    return t


def summary(x, exit_col, label):
    t = per_quarter(x, exit_col)
    q = t.avg.dropna()
    p = x[exit_col]
    return {"rule": label, "exit": exit_col, "trades": len(p), "up_pct": 100 * (p > 0).mean(), "avg_pct": 100 * p.mean(),
            "avg_after_cost_pct": 100 * (p.mean() - COST), "median_pct": 100 * p.median(), "worst_trade_pct": 100 * p.min(),
            "best_trade_pct": 100 * p.max(), "quarters_with_trades": len(q), "quarters_positive": int((q > 0).sum()),
            "quarters_at_2pct": int((q >= 0.02).sum()), "quarters_without_trades": int(t.avg.isna().sum()),
            "first14_avg_pct": 100 * p[x.qn < 14].mean(), "last8_avg_pct": 100 * p[x.qn >= 14].mean(),
            "avg_without_best5_pct": 100 * p.sort_values().iloc[:-5].mean() if len(p) > 5 else np.nan}


S = []
for universe, x in (("F&O at the time", d[d.in_fo == True]), ("all results", d)):
    for th in THRESHOLDS:
        for ex in ("three_day", "take_profit"):
            S.append({"universe": universe, "threshold_pct": 100 * th, **summary(x[x.vs_nifty_1m < th], ex, f"lag > {-100 * th:.0f}%")})
    for ex in ("three_day", "take_profit"):
        S.append({"universe": universe, "threshold_pct": None, **summary(x, ex, "every result (baseline)")})
S = pd.DataFrame(S)
S.to_csv(f"{OUT}/summary.csv", index=False)

fo = d[d.in_fo == True]
pick = fo[fo.vs_nifty_1m < MAIN].sort_values(["qn", "cutoff", "symbol"])
pick.to_csv(f"{OUT}/trades.csv", index=False)
base = per_quarter(fo, "three_day")[["avg"]].rename(columns={"avg": "all_fo_avg"})
tq = per_quarter(pick, "three_day").join(per_quarter(pick, "take_profit")[["up", "avg"]], rsuffix="_tp").join(base)
tq["stocks"] = pick.groupby("qn").apply(lambda g: ", ".join(f"{s} {100 * v:+.1f}" for s, v in zip(g.symbol, g.three_day)))
tq.to_csv(f"{OUT}/per_quarter.csv")
pd.set_option("display.width", 250, "display.max_columns", 30, "display.max_colwidth", 120)
print(S.round(2).to_string())
print(tq.round(4).to_string())
