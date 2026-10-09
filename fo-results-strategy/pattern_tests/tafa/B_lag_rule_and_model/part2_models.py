"""PART 2 (step 1 of 2) - walk-forward model scores, as pre-registered in PREREGISTRATION.txt.

For each universe (A = all in_fo results, L1 = lag_pct < -10 only), feature set (TA 48, FA 32, TAFA 80), model
(LR, RF, GB) and run (r = 0 real labels; r = 1..30 training outcomes permuted within season, the same permutation for
every feature set / model of that run), for each season q = 6..21: fit on seasons < q (label = three_day above its
season's median within the universe), score season q. Seasons 6-7 are a threshold warm-up only.
Preprocessing fitted on training rows only (clip 1-99th pct, median fill; LR also standardises).
Real TA-only universe-A runs also score the non-results placebo days between seasons (q-1 end, q start).
Writes scores/<univ>_<fs>_<model>_r<r>.npz (resumable) and part2_features.csv (rows, features).
No evaluation here (see part2_eval.py).

    OMP_NUM_THREADS=1 python3 part2_models.py [n_workers]
"""
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.environ.get('LAB_ROOT', 'lab') + ""
OUT = f"{HERE}/scores"
os.makedirs(OUT, exist_ok=True)
NNULL = 30
SEASONS = list(range(6, 22))

TA_FEAT = ["rsi14", "rsi2", "stoch_k14", "stoch_d3", "cci20", "mfi14", "bb_pctb", "bb_width_pct", "macd_pct",
           "macd_signal_pct", "macd_hist_pct", "macd_above_signal", "macd_bull_x3", "macd_bear_x3", "macd_hist_rising",
           "close_vs_sma20_pct", "close_vs_sma50_pct", "close_vs_sma200_pct", "sma50_vs_sma200_pct", "golden_state",
           "golden_x10", "death_x10", "adx14", "plus_di14", "minus_di14", "atr14_pct", "nr7", "cdl_hammer",
           "cdl_bull_engulf", "cdl_bear_engulf", "cdl_doji", "cdl_shooting_star", "gap_pct", "full_gap_up",
           "full_gap_down", "dist_52w_high_pct", "dist_52w_low_pct", "dist_20d_high_pct", "dist_20d_low_pct",
           "don20_pos", "don20_break_up", "don20_break_dn", "obv_slope20", "price_slope20_pct", "obv_div20",
           "ret_5d_pct", "lag_pct", "vol_ratio_5_60"]
FA_RAW = ["log_mcap", "earnings_yield_pct", "pe_vs_own3y_pct", "pe_vs_peers_pct", "peg", "roe_pct", "debt_equity",
          "l1_sales_yoy_pct", "l1_pat_yoy_pct", "l1_sales_qoq_pct", "l1_pat_qoq_pct", "sales_yoy_accel_pp",
          "pat_yoy_accel_pp", "ttm_pat_yoy_pct", "ttm_sales_yoy_pct", "pat_up_yoy_4q", "sales_up_yoy_4q",
          "l1_ebitda_margin_pct", "l1_ebitda_margin_chg_yoy_pp", "l1_net_margin_pct", "l1_net_margin_chg_yoy_pp",
          "loss_any_4q", "piotroski_frac", "pat_yoy_std8_pct"]
FA_FEAT = FA_RAW + ["book_yield", "sales_yield", "days_since_dividend", "is_bank", "is_nbfc", "miss_bs", "miss_pio",
                    "miss_pe_own"]
assert len(TA_FEAT) == 48 and len(FA_FEAT) == 32
FSETS = {"TA": TA_FEAT, "FA": FA_FEAT, "TAFA": TA_FEAT + FA_FEAT}


def load():
    E = pd.read_csv(f"{SCR}/ta/build/events_ta.csv")
    E = E[(E.in_fo == True) & E.three_day.notna()]
    M = pd.read_csv(f"{SCR}/ta/B_on_lag_rule/macd_prev.csv.gz")
    E = E.merge(M, left_on=["symbol", "cutoff"], right_on=["symbol", "day"], how="left").drop(columns="day")
    F = pd.read_csv(f"{SCR}/fa/build/fa_panel.csv")
    keep = ["symbol", "quarter", "fin_type", "pb", "ps"] + [c for c in FA_RAW] + ["days_since_dividend"]
    E = E.merge(F[keep], on=["symbol", "quarter"], how="left", validate="1:1")
    E["book_yield"] = np.where(E.pb > 0, 1 / E.pb, np.nan)
    E["sales_yield"] = np.where(E.ps > 0, 1 / E.ps, np.nan)
    E["days_since_dividend"] = E.days_since_dividend.fillna(1000)
    E["is_bank"] = (E.fin_type == "Bank").astype(float)
    E["is_nbfc"] = (E.fin_type == "NBFC / financial").astype(float)
    E["miss_bs"] = E.roe_pct.isna().astype(float)
    E["miss_pio"] = E.piotroski_frac.isna().astype(float)
    E["miss_pe_own"] = E.pe_vs_own3y_pct.isna().astype(float)
    E = E.sort_values(["qn", "cutoff", "symbol"]).reset_index(drop=True)
    # placebo days between seasons (q-1 last Day+1, q first cutoff), q = 8..21, in_fo, three_day present
    b = E.groupby("qn").agg(cut_min=("i_cut", "min"), p1_max=("i_p1", "max"))
    P = pd.read_csv(f"{SCR}/ta/build/placebo_ta.csv.gz")
    P = P[(P.in_fo == True) & P.three_day.notna()].merge(M, on=["symbol", "day"], how="left")
    P["season"] = -1
    for q in range(8, 22):
        w = (P.i > b.p1_max[q - 1]) & (P.i < b.cut_min[q])
        P.loc[w, "season"] = q
    P = P[P.season >= 8].reset_index(drop=True)
    return E, P


