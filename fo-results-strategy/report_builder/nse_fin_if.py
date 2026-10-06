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
pick = {}
for sym, to, basis, bc, x, co in db.execute("SELECT * FROM if_filings"):
    if not x or not x.startswith("http"): continue
    want = "Non-Consolidated" if bank.get(sym) == "Y" else "Consolidated"
    score = (basis == want, bt(bc))
    if (sym, to) not in pick or score > pick[(sym, to)][0]:
        pick[(sym, to)] = (score, sym, to, basis, bank.get(sym, "N"), x)
have = {r[0] for r in db.execute("SELECT xbrl FROM fin")}
old_q = {(s, t) for s, t in db.execute("SELECT symbol, to_date FROM fin")}
todo = [v[1:] for k, v in pick.items() if v[5] not in have and k not in old_q]
print("integrated xbrl to fetch:", len(todo), flush=True)
pat = {t: re.compile(rf'<(?:in-bse-fin|in-capmkt):{t} [^>]*contextRef="(OneD|FourD|OneI)"[^>]*>([^<]+)<') for t in TAGS}
def work(item):
    h = Http(pause=0.05)
    try: body = h.get(item[4])
    except Exception: return item, None
    if not body: return item, None
    text = body.decode("utf-8", "replace"); out = {}
    for t, rx in pat.items():
        for ctx, v in rx.findall(text):
            try: out.setdefault(t, {})[ctx] = float(v)
            except ValueError: pass
    return item, out
with ThreadPoolExecutor(6) as pool:
    for n, (item, data) in enumerate(pool.map(work, todo), 1):
        if data is not None:
            db.execute("INSERT OR REPLACE INTO fin VALUES (?,?,?,?,?,?)", (*item[:4], item[4], json.dumps(data)))
        if n % 100 == 0: db.commit(); print(f"xbrl {n}/{len(todo)}", flush=True)
db.commit(); print("done", flush=True)
