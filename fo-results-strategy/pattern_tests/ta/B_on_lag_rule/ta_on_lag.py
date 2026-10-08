"""TA filters on top of the lag-10% + volume rule, exactly as pre-registered in PREREGISTRATION.txt.

    python3 ta_on_lag.py      (reads ../build/events_ta.csv, ../build/placebo_ta.csv.gz, macd_prev.csv.gz; writes here)

Outputs: run.log, splits_S85.csv, splits_S44.csv, replacement_rules.csv, refined_rules.csv (if any promoted),
         per_quarter_rules.csv, trades_S85_with_ta.csv
"""
import os
import sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(os.path.dirname(HERE), "build")
REPO = os.environ.get('REPO_ROOT', '.') + "/results/lag10_volume"
COST = 0.17
NPERM, NBOOT, NLUCK = 20000, 2000, 20000
rng = np.random.default_rng(20261008)
pd.set_option("display.width", 250, "display.max_columns", 60, "display.max_rows", 200)


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
E = pd.read_csv(f"{BUILD}/events_ta.csv")
E = E[(E.in_fo == True) & E.three_day.notna()].reset_index(drop=True)
P = pd.read_csv(f"{BUILD}/placebo_ta.csv.gz", low_memory=False)
P = P[P.in_fo == True].reset_index(drop=True)
M = pd.read_csv(f"{HERE}/macd_prev.csv.gz")
E = E.merge(M, left_on=["symbol", "cutoff"], right_on=["symbol", "day"], how="left").drop(columns="day")
P = P.merge(M, on=["symbol", "day"], how="left")
P["month"] = P.day.str[:7]
print(f"in_fo events with three_day: {len(E)}  (mean three_day {E.three_day.mean():.3f}%)")

USED = ["rsi14", "rsi2", "stoch_k14", "bb_pctb", "cci20", "mfi14", "macd_bull_x3", "macd_hist_rising",
        "close_vs_sma200_pct", "golden_state", "dist_52w_low_pct", "don20_break_dn", "cdl_hammer", "cdl_bull_engulf",
        "nr7", "adx14", "minus_di14", "plus_di14", "obv_div20", "gap_pct", "cdl_doji", "lag_pct", "vol_ratio_5_60"]
assert E[USED].notna().all().all(), "missing indicator in events"
nP = len(P)
P = P[P[USED].notna().all(axis=1)].reset_index(drop=True)
print(f"in_fo placebo rows: {nP}, with every used indicator: {len(P)}")


def conds(d):
    c = {}
    c["C1_rsi14_lt30"] = d.rsi14 < 30
    c["C2_rsi2_lt10"] = d.rsi2 < 10
    c["C3_stoch_lt20"] = d.stoch_k14 < 20
    c["C4_below_lower_bb"] = d.bb_pctb < 0
    c["C5_cci_lt_m100"] = d.cci20 < -100
    c["C6_mfi_lt20"] = d.mfi14 < 20
    c["C7_oversold_ge3"] = (c["C1_rsi14_lt30"].astype(int) + c["C2_rsi2_lt10"] + c["C3_stoch_lt20"]
                            + c["C4_below_lower_bb"] + c["C5_cci_lt_m100"] + c["C6_mfi_lt20"]) >= 3
    c["C8_macd_bull_x3"] = d.macd_bull_x3 == 1
    c["C9_macd_hist_rising"] = d.macd_hist_rising == 1
    c["C10_above_sma200"] = d.close_vs_sma200_pct > 0
    c["C11_golden_state"] = d.golden_state == 1
    c["C12_near_52w_low"] = d.dist_52w_low_pct <= 5
    c["C13_don20_break_dn"] = d.don20_break_dn == 1
    c["C14_bull_candle"] = (d.cdl_hammer == 1) | (d.cdl_bull_engulf == 1)
    c["C15_nr7"] = d.nr7 == 1
    c["C16_strong_downtrend"] = (d.adx14 > 25) & (d.minus_di14 > d.plus_di14)
    c["C17_obv_bull_div"] = d.obv_div20 == 1
    c["C18_gap_down"] = d.gap_pct <= -1.0
    c["C19_doji"] = d.cdl_doji == 1
    return {k: v.to_numpy(bool) for k, v in c.items()}


