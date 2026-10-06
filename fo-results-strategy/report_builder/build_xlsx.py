"""Write the results report workbook from events.json: Summary / By industry / By stock (formulas), Events (data), Notes."""
import json, sys
from collections import Counter
from datetime import date
from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

SRC, OUT = sys.argv[1], sys.argv[2]
events = json.load(open(SRC))
for r in events:
    if r.get("abs_move") is not None and r.get("implied_move"):
        r["actual_vs_expected"] = r["abs_move"] / r["implied_move"]

P, N1, N0, N2, D, T = "0.0%", "#,##0.0", "#,##0", "0.00", "dd-mmm-yy", "@"
SECTIONS = [
    ("Stock & quarter", "DDEBF7", [
        ("quarter", "Quarter", T, 9), ("period", "Quarter period", T, 13), ("quarter_end", "Quarter end", D, 10),
        ("symbol", "Symbol", T, 12), ("company", "Company", T, 30), ("industry", "Industry (NSE)", T, 22),
        ("sector_index", "Sector index", T, 20), ("lot", "Lot size", N0, 8)]),
    ("Results timing", "E2EFDA", [
        ("results_date", "Results date", D, 10), ("results_time", "Results time (IST)", T, 9), ("timing", "Timing", T, 14),
        ("time_source", "Time source", T, 17), ("day_m1", "Day -1", D, 10), ("result_day", "Result day", D, 10),
        ("day_p1", "Day +1", D, 10), ("reaction_day", "Reaction day", D, 10)]),
    ("3-day window (Day -1, Result day, Day +1)", "FFF2CC", [
        ("ret_dm1", "Day -1 %", P, 8), ("ret_rd", "Result day %", P, 8), ("ret_dp1", "Day +1 %", P, 8),
        ("three_day", "Three-day sum %", P, 9), ("nifty_3d", "Nifty 50 3-day %", P, 9), ("sector_3d", "Sector 3-day %", P, 9),
        ("excess_nifty", "Excess vs Nifty %", P, 9), ("excess_sector", "Excess vs sector %", P, 9),
        ("peer_three_day", "Peer median 3-day %", P, 9), ("vs_peer_three_day", "Vs peers 3-day %", P, 9)]),
    ("Reaction day", "FCE4D6", [
        ("gap", "Gap at open %", P, 8), ("move", "Close move %", P, 8), ("abs_move", "Size of move %", P, 8),
        ("range", "High-low range %", P, 8), ("clv", "Close in range (0 low-1 high)", N2, 9), ("vol_ratio", "Volume vs 20D avg (x)", N2, 9)]),
    ("Before results (2 sessions before result day)", "EDEDED", [
        ("price_cutoff", "Price (Rs)", N1, 10), ("r1w", "1W %", P, 8), ("r1m", "1M %", P, 8), ("r3m", "3M %", P, 8),
        ("r6m", "6M %", P, 8), ("r1y", "1Y %", P, 8), ("sector_1m", "Sector 1M %", P, 8), ("vs_sector_1m", "1M vs sector %", P, 8)]),
    ("After results", "D9E1F2", [
        ("next5", "Next 5 sessions %", P, 9), ("next20", "Next 20 sessions %", P, 9), ("next20_vs_nifty", "Next 20 vs Nifty %", P, 9)]),
    ("Results: this quarter (Rs crore)", "E2EFDA", [
        ("basis", "Basis", T, 12), ("fin_type", "Type", T, 12), ("sales", "Sales / Interest earned", N0, 11),
        ("sales_yoy", "Sales YoY %", P, 8), ("sales_qoq", "Sales QoQ %", P, 8), ("ebitda", "EBITDA", N0, 10),
        ("ebitda_margin", "EBITDA margin %", P, 8), ("ebitda_margin_chg", "EBITDA margin chg YoY (pts)", P, 9),
        ("pat", "Net profit", N0, 10), ("pat_yoy", "Net profit YoY %", P, 8), ("pat_qoq", "Net profit QoQ %", P, 8),
        ("net_margin", "Net margin %", P, 8), ("eps", "EPS (Rs)", N2, 8)]),
    ("Banks only", "FFF2CC", [
        ("nii", "Net interest income", N0, 10), ("nii_yoy", "NII YoY %", P, 8), ("ppop_yoy", "Pre-provision profit YoY %", P, 9),
        ("prov_yoy", "Provisions YoY %", P, 9), ("gnpa", "Gross NPA %", "0.00%", 8), ("nnpa", "Net NPA %", "0.00%", 8), ("roa", "ROA % (quarter)", "0.00%", 8)]),
    ("Valuation & ratios (before results)", "FCE4D6", [
        ("mcap", "Market cap (Rs cr)", N0, 11), ("ttm_pat", "TTM net profit", N0, 10), ("pe", "P/E", N1, 7),
        ("pb", "P/B", N2, 7), ("roe", "ROE %", P, 7), ("debt_equity", "Debt / equity", N2, 8),
        ("sector_pe", "Sector index P/E", N1, 8), ("sector_pb", "Sector index P/B", N2, 8)]),
    ("Cash flow (latest half-year or year)", "EDEDED", [
        ("cf_period", "Cash-flow period", T, 9), ("cfo", "Operating cash flow", N0, 10), ("capex", "Capex", N0, 9),
        ("fcf", "Free cash flow", N0, 10), ("cfo_pat", "CFO / net profit (x)", N2, 9)]),
    ("Peers (same NSE industry, same quarter)", "D9E1F2", [
        ("peer_n", "Peers (n)", N0, 7), ("peer_sales_yoy", "Peer median sales YoY %", P, 9),
        ("peer_pat_yoy", "Peer median profit YoY %", P, 9), ("pat_yoy_rank", "Profit growth rank", T, 9),
        ("peer_pe", "Peer median P/E", N1, 8), ("pe_vs_peers", "P/E vs peers %", P, 9)]),
    ("Options (NSE F&O)", "E2EFDA", [
        ("opt_expiry", "Expiry used", D, 10), ("iv_t5", "IV 5 sessions before", P, 8), ("iv_pre", "IV before results", P, 8),
        ("iv_after", "IV after results", P, 8), ("iv_drop", "IV drop %", P, 8), ("implied_move", "Expected move % (straddle)", P, 9),
        ("actual_vs_expected", "Actual / expected move (x)", N2, 9), ("runup_return", "Run-up straddle return %", P, 9),
        ("runup_rule", "Run-up rule pass", T, 8)]),
    ("Notes", "EDEDED", [("notes", "Data notes", T, 40)]),
]
COLS = [c for _, _, cols in SECTIONS for c in cols]
LETTER = {key: get_column_letter(i + 1) for i, (key, *_rest) in enumerate(COLS)}
ARIAL = "Arial"
thin = Side(style="thin", color="BFBFBF")
HEADER_ROW, FIRST = 5, 6
LAST = FIRST + len(events) - 1


