"""PART 1 - 2-condition TA+FA pairs on the lag-10% + volume rule, exactly as pre-registered in PREREGISTRATION.txt
(written before any outcome was looked at against a pair). Pairs, with the expected better side:
  X1 quality & rsi14<30 [T] | X2 profitable 4q & hammer/bull engulf [T] | X3 cheap vs own P/E & below lower BB [T]
  X4 sales & PAT growing YoY & MACD hist rising [T] | X5 Piotroski >= 5/7 & oversold count >= 3 [T]
  X6 large cap (prev-season median) & rsi14<30 [T] | X7 good fundamentals & ADX>25 with -DI>+DI [two-sided]
  X8 good fundamentals & oversold >= 3 [T] | X9 profitable 4q & close > SMA200 [T]
  X10 cheap vs peers & within 5% of 52w low [T] | X11 good fundamentals & OBV bullish divergence [T]
  X12 loss in any of 4q & strong downtrend [F]
Promotion: >= 1pp better in both halves (>= 5 known each side each half), Holm AND family-wise maxT p < 0.05 over the
12 on S85, prior side, and D beats the non-results placebo D.

    python3 part1_pairs.py      (writes part1_*.csv and part1_run.log here)
"""
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.environ.get('LAB_ROOT', 'lab') + ""
TA = f"{SCR}/ta/build"
REPO = os.environ.get('REPO_ROOT', '.') + "/results/lag10_volume"
COST = 0.17
NPERM, NPERM_REST, NBOOT, NLUCK = 20000, 4000, 2000, 20000
rng = np.random.default_rng(20261009)
pd.set_option("display.width", 280, "display.max_columns", 90, "display.max_rows", 400)


class Tee:
    def __init__(self, path):
        self.f = open(path, "w")

    def write(self, s):
        self.f.write(s)
        sys.__stdout__.write(s)

    def flush(self):
        self.f.flush()
        sys.__stdout__.flush()


sys.stdout = Tee(f"{HERE}/part1_run.log")

# ------------------------------------------------------------------------------------------------ data
F = pd.read_csv(f"{SCR}/fa/build/fa_panel.csv")
F = F[[c for c in F.columns if not c.startswith("rq_")]]
TACOLS = ["rsi14", "rsi2", "stoch_k14", "bb_pctb", "cci20", "mfi14", "close_vs_sma200_pct", "dist_52w_low_pct",
          "cdl_hammer", "cdl_bull_engulf", "adx14", "minus_di14", "plus_di14", "obv_div20"]
E0 = pd.read_csv(f"{TA}/events_ta.csv", usecols=["symbol", "quarter", "qn", "cutoff", "in_fo", "lag_pct",
                                                 "vol_ratio_5_60", "three_day", "take_profit"] + TACOLS)
M = pd.read_csv(f"{SCR}/ta/B_on_lag_rule/macd_prev.csv.gz")
E0 = E0.merge(M, left_on=["symbol", "cutoff"], right_on=["symbol", "day"], how="left").drop(columns="day")
E = F.merge(E0.rename(columns={"three_day": "three_day_ta", "qn": "qn_ta", "cutoff": "cutoff_ta", "in_fo": "in_fo_ta"}),
            on=["symbol", "quarter"], how="left", validate="1:1")
assert (E.qn == E.qn_ta).all() and (E.cutoff == E.cutoff_ta).all()
E = E[(E.in_fo == True) & E.three_day.notna()].reset_index(drop=True)
assert E[TACOLS + ["macd_hist_rising", "lag_pct", "vol_ratio_5_60"]].notna().all().all(), "TA missing in events"
print(f"in_fo results with three_day: {len(E)}; max |three_day - TA panel| {np.abs(E.three_day - E.three_day_ta).max():.1e}"
      f", max |tp3 - take_profit| {np.abs(E.tp3 - E.take_profit).max():.1e}")

MED_ALL = F[F.in_fo == True].groupby("qn").log_mcap.median()
MED_PREV = {q: MED_ALL.get(q - 1, MED_ALL[q]) for q in MED_ALL.index}          # previous season's median (PIT)


