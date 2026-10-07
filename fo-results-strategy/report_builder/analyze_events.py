"""Build one row per stock per quarter (last 22 quarters) from the NSE data stores -> events.json."""
import csv, json, math, sqlite3, statistics, sys
from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fo_results_strategy.pricing import straddle_implied_vol

SP = sys.argv[1]
R = f"{SP}/report"
QUARTERS = [("2021-03-31", "Q4 FY21", "Jan-Mar 2021"), ("2021-06-30", "Q1 FY22", "Apr-Jun 2021"),
            ("2021-09-30", "Q2 FY22", "Jul-Sep 2021"), ("2021-12-31", "Q3 FY22", "Oct-Dec 2021"),
            ("2022-03-31", "Q4 FY22", "Jan-Mar 2022"), ("2022-06-30", "Q1 FY23", "Apr-Jun 2022"),
            ("2022-09-30", "Q2 FY23", "Jul-Sep 2022"), ("2022-12-31", "Q3 FY23", "Oct-Dec 2022"), ("2023-03-31", "Q4 FY23", "Jan-Mar 2023"),
            ("2023-06-30", "Q1 FY24", "Apr-Jun 2023"), ("2023-09-30", "Q2 FY24", "Jul-Sep 2023"),
            ("2023-12-31", "Q3 FY24", "Oct-Dec 2023"), ("2024-03-31", "Q4 FY24", "Jan-Mar 2024"),
            ("2024-06-30", "Q1 FY25", "Apr-Jun 2024"), ("2024-09-30", "Q2 FY25", "Jul-Sep 2024"),
            ("2024-12-31", "Q3 FY25", "Oct-Dec 2024"), ("2025-03-31", "Q4 FY25", "Jan-Mar 2025"),
            ("2025-06-30", "Q1 FY26", "Apr-Jun 2025"), ("2025-09-30", "Q2 FY26", "Jul-Sep 2025"),
            ("2025-12-31", "Q3 FY26", "Oct-Dec 2025"), ("2026-03-31", "Q4 FY26", "Jan-Mar 2026"),
            ("2026-06-30", "Q1 FY27", "Apr-Jun 2026")]
RESULT_DESCS = {"Financial Result Updates", "Outcome of Board Meeting", "Integrated Filing- Financial", "Financial Results",
                "Results"}
TEXT_DESCS = {"Press Release", "General Updates", "Updates", "Investor Presentation"}
SLIP, BROKERAGE = 0.02, 20.0


def d(s):
    return date.fromisoformat(s)


