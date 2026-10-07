"""Test the user's two pre-results screens (Condition A / Condition B) on 15 quarters of F&O results.

All measured at the performance cutoff = 2 sessions before the result session (as in the user's file); the outcome
is the three-day results window (Day-1 + Result day + Day+1), i.e. buy at the cutoff close, sell at the Day+1 close.

  Rule                                   Condition A          Condition B
  Stock 1M > sector 1M                   required             required
  Stock 3M > sector 3M                   required             -
  Return order                           1M < 1Y < 3Y < 5Y    1M < 1Y < 5Y
  Previous two three-day sums (total)    > 0                  -
  Previous four quarterly net profits    -                    strictly increasing
  No dividend ex-date in the last        365 days             180 days

Sector = the NSE sector index matched to the stock's industry (BSE indices are not reachable from the build machine).
Returns are total (not annualised), as in the user's file. Optional extra filter from that file: P/B above peer median.

    python3 screen_test.py DATA OUT_DIR
"""
import csv, json, math, statistics, sys
from datetime import date, timedelta
from pathlib import Path

RB = Path(__file__).resolve().parents[1] / "report_builder"
DATA, OUT = sys.argv[1], sys.argv[2]
sys.argv = [sys.argv[0], DATA]
__file__ = str(RB / "analyze_events.py")
exec(open(RB / "analyze_events.py").read().split("# ---------------------------------------------------------------- results date and time")[0])

COST = 0.0017
ev = json.load(open(f"{DATA}/report/events.json"))
QORDER = [q for _, q, _ in QUARTERS]
DIVS = defaultdict(list)
for sym, ex in px.execute("SELECT symbol, ex_date FROM div"):
    DIVS[sym].append(ex)
FIRST_DAY = {sym: days[0] for sym, days in STOCK_DAYS.items()}


def long_ret(sym, years, cut_i):
    """Total return from the last session on or before (cutoff - N calendar years) to the cutoff; None if not listed then."""
    cut_day = SESSIONS[cut_i]
    start = d(cut_day)
    try:
        start = start.replace(year=start.year - years)
    except ValueError:                       # 29 Feb
        start = start.replace(year=start.year - years, day=28)
    i0 = bisect_right(SESSIONS, start.isoformat()) - 1
    if i0 < 0 or sym not in FIRST_DAY or FIRST_DAY[sym] > SESSIONS[i0]:
        return None
    g, n = 1.0, 0
    for k in range(i0 + 1, cut_i + 1):        # close / previous close chains across holidays and suspensions
        r = daily_ret(sym, SESSIONS[k])
        if r is not None:
            g *= 1 + r
            n += 1
    return g - 1 if n else None


def no_dividend(sym, cut_day, days):
    lo = (d(cut_day) - timedelta(days=days)).isoformat()
    return not any(lo < ex <= cut_day for ex in DIVS.get(sym, []))


by_key = {(r["symbol"], r["quarter"]): r for r in ev}
rows = []
for r in ev:
    if r["result_day"] not in SPOS:
        continue
    sym, q = r["symbol"], r["quarter"]
    qn = QORDER.index(q)
    rs_i = SPOS[r["result_day"]]
    c = rs_i - 2
    cut_day = SESSIONS[c]
    sec = r["sector_index"]
    r1m, r3m, r1y = stock_ret(sym, c - 21, c), stock_ret(sym, c - 63, c), stock_ret(sym, c - 250, c)
    r3y, r5y = long_ret(sym, 3, c), long_ret(sym, 5, c)
    s1m, s3m = index_ret(sec, c - 21, c), index_ret(sec, c - 63, c)
    prev = [by_key.get((sym, QORDER[qn - k])) if qn - k >= 0 else None for k in (1, 2)]
    prev_sum = (prev[0]["three_day"] + prev[1]["three_day"]) if all(p and p.get("three_day") is not None for p in prev) else None
    pats = [fin_q(sym, qshift(r["quarter_end"], k)) for k in (4, 3, 2, 1)]
    pats = [p["pat"] if p else None for p in pats]
    rising = all(x is not None for x in pats) and all(a < b for a, b in zip(pats, pats[1:]))
    ok = lambda *xs: all(x is not None for x in xs)
    c_1m = ok(r1m, s1m) and r1m > s1m
    c_3m = ok(r3m, s3m) and r3m > s3m
    order_a = ok(r1m, r1y, r3y, r5y) and r1m < r1y < r3y < r5y
    order_b = ok(r1m, r1y, r5y) and r1m < r1y < r5y
    cond_a = c_1m and c_3m and order_a and prev_sum is not None and prev_sum > 0 and no_dividend(sym, cut_day, 365)
    cond_b = c_1m and order_b and rising and no_dividend(sym, cut_day, 180)
    rows.append({"symbol": sym, "quarter": q, "qn": qn, "results_date": r["results_date"], "cutoff": cut_day,
                 "industry": r["industry"], "sector_index": sec, "r1m": r1m, "r3m": r3m, "r1y": r1y, "r3y": r3y, "r5y": r5y,
                 "sector_1m": s1m, "sector_3m": s3m, "prev_two_sums": prev_sum, "pat_q4": pats[0], "pat_q1": pats[3],
                 "profit_rising": rising, "no_div_365": no_dividend(sym, cut_day, 365), "no_div_180": no_dividend(sym, cut_day, 180),
                 "c_1m": c_1m, "c_3m": c_3m, "order_a": order_a, "order_b": order_b, "cond_a": cond_a, "cond_b": cond_b,
                 "pb": r.get("pb"), "three_day": r.get("three_day"), "excess_nifty": r.get("excess_nifty"),
                 "in_fo": bool(r.get("opt_expiry"))})