def fa_parts(d, size_q):
    """name -> (known, true). size_q: season whose median log_mcap applies to each row."""
    c = {}
    comp = (d.fin_type == "Company").to_numpy()
    roe, de = d.roe_pct.to_numpy(float), d.debt_equity.to_numpy(float)
    k = ~np.isnan(roe) & (~comp | ~np.isnan(de))
    c["quality"] = (k, k & (roe > 15) & (~comp | (de < 0.5)))
    l4 = d.loss_any_4q.to_numpy(float)
    c["prof4q"] = (~np.isnan(l4), l4 == 0)
    c["loss4q"] = (~np.isnan(l4), l4 == 1)
    for name, col in (("cheap_own", "pe_vs_own3y_pct"), ("cheap_peers", "pe_vs_peers_pct")):
        v = d[col].to_numpy(float)
        c[name] = (~np.isnan(v), v < 0)
    py, sy = d.l1_pat_yoy_pct.to_numpy(float), d.l1_sales_yoy_pct.to_numpy(float)
    g, b = (sy > 0) & (py > 0), (sy <= 0) | (py <= 0)
    c["growing"] = (g | b, g)
    pn, pf = d.piotroski_n.to_numpy(float), d.piotroski_frac.to_numpy(float)
    k = (pn >= 5) & ~np.isnan(pf)
    c["pio_high"] = (k, k & (pf >= 5 / 7 - 1e-9))
    v = d.log_mcap.to_numpy(float)
    med = pd.Series(size_q).map(MED_PREV).to_numpy(float)
    c["large"] = (~np.isnan(v) & ~np.isnan(med), v > med)
    good = (l4 == 0) & (py > 0) & (sy > 0)
    bad = (l4 == 1) | (py <= 0) | (sy <= 0)
    c["good_fund"] = (good | bad, good)
    return c


def ta_parts(d):
    c = {"rsi30": d.rsi14 < 30, "bullc": (d.cdl_hammer == 1) | (d.cdl_bull_engulf == 1), "belowbb": d.bb_pctb < 0,
         "macdup": d.macd_hist_rising == 1,
         "os3": ((d.rsi14 < 30).astype(int) + (d.rsi2 < 10) + (d.stoch_k14 < 20) + (d.bb_pctb < 0) + (d.cci20 < -100)
                 + (d.mfi14 < 20)) >= 3,
         "sdown": (d.adx14 > 25) & (d.minus_di14 > d.plus_di14), "above200": d.close_vs_sma200_pct > 0,
         "near52": d.dist_52w_low_pct <= 5, "obvdiv": d.obv_div20 == 1}
    return {k: v.to_numpy(bool) for k, v in c.items()}


PAIRS = [("X1_quality&rsi30", "quality", "rsi30", "T"), ("X2_prof4q&bullcandle", "prof4q", "bullc", "T"),
         ("X3_cheapown&belowBB", "cheap_own", "belowbb", "T"), ("X4_growing&macdup", "growing", "macdup", "T"),
         ("X5_piohigh&oversold3", "pio_high", "os3", "T"), ("X6_large&rsi30", "large", "rsi30", "T"),
         ("X7_goodfund&strongdown", "good_fund", "sdown", "2s"), ("X8_goodfund&oversold3", "good_fund", "os3", "T"),
         ("X9_prof4q&above200", "prof4q", "above200", "T"), ("X10_cheappeers&near52wlow", "cheap_peers", "near52", "T"),
         ("X11_goodfund&obvdiv", "good_fund", "obvdiv", "T"), ("X12_loss4q&strongdown", "loss4q", "sdown", "F")]
NAMES = [p[0] for p in PAIRS]
PRIOR = {p[0]: p[3] for p in PAIRS}


def pair_labels(fa, ta):
    out = {}
    for name, f, t, _ in PAIRS:
        k, tf = fa[f]
        out[name] = (k, k & tf & ta[t], f, t)
    return out


FAE, TAE = fa_parts(E, E.qn.to_numpy()), ta_parts(E)
CE = pair_labels(FAE, TAE)

