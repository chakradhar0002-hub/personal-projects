"""VERIFIER rebuild (independent of the TA/FA panels).
Raw inputs only: report/nse_prices.db (px, ca, idx via sector_lab index_close), report/nse_fin.db (fin, filings),
sector_lab/data (sessions, events, returns, index_close). Writes verify_0/rebuilt_events.csv (all in_fo events) and
verify_0/rebuilt_daily.pkl (per-symbol adjusted series + indicators, for the placebo).

TA (textbook, computed on the stock's own trading days, split/bonus back-adjusted, at the cutoff close):
  RSI14 / RSI2 Wilder; Stochastic %K14 (raw, unsmoothed); Bollinger %B (20, 2 sd, population sd);
  CCI20 (0.015 x mean abs deviation of typical price); MFI14 (typical-price money flow).
  os3 = >= 3 of {RSI14<30, RSI2<10, %K<20, %B<0, CCI<-100, MFI<20}.
  lag = 21-session stock return (compounded adjusted daily returns, session grid) - Nifty 50 21-session return, x100.
  vol = mean adj volume of last 5 trading days / of last 60 (incl. the 5).
FA (point-in-time; a quarter counts only if published strictly before the cutoff date; publication = earliest of the
  XBRL broadcast date in `filings` / xbrl file stamp and the event's results_date for that quarter):
  basis: Non-Consolidated preferred for banks (flag B), Consolidated otherwise; quarters L1..L5 must share one basis
  (preferred first, else alternate). Sales = InterestEarned (banks) / RevenueFromOperations; PAT = owners' profit
  (bank: PAT after minority tags). loss4 = any of L1..L4 PAT < 0; sales_yoy = L1/L5-1, pat_yoy = L1/L5-1 (L5>0).
  good_fund = no loss in L1..L4 AND sales_yoy>0 AND pat_yoy>0; False if any known part fails; else unknown.
  Mis-scale guard: a filing whose sales is a power of 10 (>=10x) off the median of the stock's other quarters (same
  basis) is dropped; PAT > 500 x sales dropped.
"""
import os  # LAB_ROOT: scratch folder with ta/, fa/, report/, sector_lab/data; REPO_ROOT: this repo
import json, re, sqlite3, math
from datetime import date, datetime
from collections import defaultdict
import numpy as np, pandas as pd

SCR = os.environ.get('LAB_ROOT', 'lab') + ""
OUT = f"{SCR}/tafa/verify_0"
SL = f"{SCR}/sector_lab/data"
SES = pd.read_csv(f"{SL}/sessions.csv")["day"].tolist()
SPOS = {d: i for i, d in enumerate(SES)}
EV = pd.read_csv(f"{SL}/events.csv")
NIF = pd.read_csv(f"{SL}/index_close.csv", usecols=["day", "Nifty 50"]).set_index("day")["Nifty 50"].reindex(SES).to_numpy()

# ------------------------------------------------------------------ prices
px = sqlite3.connect(f"{SCR}/report/nse_prices.db")
P = pd.read_sql("select * from px", px)
CA = pd.read_sql("select * from ca", px)
cafac = defaultdict(lambda: 1.0); cakind = {}
for r in CA.itertuples():
    if r.factor and r.factor == r.factor:
        cafac[(r.symbol, r.ex_date)] *= r.factor
    cakind.setdefault((r.symbol, r.ex_date), set()).add(r.kind)
