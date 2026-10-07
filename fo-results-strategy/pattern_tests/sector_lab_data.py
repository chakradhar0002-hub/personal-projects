"""Export a flat data pack for the sector-strategy study, so every test reads the same, corporate-action-safe inputs.

    python3 sector_lab_data.py DATA features22.csv OUT_DIR

Writes to OUT_DIR:
  sessions.csv     trading sessions (Nifty 50 days), with their position i
  returns.csv      adjusted close-to-close daily return per session (rows) and symbol (columns); blank = no trade
  intraday.csv     close / open - 1 per session and symbol (gap = (1 + daily) / (1 + intraday) - 1)
  index_close.csv  close of every NSE index per session (blank = not published that day)
  events.csv       one row per result: dates as sessions, sector index, industry, peer group, three-day window, F&O flag
"""
import csv, json, sys
from pathlib import Path

RB = Path(__file__).resolve().parents[1] / "report_builder"
DATA, FEAT, OUT = sys.argv[1], sys.argv[2], Path(sys.argv[3])
sys.argv = [sys.argv[0], DATA]
__file__ = str(RB / "analyze_events.py")
exec(open(RB / "analyze_events.py").read().split("# ---------------------------------------------------------------- options")[0])
OUT.mkdir(parents=True, exist_ok=True)

syms = sorted(stock)
with open(OUT / "sessions.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["i", "day"])
    w.writerows(enumerate(SESSIONS))
with open(OUT / "returns.csv", "w", newline="") as f, open(OUT / "intraday.csv", "w", newline="") as g:
    wr, wi = csv.writer(f), csv.writer(g)
    wr.writerow(["day"] + syms)
    wi.writerow(["day"] + syms)
    for day in SESSIONS:
        rr, ii = [day], [day]
        for s in syms:
            r = daily_ret(s, day)
            rr.append("" if r is None else f"{r:.6g}")
            row = stock[s].get(day)
            ii.append(f"{row[3] / row[0] - 1:.6g}" if row and row[0] and row[3] else "")
        wr.writerow(rr)
        wi.writerow(ii)
names = sorted(n for n in indexes if not any(k in n for k in ("G-Sec", "GSEC", "Bond", "1D Rate", "Inverse", "Leverage")))
with open(OUT / "index_close.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["day"] + names)
    for day in SESSIONS:
        w.writerow([day] + [(indexes[n].get(day) or ("",))[0] or "" for n in names])

REAL_ESTATE = {"DLF", "GODREJPROP", "LODHA", "OBEROIRLTY", "PHOENIXLTD", "PRESTIGE"}
GROUPS = {"Banks": {"Banks"}, "NBFCs": {"Finance", "Finance - Housing", "Financial Institution"}, "Insurers": {"Insurance"},
          "Metals": {"Steel And Steel Products", "Aluminium", "Metals", "Mining"},
          "FMCG": {"Personal Care", "Food And Food Processing", "Cigarettes", "Diversified", "Brew/Distilleries"},
          "IT services": {"Computers - Software"}, "Pharma": {"Pharmaceuticals"},
          "Consumer brands": {"Consumer Durables", "Paints", "Gems Jewellery And Watches", "Airconditioners", "Textile Products", "Retail"}}


def group_of(sym, ind):
    if sym in REAL_ESTATE:
        return "Real estate"
    return next((g for g, inds in GROUPS.items() if ind in inds), "")


feat = {(r["symbol"], r["quarter"]): r for r in csv.DictReader(open(FEAT))}
ev = json.load(open(f"{DATA}/report/events.json"))
QORDER = [q for _, q, _ in QUARTERS]
cols = ["symbol", "company", "quarter", "qn", "period", "quarter_end", "results_date", "results_time", "timing", "industry",
        "peer_group", "sector_index", "fin_type", "mcap", "cutoff", "day_m1", "result_day", "day_p1", "reaction_day",
        "i_cut", "i_m1", "i_rd", "i_p1", "i_react", "ret_dm1", "ret_rd", "ret_dp1", "three_day", "move", "gap",
        "sector_3d", "nifty_3d", "excess_nifty", "excess_sector", "in_fo", "sales_yoy", "pat_yoy", "sales_qoq", "pat_qoq",
        "pe", "next5", "next20", "next20_vs_nifty"]
with open(OUT / "events.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in ev:
        x = dict(r)
        fr = feat.get((r["symbol"], r["quarter"]), {})
        x["qn"] = QORDER.index(r["quarter"])
        x["cutoff"] = sess(SPOS[r["day_m1"]] - 1) if r.get("day_m1") in SPOS else ""
        x["in_fo"] = fr.get("in_fo", "")
        x["peer_group"] = group_of(r["symbol"], r["industry"])
        for k, day in (("i_cut", x["cutoff"]), ("i_m1", r.get("day_m1")), ("i_rd", r.get("result_day")),
                       ("i_p1", r.get("day_p1")), ("i_react", r.get("reaction_day"))):
            x[k] = SPOS.get(day, "")
        w.writerow(x)
print("symbols", len(syms), "sessions", len(SESSIONS), "indices", len(names), "events", len(ev))
