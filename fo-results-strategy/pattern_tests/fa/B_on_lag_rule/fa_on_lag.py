"""Fundamental filters on the lag-10% + volume rule, exactly as pre-registered in PREREGISTRATION.txt.

    python3 fa_on_lag.py     (reads ../build/fa_panel.csv, ../../ta/build/{events_ta.csv, placebo_ta.csv.gz,
                              adjusted_ohlcv.csv.gz}, sector_lab index_close.csv, the repo trade files; writes here)

Outputs: run.log, splits_S85.csv, splits_S44.csv, replacement_rules.csv, refined_rules.csv (only if promoted),
         per_quarter_splits.csv, per_quarter_rules.csv, trades_S85_with_fa.csv, prevalence.csv
"""
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.dirname(os.path.dirname(HERE))                       # scratchpad
TA = f"{SCR}/ta/build"
REPO = os.environ.get('REPO_ROOT', '.') + "/results/lag10_volume"
COST = 0.17
NPERM, NPERM_REST, NBOOT, NLUCK = 20000, 4000, 2000, 20000
rng = np.random.default_rng(20261008)
pd.set_option("display.width", 260, "display.max_columns", 80, "display.max_rows", 300)


class Tee:
    def __init__(self, path):
        self.f = open(path, "w")

    def write(self, s):
        self.f.write(s)
        sys.__stdout__.write(s)

    def flush(self):
        self.f.flush()
        sys.__stdout__.flush()


sys.stdout = Tee(f"{HERE}/run.log")

# ------------------------------------------------------------------------------------------------ data
F = pd.read_csv(f"{SCR}/fa/build/fa_panel.csv")
E0 = pd.read_csv(f"{TA}/events_ta.csv", usecols=["symbol", "quarter", "qn", "cutoff", "lag_pct", "vol_ratio_5_60",
                                                 "three_day", "take_profit", "in_fo"])
E = F.merge(E0.rename(columns={"three_day": "three_day_ta", "qn": "qn_ta", "cutoff": "cutoff_ta", "in_fo": "in_fo_ta"}),
            on=["symbol", "quarter"], how="left", validate="1:1")
assert (E.qn == E.qn_ta).all() and (E.cutoff == E.cutoff_ta).all()
assert ((E.in_fo == E.in_fo_ta) | E.in_fo_ta.isna()).all()                 # 2 demergers: no in_fo in events_ta
print(f"panel rows without an events_ta in_fo flag (demergers, three_day NaN): "
      f"{list(zip(E[E.in_fo_ta.isna()].symbol, E[E.in_fo_ta.isna()].quarter))}")
E = E[(E.in_fo == True) & E.three_day.notna()].reset_index(drop=True)
print(f"in_fo results with three_day: {len(E)} (mean three_day {E.three_day.mean():.3f}%)")
print(f"check panel vs events_ta: max |three_day diff| {np.abs(E.three_day - E.three_day_ta).max():.2e}, "
      f"max |tp3 - take_profit| {np.abs(E.tp3 - E.take_profit).max():.2e}, lag/vol missing "
      f"{int(E.lag_pct.isna().sum())}/{int(E.vol_ratio_5_60.isna().sum())}")

# size threshold: median log_mcap of in_fo results per quarter (fixed from the whole in_fo panel)
MED_MCAP = F[F.in_fo == True].groupby("qn").log_mcap.median()


