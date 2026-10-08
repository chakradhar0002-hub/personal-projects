"""Independent point-in-time market cap for the lag10+volume trades (and all in_fo results), from the filings db.

Shares: latest quarterly filing among Q-1, Q-2 (Q = reported quarter) whose own results were PUBLISHED strictly before
the cutoff (results_date from events.json of that earlier quarter), paid-up capital / face value, scaled to the cutoff
with NSE bonus/split factors. Two variants: (a) analyze_events.checked_shares (median-checked), (b) raw filing count
with our own sanity: EPS-implied count (PAT/EPS) when it disagrees by > 2x.
Price: raw NSE close on the cutoff day. Nifty 50 close on the cutoff day from the same price db.
Output: mcap_pit.csv (symbol, quarter, cutoff, mcap_a, mcap_b, nifty, shares source, filing quarter, filing date).
"""
import os  # LAB_ROOT: scratch folder with report/, search22/, sector_lab/data, fa/; REPO_ROOT: this repo
import csv, json, sys
from pathlib import Path

DATA = os.environ.get('LAB_ROOT', 'lab') + ""
HERE = Path(__file__).resolve().parent
RB = Path(os.environ.get('REPO_ROOT', '.') + "/report_builder")
sys.argv = [sys.argv[0], DATA]
__file__ = str(RB / "analyze_events.py")
exec(open(RB / "analyze_events.py").read().split("# ---------------------------------------------------------------- results date and time")[0])

ev = json.load(open(f"{DATA}/report/events.json"))
RD = {(r["symbol"], r["quarter_end"]): r.get("results_date") for r in ev}
QE = {q: qe for qe, q, _ in QUARTERS}
QN = {q: i for i, (_, q, _) in enumerate(QUARTERS)}
# fallback publication date (quarters before the event set): earliest NSE filing broadcast for that quarter
for sym_, to_, bc_ in fn.execute("SELECT symbol, to_date, broadcast FROM filings"):
    qq, tt = nse_date(to_), nse_dt(bc_)
    if qq and tt:
        k_ = (sym_, qq.isoformat())
        if k_ not in RD or RD[k_] is None:
            RD[k_] = tt.date().isoformat()
        elif k_ in RD and RD.get(("_fb",) + k_) is None:
            pass

import pandas as pd
sl = pd.read_csv(f"{DATA}/sector_lab/data/events.csv", usecols=["symbol", "quarter", "cutoff", "in_fo", "three_day"])
rows = []
for r in sl.itertuples(index=False):
    sym, q, cut = r.symbol, r.quarter, r.cutoff
    qe = QE[q]
    price = stock.get(sym, {}).get(cut)
    price = price[3] if price else None
    nif = indexes["Nifty 50"].get(cut, (None,))[0]
    rec = {"symbol": sym, "quarter": q, "qn": QN[q], "cutoff": cut, "price": price, "nifty": nif}
    for k in (1, 2):
        lq = qshift(qe, k)
        rd = RD.get((sym, lq))
        f = fin_q(sym, lq)
        if f is None or not rd or rd >= cut:
            continue
        sa, fixed = checked_shares(sym, lq)
        sb = filing_shares(f)
        m = share_multiplier(sym, lq, cut)
        rec.update({"filing_q": lq, "filing_pub": rd, "lag": k, "shares_fixed": fixed,
                    "mcap_a": price * sa * m / CR if price and sa else None,
                    "mcap_b": price * sb * m / CR if price and sb else None})
        break
    rows.append(rec)
out = pd.DataFrame(rows)
out.to_csv(HERE / "mcap_pit.csv", index=False)
print(out.describe().T)
print("lag dist", out.lag.value_counts(dropna=False).to_dict())
