"""Run the pre-registered TA + FA combined screens (definitions, statistics and pass rule: combos.py header).

    python3 run_combos.py   -> out/summary.csv, out/per_quarter.csv, out/trades.csv, out/run_log.txt, out/prereg_hash.txt

Inputs (read-only): ta/build/events_ta.csv, ta/build/placebo_ta.csv.gz, ta/build/adjusted_ohlcv.csv.gz,
fa/build/fa_panel.csv, fa/A_pre_results/out/extra_features.csv, sector_lab/data/{sessions,index_close}.csv,
results/lag10_volume/trades.csv (repo).
"""
import hashlib
import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
SP = os.path.dirname(os.path.dirname(HERE))
TA = f"{SP}/ta/build"
FA = f"{SP}/fa/build"
EXTRA = f"{SP}/fa/A_pre_results/out/extra_features.csv"
PACK = f"{SP}/sector_lab/data"
REPO = os.environ.get('REPO_ROOT', '.') + ""
LAG10 = f"{REPO}/results/lag10_volume/trades.csv"
LAG13 = f"{REPO}/results/lag10_volume/trades_vol13.csv"
NPERM = 20000
CHUNK = 1000
RNG = np.random.default_rng(20261009)
sys.path.insert(0, HERE)
import combos  # noqa: E402

LOG = open(f"{OUT}/run_log.txt", "w")


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    LOG.write(s + "\n")
    LOG.flush()


# ------------------------------------------------------------------ pre-registration fingerprint (before outcomes)
h = hashlib.sha256(open(f"{HERE}/combos.py", "rb").read()).hexdigest()
with open(f"{OUT}/prereg_hash.txt", "a") as fh:
    fh.write(f"{datetime.now().isoformat(timespec='seconds')} combos.py sha256 {h}\n")
log("combos.py sha256", h)

OUTCOME_FA = ["three_day", "tp3", "ret_dm1", "ret_rd", "ret_dp1", "excess_nifty_3d", "move", "nifty_react",
              "react_excess_nifty", "next5", "next20", "next20_vs_nifty"]
FA_KEEP = ["roe_pct", "debt_equity", "pe", "loss_any_4q", "fin_type", "pe_vs_own3y_pct", "pe_vs_peers_pct",
           "l1_sales_yoy_pct", "peg", "piotroski_full7", "piotroski_n", "piotroski_frac",
           "l1_ebitda_margin_chg_yoy_pp", "pe_own3y_median", "pe_peer_median"]
EX_KEEP = ["pat_l1", "pat_l5", "pat_l2", "pat_l6"]


def cl_se(v, g):
    v = np.asarray(v, float)
    n = len(v)
    if n < 2:
        return np.nan
    u = pd.Series(v - v.mean()).groupby(np.asarray(g)).sum().to_numpy()
    G = len(u)
    if G < 2:
        return np.nan
    return np.sqrt(G / (G - 1) * (u ** 2).sum()) / n


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
    m = len(p)
    o = np.argsort(p)
    q = np.empty(m)
    prev = 1.0
    for r in range(m - 1, -1, -1):
        i = o[r]
        prev = min(prev, p[i] * m / (r + 1))
        q[i] = prev
    return q


def tp_short(d1, d2, t3):
    s1, s12 = -d1, -(d1 + d2)
    return np.where(s1 > 3, s1, np.where(s12 > 3, s12, -t3))


