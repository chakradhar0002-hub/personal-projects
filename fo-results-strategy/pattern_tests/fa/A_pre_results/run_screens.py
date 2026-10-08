"""Run the pre-registered pre-results fundamental screens (definitions and decision rule: screens.py header).

    python3 pit_extra.py      (once: out/extra_features.csv)
    python3 run_screens.py    -> out/summary_screens.csv, out/per_quarter.csv, out/picks.csv, out/lag10_filters.csv,
                                 out/run_log.txt, out/prereg_hash.txt
"""
import os  # LAB_ROOT: scratch folder with report/, search22/, sector_lab/data, fa/; REPO_ROOT: this repo
import hashlib
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
DATA = os.environ.get('LAB_ROOT', 'lab') + ""
REPO = Path(os.environ.get('REPO_ROOT', '.') + "")
sys.path.insert(0, str(HERE))
import screens  # noqa: E402

R = 20000
COST = screens.COST
LOGF = open(OUT / "run_log.txt", "w")


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    LOGF.write(s + "\n")
    LOGF.flush()


# ---------------------------------------------------------------- pre-registration fingerprint (before any outcome)
h = hashlib.sha256(open(HERE / "screens.py", "rb").read()).hexdigest()
with open(OUT / "prereg_hash.txt", "a") as fh:
    fh.write(f"{datetime.now().isoformat(timespec='seconds')} screens.py sha256 {h}\n")
log("screens.py sha256", h)

# ---------------------------------------------------------------- data
panel = pd.read_csv(f"{DATA}/fa/build/fa_panel.csv")
extra = pd.read_csv(OUT / "extra_features.csv")
panel = panel.merge(extra, on=["symbol", "quarter"], how="left", validate="1:1")
U = panel[(panel.in_fo == True) & panel.three_day.notna()].reset_index(drop=True)
log("universe in_fo with three_day:", len(U))
qn = U.qn.to_numpy()

# placebo windows: same three-session window shifted k sessions earlier
sl = pd.read_csv(f"{DATA}/sector_lab/data/events.csv", usecols=["symbol", "quarter", "i_cut"])
U = U.merge(sl, on=["symbol", "quarter"], how="left", validate="1:1")
rets = pd.read_csv(f"{DATA}/sector_lab/data/returns.csv")
days = rets["day"].to_numpy()
RET = {c: rets[c].to_numpy(dtype=float) for c in rets.columns if c != "day"}


def window(sym, i0):
    a = RET.get(sym)
    if a is None or i0 < 1 or i0 + 2 >= len(a):
        return np.nan
    w = a[i0:i0 + 3]
    return 100 * w.sum() if np.isfinite(w).all() else np.nan


chk = np.array([window(s, i + 1) for s, i in zip(U.symbol, U.i_cut)])
dd = np.abs(chk - U.three_day.to_numpy())
log(f"alignment check (returns.csv window i_cut+1..+3 vs three_day): n={np.isfinite(dd).sum()}, "
    f"median abs diff {np.nanmedian(dd):.2e}, share > 0.01pp {(dd > 0.01).mean():.3f}")
for k in (15, 30):
    pl = np.array([window(s, i - k + 1) for s, i in zip(U.symbol, U.i_cut)])
    known = np.array([(isinstance(p1, str) and int(i - k) >= 0 and p1 < days[int(i - k)]) for p1, i in zip(U.l1_published, U.i_cut)])
    pl[~known] = np.nan
    U[f"placebo_k{k}"] = pl
    log(f"placebo k={k}: values {np.isfinite(pl).sum()}")

S = screens.build_flags(U)
assert len(S) == 44
log("screens:", len(S))
rng = np.random.default_rng(20261008)


