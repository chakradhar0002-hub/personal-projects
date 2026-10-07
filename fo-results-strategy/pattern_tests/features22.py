"""Pre-results features for every results event (22 quarters), all known at the cutoff = 2 sessions before the result
session (the user's performance cutoff). Outcome: the three-day window (Day-1 + Result day + Day+1), i.e. buy at the
cutoff close, sell at the Day+1 close.

    python3 features22.py DATA OUT.csv
"""
import csv, json, math, statistics, sys
from datetime import timedelta
from pathlib import Path

RB = Path(__file__).resolve().parents[1] / "report_builder"
DATA, OUT = sys.argv[1], sys.argv[2]
sys.argv = [sys.argv[0], DATA]
__file__ = str(RB / "analyze_events.py")
exec(open(RB / "analyze_events.py").read().split("# ---------------------------------------------------------------- results date and time")[0])

ev = json.load(open(f"{DATA}/report/events.json"))
QORDER = [q for _, q, _ in QUARTERS]
DIVS = defaultdict(list)
for sym, ex in px.execute("SELECT symbol, ex_date FROM div"):
    DIVS[sym].append(ex)
FIRST_DAY = {sym: days[0] for sym, days in STOCK_DAYS.items()}

# adjusted price index per stock (chained close / previous close, corporate-action safe)
LEVEL = {}
for sym, days in STOCK_DAYS.items():
    lv, x = {}, 1.0
    for day in days:
        r = daily_ret(sym, day)
        x *= 1 + r if r is not None else 1
        lv[day] = x
    LEVEL[sym] = lv


def level_at(sym, i):
    """Index level at session i (last traded day on or before it)."""
    days = STOCK_DAYS.get(sym)
    if not days or i < 0:
        return None
    j = bisect_right(days, SESSIONS[i]) - 1
    return LEVEL[sym][days[j]] if j >= 0 else None


def ret(sym, i0, i1):
    if i0 < 0 or sym not in FIRST_DAY or FIRST_DAY[sym] > SESSIONS[i0]:
        return None
    a, b = level_at(sym, i0), level_at(sym, i1)
    return b / a - 1 if a and b else None


def years_back(c, years):
    day = d(SESSIONS[c])
    try:
        day = day.replace(year=day.year - years)
    except ValueError:
        day = day.replace(year=day.year - years, day=28)
    return bisect_right(SESSIONS, day.isoformat()) - 1


def window_rets(sym, c, n):
    out = []
    for k in range(c - n + 1, c + 1):
        if k > 0:
            r = daily_ret(sym, SESSIONS[k])
            if r is not None:
                out.append(r)
    return out


def vol_avg(sym, c, n):
    vs = [stock[sym][SESSIONS[k]][5] for k in range(c - n + 1, c + 1) if k >= 0 and SESSIONS[k] in stock[sym] and stock[sym][SESSIONS[k]][5]]
    return statistics.mean(vs) if vs else None


def idx_close(name, i):
    return index_close(name, SESSIONS[i]) if 0 <= i < len(SESSIONS) else None


