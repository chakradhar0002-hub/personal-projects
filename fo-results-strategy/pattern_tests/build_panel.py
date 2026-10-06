"""Event panel for pattern tests: daily excess returns (vs Nifty 50) from 10 sessions before to 20 after the
reaction day, reaction-day open/close, and the ATM short straddle held across the numbers (exact NSE prices,
missing exit legs fetched from the F&O bhavcopy).

    python3 build_panel.py DATA OUT.csv        (DATA = the report_builder data folder)
"""
import csv, io, json, sys, zipfile
from datetime import datetime
from pathlib import Path

RB = Path(__file__).resolve().parents[1] / "report_builder"
DATA, OUT = sys.argv[1], sys.argv[2]
sys.argv = [sys.argv[0], DATA]
__file__ = str(RB / "analyze_events.py")
exec(open(RB / "analyze_events.py").read().split("# ---------------------------------------------------------------- financials")[0])
from fo_results_strategy.realdata import Http, bhavcopy_urls

ev = json.load(open(f"{DATA}/report/events.json"))
QORDER = [q for _, q, _ in QUARTERS]
K = range(-10, 21)


def nifty_day(i):
    return index_ret("Nifty 50", i - 1, i)


def straddle_legs(e):
    """(entry day, exit day, expiry, strike, entry premium, spot) for the ATM straddle sold at the last close before the numbers."""
    if not e.get("opt_expiry"):
        return None
    R = SPOS[e["reaction_day"]]
    P = R - 1
    ch, spot = chain(e["symbol"], sess(P))
    if not ch or not spot:
        return None
    k = atm(ch, spot, e["opt_expiry"])
    if not k:
        return None
    prem = ch[(e["opt_expiry"], k)]["CE"][0] + ch[(e["opt_expiry"], k)]["PE"][0]
    return sess(P), sess(R), e["opt_expiry"], k, prem, spot


# ---- fetch exit legs that fell outside the stored +-5% strike band (big moves) so they are not dropped
needs = {}
for e in ev:
    s = straddle_legs(e)
    if not s:
        continue
    _, exit_day, exp, k, _, _ = s
    ch_r, _ = chain(e["symbol"], exit_day)
    for kind in ("CE", "PE"):
        if leg_price(ch_r, exp, k, kind) is None:
            needs.setdefault(exit_day, set()).add((e["symbol"], exp, k))
print("exit days to re-read:", len(needs), "legs:", sum(len(v) for v in needs.values()), flush=True)
added = 0
for day in sorted(needs):
    raw = None
    for url in bhavcopy_urls(datetime.strptime(day, "%Y-%m-%d").date()):
        try:
            body = Http(pause=0.05).get(url)
        except Exception:
            body = None
        if body and body.startswith(b"PK"):
            raw = body
            break
    if raw is None:
        continue
    want = needs[day]
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        rd = csv.DictReader(io.StringIO(z.read(z.namelist()[0]).decode("utf-8", "replace")))
        for r in rd:
            if "TckrSymb" in r:
                if r["FinInstrmTp"] != "STO":
                    continue
                key = (r["TckrSymb"].strip(), r["XpryDt"].strip(), float(r["StrkPric"]))
                vals = (r["OptnTp"].strip(), float(r["ClsPric"] or 0), float(r["SttlmPric"] or 0), float(r["TtlTradgVol"] or 0))
            else:
                if r["INSTRUMENT"].strip() != "OPTSTK":
                    continue
                key = (r["SYMBOL"].strip(), datetime.strptime(r["EXPIRY_DT"].strip(), "%d-%b-%Y").date().isoformat(),
                       float(r["STRIKE_PR"]))
                vals = (r["OPTION_TYP"].strip(), float(r["CLOSE"] or 0), float(r["SETTLE_PR"] or 0), float(r["CONTRACTS"] or 0))
            if key in want:
                row = (day, key[0], key[1], vals[0], key[2], vals[1], vals[2], vals[3])
                if not op.execute("SELECT 1 FROM q WHERE day=? AND symbol=? AND expiry=? AND kind=? AND strike=?", row[:5]).fetchone():
                    op.execute("INSERT INTO q VALUES (?,?,?,?,?,?,?,?)", row)
                    added += 1
    op.commit()
print("legs added:", added, flush=True)

# ---- panel
cols = None
with open(OUT, "w", newline="") as fh:
    w = None
    for e in ev:
        R = SPOS[e["reaction_day"]]
        row = {"symbol": e["symbol"], "quarter": e["quarter"], "qn": QORDER.index(e["quarter"]), "results_date": e["results_date"],
               "reaction_day": e["reaction_day"], "R": R}
        for k in K:
            i = R + k
            if i >= len(SESSIONS):
                row[f"x{k}"] = None
                continue
            s, n = daily_ret(e["symbol"], sess(i)), nifty_day(i)
            row[f"x{k}"] = s - n if s is not None and n is not None else None
        bar = stock[e["symbol"]].get(sess(R))
        nb = indexes["Nifty 50"].get(sess(R))
        n_open = px.execute("SELECT open FROM idx WHERE name='Nifty 50' AND day=?", (sess(R),)).fetchone()
        if bar and bar[0] and bar[3] and n_open and n_open[0] and nb and not CA.get((e["symbol"], sess(R))):
            row["oc"] = bar[3] / bar[0] - 1
            row["nifty_oc"] = nb[0] / n_open[0] - 1
        s = straddle_legs(e)
        if s:
            entry_day, exit_day, exp, k, prem, spot = s
            ch_r, spot_r = chain(e["symbol"], exit_day)
            ce, pe = leg_price(ch_r, exp, k, "CE"), leg_price(ch_r, exp, k, "PE")
            row.update(st_prem=prem, st_spot=spot, st_strike=k)
            if ce is not None and pe is not None:
                lot = LOTS.get(e["symbol"])
                cost = SLIP * (prem + ce + pe) + (4 * BROKERAGE / lot if lot else 0)
                row["short_straddle"] = (prem - (ce + pe) - cost) / prem       # return on premium collected
        if w is None:
            cols = list(row) + ["oc", "nifty_oc", "st_prem", "st_spot", "st_strike", "short_straddle"]
            cols = list(dict.fromkeys(cols))
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
        w.writerow(row)
print("panel rows:", len(ev), flush=True)
