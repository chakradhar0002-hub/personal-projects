"""Sector-appropriate valuation before results: P/B for banks, NBFCs (and as a variant metals and real estate), P/E for
FMCG, IT services, pharma and consumer brands. Is a stock that is cheap (or expensive) against its sector peers on the
same date, or against its own past, more likely to rise in the three-day results window?

Valuation is measured at the cutoff (2 sessions before the result session) for the stock AND its peers on that same
date: price that day x shares from the previous quarter's filing (adjusted for later bonus/splits) / trailing four
quarters' profit (P/E) or the latest published half-year book value (P/B). Only fundamentals published before the
quarter being reported are used. P/B exists from the Oct-Dec 2022 results on (earlier results filings have no balance
sheet).

    python3 valuation.py DATA OUT_DIR
"""
import csv, json, math, statistics, sys
from pathlib import Path

RB = Path(__file__).resolve().parents[1] / "report_builder"
DATA, OUT = sys.argv[1], sys.argv[2]
sys.argv = [sys.argv[0], DATA]
__file__ = str(RB / "analyze_events.py")
exec(open(RB / "analyze_events.py").read().split("# ---------------------------------------------------------------- results date and time")[0])

COST = 0.0017
REAL_ESTATE = {"DLF", "GODREJPROP", "LODHA", "OBEROIRLTY", "PHOENIXLTD", "PRESTIGE"}
GROUPS = {   # group -> (metric, industries)
    "Banks": ("pb", {"Banks"}),
    "NBFCs": ("pb", {"Finance", "Finance - Housing", "Financial Institution"}),
    "Insurers": ("pb", {"Insurance"}),
    "Metals": ("pb", {"Steel And Steel Products", "Aluminium", "Metals", "Mining"}),
    "Real estate": ("pb", set()),
    "FMCG": ("pe", {"Personal Care", "Food And Food Processing", "Cigarettes", "Diversified", "Brew/Distilleries"}),
    "IT services": ("pe", {"Computers - Software"}),
    "Pharma": ("pe", {"Pharmaceuticals"}),
    "Consumer brands": ("pe", {"Consumer Durables", "Paints", "Gems Jewellery And Watches", "Airconditioners",
                               "Textile Products", "Retail"}),
}
CORE = {"Banks", "NBFCs", "Insurers", "FMCG", "IT services", "Pharma", "Consumer brands"}


def group_of(sym, industry):
    if sym in REAL_ESTATE:
        return "Real estate"
    for g, (_, inds) in GROUPS.items():
        if industry in inds:
            return g
    return None


def close_on(sym, day):
    days = STOCK_DAYS.get(sym)
    if not days:
        return None
    j = bisect_right(days, day) - 1
    return stock[sym][days[j]][3] if j >= 0 and (d(day) - d(days[j])).days <= 7 else None


def valuation(sym, qend, day, metric):
    """P/E or P/B of `sym` on `day`, using fundamentals up to the quarter before `qend`."""
    prev = [fin_q(sym, qshift(qend, k)) for k in (1, 2, 3, 4)]
    shares, _ = checked_shares(sym, qshift(qend, 1))
    price = close_on(sym, day)
    if not shares or not price:
        return None
    mcap = price * shares * share_multiplier(sym, qshift(qend, 1), day) / CR
    if metric == "pe":
        if not all(p and p.get("pat") is not None for p in prev):
            return None
        ttm = sum(p["pat"] for p in prev)
        return mcap / ttm if ttm > 0 else None
    hq = next((q for q in (qshift(qend, k) for k in (1, 2, 3)) if q[5:7] in ("03", "09")), None)
    hf = fin_q(sym, hq) if hq else None
    return mcap / hf["equity"] if hf and hf.get("equity") and hf["equity"] > 0 else None


ev = json.load(open(f"{DATA}/report/events.json"))
QORDER = [q for _, q, _ in QUARTERS]
members = defaultdict(set)                     # (group, quarter) -> symbols reporting that quarter
for r in ev:
    g = group_of(r["symbol"], r["industry"])
    if g:
        members[(g, r["quarter"])].add(r["symbol"])

