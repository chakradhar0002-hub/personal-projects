"""POST-HOC (descriptive only): profile of the A|TAFA|GB|top10 picks vs all out-of-sample in_fo results (median of
key features), and the impurity importances of the last walk-forward model (trained on seasons 0..20)."""
import os, warnings
os.environ["OMP_NUM_THREADS"] = "1"
warnings.simplefilter("ignore")
import numpy as np, pandas as pd
import part2_models as M
HERE = os.path.dirname(os.path.abspath(__file__))
sc = np.load(f"{HERE}/scores/A_TAFA_GB_r0.npz")["score"]
QN = M.QN
pk = np.zeros(len(M.E), bool)
for q in range(8, 22):
    past = (QN >= 6) & (QN < q)
    pk[QN == q] = sc[QN == q] > np.quantile(sc[past], 0.9)
ev = QN >= 8
cols = ["lag_pct", "ret_5d_pct", "close_vs_sma200_pct", "dist_52w_high_pct", "rsi14", "atr14_pct", "vol_ratio_5_60",
        "log_mcap", "roe_pct", "earnings_yield_pct", "l1_pat_yoy_pct", "l1_sales_yoy_pct", "piotroski_frac",
        "loss_any_4q", "debt_equity", "pe_vs_peers_pct"]
prof = pd.DataFrame({"picks_median": M.E.loc[pk, cols].median(), "all_median": M.E.loc[ev, cols].median(),
                     "picks_missing": M.E.loc[pk, cols].isna().mean(), "all_missing": M.E.loc[ev, cols].isna().mean()})
print(prof.round(2).to_string())
print("fin_type share picks:", M.E.loc[pk, "fin_type"].value_counts(normalize=True).round(2).to_dict(),
      " all:", M.E.loc[ev, "fin_type"].value_counts(normalize=True).round(2).to_dict())
X = M.XS["TAFA"]
lab = M.labels("A", 0)
tr = QN < 21
st, Xtr = M.prep_fit(X[tr])
m = M.make_model("GB").fit(Xtr, lab[tr])
imp = pd.Series(m.feature_importances_, index=M.FSETS["TAFA"]).sort_values(ascending=False)
print("\nlast model (trained on seasons 0..20) top 15 importances:\n", imp.head(15).round(3).to_string())
print("TA share of importance:", imp[M.TA_FEAT].sum().round(3), " FA share:", imp[M.FA_FEAT].sum().round(3))