P = P.sort_values(["symbol", "day"])
P = P[P.day.isin(SPOS)]
weird = []
DAILY = {}
for sym, g in P.groupby("symbol", sort=False):
    g = g.reset_index(drop=True)
    c, pc = g.close.to_numpy(float), g.prevclose.to_numpy(float)
    ratio = np.full(len(g), 1.0)        # price adjustment factor applied at day t to all EARLIER prices
    ret = np.full(len(g), np.nan)
    for t in range(len(g)):
        if t == 0 or not pc[t]:
            continue
        rr = pc[t] / c[t - 1]
        key = (sym, g.day[t])
        if key in cakind:
            f = cafac[key] if key in cafac else None
            if abs(rr - 1) > 0.01:                      # NSE already adjusted prevclose
                ratio[t] = rr
                ret[t] = c[t] / pc[t] - 1
            elif f:                                     # unadjusted prevclose: use the CA factor
                ratio[t] = 1 / f
                ret[t] = c[t] * f / pc[t] - 1
            else:                                       # demerger with unadjusted prevclose: unknown
                ret[t] = np.nan
        else:
            ret[t] = c[t] / pc[t] - 1
            if abs(rr - 1) > 0.05:
                weird.append((sym, g.day[t], rr))
                ratio[t] = rr                           # treat as an unannounced adjustment
    cum = np.cumprod(ratio[::-1])[::-1]                 # product of ratios at t..end
    adj = np.append(cum[1:], 1.0)                       # factor for prices of day t = prod ratios after t
    df = pd.DataFrame({"day": g.day, "i": g.day.map(SPOS), "o": g.open * adj, "h": g.high * adj, "l": g.low * adj,
                       "c": g.close * adj, "v": g.volume / adj, "ret": ret})
    DAILY[sym] = df
print("prices: symbols", len(DAILY), "; non-CA prevclose jumps > 5% treated as adjustments:", len(weird))
for w in weird[:15]:
    print("   ", w)

# check vs returns.csv
R = pd.read_csv(f"{SL}/returns.csv").set_index("day")
diffs = []
for sym, df in DAILY.items():
    if sym in R.columns:
        x = R[sym].reindex(df.day).to_numpy()
        m = ~np.isnan(x) & ~np.isnan(df.ret.to_numpy())
        diffs.append(np.abs(x[m] - df.ret.to_numpy()[m]))
diffs = np.concatenate(diffs)
print(f"daily returns vs returns.csv: n {len(diffs)}, max abs diff {diffs.max():.2e}, share > 1e-4 {np.mean(diffs > 1e-4):.5f}")


def wilder_rsi(c, n):
    d = np.diff(c, prepend=np.nan)
    up, dn = np.where(d > 0, d, 0.0), np.where(d < 0, -d, 0.0)
    out = np.full(len(c), np.nan)
    if len(c) <= n:
        return out
    au, ad = up[1:n + 1].mean(), dn[1:n + 1].mean()
    out[n] = 100 if ad == 0 else 100 - 100 / (1 + au / ad)
    for t in range(n + 1, len(c)):
        au = (au * (n - 1) + up[t]) / n
        ad = (ad * (n - 1) + dn[t]) / n
        out[t] = 100 if ad == 0 else 100 - 100 / (1 + au / ad)
    return out


def indicators(df):
    c, h, l, v = df.c.to_numpy(), df.h.to_numpy(), df.l.to_numpy(), df.v.to_numpy()
    s = pd.Series
    o = {}
    o["rsi14"] = wilder_rsi(c, 14)
    o["rsi2"] = wilder_rsi(c, 2)
    hh, ll = s(h).rolling(14).max().to_numpy(), s(l).rolling(14).min().to_numpy()
    o["stochk"] = 100 * (c - ll) / (hh - ll)
    ma, sd = s(c).rolling(20).mean().to_numpy(), s(c).rolling(20).std(ddof=0).to_numpy()
    sd1 = s(c).rolling(20).std(ddof=1).to_numpy()
    o["pctb"] = (c - (ma - 2 * sd)) / (4 * sd)
    o["pctb_s1"] = (c - (ma - 2 * sd1)) / (4 * sd1)
    o["pctb_25"] = (c - (ma - 2.5 * sd)) / (5 * sd)     # neighbours: 2.5 sd and 1.5 sd lower band
    o["pctb_15"] = (c - (ma - 1.5 * sd)) / (3 * sd)
    tp = (h + l + c) / 3
    tma = s(tp).rolling(20).mean().to_numpy()
    md = s(tp).rolling(20).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True).to_numpy()
    o["cci"] = (tp - tma) / (0.015 * md)
    mf = tp * v
    dtp = np.diff(tp, prepend=np.nan)
    pos, neg = np.where(dtp > 0, mf, 0.0), np.where(dtp < 0, mf, 0.0)
    ps, ns = s(pos).rolling(14).sum().to_numpy(), s(neg).rolling(14).sum().to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        o["mfi"] = np.where(ns == 0, 100.0, 100 - 100 / (1 + ps / ns))
    o["vol5"] = s(v).rolling(5).mean().to_numpy()
    o["vol60"] = s(v).rolling(60).mean().to_numpy()
    return pd.DataFrame(o, index=df.index)


