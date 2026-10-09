"""PRE-REGISTRATION - classic technical + fundamental COMBINED screens for the 3-day results window.

Written 2026-10-09 BEFORE any outcome (d1/d2/d3/three_day/take_profit/tp3/excess) was computed for any combination
below. While writing it only feature counts were looked at (how many in_fo results each combination selects, and in how
many quarters), never an outcome. run_combos.py writes the sha256 of this file to out/prereg_hash.txt before it reads
any outcome column. Every test listed here is counted in the multiple-testing family, whatever it shows.

UNIVERSE  ta/build/events_ta.csv rows with in_fo True and three_day present (3,278 F&O results, qn 0..21), joined
          1:1 on symbol + quarter to fa/build/fa_panel.csv and fa/A_pre_results/out/extra_features.csv (raw PAT of
          L1, L2, L5, L6 = the 1st, 2nd, 5th and 6th quarter before the reported one, same-basis pairs).
POINT IN TIME  technical columns use prices up to and including the cutoff close; fundamental columns are the panel's
          "pre" block (quarters before the reported one, published strictly before the cutoff; prices = cutoff close).
          No rq_ (reported-quarter) column is used anywhere.
TRADE     buy the cutoff close (2 sessions before the result session), sell the Day+1 close.
          three_day = d1 + d2 + d3 (percent, gross). Long take-profit = d1 if d1 > 3, else d1 + d2 if > 3, else three_day.
          Short trades are scored in their own direction: edge = -three_day; short take-profit = -d1 if -d1 > 3, else
          -(d1 + d2) if > 3, else -three_day. Cost 0.17 per round trip (net = edge - 0.17); a Nifty-hedged version
          (edge minus the Nifty 50's same three daily returns, direction-adjusted) costs 0.19.
          NaN in a comparison = condition false (a stock with unknown ROE is never "quality").

DEFINITIONS USED BELOW
  QA  quality (balance sheet): roe_pct > 15 and debt_equity < 0.5        (D/E not defined for banks -> never QA)
  QB  quality (earnings):      loss_any_4q == 0 and pat_l1 > pat_l5      ("profitable 4 quarters and profit growing")
  OS  oversold count = #(RSI14 < 30, %K14 < 20, %B < 0, CCI20 < -100, MFI14 < 20, Williams %R < -80)   (as in the TA run)
  OB  overbought count = #(RSI14 > 70, %K14 > 80, %B > 1, CCI20 > 100, MFI14 > 80, %R > -20)
  VO  P/E below its own 36-month median (pe_vs_own3y_pct < 0)            VP  P/E below same-industry peers (pe_vs_peers_pct < 0)
  BULLTRIG = macd_bull_x3 or hammer or bullish engulfing or RSI2 < 10
  BEARTRIG = macd_bear_x3 or shooting star or bearish engulfing or RSI2 > 90
  G   growth: pat_l5 > 0 and pat_l1 / pat_l5 - 1 > 20% and l1_sales_yoy_pct > 10
  G1o weak growth: pat_l1 < pat_l5 and l1_sales_yoy_pct < 5
  DET deteriorating: pat_l1 < pat_l5 and pat_l2 < pat_l6 (PAT below a year earlier in each of the last 2 quarters)
  IMP improving:     pat_l1 > pat_l5 and pat_l2 > pat_l6
  TURN turnaround: pat_l5 < 0 < pat_l1 (loss in the same quarter a year ago, profit last quarter)

COMBINATIONS  (L = long, S = short; "P" = the family's headline/union definition; all are tested and counted)
  1 Quality on a dip
    1A  L  QA and RSI14 < 30                     1D  L  QB and RSI14 < 30
    1B  L  QA and close < lower Bollinger band   1E  L  QB and close < lower Bollinger band
    1C  L  QA and OS >= 3                        1F  L  QB and OS >= 3
    1P  L  (QA or QB) and (RSI14 < 30 or %B < 0 or OS >= 3)
    1S  S  mirror "junk on a rally": weak quality ((company and (ROE < 10 or D/E > 1)) or a loss in the last 4 quarters)
           and overbought (RSI14 > 70 or %B > 1 or OB >= 3)
  2 Value + reversal
    2A  L  VO and MACD bullish cross (k-2..k)    2D  L  VP and MACD bullish cross
    2B  L  VO and (hammer or bullish engulfing)  2E  L  VP and (hammer or bullish engulfing)
    2C  L  VO and RSI2 < 10                      2F  L  VP and RSI2 < 10
    2P  L  (VO or VP) and BULLTRIG
    2S  S  mirror: (P/E above own 3y median or above peers) and BEARTRIG
  3 Growth + momentum (CANSLIM-like)
    3A  L  G and close > SMA50 and close > SMA200 and within 10% of the 52-week high (dist_52w_high_pct >= -10)
    3B  L  3A and 5/60-day volume ratio >= 1.0
    3S  S  mirror: G1o and close < SMA50 and close < SMA200 and within 10% of the 52-week low (dist_52w_low_pct <= 10)
  4 GARP + uptrend
    4A  L  PEG < 1 and golden-cross state (SMA50 > SMA200) and ADX14 > 25 and +DI > -DI
    4S  S  mirror: PEG > 3 and death-cross state and ADX14 > 25 and -DI > +DI
  5 Piotroski high + technical strength
    5A  L  piotroski_full7 >= 6 (all 7 computable tests available) and close > SMA200
    5B  L  piotroski_n >= 5 and piotroski_frac >= 0.85 (more coverage) and close > SMA200
    5S  S  mirror: piotroski_full7 <= 3 and close < SMA200
  6 Deteriorating + breakdown
    6A  S  DET and close < SMA200 and death-cross state
    6B  S  DET and close < SMA200 and Donchian-20 breakdown (close < prior 20-session low)
    6P  S  DET and close < SMA200 and (death-cross state or Donchian-20 breakdown)
    6L  L  mirror: IMP and close > SMA200 and golden-cross state
  7 Expensive + overbought
    7A  S  P/E > 50 and RSI14 > 70
    7B  S  P/E more than 25% above peers (pe_vs_peers_pct > 25) and RSI14 > 70
    7P  S  (P/E > 50 or P/E > peers + 25%) and RSI14 > 70
    7L  L  mirror "cheap + oversold": (P/E < 15 or P/E more than 25% below peers) and RSI14 < 30
  8 Turnaround + breakout
    8A  L  TURN and Donchian-20 breakout up (close > prior 20-session high)   (feature count: only 6 trades)
    8B  L  TURN and close > SMA50 and close > SMA200
    8C  L  loss in one of the last 4 quarters (loss_any_4q == 1) and profit last quarter (pat_l1 > 0) and
           Donchian-20 breakout up
  9 Simple combined score (fixed cut-offs; a flag with unknown inputs counts as neither good nor bad)
       fundamental flags (5): no loss in last 4 quarters; pat_l1 > pat_l5; last-quarter sales YoY > 10%;
                              EBITDA margin up YoY in the last quarter (> 0 pp); P/E below industry peers
       technical flags (5):   close > SMA200; close > SMA50; MACD line > signal; RSI14 > 50; OBV 20-day slope > 0
       good = # flags true, bad = # flags known and false (each 0..10 in total, 0..5 per part)
    9A  L  good total >= 8                        9B  S  bad total >= 8
    9C  L  fundamental good >= 4 and technical good >= 4
    9D  S  fundamental bad >= 4 and technical bad >= 4
    9SP    spread: 9A long minus 9B (mean of 9A trades minus mean of 9B trades), tested as one statistic
  => 40 tests in the family (39 trade sets + the 9SP spread).

STATISTICS (per combination; edge = direction-adjusted, percent)
  trades, distinct stocks, average, net (-0.17), take-profit average and net, up % (edge > 0), median,
  quarters with trades / positive, first 14 (qn 0..13) vs last 8 (qn 14..21) averages, average without the best 5,
  Nifty-hedged average (edge minus direction-adjusted Nifty 3-day) and its net (-0.19).
  Luck: random same-size per-quarter picks from ALL F&O results of the quarter = within-quarter permutations of the
    outcome (20,000). Statistic = average minus the random expectation (per-quarter pool means weighted by the trades
    per quarter); two-sided p = share of permutations with |stat| >= observed (+1 smoothing); also one-sided in the
    pre-registered direction. Same permutations for the take-profit outcome.
  Multiple testing over the 40 tests: Holm and Benjamini-Hochberg on the two-sided three_day p; family-wise
    Westfall-Young single-step max-|z| permutation p (same 20,000 within-quarter permutations, all 40 at once).
  Placebo (non-results days): placebo_ta.csv.gz rows with in_fo True (F&O stock-days at least 10 sessions from any
    results window; outcome = next three daily returns).
      restricted   = the SAME combination: technical part at day k AND the fundamental part as known at day k.
                     Fundamentals at day k = the stock's NEXT results row in fa_panel (its pre-results block uses only
                     quarters published before that cutoff; no results fall between day k and that cutoff, so the
                     accounting numbers are exactly those known at day k). Price-based fields are moved to day k:
                     pe_k = pe x adjclose_k / adjclose_cutoff (same for PEG), pe_vs_own3y and pe_vs_peers recomputed
                     from pe_k with that row's medians (approximation: the medians are as of the next cutoff).
                     Rows with no later results row in the panel are dropped from the restricted placebo.
      unrestricted = the technical part alone on all placebo rows (reported for every combination).
    results minus restricted placebo, z with SEs clustered by calendar month (results: cutoff month).
  Overlap with the lag-10% + volume rule (results/lag10_volume/trades.csv, 85 trades): count and the combination's
    average without those trades. Also the average of the fundamental part alone and of the technical part alone in
    the results window (descriptive: does the combination beat its parts?).

PASS CRITERIA (fixed now; all must hold to call a combination a candidate)
  (1) Holm p < 0.05 AND family-wise max-|z| p < 0.05 (three_day), effect in the pre-registered direction;
  (2) net average > 0;  (3) first-14 and last-8 averages both > 0;  (4) average without the best 5 > 0;
  (5) >= 60% of quarters with trades positive;  (6) results minus restricted placebo > 0;  (7) at least 30 trades.
  Nominal p < 0.05 in the right direction that fails any of these = "unconfirmed hint"; nominal p < 0.05 in the wrong
  direction = "reverse"; fewer than 30 trades = "too few to judge" (still counted in the family).
"""
import numpy as np
import pandas as pd

