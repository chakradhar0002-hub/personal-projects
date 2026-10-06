"""Cross-check the report against a second source: daily % changes vs BSE closes, sales / net profit vs Yahoo Finance.

    python3 bse_check_compare.py DATA/report/events.json DATA/report/yahoo_bse.json OUT.csv OUT.json DATA/report/nse_prices.db

OUT.csv has every comparison; OUT.json is the summary shown on the viewer's "BSE cross-check" tab.
"""
import csv, json, sqlite3, statistics, sys

EVENTS, YB, OUT_CSV, OUT_JSON, PRICES = sys.argv[1:6]
ev = json.load(open(EVENTS))
yb = json.load(open(YB))
CR = 1e7
DAYS = (("Day -1", "day_m1", "ret_dm1"), ("Result day", "result_day", "ret_rd"), ("Day +1", "day_p1", "ret_dp1"))

# NSE session calendar (includes weekend sessions such as Budget day)
SESSIONS = [d for (d,) in sqlite3.connect(PRICES).execute("SELECT DISTINCT day FROM idx WHERE name = 'Nifty 50' ORDER BY day")]
PREV = {d: SESSIONS[i - 1] for i, d in enumerate(SESSIONS) if i}

price, skipped_missing, stocks_with_bse = [], 0, set()
for r in ev:
    b = yb.get(r["symbol"], {}).get("bse", {})
    if len(b) < 100:
        continue
    stocks_with_bse.add(r["symbol"])
    for lab, dk, rk in DAYS:
        d, nse = r[dk], r.get(rk)
        p = PREV.get(d)
        if nse is None or p is None:
            continue
        if d not in b or p not in b:          # BSE series on Yahoo lacks that session (e.g. a weekend session)
            skipped_missing += 1
            continue
        bse = b[d][0] / b[p][0] - 1
        price.append((r["symbol"], r["quarter"], lab, d, nse, bse))

fin = []
for r in ev:
    f = yb.get(r["symbol"], {}).get("fin", {}).get(r["quarter_end"])
    if not f:
        continue
    cur = f.get("currency") or "INR"
    ni = f.get("quarterlyNetIncomeCommonStockholders") or f.get("quarterlyNetIncome")
    rev = f.get("quarterlyOperatingRevenue") or f.get("quarterlyTotalRevenue")
    for item, ours, theirs in (("Net profit", r.get("pat"), ni), ("Sales", r.get("sales"), rev)):
        if ours is not None and theirs:
            fin.append((r["symbol"], r["quarter"], r.get("fin_type") or "", r.get("basis") or "", item, ours, theirs / CR, cur))

with open(OUT_CSV, "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["check", "symbol", "quarter", "item", "date", "type", "basis", "report (NSE)", "second source", "difference",
                "diff %", "second-source currency"])
    for s, q, lab, d, x, y in price:
        w.writerow(["daily % vs BSE", s, q, lab, d, "", "", round(x * 100, 3), round(y * 100, 3), round((x - y) * 100, 3), "", ""])
    for s, q, t, basis, item, x, y, cur in fin:
        w.writerow(["financials vs Yahoo", s, q, item, "", t, basis, round(x, 2), round(y, 2), round(x - y, 2),
                    round((x / y - 1) * 100, 2) if y else "", cur])


def share(xs, cond):
    return sum(1 for x in xs if cond(x)) / len(xs) if xs else None


# ---- price summary
diffs = [abs(x - y) for *_, x, y in price]
moves = [(x, y) for *_, x, y in price if abs(x) > 0.005]
price_rows = []
for lab, _, _ in DAYS:
    ds = [abs(x - y) for _, _, l, _, x, y in price if l == lab]
    price_rows.append([lab, len(ds), share(ds, lambda d: d <= 0.001), share(ds, lambda d: d <= 0.0025), share(ds, lambda d: d <= 0.005),
                       statistics.median(ds)])
price_rows.append(["All days", len(diffs), share(diffs, lambda d: d <= 0.001), share(diffs, lambda d: d <= 0.0025),
                   share(diffs, lambda d: d <= 0.005), statistics.median(diffs)])
worst = sorted(price, key=lambda p: -abs(p[4] - p[5]))[:15]

# ---- financial summary (INR only; Yahoo reports a few companies in USD)
fin_inr = [f for f in fin if f[7] == "INR"]
usd = sorted({f[0] for f in fin if f[7] != "INR"})
fin_rows = []
for item in ("Sales", "Net profit"):
    for grp, keep in (("Companies", lambda t: t == "Company"), ("Banks", lambda t: t == "Bank"),
                      ("NBFC / financial", lambda t: t == "NBFC / financial")):
        pc = [abs(x / y - 1) for s, q, t, b, i, x, y, c in fin_inr if i == item and keep(t)]
        if pc:
            fin_rows.append([item, grp, len(pc), share(pc, lambda p: p <= 0.001), share(pc, lambda p: p <= 0.01),
                             share(pc, lambda p: p <= 0.05), statistics.median(pc)])
