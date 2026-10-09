#!/usr/bin/env python3
"""Independent rebuild (verifier) of the candidate "plain winner & GOOD reported numbers & RSI(14) > 50 at the cutoff,
hold 20 sessions" from RAW data - no TA / FA panel, no candidate code.

Raw inputs (read-only):
  report/nse_prices.db (px, idx, ca) and report/nse_fin.db via report_builder/analyze_events.py helpers
  (daily_ret = corporate-action-safe close/prevclose; fin_q = one filing's numbers), loaded the way fa/build/helpers.py
  does (exec of the first, definitions-only part of analyze_events.py).
  sector_lab/data/events.csv only for the event calendar (symbol, qn, quarter_end, results_date, timing, i_cut,
  i_react, in_fo).
Outputs (this folder): raw_events.csv (one row per in_fo event: features + outcomes), raw_daily.npz (adjusted returns,
  RSI matrix for the placebo).
Definitions (fixed before looking at any outcome, same textbook values as the candidate's pre-registration):
  RSI(14) Wilder (seed = simple mean of the first 14 gains / losses, then alpha 1/14) on the stock's own traded days,
     price = cumulative product of daily_ret (split / bonus safe), value at the cutoff session (last traded day <= cut).
  XN = daily_ret(reaction day) - Nifty 50 return that day, percent. Winner = XN > 4.
  GOOD = (PAT YoY > 25% and sales YoY > 15%) or margin change YoY > +2 pp (EBITDA margin for companies, net margin for
     banks / NBFCs), reported quarter Q vs Q-4 from fin_q (positive base only for growth).
  Outcome: entry close k = reaction day, exit close k+H, stock = compounded daily_ret (blank = 0), Nifty close ratio,
     tradable if k+21 exists and <= 2 blank daily returns in k+1..k+21.
"""
import os  # LAB_ROOT: scratch folder with ta/, fa/, report/, sector_lab/data; REPO_ROOT: this repo
import sys
import numpy as np
import pandas as pd

SP = os.environ.get('LAB_ROOT', 'lab') + ""
OUT = f"{SP}/tafa/verify_1"
RB = os.environ.get('REPO_ROOT', '.') + "/report_builder"
_argv = sys.argv
sys.argv = [_argv[0], SP]
G = {"__file__": f"{RB}/analyze_events.py", "__name__": "ae_helpers"}
exec(open(f"{RB}/analyze_events.py").read().split(
    "# ---------------------------------------------------------------- results date and time")[0], G)
sys.argv = _argv
SESSIONS, daily_ret, fin_q, stock, STOCK_DAYS = G["SESSIONS"], G["daily_ret"], G["fin_q"], G["stock"], G["STOCK_DAYS"]
indexes = G["indexes"]

ses = pd.read_csv(f"{SP}/sector_lab/data/sessions.csv")
assert ses.day.tolist() == SESSIONS[:len(ses)], "session calendars differ"
T = len(SESSIONS)
NIFTY = np.array([indexes["Nifty 50"][s][0] for s in SESSIONS], float)

ev = pd.read_csv(f"{SP}/sector_lab/data/events.csv")
syms = sorted(ev.symbol.unique())
SYM = {s: j for j, s in enumerate(syms)}
N = len(syms)

# adjusted daily returns on the full session grid (NaN = no trade / unknown)
R = np.full((T, N), np.nan)
TRADED = np.zeros((T, N), bool)
SPOS = {s: i for i, s in enumerate(SESSIONS)}
for s in syms:
    j = SYM[s]
    for day in STOCK_DAYS.get(s, []):
        i = SPOS.get(day)
        if i is None:
            continue
        TRADED[i, j] = True
        r = daily_ret(s, day)
        if r is not None:
            R[i, j] = r


def wilder_rsi(c, n=14):
    d = np.diff(c)
    out = np.full(len(c), np.nan)
    if len(d) < n:
        return out
    g, l_ = np.clip(d, 0, None), np.clip(-d, 0, None)
    ag, al = g[:n].mean(), l_[:n].mean()
    vals = [ag, al]

    def f(ag, al):
        if al == 0:
            return 100.0 if ag > 0 else 50.0
        return 100 - 100 / (1 + ag / al)
    out[n] = f(ag, al)
    for t in range(n, len(d)):
        ag = ag + (g[t] - ag) / n
        al = al + (l_[t] - al) / n
        out[t + 1] = f(ag, al)
    return out


RSI = np.full((T, N), np.nan)
for s in syms:
    j = SYM[s]
    rows = np.flatnonzero(TRADED[:, j])
    if len(rows) < 16:
        continue
    r = np.nan_to_num(R[rows, j])
    r[0] = 0.0
    c = np.cumprod(1 + r)
    RSI[rows, j] = wilder_rsi(c)
# forward-fill RSI on non-traded sessions with the last traded value (value "as of" the session)
RSI_ff = pd.DataFrame(RSI).ffill().to_numpy()
np.savez_compressed(f"{OUT}/raw_daily.npz", R=R, TRADED=TRADED, RSI=RSI, NIFTY=NIFTY, syms=np.array(syms))


def growth(a, b):
    return a / b - 1 if a is not None and b is not None and b > 0 else None



