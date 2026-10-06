import csv, json, sqlite3, sys, time, urllib.parse
from datetime import datetime
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from fo_results_strategy.realdata import Http
SP = sys.argv[1]
rows = list(csv.reader(open(f"{SP}/fo_mktlots.csv")))
UNIVERSE = sorted((r[1].strip() for r in rows[1:] if len(r) > 2 and r[2].strip().isdigit() and "NIFTY" not in r[1]), reverse=True)
QEND = {"31-Mar-2025", "30-Jun-2025", "30-Sep-2025", "31-Dec-2025", "31-Mar-2026", "30-Jun-2026", "31-Dec-2024"}
db = sqlite3.connect(f"{SP}/report/nse_fin.db", timeout=60)
api = Http(pause=0.5, retries=2)
api.opener.addheaders = [("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
                         ("Accept", "application/json"), ("Referer", "https://www.nseindia.com/")]
for sym in UNIVERSE:
    if db.execute("SELECT 1 FROM if_listed WHERE symbol=?", (sym,)).fetchone():
        print("met the other worker at", sym, flush=True); break
    try:
        raw = api.get("https://www.nseindia.com/api/integrated-filing-results?index=equities&period=Quarterly&symbol="
                      f"{urllib.parse.quote(sym)}&type=Integrated%20Filing-%20Financials", timeout=15)
        data = json.loads(raw or b"{}").get("data", [])
    except Exception as e:
        print(sym, "failed", e, flush=True); continue
    out = []
    for r in data:
        try: to = datetime.strptime(r.get("qe_Date", ""), "%d-%b-%Y").strftime("%d-%b-%Y")
        except ValueError: continue
        if to in QEND:
            out.append((sym, to, "Consolidated" if r.get("consolidated") == "Consolidated" else "Non-Consolidated",
                        r.get("broadcast_Date"), r.get("xbrl"), r.get("cmName")))
    if db.execute("SELECT 1 FROM if_listed WHERE symbol=?", (sym,)).fetchone(): break
    db.executemany("INSERT INTO if_filings VALUES (?,?,?,?,?,?)", out)
    db.execute("INSERT OR IGNORE INTO if_listed VALUES (?)", (sym,)); db.commit()
print("reverse lister done", flush=True)