def main():
    sessions = pd.read_csv(f"{PACK}/sessions.csv").day.tolist()
    sidx = {d: i for i, d in enumerate(sessions)}
    nifty = pd.read_csv(f"{PACK}/index_close.csv", index_col=0, usecols=["day", "Nifty 50"])["Nifty 50"]
    assert nifty.index.tolist() == sessions
    nv = nifty.to_numpy(float)
    nret = np.r_[np.nan, nv[1:] / nv[:-1] - 1] * 100

    # ---------------------------------------------------------------- events
    ta = pd.read_csv(f"{TA}/events_ta.csv")
    ta = ta[(ta.in_fo == True) & ta.three_day.notna()].reset_index(drop=True)
    fa = pd.read_csv(f"{FA}/fa_panel.csv")
    ex = pd.read_csv(EXTRA)
    fa = fa.merge(ex[["symbol", "quarter"] + EX_KEEP], on=["symbol", "quarter"], how="left", validate="1:1")
    fa_chk = fa[["symbol", "quarter", "three_day", "cutoff"]].rename(columns={"three_day": "three_day_fa", "cutoff": "cutoff_fa"})
    E = ta.merge(fa[["symbol", "quarter"] + FA_KEEP + EX_KEEP], on=["symbol", "quarter"], how="left", validate="1:1")
    E = E.merge(fa_chk, on=["symbol", "quarter"], how="left", validate="1:1")
    assert len(E) == 3278
    dd = (E.three_day - E.three_day_fa).abs()
    log(f"events {len(E)}; FA rows matched {E.cutoff_fa.notna().sum()}; cutoff equal {(E.cutoff == E.cutoff_fa).mean():.4f}; "
        f"three_day TA vs FA max abs diff {dd.max():.2e}")
    E["nifty3"] = nret[E.i_m1] + nret[E.i_rd] + nret[E.i_p1]
    E["excess"] = E.three_day - E.nifty3
    E["tp_short"] = tp_short(E.d1.to_numpy(), E.d2.to_numpy(), E.three_day.to_numpy())
    E["month"] = E.cutoff.str[:7]
    lag = pd.read_csv(LAG10)
    lag13 = pd.read_csv(LAG13)
    E["in_lag10"] = [k in set(zip(lag.symbol, lag.cutoff)) for k in zip(E.symbol, E.cutoff)]
    E["in_lag13"] = [k in set(zip(lag13.symbol, lag13.cutoff)) for k in zip(E.symbol, E.cutoff)]
    assert E.in_lag10.sum() == 85 and E.in_lag13.sum() == 44
    # check the panel's own pe_vs_ medians relation (used to move P/E to placebo day k)
    r1 = (100 * (E.pe / E.pe_own3y_median - 1) - E.pe_vs_own3y_pct).abs().max()
    r2 = (100 * (E.pe / E.pe_peer_median - 1) - E.pe_vs_peers_pct).abs().max()
    log(f"check pe_vs_own3y = pe/median-1: max abs diff {r1:.2e}; pe_vs_peers: {r2:.2e}")

    D = combos.build(E)
    ids = list(D)
    assert len(ids) == 39
    n = len(E)
    qn = E.qn.to_numpy()
    groups = [np.flatnonzero(qn == q) for q in np.unique(qn)]
    e3 = E.three_day.to_numpy(float)
    tpl = E.take_profit.to_numpy(float)
    tps = E.tp_short.to_numpy(float)
    exc = E.excess.to_numpy(float)
    assert np.isfinite(e3).all() and np.isfinite(tpl).all() and np.isfinite(exc).all()

    # ---------------------------------------------------------------- weight rows (pick mean minus random expectation)
    def wrow(m):
        w = np.zeros(n)
        K = m.sum()
        if K == 0:
            return w
        w[m] += 1.0 / K
        for g in groups:
            kq = m[g].sum()
            if kq:
                w[g] -= kq / (K * len(g))
        return w

    tests = ids + list(combos.SPREADS)
    J = len(tests)
    W = np.zeros((J, n))       # unsigned
    SG = np.zeros(J)
    for j, t in enumerate(tests):
        if t in D:
            W[j] = wrow(D[t]["mask"])
            SG[j] = D[t]["side"]
        else:
            a, b, _ = combos.SPREADS[t]
            W[j] = wrow(D[a]["mask"]) - wrow(D[b]["mask"])
            SG[j] = +1
    has = np.abs(W).sum(1) > 0
    # take-profit / excess: long tests use tp_long, short tests tp_short (already direction-adjusted)
    isS = SG < 0
    obs3 = SG * (W @ e3)
    obsx = SG * (W @ exc)
    obst = np.where(isS, W @ tps, W @ tpl)
    sp = [j for j, t in enumerate(tests) if t not in D]
    obst[sp] = np.nan

    S3 = np.zeros((J, NPERM), np.float32)
    ST = np.zeros((J, NPERM), np.float32)
    SX = np.zeros((J, NPERM), np.float32)
    for c0 in range(0, NPERM, CHUNK):
        B = min(CHUNK, NPERM - c0)
        idx = np.empty((n, B), np.int64)
        for g in groups:
            order = np.argsort(RNG.random((B, len(g))), axis=1)
            idx[g, :] = g[order].T
        S3[:, c0:c0 + B] = SG[:, None] * (W @ e3[idx])
        SX[:, c0:c0 + B] = SG[:, None] * (W @ exc[idx])
        tl, ts = W @ tpl[idx], W @ tps[idx]
        ST[:, c0:c0 + B] = np.where(isS[:, None], ts, tl)
    ST[sp, :] = 0.0                      # no take-profit statistic for the spread test
    log(f"permutations done: {NPERM}")

    def pvals(obs, Sm):
        sd = Sm.std(axis=1, ddof=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            z = obs / sd
            zs = Sm / sd[:, None]
        p2 = (1 + (np.abs(zs) >= np.abs(z)[:, None] - 1e-9).sum(1)) / (NPERM + 1)
        p1 = (1 + (Sm >= obs[:, None] - 1e-9).sum(1)) / (NPERM + 1)    # one-sided, pre-registered direction
        ok = np.isfinite(z)
        maxz = np.nanmax(np.abs(zs[ok]), axis=0)
        pmax = (1 + (maxz[None, :] >= np.abs(z)[:, None] - 1e-9).sum(1)) / (NPERM + 1)
        return z, p2, p1, pmax, maxz

    z3, p3, p3_one, pmax3, maxz3 = pvals(obs3, S3)
    zt, pt, pt_one, pmaxt, _ = pvals(np.nan_to_num(obst), ST)
    zx, px, px_one, pmaxx, _ = pvals(obsx, SX)
    pt[sp] = np.nan
    log(f"null 95th percentile of max|z| over {J} tests: {np.percentile(maxz3, 95):.2f}")

    # ---------------------------------------------------------------- placebo
    pl = pd.read_csv(f"{TA}/placebo_ta.csv.gz", low_memory=False)
    pl = pl[pl.in_fo == True].reset_index(drop=True)
    assert len(pl) == 120238
    fan = fa[["symbol", "qn", "cutoff"] + FA_KEEP + EX_KEEP].rename(columns={"qn": "qn_next", "cutoff": "cut_next"})
    pl = pl.merge(fan, on=["symbol", "qn_next"], how="left", validate="m:1")
    pl["has_fa"] = pl.cut_next.notna()
    assert (pl.cut_next[pl.has_fa] > pl.day[pl.has_fa]).all()
    adj = pd.read_csv(f"{TA}/adjusted_ohlcv.csv.gz", usecols=["day", "symbol", "close"]).set_index(["symbol", "day"]).close
    ck = adj.reindex(pd.MultiIndex.from_arrays([pl.symbol, pl.day])).to_numpy(float)
    cc = adj.reindex(pd.MultiIndex.from_arrays([pl.symbol, pl.cut_next.fillna("")])).to_numpy(float)
    r = ck / cc
    log(f"placebo rows {len(pl)}; with next FA row {pl.has_fa.sum()}; price ratio known {np.isfinite(r[pl.has_fa]).mean():.4f}; "
        f"median |ratio-1| {np.nanmedian(np.abs(r - 1)):.3f}")
    pl["pe"] = pl.pe * r
    pl["peg"] = pl.peg * r
    pl["pe_vs_own3y_pct"] = np.where(pl.pe_vs_own3y_pct.notna(), 100 * (pl.pe / pl.pe_own3y_median - 1), np.nan)
    pl["pe_vs_peers_pct"] = np.where(pl.pe_vs_peers_pct.notna(), 100 * (pl.pe / pl.pe_peer_median - 1), np.nan)
    pl["tp_short"] = tp_short(pl.d1.to_numpy(), pl.d2.to_numpy(), pl.three_day.to_numpy())
    pl["nifty3"] = nret[pl.i + 1] + nret[pl.i + 2] + nret[pl.i + 3]
    pl["excess"] = pl.three_day - pl.nifty3
    pl["month"] = pl.day.str[:7]
    DP = combos.build(pl)
    hasfa = pl.has_fa.to_numpy()

    # ---------------------------------------------------------------- per-test statistics
    rows, perq, trades = [], [], []
    for j, t in enumerate(tests):
        if t not in D:
            continue
        d = D[t]
        m, sg = d["mask"], d["side"]
        x = E[m]
        k = len(x)
        e = sg * x.three_day
        etp = x.tp_short if sg < 0 else x.take_profit
        ex_ = sg * x.excess
        rec = {"id": t, "family": combos.FAMILY[t[0]], "label": d["label"], "side": "long" if sg > 0 else "short",
               "trades": k, "stocks": x.symbol.nunique()}
        if k:
            byq = e.groupby(x.qn).agg(["size", "mean"])
            for q, rr in byq.iterrows():
                perq.append({"id": t, "qn": int(q), "trades": int(rr["size"]), "avg_pct": rr["mean"],
                             "tp_avg_pct": etp[x.qn == q].mean()})
            tr = x[["symbol", "quarter", "qn", "cutoff", "three_day", "take_profit", "tp_short", "excess", "in_lag10"]].copy()
            tr.insert(0, "id", t)
            tr["edge_pct"] = e
            trades.append(tr)
            rec.update({
                "avg_pct": e.mean(), "avg_net_pct": e.mean() - combos.COST, "median_pct": e.median(),
                "tp_avg_pct": etp.mean(), "tp_net_pct": etp.mean() - combos.COST, "up_pct": 100 * (e > 0).mean(),
                "q_with_trades": int(len(byq)), "q_positive": int((byq["mean"] > 0).sum()),
                "first14_pct": e[x.qn <= 13].mean() if (x.qn <= 13).any() else np.nan,
                "last8_pct": e[x.qn >= 14].mean() if (x.qn >= 14).any() else np.nan,
                "n_first14": int((x.qn <= 13).sum()), "n_last8": int((x.qn >= 14).sum()),
                "without_best5_pct": e.sort_values().iloc[:-5].mean() if k > 5 else np.nan,
                "random_avg_pct": e.mean() - obs3[j], "vs_random_pct": obs3[j],
                "z": z3[j], "p_two": p3[j], "p_one": p3_one[j], "p_maxT": pmax3[j],
                "tp_vs_random_pct": obst[j], "tp_p_two": pt[j], "tp_p_maxT": pmaxt[j],
                "hedged_avg_pct": ex_.mean(), "hedged_net_pct": ex_.mean() - combos.COST_HEDGED,
                "hedged_p_two": px[j],
                "lag10_overlap": int(x.in_lag10.sum()), "lag13_overlap": int(x.in_lag13.sum()),
                "avg_without_lag10_pct": e[~x.in_lag10].mean() if (~x.in_lag10).any() else np.nan,
                "n_without_lag10": int((~x.in_lag10).sum()),
                "fa_part_n": int(d["fa"].sum()), "fa_part_avg_pct": sg * E.three_day[d["fa"]].mean(),
                "ta_part_n": int(d["ta"].sum()), "ta_part_avg_pct": sg * E.three_day[d["ta"]].mean(),
                "se_res": cl_se(e, x.month),
            })
        # placebo
        pm = DP[t]["mask"] & hasfa
        pu = DP[t]["ta"]
        y = pl[pm]
        yu = pl[pu]
        pe_ = sg * y.three_day
        rec.update({
            "plac_restricted_n": len(y), "plac_restricted_avg_pct": pe_.mean() if len(y) else np.nan,
            "plac_restricted_tp_pct": (y.tp_short if sg < 0 else y.take_profit).mean() if len(y) else np.nan,
            "plac_unrestricted_n": len(yu), "plac_unrestricted_avg_pct": (sg * yu.three_day).mean() if len(yu) else np.nan,
            "plac_all_pct": sg * pl.three_day.mean(),
        })
        if k and len(y) > 1:
            se_p = cl_se(pe_, y.month)
            diff = rec["avg_pct"] - pe_.mean()
            rec.update({"res_minus_plac_pct": diff, "res_minus_plac_z": diff / np.sqrt(rec["se_res"] ** 2 + se_p ** 2)})
        if k:
            rec["res_minus_plac_unres_pct"] = rec["avg_pct"] - rec["plac_unrestricted_avg_pct"]
        rows.append(rec)

    # spread test
    for j, t in enumerate(tests):
        if t in D:
            continue
        a, b, lab = combos.SPREADS[t]
        ma, mb = D[a]["mask"], D[b]["mask"]
        ya, yb = E.three_day[ma], E.three_day[mb]
        pa, pb_ = pl.three_day[DP[a]["mask"] & hasfa], pl.three_day[DP[b]["mask"] & hasfa]
        qa_ = E[ma].groupby("qn").three_day.mean()
        qb_ = E[mb].groupby("qn").three_day.mean()
        qq = (qa_ - qb_).dropna()
        rows.append({"id": t, "family": combos.FAMILY["9"], "label": lab, "side": "long-short", "trades": len(ya) + len(yb),
                     "avg_pct": ya.mean() - yb.mean(), "vs_random_pct": obs3[j], "z": z3[j], "p_two": p3[j],
                     "p_one": p3_one[j], "p_maxT": pmax3[j],
                     "q_with_trades": len(qq), "q_positive": int((qq > 0).sum()),
                     "first14_pct": ya[E.qn[ma] <= 13].mean() - yb[E.qn[mb] <= 13].mean(),
                     "last8_pct": ya[E.qn[ma] >= 14].mean() - yb[E.qn[mb] >= 14].mean(),
                     "plac_restricted_n": len(pa) + len(pb_), "plac_restricted_avg_pct": pa.mean() - pb_.mean(),
                     "res_minus_plac_pct": (ya.mean() - yb.mean()) - (pa.mean() - pb_.mean()),
                     "hedged_avg_pct": E.excess[ma].mean() - E.excess[mb].mean(), "hedged_p_two": px[j]})

    Sm = pd.DataFrame(rows)
    Sm["holm_p"] = holm(Sm.p_two.to_numpy())
    Sm["bh_q"] = bh(Sm.p_two.to_numpy())
    Sm["tp_holm_p"] = np.nan
    okt = Sm.tp_p_two.notna()
    Sm.loc[okt, "tp_holm_p"] = holm(Sm.loc[okt, "tp_p_two"].to_numpy())
    Sm["hedged_holm_p"] = holm(Sm.hedged_p_two.to_numpy())
    right = Sm.vs_random_pct > 0
    crit = pd.DataFrame({
        "c1_mt": (Sm.holm_p < 0.05) & (Sm.p_maxT < 0.05) & right,
        "c2_net": Sm.avg_net_pct.fillna(Sm.avg_pct - 2 * combos.COST) > 0,
        "c3_halves": (Sm.first14_pct > 0) & (Sm.last8_pct > 0),
        "c4_wo_best5": Sm.without_best5_pct.fillna(Sm.avg_pct) > 0,
        "c5_quarters": Sm.q_positive >= 0.6 * Sm.q_with_trades,
        "c6_placebo": Sm.res_minus_plac_pct > 0,
        "c7_trades": Sm.trades >= 30,
    })
    Sm = pd.concat([Sm, crit], axis=1)
    Sm["criteria_met"] = crit.sum(1)
    Sm["verdict"] = np.select(
        [crit.all(1), Sm.trades < 30, (Sm.p_two < 0.05) & right, (Sm.p_two < 0.05) & ~right],
        ["CANDIDATE", "too few to judge", "unconfirmed hint", "reverse"], "nothing")
    Sm.to_csv(f"{OUT}/summary.csv", index=False, float_format="%.5g")
    pd.DataFrame(perq).to_csv(f"{OUT}/per_quarter.csv", index=False, float_format="%.5g")
    pd.concat(trades).to_csv(f"{OUT}/trades.csv", index=False, float_format="%.5g")

    # ---------------------------------------------------------------- print
    pd.set_option("display.width", 260, "display.max_columns", 80, "display.max_rows", 200)
    log(f"\nBaselines: all F&O results three_day {E.three_day.mean():+.3f} (n {n}), take-profit {E.take_profit.mean():+.3f}; "
        f"placebo all {pl.three_day.mean():+.3f} (n {len(pl)})")
    log("All returns direction-adjusted (short = profit of the short), percent, gross unless 'net'.")
    T1 = Sm[["id", "side", "trades", "stocks", "avg_pct", "avg_net_pct", "tp_avg_pct", "up_pct", "q_with_trades",
             "q_positive", "first14_pct", "last8_pct", "without_best5_pct", "random_avg_pct", "p_two", "holm_p",
             "p_maxT", "bh_q"]].copy()
    T1.columns = ["id", "side", "n", "stk", "avg", "net", "tp", "up%", "qT", "q+", "f14", "l8", "-b5", "rand", "p2",
                  "holm", "maxT", "bh"]
    log(T1.round(3).to_string(index=False))
    T2 = Sm[["id", "plac_restricted_n", "plac_restricted_avg_pct", "plac_unrestricted_n", "plac_unrestricted_avg_pct",
             "res_minus_plac_pct", "res_minus_plac_z", "hedged_avg_pct", "hedged_net_pct", "hedged_p_two", "tp_p_two",
             "lag10_overlap", "avg_without_lag10_pct", "fa_part_avg_pct", "ta_part_avg_pct", "criteria_met", "verdict"]].copy()
    T2.columns = ["id", "plR_n", "plR", "plU_n", "plU", "r-pR", "z", "hedg", "hnet", "h_p2", "tp_p2", "lag", "noLag",
                  "FAonly", "TAonly", "crit", "verdict"]
    log("")
    log(T2.round(3).to_string(index=False))
    log(f"\nTests {len(Sm)}; nominal p_two < 0.05: {int((Sm.p_two < 0.05).sum())} (chance ~{0.05 * len(Sm):.1f}); "
        f"Holm < 0.05: {int((Sm.holm_p < 0.05).sum())}; maxT < 0.05: {int((Sm.p_maxT < 0.05).sum())}; "
        f"BH q < 0.10: {int((Sm.bh_q < 0.10).sum())}")
    zz = np.abs(z3)
    cnt = (np.abs(S3 / S3.std(axis=1, ddof=1)[:, None]) >= 1.96).sum(0)
    log(f"count of |z| >= 1.96: observed {(zz >= 1.96).sum()}, joint null median {np.median(cnt):.0f}, "
        f"90th pct {np.percentile(cnt, 90):.0f}, P(count >= observed) {np.mean(cnt >= (zz >= 1.96).sum()):.3f}")
    LOG.close()


if __name__ == "__main__":
    main()
