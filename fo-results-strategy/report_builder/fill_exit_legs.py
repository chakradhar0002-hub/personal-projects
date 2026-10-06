"""Store the exact entry strikes on the run-up exit day when they fell outside the +-5% band of the stored chain."""
import csv, io, json, sqlite3, sys, zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
sys.argv = [sys.argv[0], sys.argv[1]]
SP = sys.argv[1]
src = open(__import__("pathlib").Path(__file__).with_name("analyze_events.py")).read().split("# ---------------------------------------------------------------- financials")[0]
exec(src)
from fo_results_strategy.realdata import Http, bhavcopy_urls
ev = json.load(open(f"{SP}/report/events.json"))
needs = {}                                   # day -> set of (symbol, expiry, strike)
for r in ev:
    if r.get("iv_t5") is None or r.get("runup_return") is not None or not r.get("opt_expiry"):
        continue
    react_i = SPOS[r["reaction_day"]]; pre_i = react_i - 1
    t5 = sess(pre_i - 5); ch5, spot5 = chain(r["symbol"], t5)
    k5 = atm(ch5, spot5, r["opt_expiry"])
    if k5:
        needs.setdefault(sess(pre_i), set()).add((r["symbol"], r["opt_expiry"], k5))
print("exit days to re-read:", len(needs), "legs:", sum(len(v) for v in needs.values()), flush=True)
def fetch(day):
    h = Http(pause=0.05)
    for url in bhavcopy_urls(date.fromisoformat(day)):
        try: body = h.get(url)
        except Exception: body = None
        if body and body.startswith(b"PK"): return day, body
    return day, None
db = sqlite3.connect(f"{SP}/report/options.db")
added = 0
with ThreadPoolExecutor(4) as pool:
    for day, raw in pool.map(fetch, sorted(needs)):
        if raw is None: continue
        want = needs[day]
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            rd = csv.DictReader(io.StringIO(z.read(z.namelist()[0]).decode("utf-8", "replace")))
            rows = []
            for r in rd:
                if "TckrSymb" in r:
                    if r["FinInstrmTp"] != "STO": continue
                    key = (r["TckrSymb"].strip(), r["XpryDt"].strip(), float(r["StrkPric"]))
                    vals = (r["OptnTp"].strip(), float(r["ClsPric"] or 0), float(r["SttlmPric"] or 0), float(r["TtlTradgVol"] or 0))
                else:
                    if r["INSTRUMENT"].strip() != "OPTSTK": continue
                    key = (r["SYMBOL"].strip(), datetime.strptime(r["EXPIRY_DT"].strip(), "%d-%b-%Y").date().isoformat(), float(r["STRIKE_PR"]))
                    vals = (r["OPTION_TYP"].strip(), float(r["CLOSE"] or 0), float(r["SETTLE_PR"] or 0), float(r["CONTRACTS"] or 0))
                if key in want:
                    rows.append((day, key[0], key[1], vals[0], key[2], vals[1], vals[2], vals[3]))
        for row in rows:
            if not db.execute("SELECT 1 FROM q WHERE day=? AND symbol=? AND expiry=? AND kind=? AND strike=?", row[:5]).fetchone():
                db.execute("INSERT INTO q VALUES (?,?,?,?,?,?,?,?)", row); added += 1
        db.commit()
print("legs added:", added, flush=True)