E, P = load()
QN = E.qn.to_numpy()
Y = E.three_day.to_numpy()
LAG = (E.lag_pct < -10).to_numpy()
UNIV = {"A": np.ones(len(E), bool), "L1": LAG}
XS = {k: E[v].to_numpy(float) for k, v in FSETS.items()}
XP = P[TA_FEAT].to_numpy(float)
PQ = P.season.to_numpy()


def labels(univ, r):
    """Training labels for run r: three_day (permuted within season among the universe's rows if r > 0) above the
    season median of the universe."""
    u = UNIV[univ]
    y = Y.copy()
    if r > 0:
        rng = np.random.default_rng((1000 if univ == "A" else 5000) + r)
        for q in np.unique(QN[u]):
            idx = np.flatnonzero(u & (QN == q))
            y[idx] = y[rng.permutation(idx)]
    med = pd.Series(Y[u]).groupby(QN[u]).median()
    lab = np.zeros(len(E), int)
    lab[u] = (y[u] > pd.Series(QN[u]).map(med).to_numpy()).astype(int)
    return lab


def prep_fit(Xtr):
    with np.errstate(all="ignore"):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            lo = np.nanpercentile(Xtr, 1, axis=0)
            hi = np.nanpercentile(Xtr, 99, axis=0)
            allnan = np.isnan(lo)
            lo[allnan], hi[allnan] = 0, 0
            Xc = np.clip(Xtr, lo, hi)
            med = np.nanmedian(Xc, axis=0)
    med[np.isnan(med)] = 0
    Xc = np.where(np.isnan(Xc), med, Xc)
    mu, sd = Xc.mean(0), Xc.std(0)
    sd[sd == 0] = 1
    return (lo, hi, med, mu, sd), Xc


def prep_apply(st, X):
    lo, hi, med, mu, sd = st
    Xc = np.clip(X, lo, hi)
    return np.where(np.isnan(Xc), med, Xc)


def make_model(name):
    if name == "LR":
        return LogisticRegression(C=1.0, max_iter=5000)
    if name == "RF":
        return RandomForestClassifier(n_estimators=300, max_depth=4, min_samples_leaf=20, max_features="sqrt",
                                      random_state=1, n_jobs=1)
    return GradientBoostingClassifier(n_estimators=150, learning_rate=0.05, max_depth=2, subsample=0.8,
                                      min_samples_leaf=20, random_state=1)


def run_task(task):
    univ, fs, model, r = task
    path = f"{OUT}/{univ}_{fs}_{model}_r{r}.npz"
    if os.path.exists(path):
        return task, 0.0
    t0 = time.time()
    u, X = UNIV[univ], XS[fs]
    lab = labels(univ, r)
    score = np.full(len(E), np.nan)
    do_plac = univ == "A" and fs == "TA" and r == 0
    pscore = np.full(len(P), np.nan)
    for q in SEASONS:
        tr, te = u & (QN < q), u & (QN == q)
        if not te.any():
            continue
        st, Xtr = prep_fit(X[tr])
        Xte = prep_apply(st, X[te])
        if model == "LR":
            Xtr, Xte = (Xtr - st[3]) / st[4], (Xte - st[3]) / st[4]
        m = make_model(model).fit(Xtr, lab[tr])
        score[te] = m.predict_proba(Xte)[:, 1]
        if do_plac and q >= 8:
            pm = PQ == q
            Xp = prep_apply(st, XP[pm])
            if model == "LR":
                Xp = (Xp - st[3]) / st[4]
            pscore[pm] = m.predict_proba(Xp)[:, 1]
    np.savez_compressed(path, score=score, pscore=pscore)
    return task, time.time() - t0


if __name__ == "__main__":
    nw = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    E[["symbol", "quarter", "qn", "cutoff", "lag_pct", "vol_ratio_5_60", "three_day", "take_profit"]].to_csv(
        f"{HERE}/part2_rows.csv", index=False)
    P[["symbol", "day", "i", "season", "three_day", "take_profit"]].to_csv(f"{HERE}/part2_placebo_rows.csv.gz",
                                                                           index=False)
    print(f"rows: events {len(E)}, lag group {LAG.sum()}, placebo window days {len(P)} "
          f"(per season {pd.Series(PQ).value_counts().sort_index().to_dict()})", flush=True)
    miss = pd.DataFrame({fs: pd.Series(np.isnan(XS[fs]).mean(0), index=FSETS[fs]) for fs in ("TA", "FA")})
    print("share missing per feature (before median fill):\n", miss.round(3).dropna(how="all").to_string(), flush=True)
    tasks = [(u, fs, m, r) for r in range(NNULL + 1) for u in ("A", "L1") for m in ("GB", "RF", "LR")
             for fs in ("TA", "FA", "TAFA")]
    t0 = time.time()
    done = 0
    with Pool(nw) as pool:
        for task, dt in pool.imap_unordered(run_task, tasks):
            done += 1
            if dt > 0 and (done % 9 == 0 or task[3] == 0):
                print(f"{done}/{len(tasks)} {task} {dt:.1f}s  elapsed {time.time() - t0:.0f}s", flush=True)
    print(f"all {len(tasks)} tasks done in {time.time() - t0:.0f}s")
