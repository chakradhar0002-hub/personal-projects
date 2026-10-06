"""NSE Integrated Filing (Financials) results, quarters Mar 2025 - Jun 2026: filings list + parsed XBRL into nse_fin.db."""
import csv, json, re, sqlite3, sys, time, urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from fo_results_strategy.realdata import Http
SP = sys.argv[1]
rows = list(csv.reader(open(f"{SP}/fo_mktlots.csv")))
UNIVERSE = sorted(r[1].strip() for r in rows[1:] if len(r) > 2 and r[2].strip().isdigit() and "NIFTY" not in r[1])
QEND = {"31-Mar-2025", "30-Jun-2025", "30-Sep-2025", "31-Dec-2025", "31-Mar-2026", "30-Jun-2026", "31-Dec-2024"}
TAGS = open(__import__("pathlib").Path(__file__).with_name("nse_fin.py")).read().split("TAGS = ")[1].split("]")[0] + "]"
TAGS = eval(TAGS)
db = sqlite3.connect(f"{SP}/report/nse_fin.db", check_same_thread=False)
db.executescript("""CREATE TABLE IF NOT EXISTS if_filings(symbol, to_date, basis, broadcast, xbrl, company);
CREATE TABLE IF NOT EXISTS if_listed(symbol PRIMARY KEY);""")
bank = {s: b for s, b in db.execute("SELECT symbol, bank FROM filings WHERE bank IS NOT NULL")}
api = Http(pause=1.2)
api.opener.addheaders = [("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
                         ("Accept", "application/json"), ("Referer", "https://www.nseindia.com/")]
listed = {r[0] for r in db.execute("SELECT symbol FROM if_listed")}
for n, sym in enumerate(UNIVERSE, 1):
    if sym in listed: continue
    try:
        raw = api.get("https://www.nseindia.com/api/integrated-filing-results?index=equities&period=Quarterly&symbol="
                      f"{urllib.parse.quote(sym)}&type=Integrated%20Filing-%20Financials")
        data = json.loads(raw or b"{}").get("data", [])
    except Exception as e:
        print(sym, "list failed", e, flush=True); time.sleep(5); continue
    out = []
    for r in data:
        try:
            to = datetime.strptime(r.get("qe_Date", ""), "%d-%b-%Y").strftime("%d-%b-%Y")
        except ValueError:
            continue
        if to in QEND:
            out.append((sym, to, "Consolidated" if r.get("consolidated") == "Consolidated" else "Non-Consolidated",
                        r.get("broadcast_Date"), r.get("xbrl"), r.get("cmName")))
    db.executemany("INSERT INTO if_filings VALUES (?,?,?,?,?,?)", out)
    db.execute("INSERT INTO if_listed VALUES (?)", (sym,)); db.commit()
    if n % 25 == 0: print(f"listed {n}/{len(UNIVERSE)}", flush=True)
def bt(s):
    try: return datetime.strptime(s, "%d-%b-%Y %H:%M:%S")
    except Exception: return datetime.min
# Read every candidate filing (a quarter can have several: consolidated / standalone, revisions, and filings whose
# main period is the half-year or full year), keep the facts by their dates, then per (stock, quarter, basis) use the
# latest filing that has the 3-month quarter.
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from xbrl_periods import fact_patterns, has_quarter, parse
db.execute("CREATE TABLE IF NOT EXISTS if_parsed(xbrl PRIMARY KEY, data TEXT)")
old_q = {(s, t) for s, t, x in db.execute("SELECT symbol, to_date, xbrl FROM fin") if "INTEGRATED" not in (x or "")}
cands = [r for r in db.execute("SELECT * FROM if_filings")
         if r[4] and r[4].startswith("http") and (r[0], r[1]) not in old_q]
done = {x for x, d in db.execute("SELECT xbrl, data FROM if_parsed") if has_quarter(json.loads(d))}   # retry the rest
todo = sorted({(r[1], r[4]) for r in cands if r[4] not in done})
print("integrated xbrl to read:", len(todo), "of", len(cands), flush=True)
PATTERNS = fact_patterns(TAGS)
def work(item):
    to, url = item
    try: body = Http(pause=0.05).get(url)
    except Exception: return url, None
    if not body: return url, None
    return url, parse(body.decode("utf-8", "replace"), datetime.strptime(to, "%d-%b-%Y").date(), PATTERNS)
with ThreadPoolExecutor(6) as pool:
    for n, (url, data) in enumerate(pool.map(work, todo), 1):
        if data is not None:
            db.execute("INSERT OR REPLACE INTO if_parsed VALUES (?,?)", (url, json.dumps(data)))
        if n % 200 == 0: db.commit(); print(f"xbrl {n}/{len(todo)}", flush=True)
db.commit()
parsed = {x: json.loads(d) for x, d in db.execute("SELECT * FROM if_parsed")}
pick = {}
for sym, to, basis, bc, x, co in cands:
    if x not in parsed: continue
    score = (has_quarter(parsed[x]), bt(bc), x)
    if (sym, to, basis) not in pick or score > pick[(sym, to, basis)][0]:
        pick[(sym, to, basis)] = (score, sym, to, basis, bank.get(sym, "N"), x)
db.execute("DELETE FROM fin WHERE xbrl LIKE '%INTEGRATED_FILING%'")
db.executemany("INSERT OR REPLACE INTO fin VALUES (?,?,?,?,?,?)",
               [(sym, to, basis, b, x, json.dumps(parsed[x])) for score, sym, to, basis, b, x in pick.values() if score[0]])
db.commit()
print("quarters stored:", sum(1 for v in pick.values() if v[0][0]), "without a 3-month quarter:",
      sorted(f"{v[1]} {v[2]} {v[3]}" for v in pick.values() if not v[0][0]), flush=True)
print("done", flush=True)