# ---- one-basis fundamentals (never mix bases): preferred basis if it has Q and Q-4, else the other basis if it has both
import json as _json
FINB = {"Consolidated": {}, "Non-Consolidated": {}}
for sym_, to_, basis_, bank_, x_, data_ in G["fn"].execute("SELECT * FROM fin"):
    q_ = G["nse_date"](to_)
    if q_ and basis_ in FINB:
        FINB[basis_][(sym_, q_.isoformat())] = (basis_, G["FLAG"].get(sym_, bank_), _json.loads(data_))
FIN_ORIG = G["FIN"]


def fin_q_b(sym, q, basis):
    G["FIN"] = FINB[basis]
    try:
        return G["fin_q"](sym, q)
    finally:
        G["FIN"] = FIN_ORIG


def fund_one_basis(sym, qend):
    pref = "Non-Consolidated" if G["FLAG"].get(sym) == "B" else "Consolidated"
    alt = "Consolidated" if pref == "Non-Consolidated" else "Non-Consolidated"
    q4 = G["qshift"](qend, 4)
    out = {}
    for fld in ("pat", "sales"):
        for b in (pref, alt):
            a0, a4 = fin_q_b(sym, qend, b), fin_q_b(sym, q4, b)
            if a0 and a4 and a0.get(fld) is not None and a4.get(fld) is not None:
                out[fld + "_yoy_1b"] = growth(a0[fld], a4[fld])
                break
    for b in (pref, alt):
        a0, a4 = fin_q_b(sym, qend, b), fin_q_b(sym, q4, b)
        if a0 and a4 and a0.get("sales") and a4.get("sales"):
            ft = "Bank" if a0["bank"] else ("NBFC / financial" if a0["nbfc"] else "Company")
            mf = "ebitda" if ft == "Company" else "pat"
            if a0.get(mf) is not None and a4.get(mf) is not None:
                out["mchg_pp_1b"] = (a0[mf] / a0["sales"] - a4[mf] / a4["sales"]) * 100
            break
    return out

rows = []
for e in ev[ev.in_fo == True].itertuples(index=False):
    j = SYM[e.symbol]
    k, ic = int(e.i_react), int(e.i_cut)
    o = dict(symbol=e.symbol, qn=int(e.qn), quarter=e.quarter, quarter_end=e.quarter_end, results_date=e.results_date,
             timing=e.timing, i_cut=ic, i_react=k, fin_type_ev=e.fin_type)
    o["rsi_cut"] = RSI_ff[ic, j]
    o["rsi_cut_traded"] = bool(TRADED[ic, j])
    o["rsi_react_m1"] = RSI_ff[k - 1, j]            # last close before the reaction (not used by the rule)
    nr = NIFTY[k] / NIFTY[k - 1] - 1
    o["XN"] = (R[k, j] - nr) * 100 if np.isfinite(R[k, j]) else np.nan
    # outcomes
    ok = k + 21 <= T - 1
    if ok:
        blanks = int((~np.isfinite(R[k + 1:k + 22, j])).sum())
        ok = blanks <= 2
    o["tradable"] = ok
    if ok:
        path = np.cumprod(1 + np.nan_to_num(R[k + 1:k + 31 if k + 31 <= T else T, j])) - 1
        npath = NIFTY[k + 1:k + 1 + len(path)] / NIFTY[k] - 1
        for H in (5, 10, 15, 20, 30):
            if H <= len(path):
                o[f"raw_H{H}"] = path[H - 1] * 100
                o[f"nif_H{H}"] = npath[H - 1] * 100
        hp = (path[:20] - npath[:20]) * 100
        hit = np.flatnonzero(hp > 3)
        o["tp_hedged_H20"] = hp[hit[0]] if len(hit) else hp[19]
    # fundamentals of the reported quarter (public at the results announcement)
    f0, f4 = fin_q(e.symbol, e.quarter_end), fin_q(e.symbol, G["qshift"](e.quarter_end, 4))
    if f0:
        ft = "Bank" if f0["bank"] else ("NBFC / financial" if f0["nbfc"] else "Company")
        o["fin_type"] = ft
        o["pat_yoy"] = None if not f4 else growth(f0["pat"], f4["pat"])
        o["sales_yoy"] = None if not f4 else growth(f0["sales"], f4["sales"])
        mfld = "ebitda" if ft == "Company" else "pat"
        m0 = f0[mfld] / f0["sales"] if f0.get(mfld) is not None and f0.get("sales") else None
        m4 = f4[mfld] / f4["sales"] if f4 and f4.get(mfld) is not None and f4.get("sales") else None
        o["mchg_pp"] = (m0 - m4) * 100 if m0 is not None and m4 is not None else None
        o["basis0"], o["basis4"] = f0["basis"], (f4["basis"] if f4 else None)
    o.update(fund_one_basis(e.symbol, e.quarter_end))
    rows.append(o)
df = pd.DataFrame(rows)
for c in ("pat_yoy", "sales_yoy", "pat_yoy_1b", "sales_yoy_1b"):
    df[c] = pd.to_numeric(df[c]) * 100
df["mchg_pp"] = pd.to_numeric(df["mchg_pp"])
df["mchg_pp_1b"] = pd.to_numeric(df["mchg_pp_1b"])
df.to_csv(f"{OUT}/raw_events.csv", index=False, float_format="%.6g")
print("events in_fo", len(df), "tradable", int(df.tradable.sum()), "rsi known", int(df.rsi_cut.notna().sum()),
      "pat_yoy known", int(df.pat_yoy.notna().sum()), "mchg known", int(df.mchg_pp.notna().sum()))
