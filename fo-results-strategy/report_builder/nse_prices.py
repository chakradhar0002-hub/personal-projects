"""NSE equity bhavcopy (EQ series, universe stocks) and all NSE index closes, every session Sep 2022 - Sep 2026,
including weekend sessions (Budget day, special Saturday sessions, Muhurat)."""
import csv, io, sqlite3, sys, zipfile
from datetime import date, timedelta
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from fo_results_strategy.realdata import Http
SP = sys.argv[1]
rows = list(csv.reader(open(f"{SP}/fo_mktlots.csv")))
UNIVERSE = {r[1].strip() for r in rows[1:] if len(r) > 2 and r[2].strip().isdigit() and "NIFTY" not in r[1]}
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
import aliases
ALIAS = aliases.load(SP, UNIVERSE)      # old symbol -> (today's symbol, rename day): rows before a rename keep the stock's history
db = sqlite3.connect(f"{SP}/report/nse_prices.db")
db.executescript("""CREATE TABLE IF NOT EXISTS px(day, symbol, open REAL, high REAL, low REAL, close REAL, prevclose REAL, volume REAL, PRIMARY KEY(day, symbol));
CREATE TABLE IF NOT EXISTS idx(day, name, open REAL, high REAL, low REAL, close REAL, pe REAL, pb REAL, PRIMARY KEY(day, name));
CREATE TABLE IF NOT EXISTS done(day PRIMARY KEY, ok INTEGER);""")
# "--refresh" re-reads days already stored (after adding aliases or series); rows are replaced, not duplicated
have = set() if "--refresh" in sys.argv else {r[0] for r in db.execute("SELECT day FROM done")}
sys.argv = [x for x in sys.argv if x != "--refresh"]
http = Http(pause=0.1)
d, end = (date.fromisoformat(sys.argv[2]), date.fromisoformat(sys.argv[3])) if len(sys.argv) > 3 else (date(2022, 9, 1), date(2026, 9, 30))
todo = []
while d <= end:
    if d.isoformat() not in have: todo.append(d)          # weekends too: Budget-day and special sessions
    d += timedelta(days=1)
print("sessions to fetch:", len(todo), flush=True)
def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None
from concurrent.futures import ThreadPoolExecutor
def fetch(d):
    h = Http(pause=0.05)
    mon = d.strftime("%b").upper()
    urls = [f"https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{d:%Y%m%d}_F_0000.csv.zip",
            f"https://nsearchives.nseindia.com/content/historical/EQUITIES/{d:%Y}/{mon}/cm{d:%d}{mon}{d:%Y}bhav.csv.zip"]
    if d < date(2024, 7, 8): urls.reverse()
    raw = None
    for u in urls:
        try: body = h.get(u)
        except Exception: body = None
        if body and body.startswith(b"PK"): raw = body; break
    idx = None
    if raw is not None:
        try: idx = h.get(f"https://nsearchives.nseindia.com/content/indices/ind_close_all_{d:%d%m%Y}.csv")
        except Exception: idx = None
    return d, raw, idx
pool = ThreadPoolExecutor(4)
for n, (d, raw, idxbody) in enumerate(pool.map(fetch, todo), 1):
    mon = d.strftime("%b").upper()
    if raw is None:
        db.execute("INSERT OR REPLACE INTO done VALUES (?,0)", (d.isoformat(),)); db.commit(); continue
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        rd = csv.DictReader(io.StringIO(z.read(z.namelist()[0]).decode("utf-8", "replace")))
        out = []
        for r in rd:
            if "TckrSymb" in r:
                sym, ser = r["TckrSymb"].strip(), r["SctySrs"].strip()
                vals = (r["OpnPric"], r["HghPric"], r["LwPric"], r["ClsPric"], r["PrvsClsgPric"], r["TtlTradgVol"])
            else:
                sym, ser = r["SYMBOL"].strip(), r["SERIES"].strip()
                vals = (r["OPEN"], r["HIGH"], r["LOW"], r["CLOSE"], r["PREVCLOSE"], r["TOTTRDQTY"])
            sym = aliases.resolve(sym, d.isoformat(), ALIAS)
            if sym in UNIVERSE and ser in ("EQ", "BE"):          # BE = trade-for-trade, e.g. during surveillance
                out.append((ser, d.isoformat(), sym, *[f(v) for v in vals]))
    out.sort(key=lambda r: r[0] == "EQ")                         # EQ wins if a stock has both on one day
    db.executemany("INSERT OR REPLACE INTO px VALUES (?,?,?,?,?,?,?,?)", [r[1:] for r in out])
    try:
        body = idxbody
        if body and not body.startswith(b"<"):
            ir = [(d.isoformat(), r["Index Name"].strip(), f(r["Open Index Value"]), f(r["High Index Value"]), f(r["Low Index Value"]),
                   f(r["Closing Index Value"]), f(r.get("P/E")), f(r.get("P/B"))) for r in csv.DictReader(io.StringIO(body.decode("utf-8", "replace")))]
            db.executemany("INSERT OR REPLACE INTO idx VALUES (?,?,?,?,?,?,?,?)", ir)
    except Exception as e:
        print(d, "index file failed", e, flush=True)
    db.execute("INSERT OR REPLACE INTO done VALUES (?,1)", (d.isoformat(),)); db.commit()
    if n % 50 == 0: print(f"{n}/{len(todo)} {d}", flush=True)
print("done", flush=True)