# ---------------------------------------------------------------- random same-size per-quarter picks
def luck(y, m, e):
    """Mean of picks, expected mean of random same-size same-quarter picks from the pool, simulated means, p (2-sided)."""
    ok = np.isfinite(y)
    m, e = m & ok, e & ok
    K = m.sum()
    if K == 0:
        return np.nan, np.nan, None, np.nan, np.nan, 0
    sim = np.zeros(R)
    exp = 0.0
    for q in np.unique(qn[m]):
        k = int((m & (qn == q)).sum())
        pool = y[e & (qn == q)]
        N = len(pool)
        exp += k * pool.mean()
        if k == N:
            sim += pool.sum()
            continue
        keys = rng.random((R, N), dtype=np.float32)
        if k <= N // 2:
            idx = np.argpartition(keys, k - 1, axis=1)[:, :k]
            sim += pool[idx].sum(axis=1)
        else:  # sample the complement
            idx = np.argpartition(keys, N - k - 1, axis=1)[:, :N - k]
            sim += pool.sum() - pool[idx].sum(axis=1)
    sim /= K
    exp /= K
    obs = y[m].mean()
    p = (1 + np.sum(np.abs(sim - exp) >= abs(obs - exp) - 1e-12)) / (R + 1)
    pct = 100 * np.mean(sim < obs)
    return obs, exp, sim, p, pct, K


def qstats(y, m, e, allmask):
    """Per-quarter rows and the quarter-clustered t of the excess vs pool."""
    ok = np.isfinite(y)
    rows = []
    for q in np.unique(qn[m & ok]):
        mq = m & ok & (qn == q)
        rows.append({"qn": int(q), "n": int(mq.sum()), "mean": y[mq].mean(),
                     "pool_mean": y[e & ok & (qn == q)].mean(), "all_mean": y[allmask & ok & (qn == q)].mean()})
    d = pd.DataFrame(rows)
    if len(d) == 0:
        return d, np.nan
    ex = d["mean"] - d["pool_mean"]
    t = ex.mean() / (ex.std(ddof=1) / np.sqrt(len(ex))) if len(ex) >= 3 and ex.std(ddof=1) > 0 else np.nan
    return d, t


def holm(p):
    p = np.asarray(p, float)
    o = np.argsort(p)
    adj = np.empty_like(p)
    run = 0.0
    for r, i in enumerate(o):
        run = max(run, (len(p) - r) * p[i])
        adj[i] = min(1.0, run)
    return adj


def bh(p):
    p = np.asarray(p, float)
    n = len(p)
    o = np.argsort(p)[::-1]
    adj = np.empty_like(p)
    run = 1.0
    for r, i in enumerate(o):
        run = min(run, p[i] * n / (n - r))
        adj[i] = run
    return adj


