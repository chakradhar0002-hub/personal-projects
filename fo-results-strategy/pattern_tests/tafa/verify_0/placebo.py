"""VERIFIER placebo: the same TA (os>=3) and FA (good_fund, point-in-time at the placebo day) on NON-results F&O
stock-days that pass the lag rule (lag < -10, vol >= 1.0). Outcome = sum of the next 3 daily returns (same as three_day).
Non-results = more than 10 sessions from any of the stock's cutoff..Day+1 windows. in_fo of a day = in_fo of the
stock's next event. Rebuilt from rebuilt_daily.pkl / rebuilt_fin.pkl (no panel)."""
import os  # LAB_ROOT: scratch folder with ta/, fa/, report/, sector_lab/data; REPO_ROOT: this repo
import numpy as np, pandas as pd
from datetime import date
SCR = os.environ.get('LAB_ROOT', 'lab') + ""
OUT = f"{SCR}/tafa/verify_0"
SL = f"{SCR}/sector_lab/data"
rng = np.random.default_rng(5)
DA = pd.read_pickle(f"{OUT}/rebuilt_daily.pkl")
FI = pd.read_pickle(f"{OUT}/rebuilt_fin.pkl")
BC = {tuple(k.split("|")): date.fromisoformat(v) for k, v in FI["BCAST"].items()}
REC = {tuple(k.split("|")): v for k, v in FI["REC"].items()}
FLAG = FI["FLAG"]
SES = pd.read_csv(f"{SL}/sessions.csv")["day"].tolist()
NIF = pd.read_csv(f"{SL}/index_close.csv", usecols=["day", "Nifty 50"]).set_index("day")["Nifty 50"].reindex(SES).to_numpy()
EV = pd.read_csv(f"{SL}/events.csv")
i0 = int(EV.i_cut.min()) - 5
i1 = int(EV.i_p1.max())


def qshift(qend, n):
    y, m = int(qend[:4]), int(qend[5:7])
    m -= 3 * n
    while m <= 0:
        m += 12; y -= 1
    return "%d-%02d-%d" % (y, m, {3: 31, 6: 30, 9: 30, 12: 31}[m])


def fa(sym, Q, day):
    cutd = date.fromisoformat(day)
    L = [qshift(Q, k) for k in range(1, 6)]
    ok = [BC.get((sym, q)) is not None and BC[(sym, q)] < cutd for q in L]
    pref = "Non-Consolidated" if FLAG.get(sym) == "B" else "Consolidated"
    alt = "Consolidated" if pref == "Non-Consolidated" else "Non-Consolidated"
    loss = np.nan
    for b in (pref, alt):
        rs = [REC.get((sym, q, b)) for q in L[:4]]
        if all(ok[:4]) and all(r and r["pat"] is not None for r in rs):
            loss = int(any(r["pat"] < 0 for r in rs)); break
    else:
        known = [REC.get((sym, q, pref)) for q, o_ in zip(L[:4], ok[:4]) if o_]
        loss = 1 if any(r and r["pat"] is not None and r["pat"] < 0 for r in known) else np.nan
    g = {}
    for fld in ("sales", "pat"):
        g[fld] = np.nan
        if ok[0] and ok[4]:
            for b in (pref, alt):
                a, z = REC.get((sym, L[0], b)), REC.get((sym, L[4], b))
                if a and z and a[fld] is not None and z[fld] is not None:
                    g[fld] = 100 * (a[fld] / z[fld] - 1) if z[fld] > 0 else np.nan
                    break
    good = loss == 0 and g["sales"] > 0 and g["pat"] > 0
    bad = loss == 1 or g["sales"] <= 0 or g["pat"] <= 0
    return 1 if good else (0 if bad else -1)


