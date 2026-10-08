"""PRE-REGISTRATION - pre-results fundamental screens for the 3-day results window.

Written before any outcome (three_day, tp3, excess_nifty_3d, ...) was computed for any screen. Only feature
distributions (coverage, quantiles) and the turnaround / size counts were looked at while writing this file.
run_screens.py logs the sha256 of this file before it computes anything.

UNIVERSE  fa_panel.csv rows with in_fo == True and three_day not missing (3,278 results, qn 0..21).
TRADE     buy the cutoff close (2 sessions before the result session), sell the Day+1 close.
OUTCOMES  primary: three_day (percent, gross).  Secondary (reported, not used for the decision): tp3 (take-profit exit),
          excess_nifty_3d.  Cost 0.17% per round trip -> net = gross - 0.17 (longs) ; short P&L = -gross - 0.17.
FEATURES  only the panel's pre-results ("pre") columns + out/extra_features.csv (raw L1/L2/L5/L6 PAT, Nifty-adjusted
          market cap), all point-in-time (filings of quarters before the reported one, published before the cutoff).
          No rq_ (reported-quarter) column is used.

SCREENS (fixed textbook cut-offs; "o" = the opposite; "elig" = rows where the inputs exist, used as the random pool)
  VALUE
    V1   P/E < 15                                   (pe > 0 only)          elig: ttm_pat & mcap known
    V1o  P/E > 50                                                           elig: same
    V2   P/B < 1.5                                                          elig: pb known (qn >= 6)
    V2o  P/B > 10                                                           elig: same
    V3   Graham number: P/E x P/B < 22.5                                    elig: pe & pb known
    V4   P/E more than 20% below own 36-month median P/E (pe_vs_own3y_pct < -20)   elig: pe_vs_own3y_pct known
    V4o  P/E more than 20% above own 36-month median (> +20)
    V5   P/E more than 25% below same-industry peers' median on the same date (pe_vs_peers_pct < -25)
    V5o  P/E more than 25% above peers (> +25)                              elig: pe_vs_peers_pct known
  QUALITY
    Q1   ROE > 15% and debt/equity < 0.5 (banks have no D/E -> excluded)    elig: roe & d/e known
    Q1o  ROE < 10% or debt/equity > 1, non-financial companies only         elig: Company with roe & d/e
    Q2   no loss in any of the last 4 reported quarters (loss_any_4q == 0)  elig: loss_any_4q known
    Q2o  a loss in at least one of the last 4 quarters
    Q3   steady profits: std of last 8 YoY PAT growths < 20 pp              elig: pat_yoy_std8_pct known
    Q3o  erratic profits: std > 75 pp
  GROWTH
    G1   last quarter PAT YoY > +20% (positive base) and sales YoY > +10%   elig: pat_l1, pat_l5, l1_sales_yoy known
    G1o  last quarter PAT below a year earlier (pat_l1 < pat_l5) and sales YoY < +5%
    G2   growth accelerating: PAT YoY and sales YoY both higher than the quarter before (both accel > 0)
    G2o  both decelerating (both accel < 0)                                 elig: both accel known
    G3   PAT up YoY in 4 of the last 4 quarters                             elig: pat_up_yoy_4q known
    G3o  PAT up YoY in 0 or 1 of the last 4
  GARP
    GP1  PEG < 1 and TTM PAT growth > 15%                                   elig: pe known and ttm_pat_prev known
    GP1o PEG > 3
  MARGIN
    M1   EBITDA margin up more than 1 pp YoY in the last quarter (non-financials)   elig: margin change known
    M1o  EBITDA margin down more than 1 pp YoY
  TURNAROUND
    T1   loss a year ago, profit last quarter (pat_l5 < 0 < pat_l1)         elig: pat_l1 & pat_l5 known
    T1o  profit a year ago, loss last quarter (pat_l1 < 0 < pat_l5)
  DETERIORATING (hypothesised shorts)
    D1   PAT below a year earlier in each of the last 2 quarters (pat_l1 < pat_l5 and pat_l2 < pat_l6)
    D1o  PAT above a year earlier in both of the last 2 quarters            elig: all four PATs known
    D2   D1 and net margin down YoY in the last quarter                     elig: D1 inputs & net margin chg known
  PIOTROSKI-style (non-financial companies; 7 of 9 tests computable)
    P1   piotroski_n >= 5 and piotroski_frac >= 0.85 (e.g. 6+/7, 6/6, 5/5)  elig: piotroski_n >= 5
    P1o  piotroski_n >= 5 and piotroski_frac <= 0.30 (e.g. 0-2/7, 0-1/6)
    P2   all 7 tests available, score >= 6                                  elig: piotroski_full7 known (qn >= 11 mostly)
    P2o  all 7 available, score <= 3
  SIZE (AMFI-style bands, deflated by the Nifty: mcap_adj = mcap x 21,700 / Nifty at the cutoff)
    S1   mid or small cap: mcap_adj < Rs 67,000 cr                          elig: mcap_adj known
    S1o  large cap: mcap_adj >= Rs 67,000 cr
    S2   small cap: mcap_adj < Rs 22,000 cr
  DIVIDEND
    DV1  paid a dividend in the last 365 days (ex-date)                     elig: all
    DV1o no dividend in the last 365 days (or none on record)
  COMBINED
    C1   quality + value: Q1 and P/E < 20
    C2   quality + value (own history): Q1 and P/E below its own 36-month median (pe_vs_own3y_pct < 0)
    C3   quality + growth: Q1 and G1
  COMPOSITE fundamental score (5 flags: no loss in 4q; pat_l1 > pat_l5; last-quarter sales YoY > 0;
                               net margin up YoY; PAT up YoY in >= 3 of last 4 quarters; all 5 must be known)
    F1   5 of 5
    F1o  0 or 1 of 5
  => 44 screens in family A (counted for the multiple-testing adjustment).

STATISTICS (per screen)
  trades, distinct stocks, avg three_day, net (-0.17), avg tp3 (and net), up % (three_day > 0), avg vs Nifty,
  quarters with trades / with positive average / at >= 2%, first 14 (qn 0-13) vs last 8 (qn 14-21),
  average without the best 5 trades (for screens hypothesised as shorts also without the worst 5),
  baseline = average of the eligible pool in the same quarters weighted by the screen's trades per quarter,
  excess = avg - baseline (also vs ALL in_fo results in the same quarters),
  luck: 20,000 random same-size picks per quarter from the eligible pool of that quarter -> two-sided p of the
        screen's mean three_day (and percentile); also a quarter-clustered t of the per-quarter excess.
  multiple testing: Holm over the 44 family-A p-values (three_day); Bonferroni and Benjamini-Hochberg reported too.
  placebo (non-results days): the same picks, three-session windows shifted 15 and 30 sessions earlier
        (sessions i_cut-k+1 .. i_cut-k+3; L1 must be published before the session i_cut-k), with the same pool
        and the same random-pick test. A real results effect should be clearly larger in the results window.

DECISION RULE (fixed now). A screen "holds up" only if ALL of:
  (a) Holm-adjusted p < 0.05 (three_day, vs random same-quarter picks);
  (b) excess vs pool has the same sign in the first 14 and the last 8 quarters;
  (c) long: average without the best 5 still > +0.17% (cost); short: average without the worst 5 still < -0.17%;
  (d) the placebo excess (average of k = 15 and 30) is less than half the results-window excess.
  Screens with < 30 trades are reported but called "too few to judge".

FAMILY B - fundamentals as a filter on the existing "lag 10% + volume" trades (results/lag10_volume/trades.csv,
  85 trades; trades_vol13.csv, 44 trades, reported as a sensitivity only). Within the trades with the flag known,
  compare flag = 1 vs flag = 0 (difference in mean three_day; permutation p, 20,000 label shuffles; Holm over 6):
    B1  no loss in the last 4 quarters (Q2)
    B2  quality: ROE > 15% and D/E < 0.5 (Q1)
    B3  P/E below its own 36-month median (pe_vs_own3y_pct < 0)
    B4  last quarter PAT above a year earlier (pat_l1 > pat_l5)
    B5  large cap (mcap_adj >= Rs 67,000 cr)
    B6  P/E below same-industry peers (pe_vs_peers_pct < 0)
  A filter is only worth using if the Holm p < 0.05 AND both halves (first 14 / last 8) show the same sign.
"""
import numpy as np
import pandas as pd

