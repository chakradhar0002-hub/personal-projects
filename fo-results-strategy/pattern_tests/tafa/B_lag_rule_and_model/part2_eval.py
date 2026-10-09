"""PART 2 (step 2 of 2) - evaluation of the walk-forward scores, as pre-registered in PREREGISTRATION.txt.

Strategies: A (all in_fo results; 3 feature sets x 3 models x top 10% / 20%) = 18; L1 (lag group, models trained on
the lag group only; top 10/20/50%) = 27; L2 (universe-A models scored on the lag group; top 50%) = 9.
Threshold for season q = (1-k) quantile of the same run's OOS scores of seasons 6..q-1 in the same universe.
Out-of-sample seasons 8..21 ("first 6" = 8..13, "last 8" = 14..21).

    python3 part2_eval.py      (reads part2_rows.csv, part2_placebo_rows.csv.gz, scores/*.npz; writes part2_*.csv)
"""
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr, ttest_rel

HERE = os.path.dirname(os.path.abspath(__file__))
COST = 0.17
NNULL = int(os.environ.get("NNULL", 30))
NLUCK, NBOOT = 20000, 2000
EVQ = list(range(8, 22))
rng = np.random.default_rng(20261009)
pd.set_option("display.width", 300, "display.max_columns", 80, "display.max_rows", 400)


class Tee:
    def __init__(self, path):
        self.f = open(path, "w")

    def write(self, s):
        self.f.write(s)
        sys.__stdout__.write(s)

    def flush(self):
        self.f.flush()
        sys.__stdout__.flush()


sys.stdout = Tee(f"{HERE}/part2_eval.log")

R = pd.read_csv(f"{HERE}/part2_rows.csv")
_F = pd.read_csv(os.environ.get('LAB_ROOT', 'lab') + "/fa/build/"
                 "fa_panel.csv", usecols=["symbol", "quarter", "excess_nifty_3d"])
R = R.merge(_F, on=["symbol", "quarter"], how="left", validate="1:1")
XN = R.excess_nifty_3d.to_numpy()
P = pd.read_csv(f"{HERE}/part2_placebo_rows.csv.gz")
QN, Y, TP = R.qn.to_numpy(), R.three_day.to_numpy(), R.take_profit.to_numpy()
LAG = (R.lag_pct < -10).to_numpy()
S85 = LAG & (R.vol_ratio_5_60 >= 1.0).to_numpy()
ALL = np.ones(len(R), bool)
EV = np.isin(QN, EVQ)
FS, MODELS = ("TA", "FA", "TAFA"), ("LR", "RF", "GB")


def load(univ, fs, model, r):
    z = np.load(f"{HERE}/scores/{univ}_{fs}_{model}_r{r}.npz")
    return z["score"], z["pscore"]


def season_labels(mask):
    """Evaluation label: three_day above the season median of the universe rows."""
    lab = np.zeros(len(R), int)
    med = pd.Series(Y[mask]).groupby(QN[mask]).median()
    lab[mask] = (Y[mask] > pd.Series(QN[mask]).map(med).to_numpy()).astype(int)
    return lab


LAB = {"A": season_labels(ALL), "L": season_labels(LAG)}


