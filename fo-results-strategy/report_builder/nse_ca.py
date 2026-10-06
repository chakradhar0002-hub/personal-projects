"""NSE corporate actions (bonus, split, consolidation, demerger) for the universe -> share multipliers."""
import csv, json, re, sqlite3, sys, urllib.parse
from datetime import datetime
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from fo_results_strategy.realdata import Http
SP = sys.argv[1]
rows = list(csv.reader(open(f"{SP}/fo_mktlots.csv")))
UNIVERSE = sorted(r[1].strip() for r in rows[1:] if len(r) > 2 and r[2].strip().isdigit() and "NIFTY" not in r[1])
db = sqlite3.connect(f"{SP}/report/nse_prices.db")
db.executescript("DROP TABLE IF EXISTS ca; CREATE TABLE ca(symbol, ex_date, kind, factor REAL, subject);")
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
n_ok = 0
for sym in UNIVERSE:
    try:
        raw = api.get("https://www.nseindia.com/api/corporates-corporateActions?index=equities&symbol="
                      f"{urllib.parse.quote(sym)}&from_date=01-12-2021&to_date=30-09-2026", timeout=20)
        j = json.loads(raw or b"[]")
    except Exception as e:
        print(sym, "failed", e, flush=True); continue
    out = []
    for r in (j if isinstance(j, list) else j.get("data", [])):
        kind, factor = parse(r.get("subject") or "")
        if kind:
            try: ex = datetime.strptime(r["exDate"], "%d-%b-%Y").date().isoformat()
            except Exception: continue
            out.append((sym, ex, kind, factor, r.get("subject")))
    db.executemany("INSERT INTO ca VALUES (?,?,?,?,?)", out); db.commit(); n_ok += 1
print("symbols:", n_ok)
for r in db.execute("SELECT * FROM ca ORDER BY ex_date"): print(r)