TA_PRIOR = {"C1_rsi14_lt30": "T", "C2_rsi2_lt10": "T", "C3_stoch_lt20": "T", "C4_below_lower_bb": "T",
            "C5_cci_lt_m100": "T", "C6_mfi_lt20": "T", "C7_oversold_ge3": "T", "C8_macd_bull_x3": "T",
            "C9_macd_hist_rising": "T", "C10_above_sma200": "T", "C11_golden_state": "T", "C12_near_52w_low": "2s",
            "C13_don20_break_dn": "2s", "C14_bull_candle": "T", "C15_nr7": "2s", "C16_strong_downtrend": "F",
            "C17_obv_bull_div": "T", "C18_gap_down": "2s", "C19_doji": "T"}
CE, CP = conds(E), conds(P)
lagE = (E.lag_pct < -10).to_numpy()
lagP = (P.lag_pct < -10).to_numpy()

# ------------------------------------------------------------------------------------------------ base sets + check
S = {}
for name, v, fname in (("S85", 1.0, "trades.csv"), ("S44", 1.3, "trades_vol13.csv")):
    m = lagE & (E.vol_ratio_5_60 >= v).to_numpy()
    ref = pd.read_csv(f"{REPO}/{fname}")
    mine = E[m]
    k1 = set(zip(mine.symbol, mine.quarter))
    k2 = set(zip(ref.symbol, ref.quarter))
    j = mine.merge(ref, on=["symbol", "quarter"], suffixes=("", "_ref"))
    print(f"{name}: panel {len(mine)} trades, repo {fname} {len(ref)}, same (symbol, quarter): {k1 == k2}, "
          f"max |three_day - ref x100| {np.abs(j.three_day - 100 * j.three_day_ref).max():.2e}, "
          f"max |take_profit diff| {np.abs(j.take_profit - 100 * j.take_profit_ref).max():.2e}")
    assert k1 == k2
    S[name] = m
PB = {"S85": lagP & (P.vol_ratio_5_60 >= 1.0).to_numpy(), "S44": lagP & (P.vol_ratio_5_60 >= 1.3).to_numpy()}
print(f"placebo base rows: P100 {PB['S85'].sum()}, P130 {PB['S44'].sum()}")


# ------------------------------------------------------------------------------------------------ helpers
def side_stats(d, pre):
    y, tp, q = d.three_day.to_numpy(), d.take_profit.to_numpy(), d.qn.to_numpy()
    n = len(y)
    out = {f"{pre}n": n}
    if n == 0:
        return out
    qm = pd.Series(y).groupby(q).mean()
    f, l_ = q <= 13, q >= 14
    ys = np.sort(y)
    out.update({f"{pre}mean": y.mean(), f"{pre}net": y.mean() - COST, f"{pre}tp": tp.mean(),
                f"{pre}up%": 100 * (y > 0).mean(), f"{pre}q": f"{(qm > 0).sum()}/{len(qm)}",
                f"{pre}n14": f.sum(), f"{pre}f14": y[f].mean() if f.any() else np.nan,
                f"{pre}n8": l_.sum(), f"{pre}l8": y[l_].mean() if l_.any() else np.nan,
                f"{pre}xb5": ys[:-5].mean() if n > 5 else np.nan})
    return out