for sym in list(DAILY):
    DAILY[sym] = pd.concat([DAILY[sym], indicators(DAILY[sym])], axis=1)

# session-grid returns matrix for lag and outcomes
RET = {sym: pd.Series(df.ret.to_numpy(), index=df.i.to_numpy()) for sym, df in DAILY.items()}


def comp(sym, i0, i1):
    """compounded return close i0 -> close i1 on the session grid (missing days count as 0)."""
    s = RET[sym]
    x = s.reindex(range(i0 + 1, i1 + 1)).to_numpy()
    if np.isnan(x).sum() > 0.2 * (i1 - i0):
        return np.nan
    return np.prod(1 + np.nan_to_num(x)) - 1


# ------------------------------------------------------------------ fundamentals
fn = sqlite3.connect(f"{SCR}/report/nse_fin.db")
FLAG = dict(fn.execute("select symbol, bank from filings"))
BCAST = {}
for sym, to, basis, bank, bc, x, ind, co in fn.execute("select * from filings"):
    try:
        q = datetime.strptime(to, "%d-%b-%Y").date().isoformat()
    except Exception:
        continue
    dt = None
    for fmt in ("%d-%b-%Y %H:%M:%S", "%d-%b-%Y %H:%M"):
        try:
            dt = datetime.strptime(bc, fmt).date(); break
        except Exception:
            pass
    m = re.search(r"_(\d{14})(?:_WEB)?\.xml$", x or "")
    xd = None
    if m:
        try:
            xd = datetime.strptime(m.group(1), "%d%m%Y%H%M%S").date()
        except ValueError:
            pass
    cands = [z for z in (dt, xd) if z]
    if cands:
        k = (sym, q)
        BCAST[k] = min(cands + ([BCAST[k]] if k in BCAST else []))
for r in EV.itertuples():
    BCAST[(r.symbol, r.quarter_end)] = date.fromisoformat(r.results_date)   # an event quarter: the results date


def v(data, tags, ctx="OneD"):
    for t in tags:
        x = data.get(t, {}).get(ctx)
        if x is not None:
            return x
    return None


REC = {}
for sym, to, basis, bank, x, data in fn.execute("select * from fin"):
    try:
        q = datetime.strptime(to, "%d-%b-%Y").date().isoformat()
    except Exception:
        continue
    dd = json.loads(data)
    flag = FLAG.get(sym, bank)
    if flag == "B":
        sales = v(dd, ["InterestEarned"])
        pat = v(dd, ["ProfitLossAfterTaxesMinorityInterestAndShareOfProfitLossOfAssociates", "ProfitLossForThePeriod",
                     "ProfitLossForPeriod"])
    else:
        sales = v(dd, ["RevenueFromOperations"])
        own, tot = v(dd, ["ProfitOrLossAttributableToOwnersOfParent"]), v(dd, ["ProfitLossForPeriod"])
        pat = tot if (own is None or (tot and (own == 0 or abs(own) < 0.25 * abs(tot)))) else own
    sales = sales / 1e7 if sales else None
    pat = pat / 1e7 if pat is not None else None
    if pat is not None and sales and abs(pat) > 500 * abs(sales):
        pat = None
    REC[(sym, q, basis)] = {"sales": sales, "pat": pat}
# mis-scale: sales off the stock's same-basis median by a power of ten
bys = defaultdict(list)
for (s, q, b), r in REC.items():
    if r["sales"]:
        bys[(s, b)].append(r["sales"])
MISSCALED = []
for (s, q, b), r in REC.items():
    lst = bys[(s, b)]
    if r["sales"] and len(lst) >= 4:
        lg = math.log10(r["sales"] / np.median(lst))
        if abs(lg) >= 0.8 and abs(lg - round(lg)) < 0.2:
            MISSCALED.append((s, q, b, round(lg)))
            r["sales"] = r["pat"] = None
print("mis-scaled filings dropped:", len(MISSCALED), MISSCALED[:10])