# ------------------------------------------------------------------------------------------------ base sets + check
lagE = (E.lag_pct < -10).to_numpy()
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
          f"max |lag - ref x100| {np.abs(j.lag_pct - 100 * j.vs_nifty_1m).max():.2e}, "
          f"max |vol - ref| {np.abs(j.vol_ratio_5_60 - j.volume_ratio).max():.2e}; mean three_day {mine.three_day.mean():.3f}"
          f" (ref {100 * ref.three_day.mean():.3f}), tp {mine.tp3.mean():.3f}")
    assert same and len(mine) == len(ref)
    S[name] = m

# ------------------------------------------------------------------------------------------------ placebo days
PCOLS = ["symbol", "day", "in_fo", "qn_next", "lag_pct", "vol_ratio_5_60", "three_day", "take_profit"] + TACOLS
P = pd.read_csv(f"{TA}/placebo_ta.csv.gz", usecols=PCOLS)
P = P[(P.in_fo == True)].merge(M, on=["symbol", "day"], how="left")
P = P[P[TACOLS + ["macd_hist_rising", "lag_pct", "vol_ratio_5_60"]].notna().all(axis=1)]
P = P[(P.lag_pct < -10) & (P.vol_ratio_5_60 >= 1.0)].reset_index(drop=True)     # only lag+volume days are used
FN = F.drop(columns=["three_day", "tp3", "in_fo"], errors="ignore")
P = P.merge(FN, left_on=["symbol", "qn_next"], right_on=["symbol", "qn"], how="left")
adj = pd.read_csv(f"{TA}/adjusted_ohlcv.csv.gz", usecols=["day", "symbol", "close"]).dropna()
cl = adj.set_index(["symbol", "day"]).close
nifty = pd.read_csv(f"{SCR}/sector_lab/data/index_close.csv", index_col=0)["Nifty 50"]
r = cl.reindex(pd.MultiIndex.from_arrays([P.symbol, P.day])).to_numpy() / \
    cl.reindex(pd.MultiIndex.from_arrays([P.symbol, P.cutoff.fillna("")])).to_numpy()
nr = nifty.reindex(P.day).to_numpy() / nifty.reindex(P.cutoff.fillna("")).to_numpy()
has_next = P.qn.notna().to_numpy()
print(f"placebo lag+vol>=1.0 days (in_fo, TA complete): {len(P)}; with a next-result FA row {has_next.sum()}; "
      f"price ratio missing where a row exists {int((np.isnan(r) & has_next).sum())}")
P["pe"] = P.pe * r
P["pe_vs_own3y_pct"] = 100 * (P.pe / P.pe_own3y_median - 1)
P["pe_vs_peers_pct"] = 100 * (P.pe / (P.pe_peer_median * nr) - 1)
P["log_mcap"] = P.log_mcap + np.log(r)
P["month"] = P.day.str[:7]
FAP = fa_parts(P, P.qn.fillna(-99).to_numpy())
CP = pair_labels(FAP, ta_parts(P))
PB = {"S85": np.ones(len(P), bool), "S44": (P.vol_ratio_5_60 >= 1.3).to_numpy()}
print(f"placebo base rows: P100 {PB['S85'].sum()}, P130 {PB['S44'].sum()}")


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


def perm_D(y, q, lab, nperm):
    """Within-quarter label permutation: D, two-sided p, null sd."""
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
    return D, (np.sum(np.abs(Dp) >= abs(D) - 1e-12) + 1) / (nperm + 1), Dp.std()


def cluster_boot_diff(y, lab, cl_):
    if lab.all() or not lab.any():
        return np.nan, np.nan
    D = y[lab].mean() - y[~lab].mean()
    codes, uniq = pd.factorize(cl_)
    K = len(uniq)
    sT = np.bincount(codes, weights=y * lab, minlength=K)
    nT = np.bincount(codes, weights=lab.astype(float), minlength=K)
    sF = np.bincount(codes, weights=y * ~lab, minlength=K)
    nF = np.bincount(codes, weights=(~lab).astype(float), minlength=K)
    W = rng.multinomial(K, np.full(K, 1 / K), size=NBOOT)
    with np.errstate(invalid="ignore", divide="ignore"):
        Db = (W @ sT) / (W @ nT) - (W @ sF) / (W @ nF)
    return D, np.nanstd(Db)


def cluster_boot_mean(y, cl_):
    codes, uniq = pd.factorize(cl_)
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