def nse_dt(s):
    for fmt in ("%d-%b-%Y %H:%M:%S", "%d-%b-%Y %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except (TypeError, ValueError):
            pass
    return None


def nse_date(s):
    try:
        return datetime.strptime(s, "%d-%b-%Y").date()
    except (TypeError, ValueError):
        return None


def pct(a, b):
    return a / b - 1 if a is not None and b not in (None, 0) else None


def growth(a, b):
    """Growth vs a positive base only (a loss base makes % growth meaningless)."""
    return a / b - 1 if a is not None and b is not None and b > 0 else None


# ---------------------------------------------------------------- universe, lots, industries
rows = list(csv.reader(open(f"{SP}/fo_mktlots.csv")))
LOTS = {r[1].strip(): int(r[2]) for r in rows[1:] if len(r) > 2 and r[2].strip().isdigit() and "NIFTY" not in r[1]}
ev = sqlite3.connect(f"{R}/nse_events.db")
company, industry = {}, {}
ind_count = defaultdict(Counter)
for sym, ind, co in ev.execute("SELECT symbol, industry, company FROM an"):
    if ind and ind.strip() not in ("-", ""):
        ind_count[sym][ind.strip()] += 1
    if co:
        company.setdefault(sym, co)
for sym, co in ev.execute("SELECT symbol, company FROM fr"):
    if co:
        company.setdefault(sym, co)
industry = {s: c.most_common(1)[0][0] for s, c in ind_count.items()}
# Stocks whose NSE announcements carry no industry: assigned from industry_fill.csv (same NSE label set, checked
# against the stock's sector in NSE's Nifty 500 list)
INDUSTRY_SRC = {s: "NSE" for s in industry}
for r in csv.DictReader(open(Path(__file__).with_name("industry_fill.csv"))):
    if r["symbol"] not in industry:
        industry[r["symbol"]], INDUSTRY_SRC[r["symbol"]] = r["industry"], "Assigned"

SECTOR_RULES = [("Bank", "Nifty Bank"), ("Finance", "Nifty Financial Services"), ("Insurance", "Nifty Financial Services"),
                ("Pharma", "Nifty Pharma"), ("Hospital", "Nifty Healthcare Index"), ("Healthcare", "Nifty Healthcare Index"),
                ("Computers", "Nifty IT"), ("Software", "Nifty IT"), ("IT ", "Nifty IT"),
                ("Automobile", "Nifty Auto"), ("Auto Ancillar", "Nifty Auto"), ("Tyres", "Nifty Auto"), ("Castings", "Nifty Auto"),
                ("Cement", "Nifty Commodities"), ("Personal Care", "Nifty FMCG"), ("Food", "Nifty FMCG"), ("Cigarettes", "Nifty FMCG"),
                ("Beverages", "Nifty FMCG"), ("Tea", "Nifty FMCG"), ("Refineries", "Nifty Oil & Gas"), ("Gas", "Nifty Oil & Gas"),
                ("Oil", "Nifty Oil & Gas"), ("Power", "Nifty Energy"), ("Aluminium", "Nifty Metal"), ("Metal", "Nifty Metal"),
                ("Mining", "Nifty Metal"), ("Steel", "Nifty Metal"), ("Realty", "Nifty Realty"), ("Construction", "Nifty Infrastructure"),
                ("Telecommunication", "Nifty Services Sector"), ("Paints", "Nifty Consumer Durables"),
                ("Airconditioners", "Nifty Consumer Durables"), ("Consumer", "Nifty Consumer Durables"), ("Jewel", "Nifty Consumer Durables"),
                ("Electrical", "Nifty India Manufacturing"), ("Electronics", "Nifty India Manufacturing"),
                ("Diesel Engines", "Nifty India Manufacturing"), ("Engineering", "Nifty India Manufacturing"),
                ("Defence", "Nifty India Defence"), ("Capital Markets", "Nifty Financial Services"), ("Internet", "Nifty India Digital"), ("Shipping", "Nifty Services Sector"), ("Travel", "Nifty Services Sector"),
                ("Media", "Nifty Media"), ("Chemicals", "Nifty Commodities"), ("Fertiliser", "Nifty Commodities"),
                ("Textile", "Nifty India Consumption"), ("Retail", "Nifty India Consumption")]


def sector_index(ind):
    for key, idx in SECTOR_RULES:
        if ind and key.lower() in ind.lower():
            return idx
    return "Nifty 500"


# ---------------------------------------------------------------- prices
px = sqlite3.connect(f"{R}/nse_prices.db")
stock = defaultdict(dict)
for day, sym, o, h, l, c, pc, v in px.execute("SELECT * FROM px ORDER BY day"):
    stock[sym][day] = (o, h, l, c, pc, v)
indexes = defaultdict(dict)
for day, name, o, h, l, c, pe, pb in px.execute("SELECT * FROM idx ORDER BY day"):
    indexes[name][day] = (c, pe, pb)
SESSIONS = sorted(indexes["Nifty 50"])
STOCK_DAYS = {sym: sorted(v) for sym, v in stock.items()}
STOCK_POS = {sym: {x: i for i, x in enumerate(days)} for sym, days in STOCK_DAYS.items()}
# NSE corporate actions: bonus / split / consolidation (share multiplier) and demergers (no multiplier)
CA = {}
for sym, ex, kind, factor, subject in px.execute("SELECT * FROM ca"):
    if (sym, ex) in CA:                                   # e.g. bonus and split on the same day: multiply
        k0, f0, s0 = CA[(sym, ex)]
        CA[(sym, ex)] = (k0, (f0 * factor) if f0 and factor else None, f"{s0} + {subject}")
    else:
        CA[(sym, ex)] = (kind, factor, subject)
CA_BY_SYM = defaultdict(list)
for (sym, ex), v in CA.items():
    CA_BY_SYM[sym].append((ex, *v))
SPOS = {s: i for i, s in enumerate(SESSIONS)}


def sess(i):
    return SESSIONS[i] if 0 <= i < len(SESSIONS) else None


def daily_ret(sym, day):
    """Close / previous close - 1. Since NSE's July-2024 bhavcopy format the previous close is no longer
    adjusted on bonus/split/demerger ex-dates, so those days are corrected with NSE's corporate actions."""
    r = stock[sym].get(day)
    if not r or not r[4]:
        return None
    ca = CA.get((sym, day))
    if ca:
        i = STOCK_POS[sym].get(day)
        prev_close = stock[sym][STOCK_DAYS[sym][i - 1]][3] if i else None
        unadjusted = prev_close is not None and abs(r[4] / prev_close - 1) < 0.01
        if unadjusted:
            kind, factor, _ = ca
            return r[3] * factor / r[4] - 1 if factor else None     # demerger: unknown split of value
    return r[3] / r[4] - 1


def stock_ret(sym, i0, i1):
    """Compounded return from close of session i0 to close of session i1 (corporate-action safe)."""
    if i0 is None or i1 is None or i0 < 0 or i1 >= len(SESSIONS) or i0 >= i1:
        return None
    g, n = 1.0, 0
    for k in range(i0 + 1, i1 + 1):
        r = daily_ret(sym, SESSIONS[k])
        if r is not None:
            g *= 1 + r
            n += 1
    return g - 1 if n >= max(1, (i1 - i0) * 0.8) else None


def index_close(name, day):
    v = indexes.get(name, {}).get(day)
    return v[0] if v else None


def index_ret(name, i0, i1):
    if i0 is None or i1 is None or i0 < 0 or i1 >= len(SESSIONS):
        return None
    return pct(index_close(name, SESSIONS[i1]), index_close(name, SESSIONS[i0]))


def index_day(name, i):
    return index_ret(name, i - 1, i)


# ---------------------------------------------------------------- options
op = sqlite3.connect(f"{R}/options.db")


def chain(sym, day):
    out = defaultdict(dict)
    for exp, kind, k, c, s, v in op.execute("SELECT expiry, kind, strike, close, settle, volume FROM q WHERE symbol=? AND day=?",
                                            (sym, day)):
        out[(exp, k)][kind] = (c, s, v)
    sp = op.execute("SELECT spot FROM spot WHERE symbol=? AND day=?", (sym, day)).fetchone()
    return out, (sp[0] if sp else None)


def sessions_between(a, b):
    """Sessions in (a, b]; b may be beyond the price data (count weekdays)."""
    if a not in SPOS:
        return None
    if b in SPOS:
        return SPOS[b] - SPOS[a]
    n = len(SESSIONS) - 1 - SPOS[a]
    x = d(SESSIONS[-1])
    while x < d(b):
        x += timedelta(days=1)
        n += x.weekday() < 5
    return n


def atm(ch, spot, exp, need_traded=True):
    best = None
    for (e, k), legs in ch.items():
        if e != exp or len(legs) < 2:
            continue
        if need_traded and not all(legs[x][2] > 0 and legs[x][0] > 0 for x in ("CE", "PE")):
            continue
        if abs(k / spot - 1) > 0.05:
            continue
        if best is None or abs(k - spot) < abs(best - spot):
            best = k
    return best


def leg_price(ch, exp, k, kind):
    legs = ch.get((exp, k), {})
    if kind not in legs:
        return None
    c, s, v = legs[kind]
    return c if v > 0 and c > 0 else (s if s > 0 else None)


def options_block(sym, pre_i, react_i, lot):
    out = {}
    pre, react = sess(pre_i), sess(react_i)
    t5 = sess(pre_i - 5)
    if not pre or not react:
        return out
    ch_pre, spot_pre = chain(sym, pre)
    if not ch_pre or not spot_pre:
        return out
    exps = sorted({e for e, _ in ch_pre})
    front = next((e for e in exps if e >= react and (sessions_between(react, e) or 0) >= 3), None)
    if not front:
        return out
    out["opt_expiry"] = front
    n_pre = sessions_between(pre, front)
    k = atm(ch_pre, spot_pre, front)
    if k:
        prem = ch_pre[(front, k)]["CE"][0] + ch_pre[(front, k)]["PE"][0]
        out["iv_pre"] = straddle_implied_vol(prem, spot_pre, k, n_pre / 252, 0.06)
        out["implied_move"] = prem / spot_pre
    ch_r, spot_r = chain(sym, react)
    if ch_r and spot_r:
        kr = atm(ch_r, spot_r, front)
        if kr:
            prem_r = ch_r[(front, kr)]["CE"][0] + ch_r[(front, kr)]["PE"][0]
            out["iv_after"] = straddle_implied_vol(prem_r, spot_r, kr, max(n_pre - (react_i - pre_i), 1) / 252, 0.06)
    if t5:
        ch5, spot5 = chain(sym, t5)
        if ch5 and spot5 and any(e == front for e, _ in ch5):
            k5 = atm(ch5, spot5, front)
            if k5:
                prem5 = ch5[(front, k5)]["CE"][0] + ch5[(front, k5)]["PE"][0]
                n5 = sessions_between(t5, front)
                out["iv_t5"] = straddle_implied_vol(prem5, spot5, k5, n5 / 252, 0.06)
                ce, pe = leg_price(ch_pre, front, k5, "CE"), leg_price(ch_pre, front, k5, "PE")
                if ce is not None and pe is not None and prem5 > 0:
                    exit_ = ce + pe
                    cost = SLIP * (prem5 + exit_) + (4 * BROKERAGE / lot if lot else 0)
                    out["runup_return"] = (exit_ - prem5 - cost) / prem5
                    out["runup_rule"] = "Yes" if n_pre is not None and n_pre <= 14 else "No"
    if out.get("iv_pre") and out.get("iv_after"):
        out["iv_drop"] = out["iv_after"] / out["iv_pre"] - 1
    return out


# ---------------------------------------------------------------- financials
fn = sqlite3.connect(f"{R}/nse_fin.db")
FLAG = {}
for sym, flag in fn.execute("SELECT symbol, bank FROM filings"):
    FLAG[sym] = flag            # NSE format flag: B = bank, F = NBFC / financial company, N = others
FIN, _rank = {}, {}
for sym, to, basis, bank, x, data in fn.execute("SELECT * FROM fin"):
    q = nse_date(to)
    if not q:
        continue
    want = "Non-Consolidated" if FLAG.get(sym) == "B" else "Consolidated"
    key, rank = (sym, q.isoformat()), basis == want
    if key not in FIN or rank > _rank[key]:
        FIN[key], _rank[key] = (basis, FLAG.get(sym, bank), json.loads(data)), rank


def val(data, tags, ctx="OneD"):
    for t in tags:
        v = data.get(t, {}).get(ctx)
        if v is not None:
            return v
    return None


CR = 1e7


def owners_profit(data, ctx="OneD"):
    """Profit attributable to owners; the total profit when that line is missing, 0 or a small unrelated figure
    (some Integrated Filings leave it at 0 or tag the minority share there)."""
    own, tot = val(data, ["ProfitOrLossAttributableToOwnersOfParent"], ctx), val(data, ["ProfitLossForPeriod"], ctx)
    if own is None or (tot and (own == 0 or abs(own) < 0.25 * abs(tot))):
        return tot
    return own


def fin_q(sym, qend):
    rec = FIN.get((sym, qend))
    if not rec:
        return None
    basis, bank, data = rec
    f = {"basis": "Consolidated" if basis == "Consolidated" else "Standalone", "bank": bank == "B", "nbfc": bank == "F"}
    paid = val(data, ["PaidUpValueOfEquityShareCapital"], "OneD") or val(data, ["PaidUpValueOfEquityShareCapital"], "OneI")
    face = val(data, ["FaceValueOfEquityShareCapital"], "OneD") or val(data, ["FaceValueOfEquityShareCapital"], "OneI")
    f["shares"] = paid / face if paid and face else None
    if f["bank"]:
        ie, iexp = val(data, ["InterestEarned"]), val(data, ["InterestExpended"])
        f["sales"] = ie / CR if ie else None
        f["nii"] = (ie - iexp) / CR if ie is not None and iexp is not None else None
        ppop = val(data, ["OperatingProfitBeforeProvisionAndContingencies"])
        f["ppop"] = ppop / CR if ppop is not None else None
        prov = val(data, ["ProvisionsOtherThanTaxAndContingencies"])
        f["prov"] = prov / CR if prov is not None else None
        pat = val(data, ["ProfitLossAfterTaxesMinorityInterestAndShareOfProfitLossOfAssociates", "ProfitLossForThePeriod",
                         "ProfitLossForPeriod"])
        pat_ytd = val(data, ["ProfitLossAfterTaxesMinorityInterestAndShareOfProfitLossOfAssociates", "ProfitLossForThePeriod",
                             "ProfitLossForPeriod"], "FourD")
        f["eps"] = val(data, ["BasicEarningsPerShareAfterExtraordinaryItems", "BasicEarningsPerShareBeforeExtraordinaryItems"])
        f["gnpa"], f["nnpa"], f["roa"] = (val(data, ["PercentageOfGrossNpa"]), val(data, ["PercentageOfNpa"]),
                                          val(data, ["ReturnOnAssets"]))
        cap, res = val(data, ["Capital"], "OneI"), val(data, ["ReservesAndSurplus"], "OneI")
        f["equity"] = (cap + res) / CR if cap is not None and res is not None else None
        f["borrow"] = None
        f["ebitda"] = None
    else:
        sales = val(data, ["RevenueFromOperations"])
        f["sales"] = sales / CR if sales else None
        pbt, fc = val(data, ["ProfitBeforeTax"]), val(data, ["FinanceCosts"]) or 0.0
        da, oi = val(data, ["DepreciationDepletionAndAmortisationExpense"]) or 0.0, val(data, ["OtherIncome"]) or 0.0
        # EBITDA is not meaningful for lenders (finance cost is their cost of goods)
        f["ebitda"] = (pbt + fc + da - oi) / CR if pbt is not None and sales and bank != "F" else None
        pat, pat_ytd = owners_profit(data), owners_profit(data, "FourD")
        f["eps"] = val(data, ["BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations",
                              "BasicEarningsLossPerShareFromContinuingOperations"])
        eq = val(data, ["EquityAttributableToOwnersOfParent", "Equity"], "OneI")
        f["equity"] = eq / CR if eq else None
        bc, bn, b = (val(data, ["BorrowingsCurrent"], "OneI"), val(data, ["BorrowingsNoncurrent"], "OneI"),
                     val(data, ["Borrowings"], "OneI"))
        f["borrow"] = ((bc or 0) + (bn or 0)) / CR if (bc is not None or bn is not None) else (b / CR if b is not None else None)
    f["pat"] = pat / CR if pat is not None else None
    f["pat_ytd"] = pat_ytd / CR if pat_ytd is not None else None
    if f["pat"] is not None and f["sales"] and abs(f["pat"]) > 500 * abs(f["sales"]):
        f["pat"] = f["pat_ytd"] = None          # mis-scaled in the filing (e.g. rupees entered as lakhs)
    cfo = val(data, ["CashFlowsFromUsedInOperatingActivities"], "FourD")
    capex = val(data, ["PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities"], "FourD")
    f["cfo"] = cfo / CR if cfo is not None else None
    f["capex"] = capex / CR if capex is not None else None
    return f


def share_multiplier(sym, after_day, upto_day):
    """Share-count multiplier from NSE bonus/split/consolidation ex-dates in (after_day, upto_day]."""
    m = 1.0
    for ex, kind, factor, subject in CA_BY_SYM.get(sym, []):
        if after_day < ex <= upto_day and factor:
            m *= factor
    return m


_SHARE_MEDIAN = {}


def filing_shares(f):
    """Paid-up capital / face value, unless profit / basic EPS from the same filing says otherwise by more than 2x."""
    raw = f.get("shares")
    implied = f["pat"] * CR / f["eps"] if f.get("pat") and f["pat"] > 0 and f.get("eps") and f["eps"] >= 0.5 else None
    if implied and (not raw or not 0.5 < raw / implied < 2):
        return implied
    return raw


def checked_shares(sym, q):
    """Share count from the quarter's filing, checked against the stock's other quarters on today's share basis (NSE
    bonus / split factors). A count more than 2x away from the median is a mis-scaled filing value: use the median."""
    if sym not in _SHARE_MEDIAN:
        adj = []
        for (s, qq) in FIN:
            if s == sym:
                f = fin_q(sym, qq)
                if f and filing_shares(f):
                    adj.append(filing_shares(f) * share_multiplier(sym, qq, SESSIONS[-1]))
        _SHARE_MEDIAN[sym] = statistics.median(adj) if len(adj) >= 3 else None
    f, med = fin_q(sym, q), _SHARE_MEDIAN[sym]
    raw = f.get("shares") if f else None
    if not med:
        return raw, False
    mult = share_multiplier(sym, q, SESSIONS[-1])
    if raw and 0.5 < raw * mult / med < 2:
        return raw, False
    return med / mult, True


def qshift(qend, n):
    """Quarter end n quarters earlier."""
    y, m = int(qend[:4]), int(qend[5:7])
    m -= 3 * n
    while m <= 0:
        m += 12
        y -= 1
    last = {3: 31, 6: 30, 9: 30, 12: 31}[m]
    return f"{y}-{m:02d}-{last}"


def fy_label(qend):
    y, m = int(qend[:4]), int(qend[5:7])
    fy = y + 1 if m >= 4 else y
    return ("H1 FY" if m == 9 else "FY") + str(fy)[2:]


# ---------------------------------------------------------------- results date and time per stock-quarter
fr_by = defaultdict(list)
for sym, to, bc in ev.execute("SELECT symbol, to_date, broadcast FROM fr"):
    q, t = nse_date(to), nse_dt(bc)
    if q and t:
        fr_by[(sym, q.isoformat())].append(t)
# From 2025 companies file results as SEBI Integrated Filings (Financials): their publication times.
for sym, to, bc in fn.execute("SELECT symbol, to_date, broadcast FROM if_filings"):
    q, t = nse_date(to), nse_dt(bc)
    if q and t:
        fr_by[(sym, q.isoformat())].append(t)
STRONG_DESCS = {"Financial Result Updates", "Integrated Filing- Financial", "Financial Results", "Results"}
an_by = defaultdict(list)       # (time, strong?) per symbol
for sym, an_dt, descr, txt in ev.execute("SELECT symbol, an_dt, descr, txt FROM an"):
    t = nse_dt(an_dt)
    if not t or not descr or "intimation" in descr.lower():
        continue
    low = (txt or "").lower()
    # notices about a future board meeting, not the results themselves ("held on ... to consider" is an outcome)
    if "intimation" in low or "will be held" in low or "trading window" in low or ("to consider" in low and "held on" not in low):
        continue
    if descr in STRONG_DESCS:
        an_by[sym].append((t, True))
    elif (descr == "Outcome of Board Meeting" or descr in TEXT_DESCS) and ("result" in low or "financial statement" in low):
        an_by[sym].append((t, False))
for v in an_by.values():
    v.sort()


def results_time(sym, qend):
    fr_times = fr_by.get((sym, qend))
    qe = d(qend)
    if not fr_times:
        # no results filing record: earliest results announcement within 75 days of the quarter end
        lo, hi = datetime.combine(qe + timedelta(days=1), time()), datetime.combine(qe + timedelta(days=75), time())
        strong = [t for t, st in an_by.get(sym, []) if st and lo <= t <= hi]
        cands = strong or [t for t, st in an_by.get(sym, []) if lo <= t <= hi]
        return (min(cands), "NSE announcement (no filing record)") if cands else (None, None)
    fr_t = min(fr_times)
    floor = datetime.combine(qe + timedelta(days=1), time())
    cands = [t for t, st in an_by.get(sym, [])
             if max(fr_t - timedelta(days=7 if st else 2), floor) <= t <= fr_t]
    return (min(cands), "NSE announcement") if cands else (fr_t, "NSE results filing")


def timing_of(t):
    if t.date().isoformat() not in SPOS:
        return "Non-trading day"
    tt = t.time()
    if tt < time(9, 15):
        return "Before open"
    if tt <= time(15, 30):
        return "During market"
    return "After close"


# ---------------------------------------------------------------- build rows
events = []
for qend, qlabel, period in QUARTERS:
    for sym in sorted(LOTS):
        t, src = results_time(sym, qend)
        if t is None or sym not in stock:
            continue
        rd = t.date().isoformat()
        rs_i = bisect_left(SESSIONS, rd)
        if rs_i < 3 or rs_i + 1 >= len(SESSIONS):
            continue
        timing = timing_of(t)
        react_i = rs_i + 1 if timing == "After close" else rs_i
        pre_i = react_i - 1
        cut_i = rs_i - 2
        row = {"quarter": qlabel, "period": period, "quarter_end": qend, "symbol": sym, "company": company.get(sym, sym),
               "industry": industry.get(sym, ""), "industry_src": INDUSTRY_SRC.get(sym, ""), "lot": LOTS.get(sym), "results_date": rd, "results_time": t.strftime("%H:%M"),
               "timing": timing, "time_source": src, "day_m1": sess(rs_i - 1), "result_day": sess(rs_i),
               "day_p1": sess(rs_i + 1), "reaction_day": sess(react_i)}
        sec = sector_index(row["industry"])
        if index_close(sec, sess(rs_i)) is None:
            sec = "Nifty 500"
        row["sector_index"] = sec
        notes = []
        dm1, dr, dp1 = daily_ret(sym, sess(rs_i - 1)), daily_ret(sym, sess(rs_i)), daily_ret(sym, sess(rs_i + 1))
        row.update(ret_dm1=dm1, ret_rd=dr, ret_dp1=dp1)
        if None not in (dm1, dr, dp1):
            row["three_day"] = dm1 + dr + dp1
            n3 = [index_day("Nifty 50", i) for i in (rs_i - 1, rs_i, rs_i + 1)]
            s3 = [index_day(sec, i) for i in (rs_i - 1, rs_i, rs_i + 1)]
            if None not in n3:
                row["nifty_3d"] = sum(n3)
                row["excess_nifty"] = row["three_day"] - row["nifty_3d"]
            if None not in s3:
                row["sector_3d"] = sum(s3)
                row["excess_sector"] = row["three_day"] - row["sector_3d"]
        rx = stock[sym].get(sess(react_i))
        if rx and rx[4]:
            o, h, l, c, pc, v = rx
            row["gap"], row["move"] = o / pc - 1, c / pc - 1
            row["abs_move"] = abs(row["move"])
            row["range"] = (h - l) / pc
            row["clv"] = (c - l) / (h - l) if h > l else 0.5
            vols = [stock[sym].get(sess(i), (0,) * 6)[5] for i in range(react_i - 20, react_i)]
            vols = [x for x in vols if x]
            row["vol_ratio"] = v / (sum(vols) / len(vols)) if vols else None
        cut = stock[sym].get(sess(cut_i))
        row["price_cutoff"] = cut[3] if cut else None
        for key, n in (("r1w", 5), ("r1m", 21), ("r3m", 63), ("r6m", 126), ("r1y", 250)):
            row[key] = stock_ret(sym, cut_i - n, cut_i)
        row["sector_1m"] = index_ret(sec, cut_i - 21, cut_i)
        row["vs_sector_1m"] = row["r1m"] - row["sector_1m"] if row["r1m"] is not None and row["sector_1m"] is not None else None
        sv = indexes.get(sec, {}).get(sess(cut_i))
        row["sector_pe"], row["sector_pb"] = (sv[1], sv[2]) if sv else (None, None)
        row["next5"] = stock_ret(sym, rs_i + 1, rs_i + 6)
        row["next20"] = stock_ret(sym, rs_i + 1, rs_i + 21)
        n20 = index_ret("Nifty 50", rs_i + 1, rs_i + 21)
        row["next20_vs_nifty"] = row["next20"] - n20 if row["next20"] is not None and n20 is not None else None
        # financials
        f0, f1, f4 = fin_q(sym, qend), fin_q(sym, qshift(qend, 1)), fin_q(sym, qshift(qend, 4))
        if f0:
            row["basis"] = f0["basis"]
            row["fin_type"] = "Bank" if f0["bank"] else ("NBFC / financial" if f0["nbfc"] else "Company")
            row["sales"], row["ebitda"], row["pat"], row["eps"] = f0["sales"], f0["ebitda"], f0["pat"], f0["eps"]
            row["sales_yoy"] = growth(f0["sales"], f4["sales"]) if f4 else None
            row["sales_qoq"] = growth(f0["sales"], f1["sales"]) if f1 else None
            row["pat_yoy"] = growth(f0["pat"], f4["pat"]) if f4 else None
            row["pat_qoq"] = growth(f0["pat"], f1["pat"]) if f1 else None
            if f0["ebitda"] is not None and f0["sales"]:
                row["ebitda_margin"] = f0["ebitda"] / f0["sales"]
                if f4 and f4.get("ebitda") is not None and f4.get("sales"):
                    row["ebitda_margin_chg"] = row["ebitda_margin"] - f4["ebitda"] / f4["sales"]
            row["net_margin"] = f0["pat"] / f0["sales"] if f0["pat"] is not None and f0["sales"] else None
            if f0["bank"]:
                row["nii"], row["gnpa"], row["nnpa"], row["roa"] = f0["nii"], f0["gnpa"], f0["nnpa"], f0["roa"]
                if f4:
                    row["nii_yoy"] = growth(f0["nii"], f4.get("nii"))
                    row["ppop_yoy"] = growth(f0["ppop"], f4.get("ppop"))
                    row["prov_yoy"] = growth(f0["prov"], f4.get("prov"))
        else:
            notes.append("no NSE XBRL results for this quarter")
        # valuation before results: last four quarters known before this result
        prev = [fin_q(sym, qshift(qend, k)) for k in (1, 2, 3, 4)]
        shares, fixed = checked_shares(sym, qshift(qend, 1))
        if all(p and p.get("pat") is not None for p in prev) and shares and row["price_cutoff"]:
            ttm = sum(p["pat"] for p in prev)
            mult = share_multiplier(sym, qshift(qend, 1), sess(cut_i))
            if abs(mult - 1) > 0.01:
                notes.append(f"share count x{mult:.2f} for a bonus/split before results (market cap adjusted)")
            if fixed:
                notes.append("share count in the previous filing looked mis-scaled; used the stock's other quarters")
            mcap = row["price_cutoff"] * shares * mult / CR
            row["mcap"], row["ttm_pat"] = mcap, ttm
            row["pe"] = mcap / ttm if ttm > 0 else None
            hq = next((q for q in (qshift(qend, k) for k in (1, 2, 3)) if q[5:7] in ("03", "09")), None)
            hf = fin_q(sym, hq) if hq else None
            if hf and hf.get("equity"):
                row["pb"] = mcap / hf["equity"]
                row["roe"] = ttm / hf["equity"]
                if hf.get("borrow") is not None and not hf["bank"]:
                    row["debt_equity"] = hf["borrow"] / hf["equity"]
        # cash flow: latest half-year or year filing up to and including this result
        cq = next((q for q in (qshift(qend, k) for k in (0, 1, 2)) if q[5:7] in ("03", "09")), None)
        cf = fin_q(sym, cq) if cq else None
        if cf and cf.get("cfo") is not None and not cf["bank"]:
            row["cf_period"] = fy_label(cq)
            row["cfo"], row["capex"] = cf["cfo"], cf["capex"]
            row["fcf"] = cf["cfo"] - (cf["capex"] or 0)
            row["cfo_pat"] = cf["cfo"] / cf["pat_ytd"] if cf.get("pat_ytd") and cf["pat_ytd"] > 0 else None
        lo_day, hi_day = sess(max(cut_i - 21, 0)), sess(min(rs_i + 21, len(SESSIONS) - 1))
        for ex, kind, factor, subject in CA_BY_SYM.get(sym, []):
            if lo_day <= ex <= hi_day:
                notes.append(f"{subject} on {ex}" + (" (returns adjusted)" if factor else " (returns across it may be off)"))
        # options
        row.update(options_block(sym, pre_i, react_i, LOTS.get(sym)))
        if "opt_expiry" not in row:
            notes.append("no option prices for this event")
        row["notes"] = "; ".join(notes)
        events.append(row)

# ---------------------------------------------------------------- peers (same NSE industry, same quarter)
by_iq = defaultdict(list)
for r in events:
    if r["industry"]:
        by_iq[(r["industry"], r["quarter"])].append(r)


def med(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


for r in events:
    peers = [p for p in by_iq.get((r["industry"], r["quarter"]), []) if p is not r]
    r["peer_n"] = len(peers)
    if len(peers) < 2:
        continue
    r["peer_three_day"] = med(p.get("three_day") for p in peers)
    if r.get("three_day") is not None and r["peer_three_day"] is not None:
        r["vs_peer_three_day"] = r["three_day"] - r["peer_three_day"]
    r["peer_sales_yoy"] = med(p.get("sales_yoy") for p in peers)
    r["peer_pat_yoy"] = med(p.get("pat_yoy") for p in peers)
    r["peer_pe"] = med(p.get("pe") for p in peers)
    if r.get("pe") and r["peer_pe"]:
        r["pe_vs_peers"] = r["pe"] / r["peer_pe"] - 1
    group = [p for p in by_iq[(r["industry"], r["quarter"])] if p.get("pat_yoy") is not None]
    if r.get("pat_yoy") is not None and len(group) >= 3:
        rank = 1 + sum(1 for p in group if p["pat_yoy"] > r["pat_yoy"])
        r["pat_yoy_rank"] = f"{rank} of {len(group)}"

json.dump(events, open(f"{R}/events.json", "w"))
print("events:", len(events))
print(Counter(r["quarter"] for r in events))
print(Counter(r["timing"] for r in events))
for k in ("three_day", "sales", "pe", "cfo", "opt_expiry", "runup_return", "peer_pe"):
    print(f"  {k:<14} filled {sum(1 for r in events if r.get(k) is not None)}")