y3 = U.three_day.to_numpy(float)
ytp = U.tp3.to_numpy(float)
ynif = U.excess_nifty_3d.to_numpy(float)
allm = np.ones(len(U), bool)
first = qn <= 13
rows, perq, picks = [], [], []
T0 = time.time()
for sid, (m, e, side, label) in S.items():
    obs, exp, sim, p, pct, K = luck(y3, m, e)
    _, exp_tp, _, p_tp, _, _ = luck(ytp, m, e)
    d, tq = qstats(y3, m, e, allm)
    dtp, _ = qstats(ytp, m, e, allm)
    all_base = (d["n"] * d["all_mean"]).sum() / d["n"].sum()
    vals = np.sort(y3[m])
    halves = {}
    for nm, hm in (("f14", first), ("l8", ~first)):
        mm = m & hm
        if mm.sum():
            o2, e2 = y3[mm].mean(), None
            dq = d[d.qn.isin(np.unique(qn[mm]))]
            e2 = (dq["n"] * dq["pool_mean"]).sum() / dq["n"].sum()
            halves[nm] = (int(mm.sum()), o2, o2 - e2, ytp[mm].mean())
        else:
            halves[nm] = (0, np.nan, np.nan, np.nan)
    pls = {}
    for k in (15, 30):
        yp = U[f"placebo_k{k}"].to_numpy(float)
        o3, e3, _, p3, _, k3 = luck(yp, m, e)
        pls[k] = (k3, o3, o3 - e3, p3)
    row = {
        "id": sid, "label": label, "side": {1: "long", -1: "short", 0: "none"}[side],
        "trades": int(K), "stocks": int(U.symbol[m].nunique()),
        "top_stock_share_pct": 100 * U.symbol[m].value_counts().iloc[0] / K,
        "avg_3d": obs, "net_3d": obs - COST, "avg_tp3": ytp[m].mean(), "net_tp3": ytp[m].mean() - COST,
        "up_pct": 100 * np.mean(y3[m] > 0), "vs_nifty": np.nanmean(ynif[m]),
        "pool_avg_same_qtrs": exp, "excess_vs_pool": obs - exp, "excess_vs_all": obs - all_base,
        "excess_tp3_vs_pool": ytp[m].mean() - exp_tp,
        "p_luck_3d": p, "pct_vs_random": pct, "p_luck_tp3": p_tp, "t_quarter_clustered": tq,
        "qtrs_with_trades": len(d), "qtrs_positive": int((d["mean"] > 0).sum()),
        "qtrs_beat_pool": int((d["mean"] > d["pool_mean"]).sum()), "qtrs_ge_2pct": int((d["mean"] >= 2).sum()),
        "qtrs_positive_tp3": int((dtp["mean"] > 0).sum()),
        "n_f14": halves["f14"][0], "avg_f14": halves["f14"][1], "excess_f14": halves["f14"][2], "tp3_f14": halves["f14"][3],
        "n_l8": halves["l8"][0], "avg_l8": halves["l8"][1], "excess_l8": halves["l8"][2], "tp3_l8": halves["l8"][3],
        "avg_wo_best5": vals[:-5].mean() if K > 5 else np.nan, "avg_wo_worst5": vals[5:].mean() if K > 5 else np.nan,
        "short_net_3d": -obs - COST,
        "pl15_n": pls[15][0], "pl15_avg": pls[15][1], "pl15_excess": pls[15][2], "pl15_p": pls[15][3],
        "pl30_n": pls[30][0], "pl30_avg": pls[30][1], "pl30_excess": pls[30][2], "pl30_p": pls[30][3],
    }
    rows.append(row)
    d = d.assign(id=sid, tp3_mean=dtp["mean"].to_numpy())
    perq.append(d)
    pk = U.loc[m, ["symbol", "quarter", "qn", "industry", "fin_type", "three_day", "tp3", "excess_nifty_3d"]].assign(id=sid)
    picks.append(pk)
    log(f"{sid:5s} n={K:5d} avg {obs:+.2f} pool {exp:+.2f} ex {obs - exp:+.2f} p {p:.4f}  tq {tq:+.2f}  ({time.time() - T0:.0f}s)")

res = pd.DataFrame(rows)
res["p_holm"] = holm(res.p_luck_3d)
res["p_bonferroni"] = np.minimum(1, res.p_luck_3d * len(res))
res["q_bh"] = bh(res.p_luck_3d)
both = holm(np.r_[res.p_luck_3d, res.p_luck_tp3])
res["p_holm_3d_in_88"], res["p_holm_tp3_in_88"] = both[:len(res)], both[len(res):]

# decision rule (screens.py header)
def verdict(r):
    if r.trades < 30:
        return "too few to judge"
    direction = np.sign(r.excess_vs_pool) if r.side == "none" else (1 if r.side == "long" else -1)
    pl = np.nanmean([r.pl15_excess, r.pl30_excess])
    a = r.p_holm < 0.05
    b = np.sign(r.excess_f14) == np.sign(r.excess_l8) == np.sign(r.excess_vs_pool)
    if direction > 0:
        c = r.avg_wo_best5 > COST
    else:
        c = r.avg_wo_worst5 < -COST
    dd = abs(pl) < 0.5 * abs(r.excess_vs_pool) if np.isfinite(pl) else False
    tags = [n for n, ok in (("a", a), ("b", b), ("c", c), ("d", dd)) if not ok]
    return "HOLDS" if not tags else "fails " + ",".join(tags)


