"""Robustness diagnostics for the finalists (no selection is made from these). Discovery qn<=13 only."""
import math, sqlite3, importlib.util
import numpy as np, pandas as pd

SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = f"{SP}/more_avg/search_instrument"
T = pd.read_csv(f"{OUT}/discovery_trades.csv")
p = pd.read_csv(f"{OUT}/plan.csv")
assert T.qn.max() <= 13 and p.qn.max() <= 13
cache = sqlite3.connect(f"file:{OUT}/bhav_cache.db?mode=ro", uri=True)
idx = pd.read_csv(f"{SP}/sector_lab/data/index_close.csv", index_col=0)["Nifty 50"]
ses = pd.read_csv(f"{SP}/sector_lab/data/sessions.csv"); i2day = dict(zip(ses.i, ses.day))


def wo_best(x, n=5):
    x = np.sort(np.asarray(x)); return x[:-n].mean()


def ncdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def bs_call(S, K, t, v, r=0.065):
    if v <= 0 or t <= 0:
        return max(S - K, 0)
    d1 = (math.log(S / K) + (r + v * v / 2) * t) / (v * math.sqrt(t)); d2 = d1 - v * math.sqrt(t)
    return S * ncdf(d1) - K * math.exp(-r * t) * ncdf(d2)


def iv_delta(S, K, t, P, r=0.065):
    lo, hi = 1e-3, 5.0
    if P <= bs_call(S, K, t, lo, r):
        v = lo
    else:
        for _ in range(100):
            mid = (lo + hi) / 2
            if bs_call(S, K, t, mid, r) > P: hi = mid
            else: lo = mid
        v = (lo + hi) / 2
    d1 = (math.log(S / K) + (r + v * v / 2) * t) / (v * math.sqrt(t))
    return v, ncdf(d1)


def q(sym, day, exps, K):
    for e in exps:
        x = cache.execute("SELECT close, settle, volume FROM opt WHERE symbol=? AND day=? AND expiry=? AND kind='CE' AND strike=?",
                          (sym, day, e, K)).fetchone()
        if x: return x
    return None


lines = []
def out(s=""):
    print(s); lines.append(s)


for cand in ["C10 OPT_ATM_WR50_LIQ (added after)", "C11 OPT_OTM5_WR50_LIQ (added after)", "C1 OPT_ATM_WR50", "C9 OPT_ITM5_WR50"]:
    s = T[(T.cand == cand) & (T.why == "ok")].merge(
        p[["symbol", "quarter", "spot", "ticker", "expiry", "exp_session_day", "i_react", "i_exit", "i_exp"]], on=["symbol", "quarter"])
    r = s.ret.values
    out(f"\n=== {cand}: n={len(s)} avg={r.mean():.2f} median={np.median(r):.2f} wo_best5={wo_best(r):.2f} hit={(r>0).mean()*100:.0f}%")
    top5 = np.sort(r)[-5:].sum() / r.sum() * 100
    out(f"  best-5 trades = {top5:.0f}% of total profit; trades losing >=50%: {(r<=-50).mean()*100:.0f}%; losing >=90%: {(r<=-90).mean()*100:.0f}%")
    # by year
    s["yr"] = s.reaction_day.str[:4]
    by = s.groupby("yr").ret.agg(["count", "mean", "sum"])
    by["share_of_profit_%"] = by["sum"] / s.ret.sum() * 100
    out("  by year:\n" + by.round(1).to_string())
    out(f"  without 2023: n={int((s.yr!='2023').sum())} avg={s[s.yr!='2023'].ret.mean():.2f} wo_best5={wo_best(s[s.yr!='2023'].ret):.2f}")
    pq = s.groupby("qn").ret.agg(["count", "mean"]).round(1)
    out("  per quarter (qn: n, mean): " + "; ".join(f"{i}: {int(a)}, {b:+.0f}" for i, (a, b) in pq.iterrows()))
    # cost doubling
    extra = 1.0 + 0.05 * s.spot / s.P
    r2 = s.ret - extra
    out(f"  costs doubled (2% premium + 0.10% notional): avg={r2.mean():.2f} wo_best5={wo_best(r2):.2f}")
    # pessimistic quote bracket: entry = max(close, settle) on k, exit (non-expiry) = min(close, settle)
    pes = []; stale = 0
    for t in s.itertuples():
        e = q(t.ticker, t.reaction_day, [t.expiry], t.K)
        Pe = max(e[0], e[1]) if e[1] > 0 else e[0]
        if e[1] > 0 and abs(e[0] / e[1] - 1) > 0.10: stale += 1
        if t.exit_how == "expiry_intrinsic":
            X = t.X
        else:
            x = q(t.ticker, t.exit_day, [t.expiry, t.exp_session_day], t.K)
            X = min(v for v in (x[0], x[1]) if v > 0) if x else t.X
        pes.append((X / Pe - 1) * 100 - 1.0 - 0.05 * t.spot / Pe)
    pes = np.array(pes)
    out(f"  entry close vs settle differ >10% on k: {stale}/{len(s)} trades")
    out(f"  pessimistic quotes (entry=max(close,settle), exit=min(close,settle)): avg={pes.mean():.2f} wo_best5={wo_best(pes):.2f} median={np.median(pes):.2f}")
    # market-drift decomposition: Nifty return over the option's holding window, and BS-delta Nifty hedge (beta=1)
    nr = np.array([(idx.loc[i2day[b]] / idx.loc[i2day[a]] - 1) * 100 for a, b in zip(s.i_react, s.i_exit)])
    dl = []
    for t in s.itertuples():
        tt = (t.i_exp - t.i_react) / 250.0
        v, d = iv_delta(t.spot, t.K, tt, t.P)
        dl.append((v, d))
    iv = np.array([x[0] for x in dl]); de = np.array([x[1] for x in dl])
    hedged = s.ret.values - de * (s.spot.values / s.P.values) * nr
    out(f"  entry IV median {np.median(iv)*100:.0f}%, BS delta median {np.median(de):.2f}, effective leverage (delta*S/P) median {np.median(de*s.spot/s.P):.1f}x")
    out(f"  Nifty over holding window: avg {nr.mean():+.2f}%; trades with Nifty down: n={int((nr<0).sum())} option avg={s.ret[nr<0].mean():.2f}; Nifty up: n={int((nr>=0).sum())} option avg={s.ret[nr>=0].mean():.2f}")
    out(f"  approx Nifty-hedged (short delta*S of Nifty per option, beta 1, hedge margin ignored): avg={hedged.mean():.2f} wo_best5={wo_best(hedged):.2f} median={np.median(hedged):.2f}")
    sr = r.mean() / r.std(ddof=1)
    out(f"  per-trade mean/sd = {sr:.3f} (cash baseline WR50 vsN on all 122 discovery trades: 0.291; same trades cash vsN: "
        f"{s.vsN_net.mean()/s.vsN_net.std(ddof=1):.3f}; unhedged cash raw: {s.raw_net.mean()/s.raw_net.std(ddof=1):.3f})")

open(f"{OUT}/diagnostics.txt", "w").write("\n".join(lines) + "\n")