COST = 0.17


def build_flags(p):
    """p: panel (in_fo universe) merged with extra_features. Returns {id: (pick mask, eligible mask, side, label)}.
    side: +1 = hypothesised long, -1 = hypothesised short, 0 = no prior direction (two-sided either way)."""
    nn = lambda *c: np.logical_and.reduce([p[x].notna().to_numpy() for x in c])
    v = lambda c: p[c].to_numpy(dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        pe, pb = v("pe"), v("pb")
        roe, de = v("roe_pct"), v("debt_equity")
        comp = (p["fin_type"] == "Company").to_numpy()
        e_pe = nn("ttm_pat", "mcap_cr")
        e_q1 = nn("roe_pct", "debt_equity")
        q1 = e_q1 & (roe > 15) & (de < 0.5)
        pat1, pat5, pat2, pat6 = v("pat_l1"), v("pat_l5"), v("pat_l2"), v("pat_l6")
        e_g1 = nn("pat_l1", "pat_l5", "l1_sales_yoy_pct")
        g1 = e_g1 & (pat5 > 0) & (pat1 / pat5 - 1 > 0.20) & (v("l1_sales_yoy_pct") > 10)
        e_d1 = nn("pat_l1", "pat_l5", "pat_l2", "pat_l6")
        d1 = e_d1 & (pat1 < pat5) & (pat2 < pat6)
        e_d2 = e_d1 & nn("l1_net_margin_chg_yoy_pp")
        pion, piof = v("piotroski_n"), v("piotroski_frac")
        e_p1 = (pion >= 5)
        madj = v("mcap_adj_cr")
        e_s = nn("mcap_adj_cr")
        dsd = v("days_since_dividend")
        fl = np.column_stack([
            v("loss_any_4q") == 0,
            pat1 > pat5,
            v("l1_sales_yoy_pct") > 0,
            v("l1_net_margin_chg_yoy_pp") > 0,
            v("pat_up_yoy_4q") >= 3])
        e_f = nn("loss_any_4q", "pat_l1", "pat_l5", "l1_sales_yoy_pct", "l1_net_margin_chg_yoy_pp", "pat_up_yoy_4q")
        fs = fl.sum(axis=1)
        allr = np.ones(len(p), bool)
        S = {
            "V1": (e_pe & (pe < 15), e_pe, +1, "P/E < 15"),
            "V1o": (e_pe & (pe > 50), e_pe, -1, "P/E > 50"),
            "V2": (nn("pb") & (pb < 1.5), nn("pb"), +1, "P/B < 1.5"),
            "V2o": (nn("pb") & (pb > 10), nn("pb"), -1, "P/B > 10"),
            "V3": (nn("pe", "pb") & (pe * pb < 22.5), nn("pe", "pb"), +1, "Graham: P/E x P/B < 22.5"),
            "V4": (nn("pe_vs_own3y_pct") & (v("pe_vs_own3y_pct") < -20), nn("pe_vs_own3y_pct"), +1, "P/E > 20% below own 3y median"),
            "V4o": (nn("pe_vs_own3y_pct") & (v("pe_vs_own3y_pct") > 20), nn("pe_vs_own3y_pct"), -1, "P/E > 20% above own 3y median"),
            "V5": (nn("pe_vs_peers_pct") & (v("pe_vs_peers_pct") < -25), nn("pe_vs_peers_pct"), +1, "P/E > 25% below industry peers"),
            "V5o": (nn("pe_vs_peers_pct") & (v("pe_vs_peers_pct") > 25), nn("pe_vs_peers_pct"), -1, "P/E > 25% above industry peers"),
            "Q1": (q1, e_q1, +1, "ROE > 15% and D/E < 0.5"),
            "Q1o": (e_q1 & comp & ((roe < 10) | (de > 1)), e_q1 & comp, -1, "ROE < 10% or D/E > 1 (companies)"),
            "Q2": (nn("loss_any_4q") & (v("loss_any_4q") == 0), nn("loss_any_4q"), +1, "No loss in last 4 quarters"),
            "Q2o": (nn("loss_any_4q") & (v("loss_any_4q") == 1), nn("loss_any_4q"), -1, "Loss in last 4 quarters"),
            "Q3": (nn("pat_yoy_std8_pct") & (v("pat_yoy_std8_pct") < 20), nn("pat_yoy_std8_pct"), +1, "Steady profit growth (std8 < 20pp)"),
            "Q3o": (nn("pat_yoy_std8_pct") & (v("pat_yoy_std8_pct") > 75), nn("pat_yoy_std8_pct"), -1, "Erratic profit growth (std8 > 75pp)"),
            "G1": (g1, e_g1, +1, "Last qtr PAT YoY > 20% and sales YoY > 10%"),
            "G1o": (e_g1 & (pat1 < pat5) & (v("l1_sales_yoy_pct") < 5), e_g1, -1, "Last qtr PAT down YoY and sales YoY < 5%"),
            "G2": (nn("pat_yoy_accel_pp", "sales_yoy_accel_pp") & (v("pat_yoy_accel_pp") > 0) & (v("sales_yoy_accel_pp") > 0),
                   nn("pat_yoy_accel_pp", "sales_yoy_accel_pp"), +1, "PAT and sales growth both accelerating"),
            "G2o": (nn("pat_yoy_accel_pp", "sales_yoy_accel_pp") & (v("pat_yoy_accel_pp") < 0) & (v("sales_yoy_accel_pp") < 0),
                    nn("pat_yoy_accel_pp", "sales_yoy_accel_pp"), -1, "PAT and sales growth both decelerating"),
            "G3": (nn("pat_up_yoy_4q") & (v("pat_up_yoy_4q") == 4), nn("pat_up_yoy_4q"), +1, "PAT up YoY 4 of last 4 quarters"),
            "G3o": (nn("pat_up_yoy_4q") & (v("pat_up_yoy_4q") <= 1), nn("pat_up_yoy_4q"), -1, "PAT up YoY 0-1 of last 4 quarters"),
            "GP1": (nn("pe", "ttm_pat_prev") & nn("peg") & (v("peg") < 1) & (v("ttm_pat_yoy_pct") > 15), nn("pe", "ttm_pat_prev"), +1,
                    "GARP: PEG < 1 and TTM PAT growth > 15%"),
            "GP1o": (nn("pe", "ttm_pat_prev") & nn("peg") & (v("peg") > 3), nn("pe", "ttm_pat_prev"), -1, "PEG > 3"),
            "M1": (nn("l1_ebitda_margin_chg_yoy_pp") & (v("l1_ebitda_margin_chg_yoy_pp") > 1), nn("l1_ebitda_margin_chg_yoy_pp"), +1,
                   "EBITDA margin up > 1pp YoY"),
            "M1o": (nn("l1_ebitda_margin_chg_yoy_pp") & (v("l1_ebitda_margin_chg_yoy_pp") < -1), nn("l1_ebitda_margin_chg_yoy_pp"), -1,
                    "EBITDA margin down > 1pp YoY"),
            "T1": (nn("pat_l1", "pat_l5") & (pat5 < 0) & (pat1 > 0), nn("pat_l1", "pat_l5"), +1, "Turnaround: loss a year ago, profit last qtr"),
            "T1o": (nn("pat_l1", "pat_l5") & (pat5 > 0) & (pat1 < 0), nn("pat_l1", "pat_l5"), -1, "Profit a year ago, loss last qtr"),
            "D1": (d1, e_d1, -1, "PAT down YoY 2 quarters running"),
            "D1o": (e_d1 & (pat1 > pat5) & (pat2 > pat6), e_d1, +1, "PAT up YoY 2 quarters running"),
            "D2": (e_d2 & d1 & (v("l1_net_margin_chg_yoy_pp") < 0), e_d2, -1, "PAT down 2 qtrs running and net margin down"),
            "P1": (e_p1 & (piof >= 0.85), e_p1, +1, "Piotroski-style high (>= 85% of tests)"),
            "P1o": (e_p1 & (piof <= 0.30), e_p1, -1, "Piotroski-style low (<= 30% of tests)"),
            "P2": (nn("piotroski_full7") & (v("piotroski_full7") >= 6), nn("piotroski_full7"), +1, "Piotroski all 7: score >= 6"),
            "P2o": (nn("piotroski_full7") & (v("piotroski_full7") <= 3), nn("piotroski_full7"), -1, "Piotroski all 7: score <= 3"),
            "S1": (e_s & (madj < 67000), e_s, 0, "Mid/small cap (adj. mcap < Rs 67,000 cr)"),
            "S1o": (e_s & (madj >= 67000), e_s, 0, "Large cap (adj. mcap >= Rs 67,000 cr)"),
            "S2": (e_s & (madj < 22000), e_s, 0, "Small cap (adj. mcap < Rs 22,000 cr)"),
            "DV1": (allr & (dsd <= 365), allr, 0, "Dividend in last 365 days"),
            "DV1o": (allr & ~(dsd <= 365), allr, 0, "No dividend in last 365 days"),
            "C1": (q1 & e_pe & (pe < 20), e_q1 & e_pe, +1, "Quality + value: ROE>15, D/E<0.5, P/E<20"),
            "C2": (q1 & nn("pe_vs_own3y_pct") & (v("pe_vs_own3y_pct") < 0), e_q1 & nn("pe_vs_own3y_pct"), +1,
                   "Quality + value: ROE>15, D/E<0.5, P/E below own 3y median"),
            "C3": (q1 & g1, e_q1 & e_g1, +1, "Quality + growth: ROE>15, D/E<0.5, PAT YoY>20%, sales YoY>10%"),
            "F1": (e_f & (fs == 5), e_f, +1, "Fundamental score 5 of 5"),
            "F1o": (e_f & (fs <= 1), e_f, -1, "Fundamental score 0-1 of 5"),
        }
    for k, (m, e, s, lab) in S.items():
        assert not (m & ~e).any(), k
    return S


def build_lag10_flags(p):
    """Family B flags (1 / 0 / NaN = unknown) on panel rows."""
    v = lambda c: p[c].to_numpy(dtype=float)
    out = {}
    with np.errstate(invalid="ignore"):
        def f(cond, known):
            x = np.where(known, cond.astype(float), np.nan)
            return x
        out["B1"] = (f(v("loss_any_4q") == 0, p["loss_any_4q"].notna().to_numpy()), "No loss in last 4 quarters")
        k = p[["roe_pct", "debt_equity"]].notna().all(axis=1).to_numpy()
        out["B2"] = (f((v("roe_pct") > 15) & (v("debt_equity") < 0.5), k), "ROE > 15% and D/E < 0.5")
        out["B3"] = (f(v("pe_vs_own3y_pct") < 0, p["pe_vs_own3y_pct"].notna().to_numpy()), "P/E below own 3y median")
        out["B4"] = (f(v("pat_l1") > v("pat_l5"), p[["pat_l1", "pat_l5"]].notna().all(axis=1).to_numpy()), "Last qtr PAT above a year earlier")
        out["B5"] = (f(v("mcap_adj_cr") >= 67000, p["mcap_adj_cr"].notna().to_numpy()), "Large cap (adj. mcap >= 67,000 cr)")
        out["B6"] = (f(v("pe_vs_peers_pct") < 0, p["pe_vs_peers_pct"].notna().to_numpy()), "P/E below industry peers")
    return out