def qshift(qend, n):
    y, m = int(qend[:4]), int(qend[5:7])
    m -= 3 * n
    while m <= 0:
        m += 12; y -= 1
    return f"{y}-{m:02d}-{ {3: 31, 6: 30, 9: 30, 12: 31}[m] }".replace(" ", "")


def fa(sym, Q, cut):
    cutd = date.fromisoformat(cut)
    L = [qshift(Q, k) for k in range(1, 6)]
    pub = [BCAST.get((sym, q)) for q in L]
    ok = [p is not None and p < cutd for p in pub]
    pref = "Non-Consolidated" if FLAG.get(sym) == "B" else "Consolidated"
    alt = "Consolidated" if pref == "Non-Consolidated" else "Non-Consolidated"
    out = {"l1_pub": pub[0].isoformat() if pub[0] else None, "l1_ok": ok[0]}
    # loss in L1..L4: one basis with all 4 pat, published
    loss = None
    for b in (pref, alt):
        rs = [REC.get((sym, q, b)) for q in L[:4]]
        if all(ok[:4]) and all(r and r["pat"] is not None for r in rs):
            loss = int(any(r["pat"] < 0 for r in rs)); out["basis4"] = b; break
    if loss is None:
        known = [REC.get((sym, q, pref)) for q, o_ in zip(L[:4], ok[:4]) if o_]
        loss = 1 if any(r and r["pat"] is not None and r["pat"] < 0 for r in known) else np.nan
    out["loss4"] = loss
    for fld in ("sales", "pat"):
        g = np.nan
        if ok[0] and ok[4]:
            for b in (pref, alt):
                a, z = REC.get((sym, L[0], b)), REC.get((sym, L[4], b))
                if a and z and a[fld] is not None and z[fld] is not None:
                    g = 100 * (a[fld] / z[fld] - 1) if z[fld] > 0 else np.nan
                    out[f"{fld}_l1"], out[f"{fld}_l5"], out[f"{fld}_basis"] = a[fld], z[fld], b
                    break
        out[f"{fld}_yoy"] = g
    return out


# ------------------------------------------------------------------ events
rows = []
E = EV[EV.in_fo == True]
for r in E.itertuples():
    sym = r.symbol
    o = {"symbol": sym, "quarter": r.quarter, "qn": r.qn, "cutoff": r.cutoff, "quarter_end": r.quarter_end,
         "fin_type": r.fin_type}
    df = DAILY.get(sym)
    ic = int(r.i_cut)
    if df is not None:
        j = np.searchsorted(df.i.to_numpy(), ic, side="right") - 1
        if j >= 0 and df.i.iat[j] == ic:
            for k in ("rsi14", "rsi2", "stochk", "pctb", "pctb_s1", "pctb_25", "pctb_15", "cci", "mfi"):
                o[k] = df[k].iat[j]
            o["vol"] = df.vol5.iat[j] / df.vol60.iat[j]
        o["lag"] = 100 * (comp(sym, ic - 21, ic) - (NIF[ic] / NIF[ic - 21] - 1))
        dr = [RET[sym].get(int(i), np.nan) for i in (r.i_m1, r.i_rd, r.i_p1)]
        o["d1"], o["d2"], o["d3"] = [100 * x for x in dr]
        o["three_day"] = 100 * sum(dr)
    o.update(fa(sym, r.quarter_end, r.cutoff))
    rows.append(o)
X = pd.DataFrame(rows)
d1, d2 = X.d1, X.d1 + X.d2
X["tp3"] = np.where(X.d1 > 3, X.d1, np.where(d2 > 3, d2, X.three_day))
X.to_csv(f"{OUT}/rebuilt_events.csv", index=False)
pd.to_pickle({s: df[["day", "i", "c", "ret", "rsi14", "rsi2", "stochk", "pctb", "cci", "mfi", "vol5", "vol60"]]
              for s, df in DAILY.items()}, f"{OUT}/rebuilt_daily.pkl")
pd.to_pickle({"BCAST": {f"{k[0]}|{k[1]}": v_.isoformat() for k, v_ in BCAST.items()},
              "REC": {f"{k[0]}|{k[1]}|{k[2]}": v_ for k, v_ in REC.items()}, "FLAG": FLAG}, f"{OUT}/rebuilt_fin.pkl")
print("in_fo events", len(X), "three_day known", X.three_day.notna().sum())
