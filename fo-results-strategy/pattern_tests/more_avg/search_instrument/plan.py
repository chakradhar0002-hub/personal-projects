"""Entry-side plan for discovery (qn<=13) winners: spot, expiry, strikes, entry quotes, exit day.
Uses only information available at the close of k (no outcome)."""
import bisect, csv, sqlite3
import numpy as np, pandas as pd

SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = f"{SP}/more_avg/search_instrument"
f = pd.read_csv(f"{SP}/tafa/C_post_results/features.csv")
w = f[(f.qn <= 13) & (f.XN > 4)].copy().reset_index(drop=True)
assert w.qn.max() <= 13
ses = pd.read_csv(f"{SP}/sector_lab/data/sessions.csv")
days = ses.day.tolist(); i2day = dict(zip(ses.i, ses.day)); day2i = dict(zip(ses.day, ses.i))

alias = {}
for r in csv.reader(open(f"{SP}/symbolchange.csv", encoding="latin-1")):
    if len(r) >= 4:
        alias.setdefault(r[2].strip(), []).append(r[1].strip())

cache = sqlite3.connect(f"file:{OUT}/bhav_cache.db?mode=ro", uri=True)
odb = sqlite3.connect(f"file:{SP}/report/options.db?mode=ro", uri=True)


def exp_session(e):
    """last session <= listed expiry date"""
    j = bisect.bisect_right(days, e) - 1
    return day2i[days[j]]


def ticker_on(sym, day):
    cands = [sym]
    stack = [sym]
    while stack:
        x = stack.pop()
        for o in alias.get(x, []):
            cands.append(o); stack.append(o)
    for t in cands:
        if cache.execute("SELECT 1 FROM opt WHERE symbol=? AND day=? LIMIT 1", (t, day)).fetchone():
            return t
    return None


def nearest(strikes, target):
    return min(strikes, key=lambda k: (abs(k - target), k))


rows = []
for r in w.itertuples():
    k = r.reaction_day; ik = r.i_react
    out = dict(symbol=r.symbol, quarter=r.quarter, qn=r.qn, reaction_day=k, i_react=ik, XN=r.XN,
               cut_rsi14=r.cut_rsi14, WR50=bool(r.cut_rsi14 > 50))
    t = ticker_on(r.symbol, k)
    out["ticker"] = t
    if t is None:
        out["status"] = "no_options_on_k"; rows.append(out); continue
    ch = pd.read_sql("SELECT expiry, kind, strike, close, settle, volume FROM opt WHERE symbol=? AND day=?",
                     cache, params=(t, k))
    # spot: options.db spot table (same ticker), else put-call parity on nearest expiry
    sp = odb.execute("SELECT spot FROM spot WHERE symbol=? AND day=?", (t, k)).fetchone()
    if sp is None and t != r.symbol:
        sp = odb.execute("SELECT spot FROM spot WHERE symbol=? AND day=?", (r.symbol, k)).fetchone()
    spot_src = "options.db"
    if sp is None:
        e0 = min(e for e in ch.expiry.unique() if e >= k)
        c0 = ch[(ch.expiry == e0) & (ch.volume > 0) & (ch.close > 0)]
        pv = c0.pivot_table(index="strike", columns="kind", values="close")
        est = sorted((pv.CE - pv.PE + pv.index).dropna().tolist()) if {"CE", "PE"} <= set(pv.columns) else []
        sp = (est[len(est) // 2],) if len(est) >= 3 else None
        spot_src = "parity"
    if sp is None:
        out["status"] = "no_spot"; rows.append(out); continue
    S = sp[0]; out["spot"] = S; out["spot_src"] = spot_src
    exps = sorted(e for e in ch.expiry.unique() if e >= k)
    ex = None
    for e in exps:
        if exp_session(e) - ik >= 15:
            ex = e; break
    if ex is None:
        out["status"] = "no_expiry"; rows.append(out); continue
    iexp = exp_session(ex)
    out.update(expiry=ex, i_exp=iexp, exp_session_day=i2day[iexp])
    iexit = min(ik + 20, iexp)
    out.update(i_exit=iexit, exit_day=i2day[iexit], exit_at_expiry=bool(iexit == iexp))
    ce = ch[(ch.expiry == ex) & (ch.kind == "CE")].set_index("strike").sort_index()
    strikes = ce.index.tolist()
    for lab, mult in (("ATM", 1.0), ("OTM5", 1.05), ("ITM5", 0.95)):
        K = nearest(strikes, S * mult)
        q = ce.loc[K]
        out[f"K_{lab}"] = K; out[f"P_{lab}"] = q.close; out[f"V_{lab}"] = q.volume; out[f"Set_{lab}"] = q.settle
    # futures (same expiry) + Nifty futures same expiry date, for diagnostic D4
    fu = cache.execute("SELECT close, settle, volume FROM fut WHERE symbol=? AND day=? AND expiry=?", (t, k, ex)).fetchone()
    nf = cache.execute("SELECT close, settle, volume FROM fut WHERE symbol='NIFTY' AND day=? AND expiry=?", (k, ex)).fetchone()
    out["F_entry"] = fu[0] if fu else np.nan; out["NF_entry"] = nf[0] if nf else np.nan
    out["status"] = "ok"
    rows.append(out)

p = pd.DataFrame(rows)
p.to_csv(f"{OUT}/plan.csv", index=False)
print(p.status.value_counts())
print(p.groupby("WR50").status.value_counts())
print("spot src", p.spot_src.value_counts().to_dict())
print("ticker != symbol:", (p.ticker.notna() & (p.ticker != p.symbol)).sum())
for lab in ("ATM", "OTM5", "ITM5"):
    print(lab, "zero-vol entry:", ((p.status == "ok") & ~(p[f"V_{lab}"] > 0)).sum(), " WR50:",
          ((p.status == "ok") & p.WR50 & ~(p[f"V_{lab}"] > 0)).sum(),
          " K/S median:", (p[f"K_{lab}"] / p.spot).median().round(4),
          " P/S median %:", (100 * p[f"P_{lab}"] / p.spot).median().round(2))
print("same K ATM==OTM5:", (p.K_ATM == p.K_OTM5).sum())
print("exit_at_expiry share:", p.exit_at_expiry.mean())
print("max exit day:", p.exit_day.max())
need = sorted(set(p.exit_day.dropna()))
pd.DataFrame({"day": need}).to_csv(f"{OUT}/exit_days_needed.csv", index=False)
print("exit days needed", len(need))