rows = []
for r in ev:
    g = group_of(r["symbol"], r["industry"])
    if not g or r.get("three_day") is None or r["result_day"] not in SPOS:
        continue
    metric = GROUPS[g][0]
    cut = SESSIONS[SPOS[r["result_day"]] - 2]
    v = valuation(r["symbol"], r["quarter_end"], cut, metric)
    peers = [valuation(p, r["quarter_end"], cut, metric) for p in members[(g, r["quarter"])] if p != r["symbol"]]
    peers = [x for x in peers if x]
    own = []
    qn = QORDER.index(r["quarter"])
    for k in range(1, 9):                      # the stock's own valuation at its previous 8 cutoffs
        if qn - k < 0:
            break
        pr = next((x for x in ev if x["symbol"] == r["symbol"] and x["quarter"] == QORDER[qn - k]), None)
        if pr and pr["result_day"] in SPOS:
            pv = valuation(r["symbol"], pr["quarter_end"], SESSIONS[SPOS[pr["result_day"]] - 2], metric)
            if pv:
                own.append(pv)
    d1, d2, d3 = r["ret_dm1"], r["ret_rd"], r["ret_dp1"]
    rows.append({"symbol": r["symbol"], "quarter": r["quarter"], "qn": qn, "group": g, "metric": metric, "cutoff": cut,
                 "value": v, "peer_median": statistics.median(peers) if len(peers) >= 2 else None, "peers": len(peers),
                 "vs_peers": v / statistics.median(peers) - 1 if v and len(peers) >= 2 else None,
                 "own_median_2y": statistics.median(own) if len(own) >= 4 else None,
                 "vs_own_2y": v / statistics.median(own) - 1 if v and len(own) >= 4 else None,
                 "three_day": r["three_day"], "excess_nifty": r.get("excess_nifty"),
                 "tp3": d1 if d1 > 0.03 else (d1 + d2 if d1 + d2 > 0.03 else d1 + d2 + d3)})