worst_fin = sorted([f for f in fin_inr if f[2] == "Company" and f[4] == "Net profit"], key=lambda f: -abs(f[5] / f[6] - 1))[:15]

pct = lambda v: f"{v:.1%}"
co_np = next(r for r in fin_rows if r[0] == "Net profit" and r[1] == "Companies")
summary = {
    "intro": ("Is the report's data the same as BSE's? bseindia.com is blocked from the machine that built this report, so BSE "
              "closing prices were taken from Yahoo Finance's BSE tickers (.BO), and quarterly sales and net profit from Yahoo "
              "Finance. Companies file the same results XBRL on NSE and BSE, so the financial figures on BSE are the same "
              "documents the report reads from NSE; Yahoo is used as an independent check of how they were read."),
    "cards": [
        [pct(price_rows[-1][4]), f"of {len(diffs):,} daily % changes within 0.5 pt of BSE ({len(stocks_with_bse)} stocks)"],
        [f"{price_rows[-1][5] * 100:.2f} pt", "median gap between the NSE and BSE daily % change"],
        [pct(share(moves, lambda m: (m[0] > 0) == (m[1] > 0))), "same up / down direction on BSE (moves over 0.5%)"],
        [pct(co_np[4]), f"of {co_np[2]:,} company net-profit figures within 1% of Yahoo"],
    ],
    "sections": [
        {"title": "Daily % change: report (NSE) vs BSE close",
         "text": (f"Each of Day -1, Result day and Day +1 compared with BSE's close-to-close change over the same two sessions. "
                  f"{skipped_missing:,} day comparisons were skipped because the BSE series on Yahoo lacks that session (mostly the "
                  "weekend sessions: Budget days 1-Feb-2025 and 1-Feb-2026, 20-Jan-2024, 18-May-2024). 69 stocks have no BSE history "
                  "on Yahoo before Jul-2026 and are not in this check. Gaps come from the two exchanges' separate closing auctions."),
         "table": {"cols": ["Day", "Comparisons", "Within 0.1 pt", "Within 0.25 pt", "Within 0.5 pt", "Median gap (pt)"],
                   "fmts": ["t", "n0", "p1", "p1", "p1", "p2"], "sections": [], "rows": price_rows}},
        {"title": "Largest daily gaps vs BSE",
         "text": ("The biggest gaps were checked by hand and are stale prices in the BSE series on Yahoo, not the report: e.g. "
                  "JIOFIN on 15-Jan-2024 shows 255.20 on Yahoo (the previous day's BSE close repeated) while it closed at 266.75 "
                  "on NSE, and the next day both exchanges agree again (248.85 / 248.90). A stale day shows up as a pair of "
                  "opposite gaps on consecutive days."),
         "table": {"cols": ["Symbol", "Quarter", "Day", "Date", "NSE %", "BSE %", "Gap (pt)"],
                   "fmts": ["t", "t", "t", "d", "p2", "p2", "p2"], "sections": [],
                   "rows": [[s, q, l, d, x, y, x - y] for s, q, l, d, x, y in worst]}},
        {"title": "Sales and net profit: report (NSE XBRL) vs Yahoo Finance",
         "text": ("Yahoo has the last 5-6 quarters only. Sales differ by design for banks (report: interest earned) and for "
                  "companies that collect excise duty (refiners, cigarettes, liquor: the report uses revenue from operations "
                  "including excise, Yahoo nets it). Net-profit gaps are mostly exceptional or discontinued items that Yahoo leaves "
                  "out (e.g. ITC's hotel demerger gain) and banks, where the report uses the standalone bank and Yahoo the group."
                  + (f" Not compared: {', '.join(usd)} (Yahoo reports in USD)." if usd else "")),
         "table": {"cols": ["Item", "Group", "Comparisons", "Same (within 0.1%)", "Within 1%", "Within 5%", "Median gap"],
                   "fmts": ["t", "t", "n0", "p1", "p1", "p1", "p2"], "sections": [], "rows": fin_rows}},
        {"title": "Largest net-profit gaps vs Yahoo (companies, Rs crore)",
         "table": {"cols": ["Symbol", "Quarter", "Basis", "Report", "Yahoo", "Gap %"],
                   "fmts": ["t", "t", "t", "n1", "n1", "p1"], "sections": [],
                   "rows": [[s, q, b, x, y, x / y - 1] for s, q, t, b, i, x, y, c in worst_fin]}},
    ],
}
json.dump(summary, open(OUT_JSON, "w"), indent=1)
print(json.dumps(summary["cards"]))
for r in price_rows + fin_rows:
    print(r)
print("worst price:", [(s, q, l, round((x - y) * 100, 2)) for s, q, l, d, x, y in worst[:8]])
print("worst profit:", [(s, q, round(x, 1), round(y, 1)) for s, q, t, b, i, x, y, c in worst_fin[:10]])
