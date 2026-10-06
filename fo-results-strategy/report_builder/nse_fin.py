"""NSE quarterly results XBRL for every universe stock, Dec 2021 - Jun 2026 quarters: parsed key figures in sqlite."""
import csv, json, re, sqlite3, sys, time, urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from fo_results_strategy.realdata import Http
SP = sys.argv[1]
rows = list(csv.reader(open(f"{SP}/fo_mktlots.csv")))
UNIVERSE = sorted(r[1].strip() for r in rows[1:] if len(r) > 2 and r[2].strip().isdigit() and "NIFTY" not in r[1])
QEND = {"31-Dec-2021", "31-Mar-2022", "30-Jun-2022", "30-Sep-2022", "31-Dec-2022", "31-Mar-2023", "30-Jun-2023", "30-Sep-2023",
        "31-Dec-2023", "31-Mar-2024", "30-Jun-2024", "30-Sep-2024", "31-Dec-2024", "31-Mar-2025", "30-Jun-2025", "30-Sep-2025",
        "31-Dec-2025", "31-Mar-2026", "30-Jun-2026"}
TAGS = ["RevenueFromOperations", "OtherIncome", "Income", "Expenses", "FinanceCosts", "DepreciationDepletionAndAmortisationExpense",
        "ProfitBeforeTax", "TaxExpense", "ProfitLossForPeriod", "ProfitOrLossAttributableToOwnersOfParent",
        "BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations", "BasicEarningsLossPerShareFromContinuingOperations",
        "PaidUpValueOfEquityShareCapital", "FaceValueOfEquityShareCapital", "Equity", "EquityAttributableToOwnersOfParent",
        "BorrowingsCurrent", "BorrowingsNoncurrent", "Borrowings", "CashFlowsFromUsedInOperatingActivities",
        "PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities", "CashFlowsFromUsedInInvestingActivities",
        "CashFlowsFromUsedInFinancingActivities", "CashAndCashEquivalents",
        # banks
        "InterestEarned", "InterestExpended", "OperatingExpenses", "OperatingProfitBeforeProvisionAndContingencies",
        "ProvisionsOtherThanTaxAndContingencies", "ProfitLossForThePeriod", "ProfitLossAfterTaxesMinorityInterestAndShareOfProfitLossOfAssociates",
        "BasicEarningsPerShareAfterExtraordinaryItems", "PercentageOfGrossNpa", "PercentageOfNpa", "ReturnOnAssets",
        "CET1Ratio", "CapitalAdequacyRatio", "Deposits", "Advances", "Capital", "ReservesAndSurplus"]
db = sqlite3.connect(f"{SP}/report/nse_fin.db", check_same_thread=False)
db.executescript("""CREATE TABLE IF NOT EXISTS filings(symbol, to_date, basis, bank, broadcast, xbrl, industry, company);
CREATE TABLE IF NOT EXISTS listed(symbol PRIMARY KEY);
CREATE TABLE IF NOT EXISTS fin(symbol, to_date, basis, bank, xbrl PRIMARY KEY, data TEXT);""")
api = Http(pause=1.2)
api.opener.addheaders = [("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
                         ("Accept", "application/json"), ("Referer", "https://www.nseindia.com/")]
listed = {r[0] for r in db.execute("SELECT symbol FROM listed")}
for n, sym in enumerate(UNIVERSE, 1):
    if sym in listed: continue
    try:
        fr = json.loads(api.get(f"https://www.nseindia.com/api/corporates-financial-results?index=equities&period=Quarterly&symbol={urllib.parse.quote(sym)}") or b"[]")
    except Exception as e:
        print(sym, "list failed", e, flush=True); time.sleep(5); continue
    db.executemany("INSERT INTO filings VALUES (?,?,?,?,?,?,?,?)",
                   [(sym, r.get("toDate"), r.get("consolidated"), r.get("bank"), r.get("broadCastDate") or r.get("filingDate"), r.get("xbrl"),
                     r.get("industry"), r.get("companyName")) for r in (fr if isinstance(fr, list) else []) if r.get("toDate") in QEND])
    db.execute("INSERT INTO listed VALUES (?)", (sym,)); db.commit()
    if n % 25 == 0: print(f"listed {n}/{len(UNIVERSE)}", flush=True)
def bt(s):
    try: return datetime.strptime(s, "%d-%b-%Y %H:%M:%S")
    except Exception:
        try: return datetime.strptime(s, "%d-%b-%Y %H:%M")
        except Exception: return datetime.min
# preferred filing per (symbol, quarter): banks standalone, others consolidated (else standalone); latest revision
pick = {}
for sym, to, basis, bank, bc, x, ind, co in db.execute("SELECT * FROM filings"):
    if not x or not x.startswith("http"): continue
    want = "Non-Consolidated" if bank == "Y" else "Consolidated"
    score = (basis == want, bt(bc))
    key = (sym, to)
    if key not in pick or score > pick[key][0]:
        pick[key] = (score, sym, to, basis, bank, x)
have = {r[0] for r in db.execute("SELECT xbrl FROM fin")}
todo = [v[1:] for v in pick.values() if v[5] not in have]
print("xbrl to fetch:", len(todo), flush=True)
pat = {t: re.compile(rf'<in-bse-fin:{t} [^>]*contextRef="(OneD|FourD|OneI)"[^>]*>([^<]+)<') for t in TAGS}
def work(item):
    sym, to, basis, bank, x = item
    h = Http(pause=0.05)
    try:
        body = h.get(x)
    except Exception as e:
        return item, None
    if not body: return item, None
    text = body.decode("utf-8", "replace")
    out = {}
    for t, rx in pat.items():
        for ctx, v in rx.findall(text):
            try: out.setdefault(t, {})[ctx] = float(v)
            except ValueError: pass
    return item, out
with ThreadPoolExecutor(6) as pool:
    for n, (item, data) in enumerate(pool.map(work, todo), 1):
        if data is not None:
            db.execute("INSERT OR REPLACE INTO fin VALUES (?,?,?,?,?,?)", (*item[:4], item[4], json.dumps(data)))
        if n % 100 == 0:
            db.commit(); print(f"xbrl {n}/{len(todo)}", flush=True)
db.commit(); print("done", flush=True)
