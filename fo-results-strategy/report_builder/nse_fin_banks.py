"""Standalone results XBRL for banks (NSE flag B), all quarters, from both the old results API and Integrated Filings."""
import json, re, sqlite3, sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from fo_results_strategy.realdata import Http
SP = sys.argv[1]
TAGS = eval(open(__import__("pathlib").Path(__file__).with_name("nse_fin.py")).read().split("TAGS = ")[1].split("]")[0] + "]")
db = sqlite3.connect(f"{SP}/report/nse_fin.db", timeout=60)
banks = {s for (s,) in db.execute("SELECT DISTINCT symbol FROM filings WHERE bank='B'")}
def bt(s):
    for f in ("%d-%b-%Y %H:%M:%S", "%d-%b-%Y %H:%M"):
        try: return datetime.strptime(s, f)
        except Exception: pass
    return datetime.min
pick = {}
rows = list(db.execute("SELECT symbol, to_date, basis, broadcast, xbrl FROM filings WHERE bank='B' AND basis='Non-Consolidated'"))
rows += list(db.execute("SELECT symbol, to_date, basis, broadcast, xbrl FROM if_filings WHERE basis='Non-Consolidated'"))
for sym, to, basis, bc, x in rows:
    if sym in banks and x and x.startswith("http"):
        if (sym, to) not in pick or bt(bc) > bt(pick[(sym, to)][3]):
            pick[(sym, to)] = (sym, to, basis, bc, x)
have = {r[0] for r in db.execute("SELECT xbrl FROM fin")}
todo = [(s, t, b, "B", x) for (s, t, b, bc, x) in pick.values() if x not in have]
print("bank standalone xbrl to fetch:", len(todo), flush=True)
pat = {t: re.compile(rf'<(?:in-bse-fin|in-capmkt):{t} [^>]*contextRef="(OneD|FourD|OneI)"[^>]*>([^<]+)<') for t in TAGS}
def work(item):
    try: body = Http(pause=0.05).get(item[4])
    except Exception: return item, None
    if not body: return item, None
    text, out = body.decode("utf-8", "replace"), {}
    for t, rx in pat.items():
        for ctx, v in rx.findall(text):
            try: out.setdefault(t, {})[ctx] = float(v)
            except ValueError: pass
    return item, out
with ThreadPoolExecutor(6) as pool:
    for item, data in pool.map(work, todo):
        if data is not None:
            db.execute("INSERT OR REPLACE INTO fin VALUES (?,?,?,?,?,?)", (*item[:4], item[4], json.dumps(data)))
db.commit(); print("done", flush=True)