def perm_test(y, q, lab):
    """Within-quarter label permutation. Returns D, two-sided p, sd of the null."""
    o = np.argsort(q, kind="stable")
    y, q, lab = y[o], q[o], lab[o]
    if lab.all() or not lab.any():
        return np.nan, np.nan, np.nan
    D = y[lab].mean() - y[~lab].mean()
    keys = q[None, :] + rng.random((NPERM, len(y)))
    idx = np.argsort(keys, axis=1)
    L = lab[idx]                                       # permuted labels, quarter counts preserved
    nT = L.sum(1)
    sT = (L * y[None, :]).sum(1)
    Dp = sT / nT - (y.sum() - sT) / (len(y) - nT)
    p = (np.sum(np.abs(Dp) >= abs(D) - 1e-12) + 1) / (NPERM + 1)
    return D, p, Dp.std()


def cluster_boot_diff(y, lab, cl):
    """Mean(True) - mean(False) on placebo rows, calendar-month cluster bootstrap SE."""
    if lab.all() or not lab.any():
        return np.nan, np.nan, int(lab.sum())
    D = y[lab].mean() - y[~lab].mean()
    codes, uniq = pd.factorize(cl)
    K = len(uniq)
    sT = np.bincount(codes, weights=y * lab, minlength=K)
    nT = np.bincount(codes, weights=lab.astype(float), minlength=K)
    sF = np.bincount(codes, weights=y * ~lab, minlength=K)
    nF = np.bincount(codes, weights=(~lab).astype(float), minlength=K)
    W = rng.multinomial(K, np.full(K, 1 / K), size=NBOOT)
    Db = (W @ sT) / (W @ nT) - (W @ sF) / (W @ nF)
    return D, np.nanstd(Db), int(lab.sum())


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
    for r, i in enumerate(o):
        run = max(run, (m - r) * p[i])
        adj[i] = min(1, run)
    return adj


# ------------------------------------------------------------------------------------------------ splits
def splits(base):
    m, pm = S[base], PB[base]
    d = E[m].reset_index(drop=True)
    y, tp, q = d.three_day.to_numpy(), d.take_profit.to_numpy(), d.qn.to_numpy()
    py, ptp, pmo, pq = (P.three_day.to_numpy()[pm], P.take_profit.to_numpy()[pm], P.month.to_numpy()[pm],
                        P.qn_prev.to_numpy()[pm])
    rows = []
    for c in CE:
        lab = CE[c][m]
        plab = CP[c][pm]
        r = {"cond": c, "ta_prior": TA_PRIOR[c]}
        r.update(side_stats(d[lab], "T_"))
        r.update(side_stats(d[~lab], "F_"))
        D, p, sd = perm_test(y, q, lab)
        Dtp, ptp_, _ = perm_test(tp, q, lab)
        r.update({"D": D, "p_perm": p, "sd_null": sd, "D_tp": Dtp, "p_perm_tp": ptp_})
        f, l_ = q <= 13, q >= 14
        r["D_f14"] = y[f & lab].mean() - y[f & ~lab].mean() if (f & lab).any() and (f & ~lab).any() else np.nan
        r["D_l8"] = y[l_ & lab].mean() - y[l_ & ~lab].mean() if (l_ & lab).any() and (l_ & ~lab).any() else np.nan
        r["minside_f14"] = min((f & lab).sum(), (f & ~lab).sum())
        r["minside_l8"] = min((l_ & lab).sum(), (l_ & ~lab).sum())
        Dp, sep, npT = cluster_boot_diff(py, plab, pmo)
        r.update({"plac_nT": npT, "plac_nF": int((~plab).sum()), "plac_meanT": py[plab].mean() if plab.any() else np.nan,
                  "plac_meanF": py[~plab].mean() if (~plab).any() else np.nan, "D_plac": Dp, "se_plac": sep})
        pf, pl = pq <= 13, pq >= 14
        r["D_plac_f14"] = py[pf & plab].mean() - py[pf & ~plab].mean()
        r["D_plac_l8"] = py[pl & plab].mean() - py[pl & ~plab].mean()
        r["D_plac_tp"] = ptp[plab].mean() - ptp[~plab].mean() if plab.any() and (~plab).any() else np.nan
        r["z_vs_plac"] = (D - Dp) / np.sqrt(sd ** 2 + sep ** 2)
        rows.append(r)
    T = pd.DataFrame(rows)
    T["p_holm"] = holm(T.p_perm.fillna(1))
    # promotion rule (pre-registered)
    sgn = np.sign(T.D)
    T["a_both_halves"] = (sgn * T.D_f14 >= 1.0) & (sgn * T.D_l8 >= 1.0) & (T.minside_f14 >= 5) & (T.minside_l8 >= 5)
    T["b_p05"] = T.p_perm < 0.05
    T["c_beats_plac"] = sgn * (T.D - T.D_plac) > 0
    T["better_side"] = np.where(T.D > 0, "True", "False")
    T["promoted"] = T.a_both_halves & T.b_p05 & T.c_beats_plac
    return T