res["verdict"] = res.apply(verdict, axis=1)
res.to_csv(OUT / "summary_screens.csv", index=False)
pd.concat(perq).to_csv(OUT / "per_quarter.csv", index=False)
pd.concat(picks).to_csv(OUT / "picks.csv", index=False)
pd.set_option("display.width", 250)
log(res[["id", "trades", "avg_3d", "net_3d", "avg_tp3", "up_pct", "excess_vs_pool", "excess_vs_all", "p_luck_3d", "p_holm",
         "t_quarter_clustered", "qtrs_with_trades", "qtrs_positive", "avg_f14", "avg_l8", "excess_f14", "excess_l8",
         "avg_wo_best5", "pl15_excess", "pl30_excess", "verdict"]].round(3).to_string())

# ---------------------------------------------------------------- family B: fundamentals as a filter on lag10 + volume
B = screens.build_lag10_flags(U)
outb = []
for fname, tag in (("trades.csv", "lag10_vol1.0"), ("trades_vol13.csv", "lag10_vol1.3")):
    tr = pd.read_csv(REPO / "results" / "lag10_volume" / fname)
    j = U.reset_index().merge(tr[["symbol", "quarter", "three_day", "take_profit"]], on=["symbol", "quarter"], suffixes=("", "_tr"))
    log(f"{tag}: trades {len(tr)}, matched to panel universe {len(j)}; max |three_day diff| "
        f"{(j.three_day - 100 * j.three_day_tr).abs().max():.2e}")
    ii = j["index"].to_numpy()
    y = U.three_day.to_numpy(float)[ii]
    yt = U.tp3.to_numpy(float)[ii]
    q = qn[ii]
    log(f"{tag}: all trades avg {y.mean():+.2f} tp3 {yt.mean():+.2f}")
    for bid, (flag, lab) in B.items():
        f = flag[ii]
        k = np.isfinite(f)
        f1, f0 = k & (f == 1), k & (f == 0)
        rec = {"set": tag, "id": bid, "label": lab, "n_known": int(k.sum()), "n_flag1": int(f1.sum()), "n_flag0": int(f0.sum()),
               "avg_flag1": y[f1].mean() if f1.any() else np.nan, "avg_flag0": y[f0].mean() if f0.any() else np.nan,
               "tp3_flag1": yt[f1].mean() if f1.any() else np.nan, "tp3_flag0": yt[f0].mean() if f0.any() else np.nan}
        rec["diff"] = rec["avg_flag1"] - rec["avg_flag0"]
        if f1.sum() >= 3 and f0.sum() >= 3:
            yk, fk = y[k], f[k] == 1
            sims = np.empty(R)
            for r in range(R):
                perm = rng.permutation(fk)
                sims[r] = yk[perm].mean() - yk[~perm].mean()
            rec["p_perm"] = (1 + np.sum(np.abs(sims) >= abs(rec["diff"]) - 1e-12)) / (R + 1)
        else:
            rec["p_perm"] = np.nan
        for nm, hm in (("f14", q <= 13), ("l8", q >= 14)):
            a1, a0 = f1 & hm, f0 & hm
            rec[f"diff_{nm}"] = (y[a1].mean() - y[a0].mean()) if a1.any() and a0.any() else np.nan
            rec[f"n1_{nm}"], rec[f"n0_{nm}"] = int(a1.sum()), int(a0.sum())
        outb.append(rec)
ob = pd.DataFrame(outb)
for tag in ob.set.unique():
    s = ob.set == tag
    ob.loc[s, "p_holm"] = holm(ob.loc[s, "p_perm"].fillna(1).to_numpy())
ob.to_csv(OUT / "lag10_filters.csv", index=False)
log(ob.round(3).to_string())
log(f"done in {time.time() - T0:.0f}s")