COST = 0.17
COST_HEDGED = 0.19

FAMILY = {"1": "Quality on a dip", "2": "Value + reversal", "3": "Growth + momentum (CANSLIM-like)",
          "4": "GARP + uptrend", "5": "Piotroski high + technical strength", "6": "Deteriorating + breakdown",
          "7": "Expensive + overbought", "8": "Turnaround + breakout", "9": "Combined score"}


def _b(s):
    """bool numpy array; NaN comparisons are already False."""
    return np.asarray(s, dtype=bool)


def counts(x):
    os_ = ((x.rsi14 < 30).astype(int) + (x.stoch_k14 < 20) + (x.bb_pctb < 0) + (x.cci20 < -100) + (x.mfi14 < 20)
           + (x.willr14 < -80))
    ob_ = ((x.rsi14 > 70).astype(int) + (x.stoch_k14 > 80) + (x.bb_pctb > 1) + (x.cci20 > 100) + (x.mfi14 > 80)
           + (x.willr14 > -20))
    return os_.to_numpy(), ob_.to_numpy()


def score_parts(x):
    """(fundamental good, fundamental bad, technical good, technical bad) counts per row."""
    def fl(cond, known):
        known = _b(known)
        return np.where(known, _b(cond).astype(float), np.nan)
    F = np.column_stack([
        fl(x.loss_any_4q == 0, x.loss_any_4q.notna()),
        fl(x.pat_l1 > x.pat_l5, x.pat_l1.notna() & x.pat_l5.notna()),
        fl(x.l1_sales_yoy_pct > 10, x.l1_sales_yoy_pct.notna()),
        fl(x.l1_ebitda_margin_chg_yoy_pp > 0, x.l1_ebitda_margin_chg_yoy_pp.notna()),
        fl(x.pe_vs_peers_pct < 0, x.pe_vs_peers_pct.notna())])
    T = np.column_stack([
        fl(x.close_vs_sma200_pct > 0, x.close_vs_sma200_pct.notna()),
        fl(x.close_vs_sma50_pct > 0, x.close_vs_sma50_pct.notna()),
        fl(x.macd_pct > x.macd_signal_pct, x.macd_pct.notna() & x.macd_signal_pct.notna()),
        fl(x.rsi14 > 50, x.rsi14.notna()),
        fl(x.obv_slope20 > 0, x.obv_slope20.notna())])
    return ((F == 1).sum(1), (F == 0).sum(1), (T == 1).sum(1), (T == 0).sum(1))