def auc(score, lab):
    ok = ~np.isnan(score)
    s, l_ = score[ok], lab[ok]
    n1, n0 = l_.sum(), (1 - l_).sum()
    if n1 == 0 or n0 == 0:
        return np.nan
    rk = rankdata(s)
    return (rk[l_ == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def auc_stats(score, mask, lab, min_rows=4):
    m = mask & EV
    pooled = auc(score[m], lab[m])
    per, ics = {}, []
    for q in EVQ:
        mq = mask & (QN == q)
        if mq.sum() >= min_rows:
            per[q] = auc(score[mq], lab[mq])
            ics.append(spearmanr(score[mq], Y[mq])[0])
    return pooled, np.nanmean(list(per.values())), np.nanmean(ics), per


def picks(score, mask, k):
    pick = np.zeros(len(R), bool)
    thr = {}
    for q in EVQ:
        past = mask & (QN >= 6) & (QN < q) & ~np.isnan(score)
        thr[q] = np.quantile(score[past], 1 - k)
        te = mask & (QN == q)
        pick[te] = score[te] > thr[q]
    return pick, thr


def stats(pick):
    y, tp, q = Y[pick], TP[pick], QN[pick]
    n = len(y)
    out = {"n": n}
    if n == 0:
        return out
    qm = pd.Series(y).groupby(q).mean()
    f, l_ = q <= 13, q >= 14
    ys = np.sort(y)
    out.update({"mean": y.mean(), "net": y.mean() - COST, "tp": tp.mean(), "tp_net": tp.mean() - COST,
                "up%": 100 * (y > 0).mean(), "q_trades": len(qm), "q_pos": int((qm > 0).sum()),
                "n_f6": int(f.sum()), "f6": y[f].mean() if f.any() else np.nan,
                "n_l8": int(l_.sum()), "l8": y[l_].mean() if l_.any() else np.nan,
                "xb5": ys[:-5].mean() if n > 5 else np.nan})
    return out


QIDX = {q: np.flatnonzero(QN == q) for q in EVQ}


def luck(pick, mask):
    obs = Y[pick].mean()
    tot = np.zeros(NLUCK)
    n = 0
    for q, idx in QIDX.items():
        idx = idx[mask[idx]]
        k = int(pick[idx].sum())
        if k == 0:
            continue
        sel = np.argsort(rng.random((NLUCK, len(idx))), axis=1)[:, :k]
        tot += Y[idx][sel].sum(1)
        n += k
    rnd = tot / n
    return (np.sum(rnd >= obs - 1e-12) + 1) / (NLUCK + 1), rnd.mean()


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


# ------------------------------------------------------------------------------------------------ strategies
STRATS = []
for fs in FS:
    for mo in MODELS:
        for k in (0.10, 0.20):
            STRATS.append(("A", fs, mo, k, "A", ALL, "A"))
        for k in (0.10, 0.20, 0.50):
            STRATS.append(("L1", fs, mo, k, "L1", LAG, "L"))
        STRATS.append(("L2", fs, mo, 0.50, "A", LAG, "L"))
# (family, feature set, model, k, score source universe, eligible rows, label set)

rows, PERQ, AUCSEASON = [], [], []
null_means = {}
null_aucs = {}
cache = {}


def get(univ, fs, mo, r):
    key = (univ, fs, mo, r)
    if key not in cache:
        sc, ps = load(univ, fs, mo, r)
        cache[key] = (sc, ps if (r == 0 and fs == "TA" and univ == "A") else None)
    return cache[key]


for fam, fs, mo, k, src, mask, labset in STRATS:
    name = f"{fam}|{fs}|{mo}|top{int(k * 100)}"
    sc, _ = get(src, fs, mo, 0)
    pick, thr = picks(sc, mask, k)
    r = {"family": fam, "fs": fs, "model": mo, "k": k, "strategy": name}
    r.update(stats(pick))
    r["luck_p"], r["rand_mean"] = luck(pick, mask)
    # descriptive (not part of the criteria): overlap with the lag rule, picks outside it, excess over Nifty
    r.update({"vs_nifty": np.nanmean(XN[pick]), "in_S85": int((pick & S85).sum()), "in_lag": int((pick & LAG).sum()),
              "not_S85_mean": Y[pick & ~S85].mean() if (pick & ~S85).any() else np.nan,
              "not_lag_mean": Y[pick & ~LAG].mean() if (pick & ~LAG).any() else np.nan})
    pooled, per_mean, ic, per = auc_stats(sc, mask, LAB[labset])
    r.update({"auc_pooled": pooled, "auc_season_mean": per_mean, "ic_mean": ic})
    for q, a in per.items():
        AUCSEASON.append({"family": fam, "fs": fs, "model": mo, "qn": q, "auc": a})
    nm, na = [], []
    for rr in range(1, NNULL + 1):
        s0, _ = get(src, fs, mo, rr)
        pk, _ = picks(s0, mask, k)
        nm.append(Y[pk].mean() if pk.any() else np.nan)
        na.append(auc(s0[mask & EV], LAB[labset][mask & EV]))
    nm, na = np.array(nm), np.array(na)
    null_means[name], null_aucs[name] = nm, na
    r.update({"null_mean_avg": np.nanmean(nm), "null_mean_sd": np.nanstd(nm),
              "p_null_mean": (np.sum(nm >= r["mean"] - 1e-12) + 1) / (NNULL + 1) if r["n"] else 1.0,
              "null_auc_avg": np.nanmean(na), "null_auc_sd": np.nanstd(na),
              "p_null_auc": (np.sum(na >= pooled - 1e-12) + 1) / (NNULL + 1)})
    rows.append(r)
    g = pd.DataFrame({"qn": QN[pick], "y": Y[pick], "tp": TP[pick], "sym": R.symbol.to_numpy()[pick]})
    for q in EVQ:
        gq = g[g.qn == q]
        PERQ.append({"strategy": name, "qn": q, "thr": thr[q], "n": len(gq),
                     "mean": gq.y.mean() if len(gq) else np.nan, "tp": gq.tp.mean() if len(gq) else np.nan,
                     "universe_mean": Y[mask & (QN == q)].mean(), "universe_n": int((mask & (QN == q)).sum())})
    # free null caches of this config when done with the last strategy using it
T = pd.DataFrame(rows)

# Holm within family; family-wise maxT over null runs
for fam in ("A", "L1", "L2"):
    f = T.family == fam
    T.loc[f, "luck_holm"] = holm(T.loc[f, "luck_p"].to_numpy())
    names = T.loc[f, "strategy"].tolist()
    NM = np.vstack([null_means[n] for n in names])                 # strategies x runs
    mu, sd = np.nanmean(NM, 1, keepdims=True), np.nanstd(NM, 1, keepdims=True)
    sd[sd == 0] = np.nan
    Z = np.where(np.isnan(NM), -np.inf, (NM - mu) / sd)
    mx = Z.max(0)
    zobs = (T.loc[f, "mean"].to_numpy() - mu[:, 0]) / sd[:, 0]
    T.loc[f, "z_vs_null"] = zobs
    T.loc[f, "p_fw_null"] = [(np.sum(mx >= z - 1e-12) + 1) / (NNULL + 1) for z in zobs]
T["WORKS"] = ((T.net > 0) & (T.luck_holm < 0.05) & (T.p_null_mean < 0.05) & (T.p_null_auc < 0.05) & (T.f6 > 0)
              & (T.l8 > 0) & (T.xb5 > 0))
T.to_csv(f"{HERE}/part2_strategies.csv", index=False, float_format="%.4f")
pd.DataFrame(PERQ).to_csv(f"{HERE}/part2_per_quarter.csv", index=False, float_format="%.4f")
pd.DataFrame(AUCSEASON).drop_duplicates(["family", "fs", "model", "qn"]).to_csv(f"{HERE}/part2_auc_per_season.csv", index=False, float_format="%.4f")

# ------------------------------------------------------------------------------------------------ references
print("==================== REFERENCES (out-of-sample seasons 8..21; not counted) ====================")
refs = []
for nm_, m in (("all in_fo results", ALL & EV), ("lag group (lag < -10)", LAG & EV),
               ("lag rule S85 (lag + volume >= 1.0)", S85 & EV), ("lag group WITHOUT volume >= 1.0", LAG & ~S85 & EV)):
    rr = {"reference": nm_}
    rr.update(stats(m))
    refs.append(rr)
REF = pd.DataFrame(refs)
print(REF.round(3).to_string(index=False))
# the volume filter as a "score" inside the lag group: AUC of vol_ratio for the lag-group label
va = auc_stats(R.vol_ratio_5_60.to_numpy(float), LAG, LAB["L"])
print(f"volume ratio as a ranking score inside the lag group: pooled AUC {va[0]:.3f}, mean per-season AUC {va[1]:.3f},"
      f" mean IC {va[2]:.3f}")
la = auc_stats(-R.lag_pct.to_numpy(float), ALL, LAB["A"])
print(f"-lag_pct as a ranking score on all in_fo results: pooled AUC {la[0]:.3f}, mean per-season AUC {la[1]:.3f}, "
      f"mean IC {la[2]:.3f}")

SHOW = ["strategy", "n", "mean", "net", "tp", "tp_net", "up%", "q_trades", "q_pos", "n_f6", "f6", "n_l8", "l8", "xb5",
        "luck_p", "luck_holm", "rand_mean", "auc_pooled", "auc_season_mean", "ic_mean", "null_mean_avg", "p_null_mean",
        "null_auc_avg", "p_null_auc", "z_vs_null", "p_fw_null", "WORKS", "vs_nifty", "in_S85", "in_lag",
        "not_S85_mean", "not_lag_mean"]
for fam, title in (("A", "A: all in_fo results"), ("L1", "L1: lag group, models trained on the lag group only"),
                   ("L2", "L2: lag group, universe-A models, top 50% of past lag-group scores")):
    print(f"\n==================== {title} (three_day %, gross unless 'net') ====================")
    print(T[T.family == fam][SHOW].round(3).to_string(index=False))

# ------------------------------------------------------------------------------------------------ combination adds
print("\n==================== DOES TA+FA ADD TO TA ALONE / FA ALONE? (universe A, real runs) ====================")
AS = pd.DataFrame(AUCSEASON).drop_duplicates(["family", "fs", "model", "qn"])
comb = []
for mo in MODELS:
    a = AS[(AS.family == "A") & (AS.model == mo)].pivot(index="qn", columns="fs", values="auc")
    c = {"model": mo, "auc_TA": a.TA.mean(), "auc_FA": a.FA.mean(), "auc_TAFA": a.TAFA.mean()}
    for other in ("TA", "FA"):
        d = a.TAFA - a[other]
        t, p = ttest_rel(a.TAFA, a[other])
        c.update({f"dAUC_vs_{other}": d.mean(), f"t_vs_{other}": t, f"p_vs_{other}": p,
                  f"seasons_better_vs_{other}": f"{int((d > 0).sum())}/{len(d)}"})
    for k in (10, 20):
        g = T[(T.family == "A") & (T.model == mo) & (T.k == k / 100)].set_index("fs")
        for col in ("mean", "f6", "l8"):
            c[f"top{k}_{col}_TA/FA/TAFA"] = "/".join(f"{g.loc[f, col]:.2f}" for f in FS)
        c[f"top{k}_TAFA_beats_both_halves"] = bool(all(g.loc["TAFA", h] > max(g.loc["TA", h], g.loc["FA", h])
                                                       for h in ("f6", "l8")))
    c["ADDS"] = bool(c["dAUC_vs_TA"] > 0 and c["dAUC_vs_FA"] > 0 and c["p_vs_TA"] < 0.05 and c["p_vs_FA"] < 0.05
                     and c["top10_TAFA_beats_both_halves"] and c["top20_TAFA_beats_both_halves"])
    comb.append(c)
C = pd.DataFrame(comb)
C.to_csv(f"{HERE}/part2_combination.csv", index=False, float_format="%.4f")
print(C.round(4).T.to_string())

# ------------------------------------------------------------------------------------------------ bouncers
print("\n==================== DOES TA+FA RANK THE BOUNCERS? (lag group, top 50%) vs the volume filter ====================")
vol = stats(S85 & EV)
B = T[(T.family.isin(["L1", "L2"])) & (T.k == 0.5)].copy()
B["beats_volume_both_halves"] = (B.f6 > vol["f6"]) & (B.l8 > vol["l8"])
B["RANKS_BOUNCERS"] = B.beats_volume_both_halves & (B.p_null_auc < 0.05)
print(f"volume filter (S85, seasons 8..21): n {vol['n']}, mean {vol['mean']:.3f}, first 6 {vol['f6']:.3f} "
      f"(n {vol['n_f6']}), last 8 {vol['l8']:.3f} (n {vol['n_l8']})")
print(B[["strategy", "n", "mean", "f6", "l8", "xb5", "auc_pooled", "p_null_auc", "p_null_mean",
         "beats_volume_both_halves", "RANKS_BOUNCERS"]].round(3).to_string(index=False))
B.to_csv(f"{HERE}/part2_bouncers.csv", index=False, float_format="%.4f")

# overlap of the L2/L1 top-50% picks with the volume filter
print("\noverlap with the volume filter (lag group, seasons 8..21):")
for fam, src in (("L1", "L1"), ("L2", "A")):
    for fs in FS:
        for mo in MODELS:
            sc, _ = get(src, fs, mo, 0)
            pk, _ = picks(sc, LAG, 0.5)
            both = pk & S85
            print(f"  {fam}|{fs}|{mo}: picks {pk.sum()}, also volume >= 1.0: {both.sum()} (mean {Y[both].mean():.2f}),"
                  f" picks without volume: {(pk & ~S85).sum()} (mean {Y[pk & ~S85].mean():.2f}), "
                  f"volume trades the model skips: {(S85 & EV & ~pk).sum()} (mean {Y[S85 & EV & ~pk].mean():.2f})")

# ------------------------------------------------------------------------------------------------ TA placebo
print("\n==================== PLACEBO: TA-only universe-A models on non-results days between seasons ====================")
PQ, PY = P.season.to_numpy(), P.three_day.to_numpy()
month = P.day.str[:7].to_numpy()
pl = []
for mo in MODELS:
    sc, psc = get("A", "TA", mo, 0)
    for k in (0.10, 0.20):
        pick, thr = picks(sc, ALL, k)
        ppick = np.zeros(len(P), bool)
        for q in EVQ:
            m = PQ == q
            ppick[m] = psc[m] > thr[q]
        # month-cluster bootstrap of (picked mean - all mean) on placebo days
        codes, uniq = pd.factorize(month)
        K = len(uniq)
        sp = np.bincount(codes, weights=PY * ppick, minlength=K)
        npk = np.bincount(codes, weights=ppick.astype(float), minlength=K)
        sa = np.bincount(codes, weights=PY, minlength=K)
        na_ = np.bincount(codes, minlength=K).astype(float)
        W = rng.multinomial(K, np.full(K, 1 / K), size=NBOOT)
        with np.errstate(invalid="ignore", divide="ignore"):
            db = (W @ sp) / (W @ npk) - (W @ sa) / (W @ na_)
        ev_ex = Y[pick].mean() - Y[EV].mean()
        pl.append({"strategy": f"A|TA|{mo}|top{int(k * 100)}", "event_n": int(pick.sum()), "event_mean": Y[pick].mean(),
                   "events_all_mean": Y[EV].mean(), "event_excess": ev_ex, "plac_n": int(ppick.sum()),
                   "plac_share_picked": ppick.mean(), "plac_mean": PY[ppick].mean(), "plac_all_mean": PY.mean(),
                   "plac_excess": PY[ppick].mean() - PY.mean(), "plac_excess_lo": np.nanpercentile(db, 2.5),
                   "plac_excess_hi": np.nanpercentile(db, 97.5),
                   "event_minus_placebo_excess": ev_ex - (PY[ppick].mean() - PY.mean())})
PL = pd.DataFrame(pl)
PL.to_csv(f"{HERE}/part2_placebo.csv", index=False, float_format="%.4f")
print(PL.round(3).to_string(index=False))
print(f"\nThings tested (pre-registered): {len(T)} strategies (A {int((T.family == 'A').sum())}, L1 "
      f"{int((T.family == 'L1').sum())}, L2 {int((T.family == 'L2').sum())}) + {len(PL)} TA placebo checks; "
      f"WORKS: {int(T.WORKS.sum())}")