by_key = {(r["symbol"], r["quarter"]): r for r in ev}
rows = []
for r in ev:
    if r["result_day"] not in SPOS or r.get("three_day") is None:
        continue
    sym, q = r["symbol"], r["quarter"]
    qn = QORDER.index(q)
    rs_i = SPOS[r["result_day"]]
    c = rs_i - 2
    cut = SESSIONS[c]
    sec = r["sector_index"]
    f = {"symbol": sym, "quarter": q, "qn": qn, "results_date": r["results_date"], "cutoff": cut, "industry": r["industry"],
         "fin_type": r.get("fin_type"), "timing": r["timing"], "three_day": r["three_day"], "excess_nifty": r.get("excess_nifty"),
         "in_fo": bool(r.get("opt_expiry"))}
    # user's +3% take-profit: stop after Day-1 if it is up > 3%, after the Result day if the two days add to > 3%
    d1, d2, d3 = r["ret_dm1"], r["ret_rd"], r["ret_dp1"]
    f["tp3"] = d1 if d1 > 0.03 else (d1 + d2 if d1 + d2 > 0.03 else d1 + d2 + d3)
    # momentum and trend
    for lab, n in (("r1w", 5), ("r1m", 21), ("r3m", 63), ("r6m", 126), ("r1y", 250)):
        f[lab] = ret(sym, c - n, c)
    f["r3y"] = ret(sym, years_back(c, 3), c)
    f["r5y"] = ret(sym, years_back(c, 5), c)
    lv = [level_at(sym, k) for k in range(c - 249, c + 1)]
    lv = [x for x in lv if x]
    now = level_at(sym, c)
    if now and len(lv) > 200:
        f["from_52w_high"] = now / max(lv) - 1
        f["from_52w_low"] = now / min(lv) - 1
        f["vs_ma50"] = now / statistics.mean(lv[-50:]) - 1
        f["vs_ma200"] = now / statistics.mean(lv[-200:]) - 1
    w60 = window_rets(sym, c, 60)
    f["vol60"] = statistics.stdev(w60) * math.sqrt(252) if len(w60) > 40 else None
    v5, v60 = vol_avg(sym, c, 5), vol_avg(sym, c, 60)
    f["volume_5d_vs_60d"] = v5 / v60 if v5 and v60 else None
    # relative strength
    for lab, n in (("1w", 5), ("1m", 21), ("3m", 63)):
        s_ret = index_ret(sec, c - n, c)
        n_ret = index_ret("Nifty 50", c - n, c)
        f[f"sector_{lab}"] = s_ret
        f[f"vs_sector_{lab}"] = f[f"r{lab}"] - s_ret if f[f"r{lab}"] is not None and s_ret is not None else None
        f[f"vs_nifty_{lab}"] = f[f"r{lab}"] - n_ret if f[f"r{lab}"] is not None and n_ret is not None else None
        f[f"nifty_{lab}"] = n_ret
    vix = idx_close("India VIX", c)
    f["india_vix"] = vix
    # past results reactions of this stock
    past = [by_key.get((sym, QORDER[qn - k])) for k in range(1, qn + 1)]
    past3 = [p["three_day"] for p in past if p and p.get("three_day") is not None]
    f["prev1_3d"] = past[0]["three_day"] if past and past[0] and past[0].get("three_day") is not None else None
    f["prev2_sum"] = (past[0]["three_day"] + past[1]["three_day"]) if len(past) > 1 and all(p and p.get("three_day") is not None for p in past[:2]) else None
    f["past_avg_3d"] = statistics.mean(past3) if len(past3) >= 3 else None
    f["past_pct_up"] = sum(x > 0 for x in past3) / len(past3) if len(past3) >= 3 else None
    f["prev1_next20"] = past[0].get("next20") if past and past[0] else None
    # fundamentals known before the numbers (previous quarter's filing and valuation at the cutoff)
    p1 = fin_q(sym, qshift(r["quarter_end"], 1))
    p5 = fin_q(sym, qshift(r["quarter_end"], 5))
    pats = [fin_q(sym, qshift(r["quarter_end"], k)) for k in (4, 3, 2, 1)]
    pats = [p["pat"] if p else None for p in pats]
    sales = [fin_q(sym, qshift(r["quarter_end"], k)) for k in (4, 3, 2, 1)]
    sales = [p["sales"] if p else None for p in sales]
    f["prev_pat_yoy"] = growth(p1["pat"], p5["pat"]) if p1 and p5 else None
    f["prev_sales_yoy"] = growth(p1["sales"], p5["sales"]) if p1 and p5 else None
    f["profit_rising_4q"] = int(all(x is not None for x in pats) and all(a < b for a, b in zip(pats, pats[1:])))
    f["sales_rising_4q"] = int(all(x is not None for x in sales) and all(a < b for a, b in zip(sales, sales[1:])))
    f["prev_net_margin"] = p1["pat"] / p1["sales"] if p1 and p1.get("pat") is not None and p1.get("sales") else None
    for k in ("pe", "pb", "roe", "debt_equity", "pe_vs_peers"):
        f[k] = r.get(k)
    f["log_mcap"] = math.log(r["mcap"]) if r.get("mcap") and r["mcap"] > 0 else None
    # dividends
    exs = [ex for ex in DIVS.get(sym, []) if ex <= cut]
    f["days_since_dividend"] = (d(cut) - d(max(exs))).days if exs else 9999
    # options 5 sessions before the last pre-results close (known at the cutoff)
    f["iv_t5"] = r.get("iv_t5")
    f["iv_vs_realised"] = r["iv_t5"] / f["vol60"] if r.get("iv_t5") and f.get("vol60") else None
    # calendar
    f["days_after_quarter_end"] = (d(r["results_date"]) - d(r["quarter_end"])).days
    f["after_close"] = int(r["timing"] == "After close")
    rows.append(f)

# peer read-through: same-industry stocks whose Day+1 closed on or before this cutoff, this season
by_iq = defaultdict(list)
for f, r in zip(rows, [by_key[(x["symbol"], x["quarter"])] for x in rows]):
    by_iq[(f["industry"], f["quarter"])].append((r["day_p1"], f["three_day"]))
for f in rows:
    early = [t for dp1, t in by_iq.get((f["industry"], f["quarter"]), []) if dp1 <= f["cutoff"]]
    f["peers_reported_3d"] = statistics.mean(early) if early else None
    f["peers_reported_n"] = len(early)
# season-wide mood so far: average three-day of all stocks reported before this cutoff
season = defaultdict(list)
for f in rows:
    season[f["quarter"]].append((by_key[(f["symbol"], f["quarter"])]["day_p1"], f["three_day"]))
for f in rows:
    early = [t for dp1, t in season[f["quarter"]] if dp1 <= f["cutoff"]]
    f["season_so_far_3d"] = statistics.mean(early) if len(early) >= 5 else None

cols = list(dict.fromkeys(k for f in rows for k in f))
with open(OUT, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)
print("rows", len(rows), "quarters", sorted({f['qn'] for f in rows}), "features", len(cols))