# P/B above the median of other stocks in the same industry and quarter (the extra filter in the user's file)
groups = defaultdict(list)
for x in rows:
    if x["pb"]:
        groups[(x["industry"], x["quarter"])].append(x)
for x in rows:
    peers = [p["pb"] for p in groups.get((x["industry"], x["quarter"]), []) if p is not x]
    x["pb_above_peers"] = bool(x["pb"] and len(peers) >= 2 and x["pb"] > statistics.median(peers))

with open(f"{OUT}/screen_events.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)


def tstat(xs):
    xs = [x for x in xs if x is not None]
    return statistics.mean(xs) / statistics.stdev(xs) * math.sqrt(len(xs)) if len(xs) > 2 and statistics.stdev(xs) > 0 else float("nan")


def summary(label, pick, first_q=0):
    base = [x for x in rows if x["three_day"] is not None and x["qn"] >= first_q]
    m = [x for x in base if pick(x)]
    if not m:
        return {"screen": label, "matches": 0}
    qavg = defaultdict(list)
    for x in base:
        qavg[x["qn"]].append(x["three_day"])
    qavg = {k: statistics.mean(v) for k, v in qavg.items()}
    per_q = defaultdict(list)
    for x in m:
        per_q[x["qn"]].append(x["three_day"] - qavg[x["qn"]])
    diffs = {k: statistics.mean(v) for k, v in per_q.items()}
    net = [x["three_day"] - COST for x in m]
    return {"screen": label, "matches": len(m), "stocks": len({x["symbol"] for x in m}),
            "avg_three_day": statistics.mean(x["three_day"] for x in m), "median": statistics.median(x["three_day"] for x in m),
            "pct_up": sum(x["three_day"] > 0 for x in m) / len(m),
            "avg_vs_nifty": statistics.mean(x["excess_nifty"] for x in m),
            "all_stocks_avg": statistics.mean(x["three_day"] for x in base), "all_stocks_pct_up": sum(x["three_day"] > 0 for x in base) / len(base),
            "vs_same_quarter_avg": statistics.mean(x["three_day"] - qavg[x["qn"]] for x in m),
            "t_by_quarter": tstat(list(diffs.values())), "quarters_with_matches": len(diffs),
            "quarters_better": f"{sum(v > 0 for v in diffs.values())}/{len(diffs)}",
            "first_9q_vs_avg": statistics.mean([v for k, v in diffs.items() if k < 9]) if any(k < 9 for k in diffs) else None,
            "last_6q_vs_avg": statistics.mean([v for k, v in diffs.items() if k >= 9]) if any(k >= 9 for k in diffs) else None,
            "avg_after_cost": statistics.mean(net), "win_after_cost": sum(v > 0 for v in net) / len(net)}


screens = [
    ("Condition A", lambda x: x["cond_a"], 2),
    ("Condition B", lambda x: x["cond_b"], 0),
    ("A or B", lambda x: x["cond_a"] or x["cond_b"], 2),
    ("A or B, P/B above peers", lambda x: (x["cond_a"] or x["cond_b"]) and x["pb_above_peers"], 2),
    ("A or B, F&O at the time", lambda x: (x["cond_a"] or x["cond_b"]) and x["in_fo"], 2),
    ("1M beats sector only", lambda x: x["c_1m"], 0),
    ("3M beats sector only", lambda x: x["c_3m"], 0),
    ("Return order A only", lambda x: x["order_a"], 0),
    ("Return order B only", lambda x: x["order_b"], 0),
    ("Previous two sums > 0 only", lambda x: x["prev_two_sums"] is not None and x["prev_two_sums"] > 0, 2),
    ("Profits rising 4 quarters only", lambda x: x["profit_rising"], 0),
    ("No dividend 365 days only", lambda x: x["no_div_365"], 0),
    ("No dividend 180 days only", lambda x: x["no_div_180"], 0),
]
res = [summary(*s) for s in screens]
with open(f"{OUT}/screen_summary.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(res[0]))
    w.writeheader()
    w.writerows(res)
for x in res:
    print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in x.items()})
print("matches:")
for x in sorted((x for x in rows if x["cond_a"] or x["cond_b"]), key=lambda x: x["results_date"]):
    print(x["quarter"], x["symbol"], x["results_date"], "A" if x["cond_a"] else "-", "B" if x["cond_b"] else "-",
          "PB+" if x["pb_above_peers"] else "", None if x["three_day"] is None else round(x["three_day"] * 100, 2))