def font(**kw):
    return Font(name=ARIAL, size=kw.pop("size", 10), **kw)


wb = Workbook()
summary = wb.active
summary.title = "Summary"
wi, ws, wst, wn = wb.create_sheet("By industry"), wb.create_sheet("Events"), wb.create_sheet("By stock"), wb.create_sheet("Notes")
wb.move_sheet("Events", offset=1)

# ------------------------------------------------------------------ Events
ws["A1"] = "F&O stocks - results report, last 15 quarters (no conditions applied)"
ws["A1"].font = font(bold=True, size=13)
ws["A2"] = (f"{len(events)} results events, {len({r['symbol'] for r in events})} stocks. All data from NSE: results date/time "
            "(NSE filings), prices (equity bhavcopy), indices, financials (results XBRL), options (F&O bhavcopy). See Notes.")
ws["A2"].font = font(italic=True, color="595959")
col = 1
for title, color, cols in SECTIONS:
    start = col
    for key, header, fmt, width in cols:
        c = ws.cell(HEADER_ROW, col, header)
        c.font = font(bold=True)
        c.fill = PatternFill("solid", fgColor=color)
        c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        c.border = Border(bottom=thin, top=thin, left=thin, right=thin)
        ws.column_dimensions[get_column_letter(col)].width = width
        col += 1
    ws.merge_cells(start_row=4, start_column=start, end_row=4, end_column=col - 1)
    b = ws.cell(4, start, title)
    b.font = font(bold=True)
    b.fill = PatternFill("solid", fgColor=color)
    b.alignment = Alignment(horizontal="center")
