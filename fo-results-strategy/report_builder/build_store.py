"""Download the NSE F&O bhavcopy for every session in 15 results-season windows and keep a compact
option store (2 nearest expiries, strikes within +-5% of spot) in sqlite."""
import csv, io, sqlite3, sys, zipfile
from datetime import date, datetime, timedelta
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from fo_results_strategy.realdata import Http, bhavcopy_urls
from fo_results_strategy.pricing import implied_vol

SP = sys.argv[1]
SEASONS = [("Q3 FY23", "2023-01-05", "2023-02-16"), ("Q4 FY23", "2023-04-05", "2023-05-31"),
           ("Q1 FY24", "2023-07-05", "2023-08-16"), ("Q2 FY24", "2023-10-05", "2023-11-16"),
           ("Q3 FY24", "2024-01-05", "2024-02-16"), ("Q4 FY24", "2024-04-05", "2024-05-31"),
           ("Q1 FY25", "2024-07-05", "2024-08-16"), ("Q2 FY25", "2024-10-05", "2024-11-16"),
           ("Q3 FY25", "2025-01-05", "2025-02-16"), ("Q4 FY25", "2025-04-05", "2025-05-31"),
           ("Q1 FY26", "2025-07-05", "2025-08-16"), ("Q2 FY26", "2025-10-05", "2025-11-16"),
           ("Q3 FY26", "2026-01-05", "2026-02-16"), ("Q4 FY26", "2026-04-05", "2026-05-31"),
           ("Q1 FY27", "2026-07-05", "2026-08-16")]
rows = list(csv.reader(open(f"{SP}/fo_mktlots.csv")))
UNIVERSE = {r[1].strip() for r in rows[1:] if len(r) > 2 and r[2].strip().isdigit() and "NIFTY" not in r[1]}
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
import aliases
ALIAS = aliases.load(SP, UNIVERSE)      # old symbol -> (today's symbol, rename day)
days = set()
for _, a, b in SEASONS:
    d, end = date.fromisoformat(a) - timedelta(days=12), date.fromisoformat(b) + timedelta(days=6)
    while d <= end:
        days.add(d)          # weekends too (Budget day and special sessions); days with no file are skipped
        d += timedelta(days=1)
db = sqlite3.connect(f"{SP}/report/options.db")
db.executescript("""CREATE TABLE IF NOT EXISTS done(day TEXT PRIMARY KEY, ok INTEGER);
CREATE TABLE IF NOT EXISTS spot(day TEXT, symbol TEXT, spot REAL, PRIMARY KEY(day, symbol));
CREATE TABLE IF NOT EXISTS q(day TEXT, symbol TEXT, expiry TEXT, kind TEXT, strike REAL, close REAL, settle REAL, volume REAL);
CREATE INDEX IF NOT EXISTS qi ON q(symbol, day, expiry);""")
have = {r[0] for r in db.execute("SELECT day FROM done WHERE ok = 1")}
none = {r[0] for r in db.execute("SELECT day FROM done WHERE ok = 0")}
# "--aliases": re-read stored days and add only the rows of renamed stocks under their old symbols
ALIAS_ONLY = "--aliases" in sys.argv
last_rename = max((v[1] for v in ALIAS.values() if v[1] < "2099"), default="")
todo = sorted(d for d in days if d.isoformat() not in none and
              ((ALIAS_ONLY and d.isoformat() in have and d.isoformat() < last_rename) or d.isoformat() not in have))
print("sessions to fetch:", len(todo), "of", len(days), "(aliases only)" if ALIAS_ONLY else "", flush=True)


def download(d):
    h = Http(pause=0.05)
    for url in bhavcopy_urls(d):
        try:
            body = h.get(url)
        except Exception as e:
            print(d, "error", e, flush=True); body = None
        if body and body.startswith(b"PK"):
            return d, body
    return d, None


from concurrent.futures import ThreadPoolExecutor
pool = ThreadPoolExecutor(4)
for n, (d, raw) in enumerate(pool.map(download, todo), 1):
    alias_only = d.isoformat() in have
    if raw is None:
        if not alias_only:
            db.execute("INSERT OR REPLACE INTO done VALUES (?, 0)", (d.isoformat(),)); db.commit()
        continue
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        text = z.read(z.namelist()[0]).decode("utf-8", "replace")
    rd = csv.DictReader(io.StringIO(text))
    udiff = "TckrSymb" in rd.fieldnames
    opts, spot = {}, {}
    for r in rd:
        if udiff:
            tp, raw_sym = r["FinInstrmTp"], r["TckrSymb"].strip()
            sym = aliases.resolve(raw_sym, d.isoformat(), ALIAS)
            if sym not in UNIVERSE or tp != "STO" or (alias_only and sym == raw_sym): continue
            exp, kind, k = r["XpryDt"].strip(), r["OptnTp"].strip(), float(r["StrkPric"])
            c, s, v = float(r["ClsPric"] or 0), float(r["SttlmPric"] or 0), float(r["TtlTradgVol"] or 0)
            if r.get("UndrlygPric"): spot.setdefault(sym, float(r["UndrlygPric"]))
        else:
            if r["INSTRUMENT"].strip() != "OPTSTK": continue
            raw_sym = r["SYMBOL"].strip()
            sym = aliases.resolve(raw_sym, d.isoformat(), ALIAS)
            if sym not in UNIVERSE or (alias_only and sym == raw_sym): continue
            exp = datetime.strptime(r["EXPIRY_DT"].strip(), "%d-%b-%Y").date().isoformat()
            kind, k = r["OPTION_TYP"].strip(), float(r["STRIKE_PR"])
            c, s, v = float(r["CLOSE"] or 0), float(r["SETTLE_PR"] or 0), float(r["CONTRACTS"] or 0)
        opts.setdefault(sym, []).append((exp, kind, k, c, s, v))
    out_q, out_s = [], []
    for sym, lst in opts.items():
        exps = sorted({x[0] for x in lst if x[0] >= d.isoformat()})[:2]
        sp = spot.get(sym)
        if sp is None:   # put-call parity on the nearest expiry, median over traded strikes
            by = {}
            for e, kind, k, c, s, v in lst:
                if exps and e == exps[0] and v > 0 and c > 0: by.setdefault(k, {})[kind] = c
            est = sorted(v["CE"] - v["PE"] + k for k, v in by.items() if len(v) == 2)
            sp = est[len(est) // 2] if len(est) >= 3 else None
        if not sp: continue
        out_s.append((d.isoformat(), sym, sp))
        for e, kind, k, c, s, v in lst:
            if e in exps and abs(k / sp - 1) <= 0.05:
                out_q.append((d.isoformat(), sym, e, kind, k, c, s, v))
    db.executemany("INSERT OR REPLACE INTO spot VALUES (?,?,?)", out_s)
    db.executemany("DELETE FROM q WHERE day = ? AND symbol = ?", [x[:2] for x in out_s])     # re-runs replace, not duplicate
    db.executemany("INSERT INTO q VALUES (?,?,?,?,?,?,?,?)", out_q)
    db.execute("INSERT OR REPLACE INTO done VALUES (?, 1)", (d.isoformat(),)); db.commit()
    if n % 25 == 0: print(f"{n}/{len(todo)} {d}", flush=True)
print("done", flush=True)