def labels(d):
    """name -> (known mask, true mask) as numpy bool arrays. Definitions as in PREREGISTRATION.txt."""
    c = {}
    comp = (d.fin_type == "Company").to_numpy()
    roe, de = d.roe_pct.to_numpy(float), d.debt_equity.to_numpy(float)
    k = ~np.isnan(roe) & (~comp | ~np.isnan(de))
    c["F1_quality"] = (k, k & (roe > 15) & (~comp | (de < 0.5)))
    v = d.loss_any_4q.to_numpy(float)
    c["F2_profitable_4q"] = (~np.isnan(v), v == 0)
    for name, col in (("F3_l1_pat_growth", "l1_pat_yoy_pct"), ("F4_pat_accel", "pat_yoy_accel_pp"),
                      ("F5_sales_accel", "sales_yoy_accel_pp")):
        v = d[col].to_numpy(float)
        c[name] = (~np.isnan(v), v > 0)
    v = np.where(comp, d.l1_ebitda_margin_chg_yoy_pp.to_numpy(float), d.l1_net_margin_chg_yoy_pp.to_numpy(float))
    c["F6_margin_up"] = (~np.isnan(v), v > 0)
    for name, col in (("F7_cheap_own3y", "pe_vs_own3y_pct"), ("F8_cheap_peers", "pe_vs_peers_pct")):
        v = d[col].to_numpy(float)
        c[name] = (~np.isnan(v), v < 0)
    pn, pf = d.piotroski_n.to_numpy(float), d.piotroski_frac.to_numpy(float)
    k = (pn >= 5) & ~np.isnan(pf)
    c["F9_piotroski_high"] = (k, k & (pf >= 5 / 7 - 1e-9))
    v, med = d.log_mcap.to_numpy(float), d.qn.map(MED_MCAP).to_numpy(float)
    c["F10_large_cap"] = (~np.isnan(v) & ~np.isnan(med), v > med)
    l4, py, sy = d.loss_any_4q.to_numpy(float), d.l1_pat_yoy_pct.to_numpy(float), d.l1_sales_yoy_pct.to_numpy(float)
    good = (l4 == 0) & (py > 0) & (sy > 0)
    bad = (l4 == 1) | (py <= 0) | (sy <= 0)
    c["F11_good_fund"] = (good | bad, good)
    if "rq_sales_yoy_pct" in d:
        rs, rp = d.rq_sales_yoy_pct.to_numpy(float), d.rq_pat_yoy_pct.to_numpy(float)
        g, b = (rs > 0) & (rp > 0), (rs <= 0) | (rp <= 0)
        c["Q1_rq_good"] = (g | b, g)
        c["Q2_rq_pat_up"] = (~np.isnan(rp), rp > 0)
        c["Q3_rq_sales_up"] = (~np.isnan(rs), rs > 0)
        v = d.rq_pat_surprise_vs_trend_pp.to_numpy(float)
        c["Q4_rq_beat_trend"] = (~np.isnan(v), v > 0)
    return c


PRIOR = {"F1_quality": "T", "F2_profitable_4q": "T", "F3_l1_pat_growth": "T", "F4_pat_accel": "T",
         "F5_sales_accel": "T", "F6_margin_up": "T", "F7_cheap_own3y": "T", "F8_cheap_peers": "T",
         "F9_piotroski_high": "T", "F10_large_cap": "2s", "F11_good_fund": "T", "Q1_rq_good": "T",
         "Q2_rq_pat_up": "T", "Q3_rq_sales_up": "T", "Q4_rq_beat_trend": "T"}
PRE = [k for k in PRIOR if k.startswith("F")]
POST = [k for k in PRIOR if k.startswith("Q")]
CE = labels(E)

# ------------------------------------------------------------------------------------------------ base sets + check
lagE = (E.lag_pct < -10).to_numpy()
volE = (E.vol_ratio_5_60 >= 1.0).to_numpy()
S = {}
for name, v, fname in (("S85", 1.0, "trades.csv"), ("S44", 1.3, "trades_vol13.csv")):
    m = lagE & (E.vol_ratio_5_60 >= v).to_numpy()
    ref = pd.read_csv(f"{REPO}/{fname}")
    mine = E[m]
    same = set(zip(mine.symbol, mine.quarter)) == set(zip(ref.symbol, ref.quarter))
    j = mine.merge(ref, on=["symbol", "quarter"], suffixes=("", "_ref"))
    print(f"{name}: rebuilt {len(mine)} trades, repo {fname} {len(ref)}, same (symbol, quarter): {same}, "
          f"max |three_day - ref x100| {np.abs(j.three_day - 100 * j.three_day_ref).max():.2e}, "
          f"max |tp3 - ref take_profit x100| {np.abs(j.tp3 - 100 * j.take_profit_ref).max():.2e}, "
          f"max |lag - ref| {np.abs(j.lag_pct - 100 * j.vs_nifty_1m).max():.2e}, "
          f"max |vol - ref| {np.abs(j.vol_ratio_5_60 - j.volume_ratio).max():.2e}")
    assert same
    S[name] = m

