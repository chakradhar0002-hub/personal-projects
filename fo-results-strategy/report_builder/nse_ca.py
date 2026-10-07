"""NSE corporate actions for the universe, Nov 2017 - Sep 2026: bonus, split, consolidation, demerger -> share multipliers
(table ca); dividend ex-dates (table div). Renamed stocks are also queried under their old symbols."""
import csv, json, re, sqlite3, sys, urllib.parse
from datetime import datetime
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from fo_results_strategy.realdata import Http
SP = sys.argv[1]
rows = list(csv.reader(open(f"{SP}/fo_mktlots.csv")))
UNIVERSE = sorted(r[1].strip() for r in rows[1:] if len(r) > 2 and r[2].strip().isdigit() and "NIFTY" not in r[1])
db = sqlite3.connect(f"{SP}/report/nse_prices.db")
db.executescript("""DROP TABLE IF EXISTS ca; CREATE TABLE ca(symbol, ex_date, kind, factor REAL, subject);
DROP TABLE IF EXISTS div; CREATE TABLE div(symbol, ex_date, subject, PRIMARY KEY(symbol, ex_date, subject));""")
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
import aliases
ALIAS = aliases.load(SP, set(UNIVERSE))
api = Http(pause=0.6, retries=2)
api.opener.addheaders = [("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
                         ("Accept", "application/json"), ("Referer", "https://www.nseindia.com/")]
def parse(subject):
    s = subject.lower()
    m = re.search(r"bonus\s*(\d+)\s*:\s*(\d+)", s)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return "bonus", (a + b) / b
    if "split" in s or "sub-division" in s or "subdivision" in s:
        nums = [float(x) for x in re.findall(r"r[se]\.?\s*(\d+(?:\.\d+)?)", s)]
        if len(nums) >= 2 and nums[1] > 0:
            return "split", nums[0] / nums[1]
    if "consolidation" in s:
        nums = [float(x) for x in re.findall(r"r[se]\.?\s*(\d+(?:\.\d+)?)", s)]
        if len(nums) >= 2 and nums[1] > 0:
            return "consolidation", nums[0] / nums[1]
    if "demerger" in s or "scheme of arrangement" in s:
        return "demerger", None
    return None, None
n_ok, seen = 0, set()
for query in UNIVERSE + sorted(ALIAS):
    try:
        raw = api.get("https://www.nseindia.com/api/corporates-corporateActions?index=equities&symbol="
                      f"{urllib.parse.quote(query)}&from_date=01-11-2017&to_date=30-09-2026", timeout=20)
        j = json.loads(raw or b"[]")
    except Exception as e:
        print(query, "failed", e, flush=True); continue
    out, divs = [], []
    for r in (j if isinstance(j, list) else j.get("data", [])):
        try: ex = datetime.strptime(r["exDate"], "%d-%b-%Y").date().isoformat()
        except Exception: continue
        sym = aliases.resolve(query, ex, ALIAS)
        if sym not in UNIVERSE:
            continue
        subject = r.get("subject") or ""
        if "dividend" in subject.lower():
            divs.append((sym, ex, subject))
        kind, factor = parse(subject)
        if kind and (sym, ex, kind) not in seen:
            seen.add((sym, ex, kind))
            out.append((sym, ex, kind, factor, subject))
    db.executemany("INSERT INTO ca VALUES (?,?,?,?,?)", out)
    db.executemany("INSERT OR IGNORE INTO div VALUES (?,?,?)", divs); db.commit(); n_ok += 1
print("symbols queried:", n_ok, "dividends:", db.execute("SELECT COUNT(*) FROM div").fetchone()[0])
for r in db.execute("SELECT * FROM ca ORDER BY ex_date"): print(r)
