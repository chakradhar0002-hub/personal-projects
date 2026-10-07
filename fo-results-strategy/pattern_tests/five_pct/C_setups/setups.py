"""
PRE-REGISTRATION  (written 2026-10-07, before any outcome was computed in this folder)
==================================================================================
Goal: find a setup, known at the cutoff close (2 sessions before the result session), whose
3-day results window (Day-1 + Result day + Day+1) averages MORE THAN +5% per trade overall.

Everything below is fixed BEFORE looking at outcomes. Thresholds come from trading logic
(round numbers), not from data. Every setup is tested exactly once, long setups in their
plain 3-day form AND in the take-profit form (tp3), short setups in plain and a symmetric
take-profit form (tp3s: exit after Day-1 if short profit > 3%, after Result day if cumulative
short profit > 3%). Short P&L = minus the window return.

Feature units are fractions (0.10 = 10%). All price features verified against daily returns:
r1w = 5-session return, r1m = 21 sessions, vs_nifty_* = stock return minus Nifty-50 return,
vs_ma50 = close / 50-session average - 1, from_52w_high/low over 250 sessions,
vol60 = annualised sd of last 60 daily returns.

NEW features built from returns.csv / intraday.csv at the cutoff close:
  ret_c0      = return on the cutoff day itself
  r3d         = 3-session return ending at the cutoff
  down_streak = consecutive down closes ending at the cutoff (up_streak likewise)
  down10      = number of down closes among the last 10 sessions
  gap_c0      = cutoff-day open vs previous close
  z1w         = r1w / (vol60 * sqrt(5/252))   (1-week move in units of the stock's own volatility)
  big_washout = 1 if (vs_nifty_1w <= -0.10) or (vs_nifty_1m <= -0.20) or (vs_ma50 <= -0.15)
Not used anywhere: after_close / timing (results time is usually not known in advance),
three_day, excess_nifty, tp3, anything from events.csv after i_cut.

UNIVERSE: main = in_fo True at the time. All-stocks version reported separately.
COSTS: 0.17% per round trip, net = gross - 0.17.

FIXED SETUPS  (id, direction, conditions ANDed; 'post-hoc' = idea came from earlier looks at all 22 quarters)
"""
import numpy as np

LN25K = float(np.log(25000.0))   # market cap 25,000 crore