# ------------------------------------------------------------------------------------------------ placebo days
P = pd.read_csv(f"{TA}/placebo_ta.csv.gz", usecols=["symbol", "day", "in_fo", "qn_prev", "qn_next", "lag_pct",
                                                    "vol_ratio_5_60", "three_day", "take_profit"])
P = P[(P.in_fo == True) & P.lag_pct.notna() & P.vol_ratio_5_60.notna()].reset_index(drop=True)
FN = F.drop(columns=["three_day", "tp3", "in_fo", "lag_pct", "vol_ratio_5_60"], errors="ignore")
FN = FN[[c for c in FN.columns if not c.startswith("rq_")]]
P = P.merge(FN, left_on=["symbol", "qn_next"], right_on=["symbol", "qn"], how="left")
adj = pd.read_csv(f"{TA}/adjusted_ohlcv.csv.gz", usecols=["day", "symbol", "close"]).dropna()
cl = adj.set_index(["symbol", "day"]).close
nifty = pd.read_csv(f"{SCR}/sector_lab/data/index_close.csv", index_col=0)["Nifty 50"]
ck = cl.reindex(pd.MultiIndex.from_arrays([P.symbol, P.day])).to_numpy()
cc = cl.reindex(pd.MultiIndex.from_arrays([P.symbol, P.cutoff.fillna("")])).to_numpy()
r = ck / cc
nr = nifty.reindex(P.day).to_numpy() / nifty.reindex(P.cutoff.fillna("")).to_numpy()
has_next = P.qn.notna().to_numpy()
print(f"placebo rows in_fo: {len(P)}; with a next-result fundamentals row: {has_next.sum()}; "
      f"price ratio missing where a row exists: {int((np.isnan(r) & has_next).sum())}")
P["pe"] = P.pe * r
P["pe_vs_own3y_pct"] = 100 * (P.pe / P.pe_own3y_median - 1)
P["pe_vs_peers_pct"] = 100 * (P.pe / (P.pe_peer_median * nr) - 1)
P["log_mcap"] = P.log_mcap + np.log(r)
P["month"] = P.day.str[:7]
CP = labels(P)
lagP = (P.lag_pct < -10).to_numpy()
volP = (P.vol_ratio_5_60 >= 1.0).to_numpy()
PB = {"S85": lagP & volP, "S44": lagP & (P.vol_ratio_5_60 >= 1.3).to_numpy()}
print(f"placebo base rows: P100 {PB['S85'].sum()} ({(PB['S85'] & has_next).sum()} with fundamentals), "
      f"P130 {PB['S44'].sum()}")


# ------------------------------------------------------------------------------------------------ helpers
def side_stats(d, pre):
    y, tp, q = d.three_day.to_numpy(), d.tp3.to_numpy(), d.qn.to_numpy()
    n = len(y)
    out = {f"{pre}n": n}
    if n == 0:
        return out
    qm = pd.Series(y).groupby(q).mean()
    f, l_ = q <= 13, q >= 14
    ys = np.sort(y)
    out.update({f"{pre}mean": y.mean(), f"{pre}net": y.mean() - COST, f"{pre}tp": tp.mean(),
                f"{pre}up%": 100 * (y > 0).mean(), f"{pre}q": f"{(qm > 0).sum()}/{len(qm)}",
                f"{pre}n14": int(f.sum()), f"{pre}f14": y[f].mean() if f.any() else np.nan,
                f"{pre}n8": int(l_.sum()), f"{pre}l8": y[l_].mean() if l_.any() else np.nan,
                f"{pre}xb5": ys[:-5].mean() if n > 5 else np.nan})
    return out


