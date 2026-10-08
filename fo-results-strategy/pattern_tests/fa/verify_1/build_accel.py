"""Independent rebuild of 'sales YoY growth accelerating' (L1 sales YoY > L2 sales YoY) for every in_fo result,
straight from nse_fin.db via analyze_events.py's fin_q (NOT the fa_panel). Point-in-time: L1 and L2 must be published
strictly before the cutoff (results_date from events.json; otherwise earliest NSE broadcast; quarters before 2021
without either = published, they are > 1 year old by the earliest cutoff for L5/L6 and checked for L1/L2).

    python3 build_accel.py   -> accel_mine.csv
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.environ.get('LAB_ROOT', 'lab') + ""
RB = os.environ.get('REPO_ROOT', '.') + "/report_builder"
sys.argv = [sys.argv[0], SCR]
__file__ = f"{RB}/analyze_events.py"
exec(open(__file__).read().split("# ---------------------------------------------------------------- results date and time")[0])
import pandas as pd
import numpy as np

ev = json.load(open(f"{SCR}/report/events.json"))
RD = {(r["symbol"], r["quarter_end"]): r["results_date"] for r in ev}
BC = {}
for sym, to, b, bk, bc in fn.execute("SELECT symbol, to_date, basis, bank, broadcast FROM filings"):
    q, t = nse_date(to), nse_dt(bc)
    if q and t:
        k = (sym, q.isoformat())
        BC[k] = min(BC.get(k, t.date()), t.date())


def pub(sym, q):
    if (sym, q) in RD:
        return RD[(sym, q)], "results_date"
    if (sym, q) in BC:
        return BC[(sym, q)].isoformat(), "broadcast"
    return None, "none"


E = pd.read_csv(f"{SCR}/sector_lab/data/events.csv")
E = E[(E.in_fo == True) & E.three_day.notna()].reset_index(drop=True)
rows = []
for r in E.itertuples():
    sym, qe, cut = r.symbol, r.quarter_end, r.cutoff
    L = {k: qshift(qe, k) for k in (1, 2, 5, 6)}
    f = {k: fin_q(sym, L[k]) for k in L}
    s = {k: (f[k]["sales"] if f[k] else None) for k in L}
    b = {k: (f[k]["basis"] if f[k] else None) for k in L}
    p1, src1 = pub(sym, L[1])
    p2, src2 = pub(sym, L[2])
    pit_ok = (p1 is None or p1 < cut) and (p2 is None or p2 < cut)
    pit_strict = (p1 is not None and p1 < cut) and (p2 is not None and p2 < cut)
    def g(a, c):
        return 100 * (s[a] / s[c] - 1) if s[a] and s[c] and s[c] > 0 and s[a] > 0 else None
    y1, y2 = g(1, 5), g(2, 6)
    rows.append({"symbol": sym, "quarter": r.quarter, "qn": r.qn, "cutoff": cut, "fin_type": r.fin_type,
                 "industry": r.industry, "three_day": 100 * r.three_day,
                 "ret_dm1": r.ret_dm1, "ret_rd": r.ret_rd, "ret_dp1": r.ret_dp1,
                 "s1": s[1], "s2": s[2], "s5": s[5], "s6": s[6],
                 "same_basis": len({b[k] for k in L}) == 1 and b[1] is not None, "basis1": b[1],
                 "y1": y1, "y2": y2, "accel": (y1 - y2) if y1 is not None and y2 is not None else None,
                 "l1_pub": p1, "l1_src": src1, "l2_pub": p2, "l2_src": src2, "pit_ok": pit_ok,
                 "pit_strict": pit_strict})
D = pd.DataFrame(rows)
# take-profit as defined in the task
dm1, rd, dp1 = D.ret_dm1, D.ret_rd, D.ret_dp1
D["tp3"] = 100 * np.where(dm1 > 0.03, dm1, np.where(dm1 + rd > 0.03, dm1 + rd, dm1 + rd + dp1))
D.to_csv(f"{HERE}/accel_mine.csv", index=False)
print(len(D), "in_fo results;", D.accel.notna().sum(), "with accel;", (~D.pit_ok).sum(), "pit violations (L1/L2 after cutoff)")
print(D.l1_src.value_counts().to_dict(), D.l2_src.value_counts().to_dict())
