"""Pre-registered pattern tests on the 15-quarter results panel.

In-sample = first 9 quarters (Q3 FY23 - Q3 FY25), out-of-sample = last 6 (Q4 FY25 - Q1 FY27).
Returns are excess over Nifty 50 (sum of daily excess returns), measured close to close.
python3 tests.py panel.csv DATA/report/events.json OUT_PREFIX
"""
import json, math, sys
import numpy as np
import pandas as pd

PANEL, EVENTS, OUT = sys.argv[1:4]
p = pd.read_csv(PANEL)
e = pd.DataFrame(json.load(open(EVENTS)))
d = p.merge(e, on=["symbol", "quarter", "results_date", "reaction_day"], how="left", suffixes=("", "_e"))
IS_Q, OOS_Q = range(0, 9), range(9, 15)
COST = 0.0015          # one round trip in a stock future (brokerage, STT, exchange fees, slippage)


def win(a, b):
    cols = [f"x{k}" for k in range(a, b + 1)]
    return d[cols].sum(axis=1, min_count=len(cols))


d["pre5"] = win(-5, -1)            # 5 sessions up to the last close before the numbers
d["pre1"] = win(-1, -1)
d["pre5_lag"] = win(-6, -2)        # signal: run-up before the last pre-results day
d["react"] = d["x0"]
d["post1"] = win(1, 1)
d["post5"] = win(1, 5)
d["post20"] = win(1, 20)
d["post20_lag"] = win(2, 20)       # enter one session after the reaction
d["base5"] = (win(-10, -6) + win(16, 20)) / 2      # normal 5-session excess for the same stocks / dates
d["abs_react"] = d["react"].abs()
d["oc_ex"] = d["oc"] - d["nifty_oc"]
news_gap = d["timing"].isin(["After close", "Before open", "Non-trading day"])

# ---- history features (strictly earlier quarters of the same stock)
d = d.sort_values(["symbol", "qn"]).reset_index(drop=True)
g = d.groupby("symbol")
d["hist_react"] = g["react"].transform(lambda s: s.shift(1).expanding(4).mean())
d["hist_absmove"] = g["abs_move"].transform(lambda s: s.shift(1).expanding(4).mean())
d["im_vs_hist"] = d["implied_move"] / d["hist_absmove"]
d["hist_post5"] = g["post5"].transform(lambda s: s.shift(1).expanding(4).mean())

# ---- peer read-through: same industry, same quarter, reacted on an earlier session
d["peer_early_react"] = np.nan
for (ind, q), grp in d.groupby(["industry", "quarter"]):
    if not isinstance(ind, str) or not ind:
        continue
    for i, r in grp.iterrows():
        early = grp[(grp["R"] < r["R"]) & grp["react"].notna()]
        if len(early):
            d.at[i, "peer_early_react"] = early["react"].mean()

# season order: where the stock's reaction falls in its quarter's season (0 = first, 1 = last)
d["season_pos"] = d.groupby("quarter")["R"].rank(pct=True)
d["combo_react_profit"] = d.groupby("quarter")["react"].rank(pct=True) + d.groupby("quarter")["pat_yoy"].rank(pct=True)
d["clv_signed"] = d["clv"] - 0.5


def per_quarter(signal, outcome, mask=None):
    rows = []
    sub = d if mask is None else d[mask]
    for q, grp in sub.groupby("qn"):
        x = grp[[signal, outcome]].dropna()
        if len(x) < 15:
            continue
        ic = x[signal].rank().corr(x[outcome].rank())
        lo, hi = x[signal].quantile(1 / 3), x[signal].quantile(2 / 3)
        spread = x[x[signal] >= hi][outcome].mean() - x[x[signal] <= lo][outcome].mean()
        rows.append((q, len(x), ic, spread))
    return pd.DataFrame(rows, columns=["qn", "n", "ic", "spread"])


def tstat(s):
    s = pd.Series(s).dropna()
    return s.mean() / s.std(ddof=1) * math.sqrt(len(s)) if len(s) > 2 and s.std(ddof=1) > 0 else float("nan")


def rank_test(name, signal, outcome, desc, mask=None, trade_legs=2):
    pq = per_quarter(signal, outcome, mask)
    out = {"test": name, "what": desc, "kind": "rank", "n": int(pq["n"].sum())}
    for lab, qs in (("is", IS_Q), ("oos", OOS_Q), ("all", range(15))):
        x = pq[pq["qn"].isin(qs)]
        out[f"{lab}_ic"] = x["ic"].mean()
        out[f"{lab}_ic_t"] = tstat(x["ic"])
        out[f"{lab}_spread"] = x["spread"].mean()
        out[f"{lab}_spread_t"] = tstat(x["spread"])
        out[f"{lab}_pos"] = (np.sign(x["spread"]) == np.sign(pq["spread"].mean())).mean()
    out["all_spread_after_cost"] = out["all_spread"] - trade_legs * COST * np.sign(out["all_spread"])
    out["oos_spread_after_cost"] = out["oos_spread"] - trade_legs * COST * np.sign(out["is_spread"])
    return out


