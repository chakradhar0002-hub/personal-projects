"""Discovery-only (qn<=13) evaluation of candidates C1-C11 + baseline + diagnostics."""
import csv, sqlite3
import numpy as np, pandas as pd

SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = f"{SP}/more_avg/search_instrument"
p = pd.read_csv(f"{OUT}/plan.csv")
assert p.qn.max() <= 13
cache = sqlite3.connect(f"file:{OUT}/bhav_cache.db?mode=ro", uri=True)

alias = {}
for r in csv.reader(open(f"{SP}/symbolchange.csv", encoding="latin-1")):
    if len(r) >= 4:
        alias.setdefault(r[2].strip(), []).append(r[1].strip())


def tickers(sym):
    out, stack = [sym], [sym]
    while stack:
        x = stack.pop()
        for o in alias.get(x, []):
            out.append(o); stack.append(o)
    return out


# ------------------------------------------------------------------ cash baseline (qn<=13 rows only)
rets = pd.read_csv(f"{SP}/sector_lab/data/returns.csv", index_col=0)
idx = pd.read_csv(f"{SP}/sector_lab/data/index_close.csv", index_col=0)
ses = pd.read_csv(f"{SP}/sector_lab/data/sessions.csv")
i2day = dict(zip(ses.i, ses.day))
nifty = idx["Nifty 50"]
raw, vsn = [], []
for r in p.itertuples():
    k = r.i_react
    dd = [i2day[k + j] for j in range(1, 21)]
    sr = rets.loc[dd, r.symbol]
    assert sr.notna().all()
    g = float(np.prod(1 + sr.values) - 1)
    nr = float(nifty.loc[i2day[k + 20]] / nifty.loc[i2day[k]] - 1)
    raw.append(g * 100 - 0.17); vsn.append((g - nr) * 100 - 0.19)
p["raw_net"] = raw; p["vsN_net"] = vsn
# cross-check vs tafa trades.csv (qn<=13 rows only)
t = pd.read_csv(f"{SP}/tafa/C_post_results/trades.csv")
t = t[t.qn <= 13][["symbol", "quarter", "raw_H20", "nifty_H20"]]
chk = p.merge(t, on=["symbol", "quarter"], how="left")
d = (chk.raw_H20 - 0.17 - chk.raw_net).abs()   # trades.csv raw_H20 is already in percent
print("cross-check raw vs trades.csv: max abs diff", round(d.max(), 4), "missing", chk.raw_H20.isna().sum())


# ------------------------------------------------------------------ option legs
def quote(syms, day, exps, K, kind="CE"):
    for s in syms:
        for exp in exps:   # listed expiry, or the session it was moved to (holiday-shifted expiry)
            q = cache.execute("SELECT close, settle, volume FROM opt WHERE symbol=? AND day=? AND expiry=? AND kind=? AND strike=?",
                              (s, day, exp, kind, K)).fetchone()
            if q:
                return q
    return None


def chain(sym, day, exp):
    return pd.read_sql("SELECT strike, close, settle, volume FROM opt WHERE symbol=? AND day=? AND expiry=? AND kind='CE'",
                       cache, params=(sym, day, exp))


def fut(syms, day, exps):
    for s in syms:
        for exp in exps:
            q = cache.execute("SELECT close, settle, volume FROM fut WHERE symbol=? AND day=? AND expiry=?", (s, day, exp)).fetchone()
            if q:
                return q
    return None


SETTLE_CHECK = []


def exit_value(r, K):
    syms = tickers(r.symbol)
    if r.ticker not in syms:
        syms = [r.ticker] + syms
    exps = [r.expiry, r.exp_session_day]
    if r.exit_at_expiry:
        # On the expiry day NSE's option 'settle' column is the underlying final settlement price (verified:
        # identical to the stock-future settle). Option value at expiry = max(U - K, 0).
        fq = fut(syms, r.exit_day, exps)
        q = quote(syms, r.exit_day, exps, K)
        U = fq[1] if fq and fq[1] > 0 else (q[1] if q and q[1] > 0 else None)
        if fq and q and fq[1] > 0 and q[1] > 0:
            SETTLE_CHECK.append(abs(q[1] / fq[1] - 1))
        if U is None:
            return None, "exit_missing"
        return max(U - K, 0.0), "expiry_intrinsic"
    q = quote(syms, r.exit_day, exps, K)
    if q is None:
        return None, "exit_missing"
    c, s, v = q
    if v > 0 and c > 0:
        return c, "close"
    if s > 0:
        return s, "settle_fallback"
    return None, "exit_missing"