rows = []
for sym, df in DA.items():
    ev = EV[EV.symbol == sym].sort_values("i_cut")
    if ev.empty:
        continue
    block = np.zeros(len(SES) + 30, bool)
    for r in ev.itertuples():
        block[max(0, int(r.i_cut) - 10):int(r.i_p1) + 11] = True
    ret = pd.Series(df.ret.to_numpy(), index=df.i.to_numpy()).reindex(range(len(SES))).to_numpy()
    lr = np.log1p(np.nan_to_num(ret))
    cum = np.concatenate([[0], np.cumsum(lr)])
    d = df[(df.i >= i0) & (df.i <= i1 - 3)].copy()
    d = d[~block[d.i.to_numpy()]]
    if d.empty:
        continue
    ii = d.i.to_numpy()
    s21 = np.exp(cum[ii + 1] - cum[ii - 20]) - 1
    d["lag"] = 100 * (s21 - (NIF[ii] / NIF[ii - 21] - 1))
    d["vol"] = d.vol5 / d.vol60
    d = d[(d.lag < -10) & (d.vol >= 1.0)]
    if d.empty:
        continue
    ii = d.i.to_numpy()
    fwd = np.stack([ret[ii + k] for k in (1, 2, 3)], 1)
    d["fwd3"] = 100 * np.nansum(fwd, 1)
    d = d[~np.isnan(fwd).any(1)]
    cuts = ev.i_cut.to_numpy()
    for r in d.itertuples():
        j = np.searchsorted(cuts, r.i)
        if j >= len(cuts):
            continue
        e = ev.iloc[j]
        if e.in_fo != True:
            continue
        rows.append({"symbol": sym, "day": r.day, "i": r.i, "lag": r.lag, "vol": r.vol, "fwd3": r.fwd3,
                     "os": int((r.rsi14 < 30) + (r.rsi2 < 10) + (r.stochk < 20) + (r.pctb < 0) + (r.cci < -100) + (r.mfi < 20)),
                     "gf": fa(sym, e.quarter_end, r.day)})
P = pd.DataFrame(rows)
P["month"] = P.day.str[:7]
P.to_csv(f"{OUT}/placebo_rows.csv", index=False)
print("placebo lag+vol non-results F&O days:", len(P), "stocks", P.symbol.nunique(), "months", P.month.nunique())


def D_and_ci(P, lab, name):
    k = lab >= 0
    t, f = P[k & (lab == 1)], P[k & (lab == 0)]
    D = t.fwd3.mean() - f.fwd3.mean()
    months = P.month.unique()
    g = {m: x for m, x in P[k].assign(lab=lab[k]).groupby("month")}
    bs = []
    for _ in range(2000):
        pick = rng.choice(months, len(months))
        z = pd.concat([g[m] for m in pick if m in g])
        bs.append(z[z.lab == 1].fwd3.mean() - z[z.lab == 0].fwd3.mean())
    bs = np.array(bs)
    print(f"{name:42s} yes n {len(t):5d} mean {t.fwd3.mean():6.2f} | no n {len(f):5d} mean {f.fwd3.mean():6.2f} | "
          f"D {D:6.2f}  month-boot se {np.nanstd(bs):.2f}  90% CI {np.nanpercentile(bs, 5):.2f}..{np.nanpercentile(bs, 95):.2f}")
    return D, np.nanstd(bs)


lab_os = (P.os >= 3).astype(int).to_numpy()
lab_gf = P.gf.to_numpy()
lab_x8 = np.where(lab_gf == -1, -1, ((lab_gf == 1) & (lab_os == 1)).astype(int))
print("all placebo days mean fwd3", round(P.fwd3.mean(), 2))
D_os, se_os = D_and_ci(P, lab_os, "TA part os>=3 (all placebo days)")
D_gf, se_gf = D_and_ci(P, lab_gf, "FA part good_fund")
D_x8, se_x8 = D_and_ci(P, lab_x8, "X8 pair (good_fund & os>=3)")
gfP = P[P.gf == 1]
D_osg, se_osg = D_and_ci(gfP, (gfP.os >= 3).astype(int).to_numpy(), "os>=3 within good_fund days")
hv = P[P.vol >= 1.3]
D_x8h, _ = D_and_ci(hv, np.where(hv.gf == -1, -1, ((hv.gf == 1) & (hv.os >= 3)).astype(int)), "X8 pair, vol >= 1.3 days")
# events: D_event for X8 = 2.42 (null sd from the permutation ~1.3)
D_ev, sd_null = 2.42, None
print("\nEvent D (X8) 2.42 vs placebo D_x8", round(D_x8, 2), "-> excess", round(2.42 - D_x8, 2))
# one-trade-per-stock-per-month placebo version (less overlap)
P1 = P.sort_values("day").groupby(["symbol", "month"]).head(1)
lab1 = np.where(P1.gf == -1, -1, ((P1.gf == 1) & (P1.os >= 3)).astype(int))
D_and_ci(P1, lab1, "X8 pair, first day per stock-month")