def perm_test(y, q, lab, nperm=NPERM):
    """Within-quarter label permutation. Returns D, two-sided p, sd of the null."""
    o = np.argsort(q, kind="stable")
    y, q, lab = y[o], q[o], lab[o]
    if lab.all() or not lab.any():
        return np.nan, np.nan, np.nan
    D = y[lab].mean() - y[~lab].mean()
    Dp = np.empty(nperm)
    step = max(1, int(4e7 // max(len(y), 1)))
    for s in range(0, nperm, step):
        k = min(step, nperm - s)
        idx = np.argsort(q[None, :] + rng.random((k, len(y))), axis=1)
        L = lab[idx]
        nT = L.sum(1)
        sT = (L * y[None, :]).sum(1)
        Dp[s:s + k] = sT / nT - (y.sum() - sT) / (len(y) - nT)
    p = (np.sum(np.abs(Dp) >= abs(D) - 1e-12) + 1) / (nperm + 1)
    return D, p, Dp.std()


def cluster_boot_diff(y, lab, cl):
    if lab.all() or not lab.any():
        return np.nan, np.nan
    D = y[lab].mean() - y[~lab].mean()
    codes, uniq = pd.factorize(cl)
    K = len(uniq)
    sT = np.bincount(codes, weights=y * lab, minlength=K)
    nT = np.bincount(codes, weights=lab.astype(float), minlength=K)
    sF = np.bincount(codes, weights=y * ~lab, minlength=K)
    nF = np.bincount(codes, weights=(~lab).astype(float), minlength=K)
    W = rng.multinomial(K, np.full(K, 1 / K), size=NBOOT)
    with np.errstate(invalid="ignore", divide="ignore"):
        Db = (W @ sT) / (W @ nT) - (W @ sF) / (W @ nF)
    return D, np.nanstd(Db)


def cluster_boot_mean(y, cl):
    codes, uniq = pd.factorize(cl)
    K = len(uniq)
    s = np.bincount(codes, weights=y, minlength=K)
    n = np.bincount(codes, minlength=K).astype(float)
    W = rng.multinomial(K, np.full(K, 1 / K), size=NBOOT)
    b = (W @ s) / (W @ n)
    return y.mean(), np.percentile(b, 2.5), np.percentile(b, 97.5)


def holm(p):
    p = np.asarray(p, float)
    o = np.argsort(p)
    m = len(p)
    adj = np.empty(m)
    run = 0
    for r_, i in enumerate(o):
        run = max(run, (m - r_) * p[i])
        adj[i] = min(1, run)
    return adj


def bh(p):
    p = np.asarray(p, float)
    m = len(p)
    o = np.argsort(p)
    adj = np.empty(m)
    run = 1.0
    for r_ in range(m - 1, -1, -1):
        i = o[r_]
        run = min(run, p[i] * m / (r_ + 1))
        adj[i] = run
    return adj


def norm_p(z):
    from scipy.stats import norm
    return 2 * norm.sf(abs(z))


# ------------------------------------------------------------------------------------------------ splits
PQS = []


def splits(base, names, placebo=True):
    m = S[base]
    d = E[m].reset_index(drop=True)
    y, tp, q = d.three_day.to_numpy(), d.tp3.to_numpy(), d.qn.to_numpy()
    rest = ~m & np.isin(E.qn.to_numpy(), np.unique(q))           # other in_fo results, same quarters
    yr, qr = E.three_day.to_numpy()[rest], E.qn.to_numpy()[rest]
    rows = []
    for c in names:
        known, lab = CE[c][0][m], CE[c][1][m]
        r = {"split": c, "prior": PRIOR[c], "n_known": int(known.sum()), "n_unknown": int((~known).sum()),
             "unknown_mean": y[~known].mean() if (~known).any() else np.nan}
        dk = d[known]
        lk = lab[known]
        r.update(side_stats(dk[lk], "T_"))
        r.update(side_stats(dk[~lk], "F_"))
        yk, tk, qk = y[known], tp[known], q[known]
        D, p, sd = perm_test(yk, qk, lk)
        Dtp, ptp, _ = perm_test(tk, qk, lk)
        r.update({"D": D, "p_perm": p, "sd_null": sd, "D_tp": Dtp, "p_perm_tp": ptp})
        # quarter-demeaned difference (within-quarter comparison only)
        dm = yk - pd.Series(yk).groupby(qk).transform("mean").to_numpy()
        r["D_wq"] = dm[lk].mean() - dm[~lk].mean() if lk.any() and (~lk).any() else np.nan
        f, l_ = qk <= 13, qk >= 14
        r["D_f14"] = yk[f & lk].mean() - yk[f & ~lk].mean() if (f & lk).any() and (f & ~lk).any() else np.nan
        r["D_l8"] = yk[l_ & lk].mean() - yk[l_ & ~lk].mean() if (l_ & lk).any() and (l_ & ~lk).any() else np.nan
        r["minside_f14"] = int(min((f & lk).sum(), (f & ~lk).sum()))
        r["minside_l8"] = int(min((l_ & lk).sum(), (l_ & ~lk).sum()))
        # comparison 1: all other in_fo results in the same quarters
        kr, lr = CE[c][0][rest], CE[c][1][rest]
        Dr, _, sdr = perm_test(yr[kr], qr[kr], lr[kr], NPERM_REST)
        r.update({"rest_nT": int((kr & lr).sum()), "rest_nF": int((kr & ~lr).sum()),
                  "rest_meanT": yr[kr & lr].mean(), "rest_meanF": yr[kr & ~lr].mean(), "D_rest": Dr,
                  "z_vs_rest": (D - Dr) / np.sqrt(sd ** 2 + sdr ** 2)})
        r["p_vs_rest"] = norm_p(r["z_vs_rest"])
        # comparison 2: non-results placebo days
        if placebo and c in CP:
            pm = PB[base]
            pk, pl = CP[c][0][pm], CP[c][1][pm]
            py, pmo = P.three_day.to_numpy()[pm][pk], P.month.to_numpy()[pm][pk]
            Dp, sep = cluster_boot_diff(py, pl[pk], pmo)
            r.update({"plac_nT": int((pk & pl).sum()), "plac_nF": int((pk & ~pl).sum()),
                      "plac_meanT": py[pl[pk]].mean(), "plac_meanF": py[~pl[pk]].mean(), "D_plac": Dp,
                      "se_plac": sep, "z_vs_plac": (D - Dp) / np.sqrt(sd ** 2 + sep ** 2)})
        for side, sl in (("T", lk), ("F", ~lk)):
            g = pd.Series(yk[sl]).groupby(qk[sl]).agg(["size", "mean"])
            for qq, row in g.iterrows():
                PQS.append({"base": base, "split": c, "side": side, "qn": qq, "n": int(row["size"]),
                            "mean": row["mean"]})
        rows.append(r)
    T = pd.DataFrame(rows)
    T["p_holm"] = holm(T.p_perm.fillna(1))
    T["p_bh"] = bh(T.p_perm.fillna(1))
    sgn = np.sign(T.D)
    T["better_side"] = np.where(T.D > 0, "True", "False")
    T["a_both_halves"] = (sgn * T.D_f14 >= 1.0) & (sgn * T.D_l8 >= 1.0) & (T.minside_f14 >= 5) & (T.minside_l8 >= 5)
    T["b_holm05"] = T.p_holm < 0.05
    T["c_prior"] = (T.prior == "2s") | ((T.prior == "T") & (T.D > 0)) | ((T.prior == "F") & (T.D < 0))
    T["promoted"] = T.a_both_halves & T.b_holm05 & T.c_prior
    T["possible_chance"] = T.a_both_halves & (T.p_perm < 0.05) & ~T.b_holm05
    return T


SHOW = ["split", "prior", "n_known", "n_unknown", "unknown_mean", "T_n", "T_mean", "T_tp", "T_up%", "T_q", "T_n14",
        "T_f14", "T_n8", "T_l8", "T_xb5", "F_n", "F_mean", "F_tp", "F_up%", "F_q", "F_n14", "F_f14", "F_n8", "F_l8",
        "F_xb5", "D", "D_wq", "p_perm", "p_holm", "p_bh", "D_f14", "D_l8", "D_tp", "p_perm_tp"]
SHOW2 = ["split", "D", "rest_nT", "rest_nF", "rest_meanT", "rest_meanF", "D_rest", "z_vs_rest", "p_vs_rest",
         "plac_nT", "plac_nF", "plac_meanT", "plac_meanF", "D_plac", "se_plac", "z_vs_plac", "minside_f14",
         "minside_l8", "a_both_halves", "b_holm05", "c_prior", "promoted", "possible_chance"]
SPL = {}
for base in ("S85", "S44"):
    T = pd.concat([splits(base, PRE).assign(family="pre"), splits(base, POST, placebo=False).assign(family="post")])
    SPL[base] = T
    T.to_csv(f"{HERE}/splits_{base}.csv", index=False, float_format="%.4f")
    for fam in ("pre", "post"):
        t = T[T.family == fam]
        print(f"\n========== SPLITS on {base}, {fam}-results family (three_day %, gross; T = condition true) ==========")
        print(t[SHOW].round(3).to_string(index=False))
        print(t[[c for c in SHOW2 if c in t]].round(3).to_string(index=False))
pd.DataFrame(PQS).to_csv(f"{HERE}/per_quarter_splits.csv", index=False, float_format="%.4f")

# ------------------------------------------------------------------------------------------------ rule reports
QALL = E.qn.to_numpy()
Y = E.three_day.to_numpy()
QIDX = {qq: np.flatnonzero(QALL == qq) for qq in np.unique(QALL)}


def luck(mask, pool=None):
    """Share of random same-size-per-quarter picks (from all in_fo results of that quarter, or from `pool`) with mean
    >= the rule's mean (one-sided)."""
    obs = Y[mask].mean()
    tot = np.zeros(NLUCK)
    n = 0
    for qq, idx in QIDX.items():
        if pool is not None:
            idx = idx[pool[idx]]
        k = int(mask[idx].sum())
        if k == 0:
            continue
        pick = np.argsort(rng.random((NLUCK, len(idx))), axis=1)[:, :k]
        tot += Y[idx][pick].sum(1)
        n += k
    rnd = tot / n
    return (np.sum(rnd >= obs - 1e-12) + 1) / (NLUCK + 1), rnd.mean()


PERQ = []


def rule_report(name, mask, pmask, parent=None):
    d = E[mask]
    r = {"rule": name}
    r.update(side_stats(d, ""))
    if len(d) == 0:
        return r
    r["tp_net"] = d.tp3.mean() - COST
    r["luck_p"], r["rand_mean"] = luck(mask)
    r["in_S85"] = int((mask & S["S85"]).sum())
    r["not_S85_n"] = int((mask & ~S["S85"]).sum())
    r["not_S85_mean"] = Y[mask & ~S["S85"]].mean() if r["not_S85_n"] else np.nan
    if parent is not None:                                   # parent trades the screen removed
        rem = parent & ~mask
        r["parent_n"], r["parent_mean"] = int(parent.sum()), Y[parent].mean()
        r["removed_n"], r["removed_mean"] = int(rem.sum()), Y[rem].mean() if rem.any() else np.nan
        r["luck_within_parent_p"], _ = luck(mask, pool=parent)
    py = P.three_day.to_numpy()[pmask]
    r["plac_n"] = int(pmask.sum())
    if pmask.sum():
        r["plac_mean"], r["plac_lo"], r["plac_hi"] = cluster_boot_mean(py, P.month.to_numpy()[pmask])
    g = d.groupby("qn").agg(n=("three_day", "size"), mean=("three_day", "mean"), tp=("tp3", "mean"))
    for qq, row in g.iterrows():
        PERQ.append({"rule": name, "qn": qq, "n": int(row.n), "mean": row["mean"], "tp_mean": row.tp,
                     "symbols": " ".join(f"{s} {v:+.1f}" for s, v in zip(d[d.qn == qq].symbol, d[d.qn == qq].three_day))})
    return r


RSHOW = ["rule", "n", "mean", "net", "tp", "tp_net", "up%", "q", "n14", "f14", "n8", "l8", "xb5", "luck_p",
         "rand_mean", "in_S85", "not_S85_n", "not_S85_mean", "parent_n", "parent_mean", "removed_n", "removed_mean",
         "luck_within_parent_p", "plac_n", "plac_mean", "plac_lo", "plac_hi"]

print("\n==================== REFERENCE RULES (not counted) ====================")
refs = [rule_report("S85 lag<-10 & vol>=1.0", S["S85"], PB["S85"]),
        rule_report("S44 lag<-10 & vol>=1.3", S["S44"], PB["S44"]),
        rule_report("lag<-10 alone", lagE, lagP), rule_report("vol>=1.0 alone", volE, volP),
        rule_report("all in_fo results", np.ones(len(E), bool), np.ones(len(P), bool))]
print(pd.DataFrame(refs)[[c for c in RSHOW if c in pd.DataFrame(refs)]].round(3).to_string(index=False))

print("\n==================== PROMOTION (pre-registered rule, decided on S85, pre-results splits) =================")
T = SPL["S85"][SPL["S85"].family == "pre"]
print(T[["split", "prior", "D", "p_perm", "p_holm", "D_f14", "D_l8", "minside_f14", "minside_l8", "a_both_halves",
         "b_holm05", "c_prior", "promoted", "possible_chance"]].round(3).to_string(index=False))
ref_rows = []
for _, row in T[T.promoted].iterrows():
    c = row.split
    for base in ("S85", "S44"):
        k, l_ = CE[c]
        kp, lp = CP[c]
        lab, plab = (k & l_, kp & lp) if row.better_side == "True" else (k & ~l_, kp & ~lp)
        ref_rows.append(rule_report(f"{base} + {c}={row.better_side}", S[base] & lab, PB[base] & plab, parent=S[base]))
if ref_rows:
    R = pd.DataFrame(ref_rows)
    R.to_csv(f"{HERE}/refined_rules.csv", index=False, float_format="%.4f")
    print(R[[c for c in RSHOW if c in R]].round(3).to_string(index=False))
else:
    print("No split met the promotion rule -> no refined rule.")
pc = T[T.possible_chance]
if len(pc):
    print("Passed both halves and raw p < 0.05 but failed Holm (possible chance, NOT promoted):", list(pc.split))

print("\n==================== REPLACEMENT RULES (all in_fo results; luck vs random same-quarter picks) ===========")
rep = []
for c in ["F1_quality", "F11_good_fund", "F2_profitable_4q", "F9_piotroski_high", "F7_cheap_own3y"]:
    g, gp = CE[c][0] & CE[c][1], CP[c][0] & CP[c][1]
    rep.append(rule_report(f"{c} + lag<-10 (no volume)", g & lagE, gp & lagP, parent=lagE))
    rep.append(rule_report(f"{c} + vol>=1.0 (no lag)", g & volE, gp & volP, parent=volE))
    rep.append(rule_report(f"{c} alone", g, gp, parent=CE[c][0]))
R = pd.DataFrame(rep)
R["luck_holm"] = holm(R.luck_p)
R.to_csv(f"{HERE}/replacement_rules.csv", index=False, float_format="%.4f")
print(R[[c for c in RSHOW + ["luck_holm"] if c in R]].round(3).to_string(index=False))
pd.DataFrame(PERQ).to_csv(f"{HERE}/per_quarter_rules.csv", index=False, float_format="%.4f")

# ------------------------------------------------------------------------------------------------ trade list + prevalence
cols = ["symbol", "quarter", "qn", "cutoff", "industry", "fin_type", "lag_pct", "vol_ratio_5_60", "three_day", "tp3",
        "roe_pct", "debt_equity", "loss_any_4q", "l1_pat_yoy_pct", "l1_sales_yoy_pct", "pat_yoy_accel_pp",
        "sales_yoy_accel_pp", "l1_ebitda_margin_chg_yoy_pp", "l1_net_margin_chg_yoy_pp", "pe", "pe_vs_own3y_pct",
        "pe_vs_peers_pct", "piotroski_n", "piotroski_frac", "mcap_cr", "rq_sales_yoy_pct", "rq_pat_yoy_pct",
        "rq_pat_surprise_vs_trend_pp", "react_excess_nifty"]
out = E[S["S85"]][cols].copy()
for c in CE:
    k, l_ = CE[c][0][S["S85"]], CE[c][1][S["S85"]]
    out[c] = np.where(k, l_.astype(int), -1)                      # 1 true, 0 false, -1 unknown
out.sort_values(["qn", "cutoff", "symbol"]).to_csv(f"{HERE}/trades_S85_with_fa.csv", index=False, float_format="%.3f")
prev = pd.DataFrame({
    "S85_known": {c: CE[c][0][S["S85"]].sum() for c in CE},
    "S85_true_share": {c: CE[c][1][S["S85"] & CE[c][0]].mean() for c in CE},
    "all_in_fo_true_share": {c: CE[c][1][CE[c][0]].mean() for c in CE},
    "P100_true_share": {c: CP[c][1][PB["S85"] & CP[c][0]].mean() if c in CP else np.nan for c in CE}})
prev.to_csv(f"{HERE}/prevalence.csv", float_format="%.3f")
print("\n==================== PREVALENCE (share true among known) ====================")
print(prev.round(3).to_string())
n_things = 2 * len(PRE) + 2 * len(POST) + len(rep) + len(ref_rows)
print(f"\nThings tested (pre-registered count): {2 * len(PRE)} pre splits + {2 * len(POST)} post splits + "
      f"{len(rep)} replacement rules + {len(ref_rows)} refined rules = {n_things}")