SETUPS = [
    # ---- LONG: oversold / washout into results --------------------------------------
    ("L01_lag1w_10",   +1, [("vs_nifty_1w", "<", -0.10)], "POST-HOC idea from earlier work (lagged Nifty >10% in the week)"),
    ("L01a_lag1w_06",  +1, [("vs_nifty_1w", "<", -0.06)], "stability variant of L01"),
    ("L01b_lag1w_08",  +1, [("vs_nifty_1w", "<", -0.08)], "stability variant of L01"),
    ("L01c_lag1w_12",  +1, [("vs_nifty_1w", "<", -0.12)], "stability variant of L01"),
    ("L01d_lag1w_15",  +1, [("vs_nifty_1w", "<", -0.15)], "stability variant of L01"),
    ("L02_lag1m_15",   +1, [("vs_nifty_1m", "<", -0.15)], "1-month lag vs Nifty below -15%"),
    ("L03_below50_10", +1, [("vs_ma50", "<", -0.10)], "10%+ below 50-day average"),
    ("L04_streak5",    +1, [("down_streak", ">=", 5)], "5+ down closes in a row into the cutoff"),
    ("L05_at52wlow",   +1, [("from_52w_low", "<=", 0.02)], "within 2% of 52-week low"),
    ("L06_capit_vol",  +1, [("volume_5d_vs_60d", ">=", 2.0), ("r1w", "<=", -0.05)], "capitulation volume: 2x volume and week down 5%+"),
    ("L07_past_pos",   +1, [("past_avg_3d", ">=", 0.03), ("past_pct_up", ">=", 0.60)], "history of big positive results reactions"),
    ("L08_goodprev_drop", +1, [("prev1_3d", ">=", 0.05), ("r1m", "<=", -0.10)], "last results reaction +5%+, stock down 10%+ in the month since"),
    ("L09_iv_oversold", +1, [("iv_vs_realised", ">=", 1.4), ("vs_nifty_1m", "<=", -0.10)], "options price a big move and stock lagged Nifty 10%+ in a month"),
    ("L10_small_oversold", +1, [("log_mcap", "<=", LN25K), ("vs_nifty_1m", "<=", -0.10)], "mcap < 25,000 cr and lagged Nifty 10%+ in a month"),
    ("L11_sector_washout", +1, [("sector_1m", "<=", -0.08), ("vs_sector_1m", "<=", -0.05)], "sector down 8%+ in a month and stock 5%+ worse than its sector"),
    ("L12_sigma_drop", +1, [("z1w", "<=", -2.5)], "1-week drop of 2.5+ own-volatility sigmas"),
    ("L13_cutday_crash", +1, [("ret_c0", "<=", -0.05)], "cutoff day itself down 5%+"),
    ("L14_drop3d",     +1, [("r3d", "<=", -0.08)], "down 8%+ in the last 3 sessions"),
    ("L15_deep_combo", +1, [("vs_ma50", "<=", -0.10), ("from_52w_high", "<=", -0.30), ("r1m", "<=", -0.10)], "deep washout combo"),
    ("L16_breakout_eps", +1, [("from_52w_high", ">=", -0.03), ("prev_pat_yoy", ">=", 0.25)], "near 52w high and last-quarter profit +25% yoy"),
    ("L17_early_strong", +1, [("days_after_quarter_end", "<=", 19), ("vs_nifty_1w", ">=", 0.06)], "POST-HOC idea (rounded): early reporter that beat Nifty 6%+ in the week"),
    ("L18_gapdown_oversold", +1, [("gap_c0", "<=", -0.03), ("r1w", "<=", -0.08)], "cutoff-day gap down 3%+ after a week down 8%+"),
    ("L19_prevpos_selloff", +1, [("prev1_3d", ">=", 0.05), ("vs_nifty_1w", "<=", -0.05)], "last results reaction +5%+, lagged Nifty 5%+ this week"),
    ("L20_peers_strong", +1, [("peers_reported_3d", ">=", 0.04)], "peers that already reported moved +4%+ on average"),
    ("L21_season_oversold", +1, [("season_so_far_3d", ">=", 0.01), ("vs_nifty_1m", "<=", -0.10)], "season rewarding results and stock lagged 10%+ in a month"),
    ("L22_big_washout", +1, [("big_washout", "==", 1)], "union of extreme oversold flags"),
    ("L23_quality_oversold", +1, [("profit_rising_4q", "==", 1), ("vs_nifty_1m", "<=", -0.08)], "profit rising 4 quarters, lagged Nifty 8%+ in a month"),
    ("L24_high_iv", +1, [("iv_vs_realised", ">=", 1.6)], "options price a very big move (long)"),
    ("L25_down10_8", +1, [("down10", ">=", 8)], "8+ down closes in last 10 sessions"),
    # ---- SHORT: huge run-up into results ---------------------------------------------
    ("S01_runup1w_10", -1, [("vs_nifty_1w", ">=", 0.10)], "beat Nifty 10%+ in the week"),
    ("S02_runup1m_20", -1, [("vs_nifty_1m", ">=", 0.20)], "beat Nifty 20%+ in the month"),
    ("S03_above50_20", -1, [("vs_ma50", ">=", 0.20)], "20%+ above 50-day average"),
    ("S04_upstreak6",  -1, [("up_streak", ">=", 6)], "6+ up closes in a row"),
    ("S05_vol_runup",  -1, [("volume_5d_vs_60d", ">=", 2.5), ("r1w", ">=", 0.08)], "2.5x volume and week up 8%+"),
    ("S06_past_neg",   -1, [("past_avg_3d", "<=", -0.03), ("past_pct_up", "<=", 0.40)], "history of big negative results reactions"),
    ("S07_iv_runup",   -1, [("iv_vs_realised", ">=", 1.4), ("vs_nifty_1m", ">=", 0.15)], "options price a big move after a 15%+ monthly outperformance"),
    ("S08_peers_weak", -1, [("peers_reported_3d", "<=", -0.04)], "peers that already reported fell 4%+ on average"),
    ("S09_cutday_spike", -1, [("ret_c0", ">=", 0.06)], "cutoff day itself up 6%+"),
    ("S10_badprev_rally", -1, [("prev1_3d", "<=", -0.05), ("r1m", ">=", 0.10)], "last results reaction -5% or worse, then rallied 10%+ in a month"),
    ("S11_sigma_rally", -1, [("z1w", ">=", 3.0)], "1-week rally of 3+ own-volatility sigmas"),
]

# Each setup is tested in two outcome versions: plain 3-day and take-profit (tp3 / tp3s).
OUTCOMES = ["3day", "tp"]

# SELECTION / HONEST-TEST PROTOCOL (fixed in advance)
#  * Candidate pool = all SETUPS x OUTCOMES (82 variants).
#  * In-sample = qn 0..13, out-of-sample = qn 14..21.
#  * "Best" = highest in-sample pooled gross average per trade among variants with
#    >= MIN_TRADES in-sample trades spread over >= 5 in-sample quarters; MIN_TRADES in {10, 20, 30}.
#  * Walk-forward: for each q in 6..21 choose the best variant on quarters < q
#    (>= MIN_TRADES trades over >= 3 quarters), apply it to quarter q, pool the picks.
#  * Luck check: identical selection with the outcome rows shuffled within each quarter
#    (all outcome columns move together), N_SHUFFLE = 500 runs.
#  * Per-setup luck check: 2000 within-quarter shuffles, one-sided p of the 22-quarter average.
#  * Placebo: same price conditions on non-results 3-day windows (cutoff with no result session
#    of that stock within 10 sessions of the window), F&O-at-the-time stocks, same 2021-2026 span.
#    Conditions that cannot exist outside results (volume, IV, peers, season, days after quarter
#    end) are dropped in the placebo and this is reported. Stock-history features (prev1_3d,
#    past_avg_3d, past_pct_up, prev_pat_yoy, profit_rising_4q) are taken from the stock's NEXT
#    result row (they only use results before the placebo date); log_mcap from the PREVIOUS row.
MIN_TRADES_LIST = [10, 20, 30]
N_SHUFFLE = 500
N_SHUFFLE_SETUP = 2000
COST = 0.0017
SEED = 20261007

# POST-RUN NOTE (added after evaluate.py ran; setups/thresholds above were NOT changed):
# the list holds 40 setups (29 long incl. 4 stability variants of L01, 11 short) -> 80 variants, not 82 as written above.
# round2_composite.py (oversold composite score, 16 variants) was designed AFTER seeing round-1 results = post-hoc.