ws.row_dimensions[HEADER_ROW].height = 54
events.sort(key=lambda r: (r["quarter_end"], r["results_date"], r["symbol"]))
for i, r in enumerate(events):
    row = FIRST + i
    for j, (key, header, fmt, width) in enumerate(COLS, 1):
        v = r.get(key)
        if v is None or v == "":
            continue
        if fmt == D and isinstance(v, str):
            v = date.fromisoformat(v)
        if isinstance(v, float) and (v != v or v in (float("inf"), float("-inf"))):
            continue
        c = ws.cell(row, j, v)
        c.number_format = fmt if fmt != T else "General"
        c.font = font()
ws.freeze_panes = ws.cell(FIRST, COLS.index(next(c for c in COLS if c[0] == "symbol")) + 2)
ws.auto_filter.ref = f"A{HEADER_ROW}:{get_column_letter(len(COLS))}{LAST}"
green, red = PatternFill("solid", fgColor="C6EFCE"), PatternFill("solid", fgColor="FFC7CE")
for key in ("three_day", "excess_nifty", "move", "runup_return", "pat_yoy", "sales_yoy"):
    rng = f"{LETTER[key]}{FIRST}:{LETTER[key]}{LAST}"
    ws.conditional_formatting.add(rng, CellIsRule(operator="greaterThan", formula=["0"], fill=green))
    ws.conditional_formatting.add(rng, CellIsRule(operator="lessThan", formula=["0"], fill=red))


def rng(key):
    return f"Events!${LETTER[key]}${FIRST}:${LETTER[key]}${LAST}"


# ------------------------------------------------------------------ Summary (formulas)
def write_table(sheet, title, note, key_col, keys, labels_extra, metrics, first_row=4):
    sheet["A1"] = title
    sheet["A1"].font = font(bold=True, size=13)
    sheet["A2"] = note
    sheet["A2"].font = font(italic=True, color="595959")
    headers = [h for h, _ in labels_extra] + [h for h, *_ in metrics]
    for j, h in enumerate(headers, 1):
        c = sheet.cell(first_row - 1, j, h)
        c.font = font(bold=True)
        c.fill = PatternFill("solid", fgColor="DDEBF7")
        c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
    sheet.row_dimensions[first_row - 1].height = 45
    for i, k in enumerate(keys):
        row = first_row + i
        for j, (_, getter) in enumerate(labels_extra, 1):
            c = sheet.cell(row, j, getter(k, row))
            c.font = font(bold=(k == "*"))
        for j, (h, formula, fmt) in enumerate(metrics, len(labels_extra) + 1):
            crit = '"<>"' if k == "*" else f"$A{row}"
            c = sheet.cell(row, j, formula(crit, row))
            c.number_format = fmt
            c.font = font(bold=(k == "*"))
    sheet.freeze_panes = sheet.cell(first_row, 2)


def avg(key, extra=""):
    return lambda crit, row: f'=IFERROR(AVERAGEIFS({rng(key)},{CRIT_COL},{crit}{extra}),"")'


def share(key, cond, extra=""):
    return lambda crit, row: (f'=IFERROR(COUNTIFS({CRIT_COL},{crit},{rng(key)},"{cond}"{extra})/'
                              f'COUNTIFS({CRIT_COL},{crit},{rng(key)},"<>"{extra}),"")')


def count(extra=""):
    return lambda crit, row: f"=COUNTIFS({CRIT_COL},{crit}{extra})"