def mean_test(name, col, desc, mask=None, base=None, cost=COST):
    sub = d if mask is None else d[mask]
    y = sub[col] - (sub[base] if base else 0)
    pq = pd.DataFrame({"qn": sub["qn"], "y": y}).dropna().groupby("qn")["y"].mean()
    out = {"test": name, "what": desc, "kind": "mean", "n": int(y.notna().sum())}
    for lab, qs in (("is", IS_Q), ("oos", OOS_Q), ("all", range(15))):
        x = pq[pq.index.isin(qs)]
        out[f"{lab}_mean"] = x.mean()
        out[f"{lab}_t"] = tstat(x)
        out[f"{lab}_pos"] = (x > 0).mean() if pq.mean() > 0 else (x < 0).mean()
    out["all_after_cost"] = out["all_mean"] - cost * np.sign(out["all_mean"])
    out["oos_after_cost"] = out["oos_mean"] - cost * np.sign(out["is_mean"])
    return out


tests = [
    # --- before the numbers (signal and trade both before results; no event risk)
    mean_test("H1", "pre5", "Stocks drift up in the 5 sessions before results (excess over normal 5-session excess)", base="base5"),
    mean_test("H1b", "pre5", "Same, raw excess vs Nifty (no baseline)"),
    mean_test("H2", "pre1", "Last session before results (Day-1 for after-close, else day before result day)"),
    # --- predicting the reaction (signal known at the last close before the numbers)
    rank_test("H3", "r1m", "react", "1-month momentum -> reaction-day excess"),
    rank_test("H4", "r3m", "react", "3-month momentum -> reaction-day excess"),
    rank_test("H5", "pre5", "react", "Run-up in the last 5 sessions -> reaction-day excess"),
    rank_test("H6", "hist_react", "react", "Stock's average past reaction (4+ earlier quarters) -> reaction"),
    rank_test("H7", "peer_early_react", "react", "Average reaction of same-industry peers that reported earlier this season -> reaction"),
    rank_test("H8", "pe_vs_peers", "react", "P/E vs peers -> reaction"),
    rank_test("H9", "season_pos", "react", "Reporting early vs late in the season -> reaction"),
    rank_test("H10", "im_vs_hist", "abs_react", "Option-implied move vs stock's past moves -> size of reaction", trade_legs=0),
    # --- after the numbers (signal known at the reaction-day close)
    rank_test("H11", "react", "post1", "Reaction -> next session (follow-through)"),
    rank_test("H12", "react", "post5", "Reaction -> next 5 sessions (post-results drift)"),
    rank_test("H13", "react", "post20", "Reaction -> next 20 sessions (post-results drift)"),
    rank_test("H14", "react", "post20_lag", "Reaction -> sessions 2-20 (enter one day late)"),
    rank_test("H15", "pat_yoy", "post20", "Profit growth YoY -> next 20 sessions"),
    rank_test("H16", "sales_yoy", "post20", "Sales growth YoY -> next 20 sessions"),
    rank_test("H17", "combo_react_profit", "post20", "Reaction + profit growth (both strong / both weak) -> next 20 sessions"),
    rank_test("H18", "clv_signed", "post5", "Where the stock closed in its reaction-day range -> next 5 sessions"),
    rank_test("H19", "gap", "oc_ex", "Opening gap on the numbers -> open-to-close (fade or follow)", mask=news_gap & (d["gap"].abs() > 0.02)),
    rank_test("H20", "hist_post5", "post5", "Stock's past post-results drift -> this drift"),
    # --- options across the numbers
    mean_test("H21", "short_straddle", "Sell ATM straddle at the last close before results, buy back at the reaction close (return on premium, after costs)", cost=0),
    rank_test("H22", "im_vs_hist", "short_straddle", "Short straddle when options price a bigger move than the stock's history", trade_legs=0),
]
res = pd.DataFrame(tests)
pd.set_option("display.width", 250, "display.max_columns", 40, "display.max_colwidth", 60)
res.to_csv(f"{OUT}_results.csv", index=False)
d.to_csv(f"{OUT}_panel_features.csv", index=False)
show = res.copy()
for c in show.columns:
    if show[c].dtype.kind == "f":
        show[c] = show[c].round(4)
print(show.drop(columns=["what"]).to_string())