with open(f"{OUT}/valuation_events.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
print("events with a group:", len(rows), "| with vs-peers value:", sum(x["vs_peers"] is not None for x in rows),
      "| with vs-own value:", sum(x["vs_own_2y"] is not None for x in rows))
for g in GROUPS:
    xs = [x for x in rows if x["group"] == g]
    if xs:
        print(f"  {g:16s} {GROUPS[g][0]}  events {len(xs):4d}  value {sum(x['value'] is not None for x in xs):4d}  "
              f"vs peers {sum(x['vs_peers'] is not None for x in xs):4d}  vs own {sum(x['vs_own_2y'] is not None for x in xs):4d}")

# all-stock average per quarter (for "vs other stocks that quarter")
qavg = defaultdict(list)
for r in ev:
    if r.get("three_day") is not None:
        qavg[QORDER.index(r["quarter"])].append(r["three_day"])
qavg = {k: statistics.mean(v) for k, v in qavg.items()}


def tstat(xs):
    xs = [x for x in xs if x is not None]
    return statistics.mean(xs) / statistics.stdev(xs) * math.sqrt(len(xs)) if len(xs) > 2 and statistics.stdev(xs) > 0 else float("nan")


def summarize(label, sel, split_q):
    if not sel:
        return {"test": label, "picks": 0}
    per_q = defaultdict(list)
    for x in sel:
        per_q[x["qn"]].append(x)
    q_mean = {q: statistics.mean(x["three_day"] for x in v) for q, v in per_q.items()}
    q_tp3 = {q: statistics.mean(x["tp3"] for x in v) for q, v in per_q.items()}
    q_ex = {q: q_mean[q] - qavg[q] for q in q_mean}
    first = [v for q, v in q_ex.items() if q < split_q]
    last = [v for q, v in q_ex.items() if q >= split_q]
    return {"test": label, "picks": len(sel), "quarters_traded": len(q_mean),
            "avg_3day": statistics.mean(x["three_day"] for x in sel), "pct_up": sum(x["three_day"] > 0 for x in sel) / len(sel),
            "avg_tp3": statistics.mean(x["tp3"] for x in sel), "tp3_up": sum(x["tp3"] > 0 for x in sel) / len(sel),
            "quarters_3day_ge_2pct": sum(v >= 0.02 for v in q_mean.values()), "quarters_tp3_ge_2pct": sum(v >= 0.02 for v in q_tp3.values()),
            "vs_all_stocks_that_quarter": statistics.mean(q_ex.values()), "t_by_quarter": tstat(list(q_ex.values())),
            "quarters_beat_all": f"{sum(v > 0 for v in q_ex.values())}/{len(q_ex)}",
            "first_part_vs_all": statistics.mean(first) if first else None, "last_8q_vs_all": statistics.mean(last) if last else None,
            "avg_3day_after_cost": statistics.mean(x["three_day"] for x in sel) - COST}


tests = []
for scope, gs in (("P/B: banks + NBFCs", {"Banks", "NBFCs"}), ("P/B: banks + NBFCs + metals + real estate", {"Banks", "NBFCs", "Metals", "Real estate"}),
                  ("P/E: FMCG + IT + pharma + consumer brands", {"FMCG", "IT services", "Pharma", "Consumer brands"}),
                  ("Your full scheme (P/B financials, P/E consumer/IT/pharma)", {"Banks", "NBFCs", "FMCG", "IT services", "Pharma", "Consumer brands"})):
    base = [x for x in rows if x["group"] in gs]
    split_q = 14
    tests.append(summarize(f"{scope} | all", base, split_q))
    for col, lab in (("vs_peers", "vs sector peers"), ("vs_own_2y", "vs own last 2 years")):
        xs = [x for x in base if x[col] is not None]
        if not xs:
            continue
        lo, hi = statistics.quantiles([x[col] for x in xs], n=3)
        tests.append(summarize(f"{scope} | cheaper {lab} (below median)", [x for x in xs if x[col] < 0], split_q))
        tests.append(summarize(f"{scope} | dearer {lab} (above median)", [x for x in xs if x[col] > 0], split_q))
        tests.append(summarize(f"{scope} | cheapest third {lab}", [x for x in xs if x[col] <= lo], split_q))
        tests.append(summarize(f"{scope} | dearest third {lab}", [x for x in xs if x[col] >= hi], split_q))
for g in GROUPS:
    xs = [x for x in rows if x["group"] == g and x["vs_peers"] is not None]
    if len(xs) >= 20:
        tests.append(summarize(f"{g} ({GROUPS[g][0]}) | cheaper vs peers", [x for x in xs if x["vs_peers"] < 0], 14))
        tests.append(summarize(f"{g} ({GROUPS[g][0]}) | dearer vs peers", [x for x in xs if x["vs_peers"] > 0], 14))

# with the user's Condition A / B (from screen.py's output, if present)
scr = Path(OUT) / "screen_events.csv"
if scr.exists():
    ab = {(x["symbol"], x["quarter"]) for x in csv.DictReader(open(scr)) if x["cond_a"] == "True" or x["cond_b"] == "True"}
    sel = [x for x in rows if (x["symbol"], x["quarter"]) in ab and x["group"] in {"Banks", "NBFCs", "FMCG", "IT services", "Pharma", "Consumer brands"}]
    tests.append(summarize("Condition A or B, in your sectors | all", sel, 14))
    tests.append(summarize("Condition A or B, in your sectors | valuation above peers", [x for x in sel if x["vs_peers"] and x["vs_peers"] > 0], 14))
    tests.append(summarize("Condition A or B, in your sectors | valuation below peers", [x for x in sel if x["vs_peers"] is not None and x["vs_peers"] < 0], 14))

with open(f"{OUT}/valuation_tests.csv", "w", newline="") as fh:
    keys = list(dict.fromkeys(k for t in tests for k in t))
    w = csv.DictWriter(fh, fieldnames=keys)
    w.writeheader()
    w.writerows(tests)
for t in tests:
    if t["picks"] == 0:
        print(f"{t['test']:90s} no picks")
        continue
    print(f"{t['test']:90s} n={t['picks']:4d} 3d {t['avg_3day']*100:+5.2f}% up {t['pct_up']:.0%} tp3 {t['avg_tp3']*100:+5.2f}% "
          f"q>=2% {t['quarters_3day_ge_2pct']}/{t['quarters_traded']} vs-all {t['vs_all_stocks_that_quarter']*100:+5.2f}% "
          f"t {t['t_by_quarter']:4.1f} beat {t['quarters_beat_all']} | first {(t['first_part_vs_all'] or 0)*100:+5.2f}% last8 {(t['last_8q_vs_all'] or 0)*100:+5.2f}%")