def maxT(y, q, labs, nperm=NPERM):
    """Westfall-Young single-step maxT: joint within-quarter permutations of y (all base-set trades); each split's D
    over its known rows, standardised by its own sd under this joint null; labs = list of (known, lab)."""
    ok = [(k & l).any() and (k & ~l).any() for k, l in labs]
    D_obs = np.array([y[k & l].mean() - y[k & ~l].mean() if g else np.nan for (k, l), g in zip(labs, ok)])
    o = np.argsort(q, kind="stable")
    yq, qq = y[o], q[o]
    labs_o = [(k[o], l[o]) for k, l in labs]
    Dp = np.full((nperm, len(labs)), np.nan)
    step = 2000
    for s in range(0, nperm, step):
        k_ = min(step, nperm - s)
        idx = np.argsort(qq[None, :] + rng.random((k_, len(yq))), axis=1)   # permutation within quarter
        Yp = yq[idx]                                                        # permuted outcomes, same positions
        for j, ((kn, lb), g) in enumerate(zip(labs_o, ok)):
            if g:
                Dp[s:s + k_, j] = Yp[:, kn & lb].mean(1) - Yp[:, kn & ~lb].mean(1)
    sd = np.nanstd(Dp, axis=0)
    mx = np.nanmax(np.abs(Dp) / sd, axis=1)
    z_obs = np.abs(D_obs) / sd
    return np.array([(np.sum(mx >= z - 1e-12) + 1) / (nperm + 1) if np.isfinite(z) else np.nan for z in z_obs])


# ------------------------------------------------------------------------------------------------ splits
PQS, CELLS = [], []


