"""Fetch NSE F&O bhavcopies for the ENTRY days (and, in pass 2, the EXIT days) of DISCOVERY (qn<=13) winners only.
Keeps STO/STF rows for the needed symbols (+ their old tickers) and NIFTY index futures in a local sqlite cache.
No price for any qn>=14 trade is fetched; every fetched day is asserted <= 2024-10-31."""
import csv, io, sqlite3, sys, zipfile
from datetime import date, datetime
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
sys.path.insert(0, __import__('os').environ.get('REPO_ROOT', '.'))  # this repo
from fo_results_strategy.realdata import Http, bhavcopy_urls

SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = f"{SP}/more_avg/search_instrument"
LAST_DAY = "2024-10-31"

f = pd.read_csv(f"{SP}/tafa/C_post_results/features.csv")
w = f[(f.qn <= 13) & (f.XN > 4)].copy()
assert w.qn.max() <= 13
ses = pd.read_csv(f"{SP}/sector_lab/data/sessions.csv")
i2day = dict(zip(ses.i, ses.day))

# old tickers for renamed symbols
alias = {}
for r in csv.reader(open(f"{SP}/symbolchange.csv", encoding="latin-1")):
    if len(r) >= 4:
        alias.setdefault(r[2].strip(), []).append(r[1].strip())
syms = set(w.symbol)
want = set(syms)
for s in list(syms):
    stack = [s]
    while stack:
        x = stack.pop()
        for o in alias.get(x, []):
            if o not in want:
                want.add(o); stack.append(o)

db = sqlite3.connect(f"{OUT}/bhav_cache.db")
db.executescript("""CREATE TABLE IF NOT EXISTS done(day TEXT PRIMARY KEY, ok INTEGER);
CREATE TABLE IF NOT EXISTS opt(day TEXT, symbol TEXT, expiry TEXT, kind TEXT, strike REAL, close REAL, settle REAL, volume REAL);
CREATE TABLE IF NOT EXISTS fut(day TEXT, symbol TEXT, expiry TEXT, close REAL, settle REAL, volume REAL, und REAL);
CREATE INDEX IF NOT EXISTS oi ON opt(symbol, day, expiry);
CREATE INDEX IF NOT EXISTS fi ON fut(symbol, day, expiry);""")


def fetch(day):
    h = Http(pause=0.05)
    for url in bhavcopy_urls(date.fromisoformat(day)):
        try:
            body = h.get(url)
        except Exception:
            body = None
        if body and body.startswith(b"PK"):
            return day, body
    return day, None


def parse(day, raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        text = z.read(z.namelist()[0]).decode("utf-8", "replace")
    rd = csv.DictReader(io.StringIO(text))
    udiff = "TckrSymb" in rd.fieldnames
    o, fu = [], []
    for r in rd:
        if udiff:
            tp, sym = r["FinInstrmTp"].strip(), r["TckrSymb"].strip()
            if tp not in ("STO", "STF", "IDF"):
                continue
            if tp == "IDF" and sym != "NIFTY":
                continue
            if tp != "IDF" and sym not in want:
                continue
            exp = r["XpryDt"].strip()
            c, s, v = float(r["ClsPric"] or 0), float(r["SttlmPric"] or 0), float(r["TtlTradgVol"] or 0)
            und = float(r["UndrlygPric"] or 0) if r.get("UndrlygPric") else None
            if tp == "STO":
                o.append((day, sym, exp, r["OptnTp"].strip(), float(r["StrkPric"]), c, s, v))
            else:
                fu.append((day, sym, exp, c, s, v, und))
        else:
            ins, sym = r["INSTRUMENT"].strip(), r["SYMBOL"].strip()
            if ins not in ("OPTSTK", "FUTSTK", "FUTIDX"):
                continue
            if ins == "FUTIDX" and sym != "NIFTY":
                continue
            if ins != "FUTIDX" and sym not in want:
                continue
            exp = datetime.strptime(r["EXPIRY_DT"].strip(), "%d-%b-%Y").date().isoformat()
            c, s, v = float(r["CLOSE"] or 0), float(r["SETTLE_PR"] or 0), float(r["CONTRACTS"] or 0)
            if ins == "OPTSTK":
                o.append((day, sym, exp, r["OPTION_TYP"].strip(), float(r["STRIKE_PR"]), c, s, v))
            else:
                fu.append((day, sym, exp, c, s, v, None))
    return o, fu


def run(days):
    have = {r[0] for r in db.execute("SELECT day FROM done WHERE ok=1")}
    todo = sorted(d for d in days if d not in have)
    assert all(d <= LAST_DAY for d in todo), "would fetch a day past the discovery window"
    print("to fetch", len(todo), "of", len(days), flush=True)
    n = 0
    with ThreadPoolExecutor(4) as pool:
        for day, raw in pool.map(fetch, todo):
            n += 1
            if raw is None:
                db.execute("INSERT OR REPLACE INTO done VALUES (?,0)", (day,)); db.commit()
                print(day, "MISSING", flush=True); continue
            o, fu = parse(day, raw)
            db.executemany("INSERT INTO opt VALUES (?,?,?,?,?,?,?,?)", o)
            db.executemany("INSERT INTO fut VALUES (?,?,?,?,?,?,?)", fu)
            db.execute("INSERT OR REPLACE INTO done VALUES (?,1)", (day,)); db.commit()
            if n % 20 == 0:
                print(n, day, len(o), len(fu), flush=True)


if __name__ == "__main__":
    which = sys.argv[1]
    if which == "entry":
        run(set(w.reaction_day))
    elif which == "exit":
        need = pd.read_csv(f"{OUT}/exit_days_needed.csv")
        run(set(need.day))