SHOW = ["cond", "ta_prior", "T_n", "T_mean", "T_tp", "T_up%", "T_q", "T_n14", "T_f14", "T_n8", "T_l8", "T_xb5",
        "F_n", "F_mean", "F_tp", "F_up%", "F_q", "F_f14", "F_l8", "D", "p_perm", "p_holm", "D_f14", "D_l8", "D_tp",
        "p_perm_tp", "plac_nT", "plac_meanT", "plac_meanF", "D_plac", "se_plac", "D_plac_f14", "D_plac_l8",
        "z_vs_plac", "a_both_halves", "b_p05", "c_beats_plac", "promoted"]
SPL = {}
for base in ("S85", "S44"):
    T = splits(base)
    SPL[base] = T
    T.to_csv(f"{HERE}/splits_{base}.csv", index=False, float_format="%.4f")
    print(f"\n==================== SPLITS on {base} (three_day %, gross; T = condition true, F = false) ==========")
    print(T[SHOW].round(3).to_string(index=False))


# ------------------------------------------------------------------------------------------------ rule reports
QALL = E.qn.to_numpy()
Y = E.three_day.to_numpy()
QIDX = {qq: np.flatnonzero(QALL == qq) for qq in np.unique(QALL)}


def luck(mask):
    """Share of random same-size-per-quarter picks (from all in_fo events of that quarter) with mean >= rule mean."""
    obs = Y[mask].mean()
    tot = np.zeros(NLUCK)
    n = 0
    for qq, idx in QIDX.items():
        k = int(mask[idx].sum())
        if k == 0:
            continue
        pick = np.argsort(rng.random((NLUCK, len(idx))), axis=1)[:, :k]
        tot += Y[idx][pick].sum(1)
        n += k
    rnd = tot / n
    return (np.sum(rnd >= obs - 1e-12) + 1) / (NLUCK + 1), rnd.mean()


PERQ = []


def rule_report(name, mask, pmask):
    d = E[mask]
    r = {"rule": name}
    r.update(side_stats(d, ""))
    if len(d) == 0:
        return r
    r["tp_net"] = d.take_profit.mean() - COST
    r["luck_p"], r["rand_mean"] = luck(mask)
    ov = mask & S["S85"]
    r["in_S85"] = int(ov.sum())
    r["not_S85_n"] = int((mask & ~S["S85"]).sum())
    r["not_S85_mean"] = Y[mask & ~S["S85"]].mean() if r["not_S85_n"] else np.nan
    py = P.three_day.to_numpy()[pmask]
    r["plac_n"] = int(pmask.sum())
    if pmask.sum():
        r["plac_mean"], r["plac_lo"], r["plac_hi"] = cluster_boot_mean(py, P.month.to_numpy()[pmask])
    pq = d.groupby("qn").three_day.agg(["count", "mean"])
    for qq, row in pq.iterrows():
        PERQ.append({"rule": name, "qn": qq, "n": int(row["count"]), "mean": row["mean"]})
    return r


RSHOW = ["rule", "n", "mean", "net", "tp", "tp_net", "up%", "q", "n14", "f14", "n8", "l8", "xb5", "luck_p",
         "rand_mean", "in_S85", "not_S85_n", "not_S85_mean", "plac_n", "plac_mean", "plac_lo", "plac_hi"]