def pick_strike(r, lab, liq):
    K = getattr(r, f"K_{lab}"); P = getattr(r, f"P_{lab}"); V = getattr(r, f"V_{lab}")
    if V > 0 and P > 0:
        return K, P, "fixed"
    if not liq:
        return None, None, "entry_zero_volume"
    target = r.spot * {"ATM": 1.0, "OTM5": 1.05, "ITM5": 0.95}[lab]
    ch = chain(r.ticker, r.reaction_day, r.expiry)
    ch = ch[(ch.volume > 0) & (ch.close > 0) & ((ch.strike / target - 1).abs() <= 0.025)]
    if ch.empty:
        return None, None, "entry_zero_volume"
    ch = ch.assign(dist=(ch.strike - target).abs()).sort_values(["dist", "strike"])
    return float(ch.strike.iloc[0]), float(ch.close.iloc[0]), "liq_fallback"


def long_call(r, lab, liq=False):
    K, P, how = pick_strike(r, lab, liq)
    if K is None:
        return dict(ret=np.nan, why=how)
    X, ex = exit_value(r, K)
    if X is None:
        return dict(ret=np.nan, why=ex, K=K, P=P)
    ret = (X / P - 1) * 100 - 1.0 - 0.05 * r.spot / P
    return dict(ret=ret, why="ok", K=K, P=P, X=X, exit_how=ex, entry_how=how, prem_pct=100 * P / r.spot,
                gross=(X / P - 1) * 100)


def spread(r):
    a = long_call(r, "ATM"); o = long_call(r, "OTM5")
    if a["why"] != "ok" or o["why"] != "ok":
        return dict(ret=np.nan, why=a["why"] if a["why"] != "ok" else o["why"])
    if a["K"] == o["K"]:
        return dict(ret=np.nan, why="same_strike")
    D = a["P"] - o["P"]
    if D <= 0:
        return dict(ret=np.nan, why="nonpositive_debit")
    V = a["X"] - o["X"]
    cost = 0.01 * (a["P"] + o["P"]) + 0.0005 * r.spot * 2
    return dict(ret=((V - D) - cost) / D * 100, why="ok", prem_pct=100 * D / r.spot, exit_how=a["exit_how"])


CANDS = {
    "C1 OPT_ATM_WR50": ("WR50", lambda r: long_call(r, "ATM")),
    "C2 OPT_OTM5_WR50": ("WR50", lambda r: long_call(r, "OTM5")),
    "C3 OPT_ATM_WIN": ("WIN", lambda r: long_call(r, "ATM")),
    "C4 OPT_OTM5_WIN": ("WIN", lambda r: long_call(r, "OTM5")),
    "C5 SPREAD_WR50": ("WR50", spread),
    "C6 FUTH_WR50 (illustr.)": ("WR50", lambda r: dict(ret=r.vsN_net / 0.25, why="ok")),
    "C7 FUTH_WIN (illustr.)": ("WIN", lambda r: dict(ret=r.vsN_net / 0.25, why="ok")),
    "C8 FUTU_WR50 (illustr.)": ("WR50", lambda r: dict(ret=r.raw_net / 0.20, why="ok")),
    "C9 OPT_ITM5_WR50": ("WR50", lambda r: long_call(r, "ITM5")),
    "C10 OPT_ATM_WR50_LIQ (added after)": ("WR50", lambda r: long_call(r, "ATM", liq=True)),
    "C11 OPT_OTM5_WR50_LIQ (added after)": ("WR50", lambda r: long_call(r, "OTM5", liq=True)),
}
ELIGIBLE = {"C1", "C2", "C3", "C4", "C5", "C9", "C10", "C11"}