def common_metrics():
    rule = f',{rng("runup_rule")},"Yes"'
    return [
        ("Results events", count(), N0),
        ("After close", count(f',{rng("timing")},"After close"'), N0),
        ("During market", count(f',{rng("timing")},"During market"'), N0),
        ("Weekend / holiday", count(f',{rng("timing")},"Non-trading day"'), N0),
        ("Avg three-day sum %", avg("three_day"), P),
        ("% three-day positive", share("three_day", ">0"), P),
        ("Avg excess vs Nifty %", avg("excess_nifty"), P),
        ("Avg size of reaction move %", avg("abs_move"), P),
        ("% sales up YoY", share("sales_yoy", ">0"), P),
        ("% profit up YoY", share("pat_yoy", ">0"), P),
        ("Avg EBITDA margin chg YoY (pts)", avg("ebitda_margin_chg"), P),
        ("Avg expected move % (options)", avg("implied_move"), P),
        ("Avg actual / expected move (x)", avg("actual_vs_expected"), N2),
        ("Avg IV drop %", avg("iv_drop"), P),
        ("Run-up trades (rule pass)", count(f'{rule},{rng("runup_return")},"<>"'), N0),
        ("Run-up avg return % (rule pass)", avg("runup_return", rule), P),
        ("Run-up win rate (rule pass)", share("runup_return", ">0", rule), P),
    ]


quarters = []
for r in events:
    if r["quarter"] not in [q for q, _ in quarters]:
        quarters.append((r["quarter"], r["period"]))
periods = dict(quarters)
CRIT_COL = rng("quarter")
write_table(summary, "Summary by quarter", "Every number is a formula over the Events sheet. 'Rule pass' = front expiry within 14 "
            "sessions of the last close before results (the playbook's run-up rule).", "quarter",
            [q for q, _ in quarters] + ["*"],
            [("Quarter", lambda k, row: "All quarters" if k == "*" else k),
             ("Period", lambda k, row: "" if k == "*" else periods[k])], common_metrics())
summary.column_dimensions["A"].width = 13
summary.column_dimensions["B"].width = 13
for j in range(3, 3 + len(common_metrics())):
    summary.column_dimensions[get_column_letter(j)].width = 11

CRIT_COL = rng("industry")
inds = [k for k, _ in Counter(r["industry"] for r in events if r["industry"]).most_common()]
write_table(wi, "By industry (NSE industry classification)", "Formulas over the Events sheet, all 15 quarters.", "industry",
            inds + ["*"], [("Industry", lambda k, row: "All industries" if k == "*" else k)], common_metrics())
wi.column_dimensions["A"].width = 32
for j in range(2, 2 + len(common_metrics())):
    wi.column_dimensions[get_column_letter(j)].width = 11

CRIT_COL = rng("symbol")
stock_metrics = [m for m in common_metrics() if m[0] not in ("During market", "Weekend / holiday")]
syms = sorted({r["symbol"] for r in events})
write_table(wst, "By stock", "Formulas over the Events sheet, all 15 quarters.", "symbol", syms,
            [("Symbol", lambda k, row: k),
             ("Company", lambda k, row: f'=INDEX({rng("company")},MATCH($A{row},{rng("symbol")},0))'),
             ("Industry", lambda k, row: f'=INDEX({rng("industry")},MATCH($A{row},{rng("symbol")},0))')], stock_metrics)
wst.column_dimensions["A"].width = 13
wst.column_dimensions["B"].width = 30
wst.column_dimensions["C"].width = 24
for j in range(4, 4 + len(stock_metrics)):
    wst.column_dimensions[get_column_letter(j)].width = 11

