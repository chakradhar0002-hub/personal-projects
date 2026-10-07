"""Per stock: NSE quarterly financial-results filings and all corporate announcements.

    python3 nse_events.py DATA                          # filings + announcements Dec 2022 - Sep 2026
    python3 nse_events.py DATA 01-03-2021 30-11-2022    # add announcements for an earlier range
"""
import csv, json, sqlite3, sys, time, urllib.parse
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from fo_results_strategy.realdata import Http
SP = sys.argv[1]
rows = list(csv.reader(open(f"{SP}/fo_mktlots.csv")))
UNIVERSE = sorted(r[1].strip() for r in rows[1:] if len(r) > 2 and r[2].strip().isdigit() and "NIFTY" not in r[1])
db = sqlite3.connect(f"{SP}/report/nse_events.db")
db.executescript("""CREATE TABLE IF NOT EXISTS fr(symbol, company, industry, from_date, to_date, broadcast, consolidated, audited, relating_to);
CREATE TABLE IF NOT EXISTS an(symbol, an_dt, descr, txt, industry, company);
CREATE TABLE IF NOT EXISTS done(symbol PRIMARY KEY);""")
FROM, TO = (sys.argv[2], sys.argv[3]) if len(sys.argv) > 3 else ("01-12-2022", "30-09-2026")
DONE = "done" if FROM == "01-12-2022" else "done_" + FROM.replace("-", "")
db.execute(f"CREATE TABLE IF NOT EXISTS {DONE}(symbol PRIMARY KEY)")
done = {r[0] for r in db.execute(f"SELECT symbol FROM {DONE}")}
http = Http(pause=1.0)
http.opener.addheaders = [("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
                          ("Accept", "application/json"), ("Referer", "https://www.nseindia.com/")]
for n, sym in enumerate(UNIVERSE, 1):
    if sym in done: continue
    s = urllib.parse.quote(sym)
    try:
        fr = json.loads(http.get(f"https://www.nseindia.com/api/corporates-financial-results?index=equities&period=Quarterly&symbol={s}") or b"[]") \
            if DONE == "done" else []
        an = json.loads(http.get(f"https://www.nseindia.com/api/corporate-announcements?index=equities&symbol={s}&from_date={FROM}&to_date={TO}") or b"[]")
    except Exception as e:
        print(sym, "failed", e, flush=True); time.sleep(5); continue
    an = an if isinstance(an, list) else an.get("data", [])
    db.executemany("INSERT INTO fr VALUES (?,?,?,?,?,?,?,?,?)",
                   [(sym, r.get("companyName"), r.get("industry"), r.get("fromDate"), r.get("toDate"), r.get("broadCastDate") or r.get("filingDate"),
                     r.get("consolidated"), r.get("audited"), r.get("relatingTo")) for r in (fr if isinstance(fr, list) else [])])
    db.executemany("INSERT INTO an VALUES (?,?,?,?,?,?)",
                   [(sym, r.get("an_dt"), r.get("desc"), (r.get("attchmntText") or "")[:400], r.get("smIndustry"), r.get("sm_name")) for r in an])
    db.execute(f"INSERT INTO {DONE} VALUES (?)", (sym,)); db.commit()
    if n % 20 == 0: print(f"{n}/{len(UNIVERSE)}", flush=True)
print("done", flush=True)