trades = []
for name, (sig, fn) in CANDS.items():
    sub = p[p.WR50] if sig == "WR50" else p
    for r in sub.itertuples():
        o = fn(r)
        o.update(cand=name, symbol=r.symbol, quarter=r.quarter, qn=r.qn, reaction_day=r.reaction_day,
                 exit_day=r.exit_day, exit_at_expiry=r.exit_at_expiry, raw_net=r.raw_net, vsN_net=r.vsN_net)
        trades.append(o)
T = pd.DataFrame(trades)
assert T.qn.max() <= 13
T.to_csv(f"{OUT}/discovery_trades.csv", index=False)


def wo_best(x, n=5):
    x = np.sort(np.asarray(x))
    return x[:-n].mean() if len(x) > n else np.nan


def stats(x, q):
    x = np.asarray(x); qq = pd.Series(x).groupby(np.asarray(q)).mean()
    return dict(n=len(x), avg=x.mean(), median=np.median(x), wo_best5=wo_best(x), hit=(x > 0).mean() * 100,
                sd=x.std(ddof=1), t=x.mean() / (x.std(ddof=1) / np.sqrt(len(x))), worst=x.min(), best=x.max(),
                loss50=(x <= -50).mean() * 100, q_with=len(qq), q_pos=int((qq > 0).sum()))


# baseline
base = p[p.WR50]
B = stats(base.vsN_net, base.qn)
print("\nBASELINE cash WR50 vsN_net discovery:", {k: round(v, 2) for k, v in B.items()})
plainB = stats(p.vsN_net, p.qn)
print("plain winners cash vsN_net discovery:", {k: round(v, 2) for k, v in plainB.items()})
bar = B["wo_best5"] + 0.5
print("bar for finalists (baseline wo_best5 + 0.5):", round(bar, 3))

rows = []
for name in CANDS:
    s = T[T.cand == name]
    ok = s[s.why == "ok"]
    st = stats(ok.ret, ok.qn)
    miss = s[s.why != "ok"].why.value_counts().to_dict()
    m = stats(ok.raw_net, ok.qn); mv = stats(ok.vsN_net, ok.qn)
    exits = ok.exit_how.value_counts().to_dict() if "exit_how" in ok else {}
    row = dict(candidate=name, signals=len(s), n=st["n"], coverage=100 * st["n"] / len(s), avg=st["avg"],
               median=st["median"], wo_best5=st["wo_best5"], hit=st["hit"], sd=st["sd"], t=st["t"], worst=st["worst"],
               best=st["best"], loss50=st["loss50"], q_with=st["q_with"], q_pos=st["q_pos"],
               prem_pct=ok.prem_pct.median() if "prem_pct" in ok and ok.prem_pct.notna().any() else np.nan,
               matched_cash_raw=m["avg"], matched_cash_vsN=mv["avg"], matched_cash_vsN_wo5=mv["wo_best5"],
               missing=str(miss), exits=str(exits))
    code = name.split()[0]
    row["eligible"] = code in ELIGIBLE
    row["passes"] = bool(row["eligible"] and st["n"] >= 35 and st["q_with"] >= 7 and row["coverage"] >= 80
                         and st["wo_best5"] >= bar)
    rows.append(row)
