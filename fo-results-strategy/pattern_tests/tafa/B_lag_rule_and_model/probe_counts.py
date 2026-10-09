"""Coverage / size probe. Touches NO outcome column (three_day, tp3, d1..d3, next*, react*). Counts only."""
import os  # LAB_ROOT: scratch folder with ta/, fa/, report/, sector_lab/data; REPO_ROOT: this repo
import numpy as np, pandas as pd
SCR = os.environ.get('LAB_ROOT', 'lab') + ""
E = pd.read_csv(f"{SCR}/ta/build/events_ta.csv")
E = E.drop(columns=["d1", "d2", "d3", "three_day", "take_profit"])
F = pd.read_csv(f"{SCR}/fa/build/fa_panel.csv")
F = F[[c for c in F.columns if not (c.startswith("rq_") or c in ("ret_dm1", "ret_rd", "ret_dp1", "three_day", "tp3",
      "excess_nifty_3d", "move", "nifty_react", "react_excess_nifty", "next5", "next20", "next20_vs_nifty"))]]
D = F.merge(E[["symbol", "quarter", "lag_pct", "vol_ratio_5_60", "rsi14", "i_cut", "i_p1"]], on=["symbol", "quarter"], how="left")
D = D[D.in_fo == True]
print("in_fo rows", len(D), "per qn:", D.groupby("qn").size().to_dict())
lag = D.lag_pct < -10
print("lag<-10 rows", lag.sum(), "per qn:", D[lag].groupby("qn").size().to_dict())
s85 = lag & (D.vol_ratio_5_60 >= 1.0)
print("S85 rows", s85.sum())
cols = ["roe_pct", "debt_equity", "loss_any_4q", "l1_pat_yoy_pct", "l1_sales_yoy_pct", "pe_vs_own3y_pct",
        "pe_vs_peers_pct", "piotroski_frac", "piotroski_n", "log_mcap", "pb", "earnings_yield_pct", "pat_up_yoy_4q",
        "pat_yoy_std8_pct", "days_since_dividend", "peg", "sales_yoy_accel_pp", "l1_ebitda_margin_chg_yoy_pp"]
cov = pd.DataFrame({"all_in_fo": D[cols].notna().mean(), "S85": D[s85][cols].notna().mean()})
print(cov.round(2))
print("S85 known roe per qn", D[s85].groupby("qn").roe_pct.apply(lambda s: s.notna().sum()).to_dict())
print("fin_type", D.fin_type.value_counts().to_dict())
# season overlap: last Day+1 session of season q-1 vs first cutoff of season q (in_fo)
g = D.groupby("qn").agg(cut_min=("i_cut", "min"), cut_max=("i_cut", "max"), p1_max=("i_p1", "max"))
g["prev_p1_max"] = g.p1_max.shift()
g["gap_sessions"] = g.cut_min - g.prev_p1_max
print(g)
P = pd.read_csv(f"{SCR}/ta/build/placebo_ta.csv.gz", usecols=["symbol", "day", "in_fo", "qn_next", "lag_pct", "vol_ratio_5_60"])
P = P[P.in_fo == True]
print("placebo in_fo rows", len(P), " lag+vol rows", ((P.lag_pct < -10) & (P.vol_ratio_5_60 >= 1)).sum())