# ------------------------------------------------------------------ Notes
notes = [
    ("Report", "One row per F&O stock per quarter for the last 15 quarters (Oct-Dec 2022 to Apr-Jun 2026 results). No filters or "
               "conditions: every stock in NSE's current F&O list that filed results for the quarter."),
    ("Universe", "Current NSE F&O stocks (fo_mktlots.csv, Oct 2026), 213 stocks. Stocks that left F&O earlier are not included "
                 "(survivorship); stocks listed later have fewer quarters."),
    ("Results date & time", "First NSE announcement about the results (financial results, outcome of board meeting, integrated "
                            "financial filing, or a press release mentioning results) in the 7 days up to the results XBRL filing; "
                            "otherwise the XBRL filing time. 'Time source' says which."),
    ("Timing", "Before open: before 09:15. During market: 09:15-15:30. After close: after 15:30. Non-trading day: announced on a "
               "weekend or holiday."),
    ("Day -1 / Result day / Day +1", "Result day = first trading session on or after the results date (same as your file). Day -1 "
                                     "and Day +1 are the sessions before and after it."),
    ("Reaction day", "First session that trades on the numbers: the next session for after-close results, otherwise the result day."),
    ("Daily % changes", "Close / previous close - 1 from the NSE equity bhavcopy. NSE's previous close is adjusted for splits, "
                        "bonuses and other corporate actions, so the % changes are safe across them."),
    ("Three-day sum %", "Day -1 % + Result day % + Day +1 % (a sum of daily changes, as in your file; not compounded, before costs)."),
    ("Excess vs Nifty / sector", "Three-day sum minus the same sum for the Nifty 50 or the stock's sector index (NSE index closes)."),
    ("Sector index", "Nifty sector index matched to the NSE industry (e.g. Banks -> Nifty Bank, Computers - Software -> Nifty IT). "
                     "Industries without a matching index use the Nifty 500."),
    ("Before results", "Returns up to the close two sessions before the result day (1W = 5, 1M = 21, 3M = 63, 6M = 126, 1Y = 250 "
                       "sessions)."),
    ("Financials", "From each quarter's NSE results XBRL. Banks: standalone filing; other companies: consolidated (standalone if "
                   "no consolidated filing). Rs crore. Sales = revenue from operations (banks: interest earned). EBITDA = profit "
                   "before tax + finance costs + depreciation - other income. Net profit = profit attributable to owners of the "
                   "company. YoY/QoQ growth is blank when the earlier quarter was a loss (not meaningful)."),
    ("Valuation", "Market cap = price two sessions before the result day x shares (paid-up capital / face value from the previous "
                  "quarter's filing). P/E = market cap / sum of the previous four quarters' net profit (what was known before the "
                  "results). P/B, ROE and debt/equity use the latest half-year balance sheet (March or September). Sector index "
                  "P/E and P/B are NSE's published values."),
    ("Cash flow", "Companies file the cash-flow statement twice a year (with September and March results), so these columns show "
                  "the latest half-year (H1) or full-year (FY) figures up to this result. Capex = purchase of property, plant and "
                  "equipment. Free cash flow = operating cash flow - capex. Not shown for banks."),
    ("Peers", "Other F&O stocks in the same NSE industry that reported in the same quarter. Medians; blank if fewer than 2 peers. "
              "Profit growth rank 1 = fastest profit growth among the group."),
    ("Options", "NSE F&O bhavcopy closing prices. Expiry used = first monthly expiry at least 3 sessions after the reaction day. IV "
                "from the at-the-money straddle. Expected move = straddle price / stock price at the last close before results. "
                "Run-up straddle = buy the ATM straddle 5 sessions before the last close before results, sell at that close; "
                "return after 2% slippage per leg per side and Rs 20 per order."),
    ("Date checks", "Results dates were checked against two independent sources: Yahoo Finance's calendar for Apr 2023 - Feb 2025 "
                    "(99% same day or within 2 days, 97% same before-open / during-market / after-close timing) and the dates in "
                    "your matched_stocks file for 2025-26 (13 of 13 match)."),
    ("Corporate actions", "Bonus issues, splits and demergers come from NSE's corporate-actions data. Since NSE's July-2024 "
                          "bhavcopy format the previous close is not adjusted on those ex-dates, so returns on those days are "
                          "corrected (bonus/split) or left blank (demerger). Rows with an action near the results are noted."),
    ("Limitations", "Closing prices only (no intraday). Financial-statement tags differ for some companies (insurers, some NBFCs), "
                    "so some fields are blank. Market cap uses the previous quarter's share count; rows flagged in 'Data notes' "
                    "had a split or bonus. Past behaviour does not predict future results."),
]
wn["A1"] = "Notes and definitions"
wn["A1"].font = font(bold=True, size=13)
for i, (k, v) in enumerate(notes, 3):
    wn.cell(i, 1, k).font = font(bold=True)
    c = wn.cell(i, 2, v)
    c.font = font()
    c.alignment = Alignment(wrap_text=True, vertical="top")
    wn.cell(i, 1).alignment = Alignment(vertical="top")
wn.column_dimensions["A"].width = 26
wn.column_dimensions["B"].width = 120
for ws_ in wb.worksheets:
    ws_.sheet_view.showGridLines = ws_.title == "Events"
wb.save(OUT)
print("saved", OUT, "rows", len(events), "cols", len(COLS))