R = pd.DataFrame(rows)
R.to_csv(f"{OUT}/discovery_table.csv", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
print(R.drop(columns=["missing", "exits"]).round(2).to_string(index=False))
print()
for r in R.itertuples():
    print(r.candidate, "| missing:", r.missing, "| exits:", r.exits)

# per-quarter
PQ = T[T.why == "ok"].groupby(["cand", "qn"]).ret.agg(["count", "mean"]).round(1)
PQ.to_csv(f"{OUT}/discovery_per_quarter.csv")

# ranking
el = R[R.passes].sort_values("wo_best5", ascending=False)
print("\nPASSING (ranked by wo_best5):")
print(el[["candidate", "n", "coverage", "avg", "wo_best5", "q_with", "q_pos"]].round(2).to_string(index=False))
open(f"{OUT}/finalists.txt", "w").write(
    f"baseline wo_best5 = {B['wo_best5']:.3f}; bar = {bar:.3f}\n" + el.head(2)[["candidate", "n", "avg", "wo_best5"]].to_string(index=False) + "\n")

# markdown table
md = ["| candidate | signals | n | cov% | avg | median | w/o best 5 | hit% | t | worst | q+/q | prem %S | matched cash raw | matched cash vsN | eligible | passes |",
      "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
md.append(f"| BASELINE cash WR50 vsN_net (ref) | 122 | {B['n']} | 100 | {B['avg']:.2f} | {B['median']:.2f} | {B['wo_best5']:.2f} | {B['hit']:.0f} | {B['t']:.1f} | {B['worst']:.1f} | {B['q_pos']}/{B['q_with']} | - | - | - | ref | ref |")
md.append(f"| plain winners cash vsN_net (ref) | 192 | {plainB['n']} | 100 | {plainB['avg']:.2f} | {plainB['median']:.2f} | {plainB['wo_best5']:.2f} | {plainB['hit']:.0f} | {plainB['t']:.1f} | {plainB['worst']:.1f} | {plainB['q_pos']}/{plainB['q_with']} | - | - | - | ref | ref |")
for r in R.itertuples():
    md.append(f"| {r.candidate} | {r.signals} | {r.n} | {r.coverage:.0f} | {r.avg:.2f} | {r.median:.2f} | {r.wo_best5:.2f} | {r.hit:.0f} | {r.t:.1f} | {r.worst:.1f} | {r.q_pos}/{r.q_with} | {'' if np.isnan(r.prem_pct) else f'{r.prem_pct:.2f}'} | {r.matched_cash_raw:.2f} | {r.matched_cash_vsN:.2f} | {'yes' if r.eligible else 'no (illustration)'} | {'YES' if r.passes else 'no'} |")
open(f"{OUT}/discovery_table.md", "w").write("\n".join(md) + "\n")
print("\n".join(md))

print("\nexpiry-day check |option settle / future settle - 1|: n", len(SETTLE_CHECK), "max", max(SETTLE_CHECK) if SETTLE_CHECK else None)

# ------------------------------------------------------------------ D4: real futures (same expiry rule), WR50 + WIN
d4 = []
for r in p.itertuples():
    syms = tickers(r.symbol)
    if r.ticker not in syms:
        syms = [r.ticker] + syms
    exps = [r.expiry, r.exp_session_day]
    fe = r.F_entry; ne = r.NF_entry
    fx = fut(syms, r.exit_day, exps); nx = fut(["NIFTY"], r.exit_day, exps)
    if not (fe > 0 and ne > 0 and fx and nx):
        d4.append(dict(symbol=r.symbol, qn=r.qn, WR50=r.WR50, ok=False)); continue
    fxv = fx[1] if r.exit_at_expiry else (fx[0] if fx[2] > 0 and fx[0] > 0 else fx[1])
    nxv = nx[1] if r.exit_at_expiry else (nx[0] if nx[2] > 0 and nx[0] > 0 else nx[1])
    hed = (fxv / fe - nxv / ne) * 100 - 0.19
    d4.append(dict(symbol=r.symbol, qn=r.qn, WR50=r.WR50, ok=True, fut_hedged_notional=hed,
                   cash_vsN=r.vsN_net, fut_unhedged_notional=(fxv / fe - 1) * 100 - 0.17,
                   ca_flag=abs((fxv / fe - 1) * 100 - (r.raw_net + 0.17)) > 15))
D4 = pd.DataFrame(d4)
D4.to_csv(f"{OUT}/d4_real_futures.csv", index=False)
for lab, sub in (("WR50", D4[D4.WR50 & D4.ok]), ("WIN", D4[D4.ok])):
    sub2 = sub[~sub.ca_flag]
    print(f"D4 {lab}: n={len(sub2)} (missing {int((~D4.ok).sum()) if lab=='WIN' else int((~D4[D4.WR50].ok).sum())}, CA-flagged dropped {int(sub.ca_flag.sum())}) "
          f"real futures hedged on notional avg={sub2.fut_hedged_notional.mean():.2f} (cash vsN same trades {sub2.cash_vsN.mean():.2f}; "
          f"note exit = min(k+20, expiry) for futures vs k+20 for cash); on 25% margin = {sub2.fut_hedged_notional.mean()/0.25:.2f}; "
          f"wo_best5 on margin {wo_best(sub2.fut_hedged_notional/0.25):.2f}")