def build(x):
    """x: frame with technical + fundamental columns (events or placebo). Returns
    {id: dict(mask, fa, ta, side (+1 long / -1 short), label, family)}; fa / ta = the parts alone."""
    os_, ob_ = counts(x)
    v = lambda c: x[c].to_numpy(dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        roe, de, pe = v("roe_pct"), v("debt_equity"), v("pe")
        p1, p5, p2, p6 = v("pat_l1"), v("pat_l5"), v("pat_l2"), v("pat_l6")
        rsi, rsi2, pctb = v("rsi14"), v("rsi2"), v("bb_pctb")
        above200, above50 = v("close_vs_sma200_pct") > 0, v("close_vs_sma50_pct") > 0
        below200, below50 = v("close_vs_sma200_pct") < 0, v("close_vs_sma50_pct") < 0
        golden, death = v("golden_state") == 1, v("golden_state") == 0
        adx, pdi, mdi = v("adx14"), v("plus_di14"), v("minus_di14")
        comp = (x["fin_type"] == "Company").to_numpy()
        QA = (roe > 15) & (de < 0.5)
        QB = (v("loss_any_4q") == 0) & (p1 > p5)
        rsi_lo, bb_lo, os3 = rsi < 30, pctb < 0, os_ >= 3
        dip = rsi_lo | bb_lo | os3
        weakq = (comp & ((roe < 10) | (de > 1))) | (v("loss_any_4q") == 1)
        overb = (rsi > 70) | (pctb > 1) | (ob_ >= 3)
        VO, VP = v("pe_vs_own3y_pct") < 0, v("pe_vs_peers_pct") < 0
        EO, EP = v("pe_vs_own3y_pct") > 0, v("pe_vs_peers_pct") > 0
        macd_b, macd_s = v("macd_bull_x3") == 1, v("macd_bear_x3") == 1
        cdl_b = (v("cdl_hammer") == 1) | (v("cdl_bull_engulf") == 1)
        cdl_s = (v("cdl_shooting_star") == 1) | (v("cdl_bear_engulf") == 1)
        r2lo, r2hi = rsi2 < 10, rsi2 > 90
        BULLT, BEART = macd_b | cdl_b | r2lo, macd_s | cdl_s | r2hi
        G = (p5 > 0) & (p1 / p5 - 1 > 0.20) & (v("l1_sales_yoy_pct") > 10)
        G1o = (p1 < p5) & (v("l1_sales_yoy_pct") < 5)
        mom = above50 & above200 & (v("dist_52w_high_pct") >= -10)
        momS = below50 & below200 & (v("dist_52w_low_pct") <= 10)
        vol1 = v("vol_ratio_5_60") >= 1.0
        peg = v("peg")
        up_trend = golden & (adx > 25) & (pdi > mdi)
        dn_trend = death & (adx > 25) & (mdi > pdi)
        pio7, pion, piof = v("piotroski_full7"), v("piotroski_n"), v("piotroski_frac")
        DET = (p1 < p5) & (p2 < p6)
        IMP = (p1 > p5) & (p2 > p6)
        brk_dn, brk_up = v("don20_break_dn") == 1, v("don20_break_up") == 1
        ppeer = v("pe_vs_peers_pct")
        exp_ = (pe > 50) | (ppeer > 25)
        cheap = ((pe > 0) & (pe < 15)) | (ppeer < -25)
        TURN = (p5 < 0) & (p1 > 0)
        TURN2 = (v("loss_any_4q") == 1) & (p1 > 0)
        fg, fb, tg, tb = score_parts(x)

    D = {}

    def add(i, side, label, fa, ta):
        D[i] = {"mask": _b(fa) & _b(ta), "fa": _b(fa), "ta": _b(ta), "side": side, "label": label, "family": i[0]}

    add("1A", +1, "QA (ROE>15, D/E<0.5) & RSI14<30", QA, rsi_lo)
    add("1B", +1, "QA & close < lower BB", QA, bb_lo)
    add("1C", +1, "QA & oversold count>=3", QA, os3)
    add("1D", +1, "QB (no loss 4q, PAT up YoY) & RSI14<30", QB, rsi_lo)
    add("1E", +1, "QB & close < lower BB", QB, bb_lo)
    add("1F", +1, "QB & oversold count>=3", QB, os3)
    add("1P", +1, "(QA or QB) & any oversold", QA | QB, dip)
    add("1S", -1, "SHORT weak quality & overbought", weakq, overb)
    add("2A", +1, "P/E<own 3y median & MACD bull cross", VO, macd_b)
    add("2B", +1, "P/E<own 3y median & hammer/bull engulf", VO, cdl_b)
    add("2C", +1, "P/E<own 3y median & RSI2<10", VO, r2lo)
    add("2D", +1, "P/E<peers & MACD bull cross", VP, macd_b)
    add("2E", +1, "P/E<peers & hammer/bull engulf", VP, cdl_b)
    add("2F", +1, "P/E<peers & RSI2<10", VP, r2lo)
    add("2P", +1, "(P/E<own or <peers) & any bull trigger", VO | VP, BULLT)
    add("2S", -1, "SHORT (P/E>own or >peers) & any bear trigger", EO | EP, BEART)
    add("3A", +1, "PAT YoY>20%, sales>10% & >SMA50,200 & <=10% off 52w high", G, mom)
    add("3B", +1, "3A & volume ratio>=1.0", G, mom & vol1)
    add("3S", -1, "SHORT PAT down, sales<5% & <SMA50,200 & <=10% above 52w low", G1o, momS)
    add("4A", +1, "PEG<1 & golden state & ADX>25, +DI>-DI", peg < 1, up_trend)
    add("4S", -1, "SHORT PEG>3 & death state & ADX>25, -DI>+DI", peg > 3, dn_trend)
    add("5A", +1, "Piotroski 7/7 avail, score>=6 & close>SMA200", pio7 >= 6, above200)
    add("5B", +1, "Piotroski n>=5, frac>=0.85 & close>SMA200", (pion >= 5) & (piof >= 0.85), above200)
    add("5S", -1, "SHORT Piotroski 7 avail, score<=3 & close<SMA200", pio7 <= 3, below200)
    add("6A", -1, "SHORT PAT down YoY 2q & <SMA200 & death state", DET, below200 & death)
    add("6B", -1, "SHORT PAT down YoY 2q & <SMA200 & 20d breakdown", DET, below200 & brk_dn)
    add("6P", -1, "SHORT PAT down YoY 2q & <SMA200 & (death or breakdown)", DET, below200 & (death | brk_dn))
    add("6L", +1, "PAT up YoY 2q & >SMA200 & golden state", IMP, above200 & golden)
    add("7A", -1, "SHORT P/E>50 & RSI14>70", pe > 50, rsi > 70)
    add("7B", -1, "SHORT P/E>peers+25% & RSI14>70", ppeer > 25, rsi > 70)
    add("7P", -1, "SHORT (P/E>50 or >peers+25%) & RSI14>70", exp_, rsi > 70)
    add("7L", +1, "(P/E<15 or <peers-25%) & RSI14<30", cheap, rsi < 30)
    add("8A", +1, "Turnaround (L5<0<L1) & 20d breakout", TURN, brk_up)
    add("8B", +1, "Turnaround & >SMA50 & >SMA200", TURN, above50 & above200)
    add("8C", +1, "Loss in last 4q, profit last q & 20d breakout", TURN2, brk_up)
    add("9A", +1, "Score: good flags >= 8 of 10", fg >= 4 - 10, (fg + tg) >= 8)   # fa part = all rows
    add("9B", -1, "SHORT score: bad flags >= 8 of 10", fb >= 4 - 10, (fb + tb) >= 8)
    add("9C", +1, "FA good>=4 of 5 & TA good>=4 of 5", fg >= 4, tg >= 4)
    add("9D", -1, "SHORT FA bad>=4 of 5 & TA bad>=4 of 5", fb >= 4, tb >= 4)
    # For 9A / 9B the "parts" are reported as FA good >= 4 / TA good >= 4 (resp. bad) for the descriptive columns.
    D["9A"]["fa"], D["9A"]["ta"] = fg >= 4, tg >= 4
    D["9B"]["fa"], D["9B"]["ta"] = fb >= 4, tb >= 4
    return D


SPREADS = {"9SP": ("9A", "9B", "Spread: 9A long minus 9B")}