def splits(base):
    m = S[base]
    d = E[m].reset_index(drop=True)
    y, tp, q = d.three_day.to_numpy(), d.tp3.to_numpy(), d.qn.to_numpy()
    rest = ~m & np.isin(E.qn.to_numpy(), np.unique(q))
    yr, qr = E.three_day.to_numpy()[rest], E.qn.to_numpy()[rest]
    rows, labs = [], []
    for c in NAMES:
        knownA, labA, fpart, tpart = CE[c]
        known, lab = knownA[m], labA[m]
        labs.append((known, lab))
        r = {"pair": c, "prior": PRIOR[c], "n_known": int(known.sum()), "n_unknown": int((~known).sum()),
             "unknown_mean": y[~known].mean() if (~known).any() else np.nan}
        dk, lk = d[known], lab[known]
        r.update(side_stats(dk[lk], "T_"))
        r.update(side_stats(dk[~lk], "F_"))
        yk, tk, qk = y[known], tp[known], q[known]
        D, p, sd = perm_D(yk, qk, lk, NPERM)
        Dtp, ptp, _ = perm_D(tk, qk, lk, NPERM)
        r.update({"D": D, "p_perm": p, "sd_null": sd, "D_tp": Dtp, "p_perm_tp": ptp})
        f, l_ = qk <= 13, qk >= 14
        r["D_f14"] = yk[f & lk].mean() - yk[f & ~lk].mean() if (f & lk).any() and (f & ~lk).any() else np.nan
        r["D_l8"] = yk[l_ & lk].mean() - yk[l_ & ~lk].mean() if (l_ & lk).any() and (l_ & ~lk).any() else np.nan
        r["minside_f14"] = int(min((f & lk).sum(), (f & ~lk).sum()))
        r["minside_l8"] = int(min((l_ & lk).sum(), (l_ & ~lk).sum()))
        # parts alone inside the base set (all rows where that part is known / always for TA)
        fk, ft = FAE[fpart][0][m], FAE[fpart][1][m]
        tt = TAE[tpart][m]
        r.update({"FApart_true_n": int((fk & ft).sum()), "FApart_true_mean": y[fk & ft].mean() if (fk & ft).any() else np.nan,
                  "TApart_true_n": int(tt.sum()), "TApart_true_mean": y[tt].mean() if tt.any() else np.nan})
        for fa_s, fa_m in (("FA_T", fk & ft), ("FA_F", fk & ~ft)):
            for ta_s, ta_m in (("TA_T", tt), ("TA_F", ~tt)):
                cm = fa_m & ta_m
                CELLS.append({"base": base, "pair": c, "cell": f"{fa_s}&{ta_s}", "n": int(cm.sum()),
                              "mean": y[cm].mean() if cm.any() else np.nan,
                              "tp": tp[cm].mean() if cm.any() else np.nan})
        # other in_fo results of the same quarters
        kr, lr = knownA[rest], labA[rest]
        Dr, _, sdr = perm_D(yr[kr], qr[kr], lr[kr], NPERM_REST)
        r.update({"rest_nT": int((kr & lr).sum()), "rest_meanT": yr[kr & lr].mean() if (kr & lr).any() else np.nan,
                  "rest_meanF": yr[kr & ~lr].mean(), "D_rest": Dr})
        # non-results placebo days
        pm = PB[base]
        pk, pl = CP[c][0][pm], CP[c][1][pm]
        py, pmo = P.three_day.to_numpy()[pm][pk], P.month.to_numpy()[pm][pk]
        Dp, sep = cluster_boot_diff(py, pl[pk], pmo)
        r.update({"plac_nT": int((pk & pl).sum()), "plac_nF": int((pk & ~pl).sum()),
                  "plac_meanT": py[pl[pk]].mean() if pl[pk].any() else np.nan, "plac_meanF": py[~pl[pk]].mean(),
                  "D_plac": Dp, "se_plac": sep, "z_vs_plac": (D - Dp) / np.sqrt(sd ** 2 + sep ** 2)})
        for side, sl in (("T", lk), ("F", ~lk)):
            g = pd.Series(yk[sl]).groupby(qk[sl]).agg(["size", "mean"])
            for qq, row in g.iterrows():
                PQS.append({"base": base, "pair": c, "side": side, "qn": qq, "n": int(row["size"]), "mean": row["mean"]})
        rows.append(r)
    T = pd.DataFrame(rows)
    T["p_holm"] = holm(T.p_perm.fillna(1))
    T["p_bh"] = bh(T.p_perm.fillna(1))
    T["p_fw_maxT"] = maxT(y, q, labs)
    sgn = np.sign(T.D)
    T["better_side"] = np.where(T.D > 0, "True", "False")
    T["a_both_halves"] = (sgn * T.D_f14 >= 1.0) & (sgn * T.D_l8 >= 1.0) & (T.minside_f14 >= 5) & (T.minside_l8 >= 5)
    T["b_adjusted"] = (T.p_holm < 0.05) & (T.p_fw_maxT < 0.05)
    T["c_prior"] = (T.prior == "2s") | ((T.prior == "T") & (T.D > 0)) | ((T.prior == "F") & (T.D < 0))
    T["d_beats_placebo"] = sgn * (T.D - T.D_plac) > 0
    T["promoted"] = T.a_both_halves & T.b_adjusted & T.c_prior & T.d_beats_placebo
    T["possible_chance"] = T.a_both_halves & (T.p_perm < 0.05) & ~T.b_adjusted
    # adds to its parts: AND side better (in the better side's direction) than each part's true side
    T["adds_to_parts"] = np.where(T.D > 0, (T.T_mean > T.FApart_true_mean) & (T.T_mean > T.TApart_true_mean),
                                  (T.T_mean < T.FApart_true_mean) & (T.T_mean < T.TApart_true_mean))
    return T


SHOW = ["pair", "prior", "n_known", "n_unknown", "unknown_mean", "T_n", "T_mean", "T_net", "T_tp", "T_up%", "T_q",
        "T_n14", "T_f14", "T_n8", "T_l8", "T_xb5", "F_n", "F_mean", "F_tp", "F_up%", "F_q", "F_n14", "F_f14", "F_n8",
        "F_l8", "F_xb5"]
SHOW2 = ["pair", "D", "p_perm", "p_holm", "p_bh", "p_fw_maxT", "D_f14", "D_l8", "D_tp", "p_perm_tp",
         "FApart_true_n", "FApart_true_mean", "TApart_true_n", "TApart_true_mean", "rest_nT", "rest_meanT",
         "rest_meanF", "D_rest", "plac_nT", "plac_nF", "plac_meanT", "plac_meanF", "D_plac", "se_plac", "z_vs_plac"]