print("\n==================== BASE RULES (reference) ====================")
base_rows = [rule_report("LAG10_VOL1.0 (S85)", S["S85"], PB["S85"]), rule_report("LAG10_VOL1.3 (S44)", S["S44"], PB["S44"])]
print(pd.DataFrame(base_rows)[RSHOW].round(3).to_string(index=False))

# refined rules (only promoted conditions)
print("\n==================== PROMOTION (pre-registered rule, decided on S85) ====================")
T = SPL["S85"]
prom = T[T.promoted]
print(T[["cond", "D", "p_perm", "p_holm", "D_f14", "D_l8", "minside_f14", "minside_l8", "D_plac", "a_both_halves",
         "b_p05", "c_beats_plac", "promoted"]].round(3).to_string(index=False))
ref_rows = []
for _, row in prom.iterrows():
    c = row.cond
    for base in ("S85", "S44"):
        lab, plab = (CE[c], CP[c]) if row.better_side == "True" else (~CE[c], ~CP[c])
        ref_rows.append(rule_report(f"{base}+{c}={row.better_side}", S[base] & lab, PB[base] & plab))
if ref_rows:
    R = pd.DataFrame(ref_rows)
    R.to_csv(f"{HERE}/refined_rules.csv", index=False, float_format="%.4f")
    print(R[RSHOW].round(3).to_string(index=False))
else:
    print("No condition met the promotion rule -> no refined rule tested.")

# replacement rules
print("\n==================== REPLACEMENT RULES (no lag filter, all in_fo events) ====================")
volE, volP = (E.vol_ratio_5_60 >= 1.0).to_numpy(), (P.vol_ratio_5_60 >= 1.0).to_numpy()
rep = []
for c in ["C1_rsi14_lt30", "C2_rsi2_lt10", "C3_stoch_lt20", "C4_below_lower_bb", "C5_cci_lt_m100", "C6_mfi_lt20",
          "C7_oversold_ge3", "C12_near_52w_low", "C13_don20_break_dn"]:
    rep.append(rule_report(f"{c} + vol>=1.0", CE[c] & volE, CP[c] & volP))
    rep.append(rule_report(f"{c} (no volume filter)", CE[c], CP[c]))
R = pd.DataFrame(rep)
R.to_csv(f"{HERE}/replacement_rules.csv", index=False, float_format="%.4f")
print(R[RSHOW].round(3).to_string(index=False))

pd.DataFrame(PERQ).pivot(index="rule", columns="qn", values="mean").round(2).to_csv(f"{HERE}/per_quarter_rules.csv")
pd.DataFrame(PERQ).to_csv(f"{HERE}/per_quarter_rules_long.csv", index=False, float_format="%.4f")

# trades of S85 with every condition flag (for inspection)
out = E[S["S85"]][["symbol", "quarter", "qn", "cutoff", "lag_pct", "vol_ratio_5_60", "three_day", "take_profit"]].copy()
for c in CE:
    out[c] = CE[c][S["S85"]].astype(int)
out.to_csv(f"{HERE}/trades_S85_with_ta.csv", index=False, float_format="%.4f")

# condition prevalence: S85 vs all in_fo events vs placebo base
print("\n==================== PREVALENCE of each condition (share true) ====================")
prev = pd.DataFrame({"S85": {c: CE[c][S["S85"]].mean() for c in CE}, "S44": {c: CE[c][S["S44"]].mean() for c in CE},
                     "all_in_fo_events": {c: CE[c].mean() for c in CE}, "P100": {c: CP[c][PB["S85"]].mean() for c in CE}})
print(prev.round(3).to_string())
n_things = 2 * len(CE) + len(rep) + len(ref_rows)
print(f"\nThings tested (pre-registered count): {2 * len(CE)} splits + {len(rep)} replacement rules + "
      f"{len(ref_rows)} refined rules = {n_things}")