SHOW3 = ["pair", "minside_f14", "minside_l8", "a_both_halves", "b_adjusted", "c_prior", "d_beats_placebo",
         "promoted", "possible_chance", "adds_to_parts"]
SPL = {}
for base in ("S85", "S44"):
    T = splits(base)
    SPL[base] = T
    T.to_csv(f"{HERE}/part1_splits_{base}.csv", index=False, float_format="%.4f")
    print(f"\n========== PAIRS on {base} (three_day %, gross; T = FA part AND TA part true; known = FA part known) ==========")
    print(T[SHOW].round(2).to_string(index=False))
    print(T[SHOW2].round(3).to_string(index=False))
    print(T[SHOW3].to_string(index=False))
pd.DataFrame(PQS).to_csv(f"{HERE}/part1_per_quarter_splits.csv", index=False, float_format="%.4f")
C = pd.DataFrame(CELLS)
C.to_csv(f"{HERE}/part1_cells_2x2.csv", index=False, float_format="%.4f")
print("\n========== 2x2 cells on S85 (n / mean three_day) ==========")
cc = C[C.base == "S85"].assign(v=lambda x: x.n.astype(str) + " / " + x["mean"].round(2).astype(str))
print(cc.pivot(index="pair", columns="cell", values="v").reindex(NAMES).to_string())

# ------------------------------------------------------------------------------------------------ refined rules
QALL, Y = E.qn.to_numpy(), E.three_day.to_numpy()
QIDX = {qq: np.flatnonzero(QALL == qq) for qq in np.unique(QALL)}


def luck(mask, pool=None):
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


T = SPL["S85"]
print("\n==================== PROMOTION (S85, three_day) ====================")
print(T[["pair", "prior", "D", "p_perm", "p_holm", "p_fw_maxT", "D_f14", "D_l8"] + SHOW3[1:]].round(3).to_string(index=False))
ref_rows = []
for _, row in T[T.promoted].iterrows():
    c = row.pair
    for base in ("S85", "S44"):
        k, l_ = CE[c][0], CE[c][1]
        mask = S[base] & ((k & l_) if row.better_side == "True" else (k & ~l_))
        pk, pl = CP[c][0], CP[c][1]
        pmask = PB[base] & ((pk & pl) if row.better_side == "True" else (pk & ~pl))
        rr = {"rule": f"{base} + {c}={row.better_side}"}
        rr.update(side_stats(E[mask], ""))
        rr["tp_net"] = E[mask].tp3.mean() - COST
        rr["luck_p"], rr["rand_mean"] = luck(mask)
        rr["luck_within_parent_p"], _ = luck(mask, pool=S[base])
        rr["plac_n"] = int(pmask.sum())
        if pmask.any():
            rr["plac_mean"], rr["plac_lo"], rr["plac_hi"] = cluster_boot_mean(P.three_day.to_numpy()[pmask],
                                                                              P.month.to_numpy()[pmask])
        ref_rows.append(rr)
if ref_rows:
    R = pd.DataFrame(ref_rows)
    R.to_csv(f"{HERE}/part1_refined_rules.csv", index=False, float_format="%.4f")
    print(R.round(3).to_string(index=False))
else:
    print("No pair met the promotion rule -> no refined rule.")
pc = T[T.possible_chance]
print("Passed both halves and raw p < 0.05 but failed the adjustment (possible chance, NOT promoted):",
      list(pc.pair) if len(pc) else "none")

# trade list with the pair flags
out = E[S["S85"]][["symbol", "quarter", "qn", "cutoff", "lag_pct", "vol_ratio_5_60", "three_day", "tp3"]].copy()
for c in NAMES:
    k, l_ = CE[c][0][S["S85"]], CE[c][1][S["S85"]]
    out[c] = np.where(k, l_.astype(int), -1)
out.sort_values(["qn", "cutoff", "symbol"]).to_csv(f"{HERE}/part1_trades_S85_flags.csv", index=False, float_format="%.3f")
print(f"\nThings tested (pre-registered): {2 * len(NAMES)} splits (12 on S85 = main family, 12 on S44) "
      f"+ {len(ref_rows)} refined rules")
