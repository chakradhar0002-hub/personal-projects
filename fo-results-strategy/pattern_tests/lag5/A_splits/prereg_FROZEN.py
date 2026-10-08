"""
prereg.py  --  PRE-REGISTERED, INTERPRETABLE SPLITS of the "lagged Nifty by > 5% over the month" group.

Written 2026-10-08 BEFORE any outcome (three_day / take_profit / placebo forward return) was computed for any split.
Only the feature distributions inside the group (no outcomes) were looked at to choose round cut points.
A frozen copy + sha256 is stored as prereg_FROZEN.py / prereg_sha256.txt before 02_splits.py is run.

GROUP: results where vs_nifty_1m (stock 21-session return minus Nifty 50 21-session return, at the cutoff close)
       < -5%.  Main universe in_fo True (679 trades); all results secondary (~936).
TRADE: buy cutoff close, sell Day+1 close (three_day = Day-1 + Result day + Day+1 returns, summed).
       Take-profit exit (tp3) reported for every split as well.  Cost 0.17% per round trip.
UNITS: all features are fractions (0.10 = 10%); results are reported in PERCENT.

For every split: side A = the side a trader would expect to BOUNCE (tested LONG);
                 side B = the side expected to KEEP FALLING (tested SHORT where `short` is True;
                 B's long average is always reported too).  Rows matching neither side are left out.
Reported per split: both sides' n, average (3-day and tp3), up-rate, quarters positive, first-14 vs last-8,
the difference A-B pooled and as a per-quarter difference with a t-value across quarters (all 22, first 14,
last 8), a depth-adjusted difference (each trade minus the average of its lag band 5-10 / 10-15 / >15),
each side's average lag (to see if a split is just depth in disguise), and the same split on a
NON-RESULTS PLACEBO (same filter, same stocks, F&O at the time, lag > 5% at a session with no result session
of that stock in [c-10, c+13], 3-day forward return summed).

------------------------------------------------------------------------------------------------------------
WHY a lagging stock might bounce or keep falling into results (the trader logic behind each family):
 F1 depth      deeper oversold -> bigger snap-back (already known; partly an ordinary bounce)
 F2 market     if the whole market fell, the stock's lag is "beta" and should mean-revert; if the market rose
               and the stock still fell, something stock-specific is wrong -> keeps falling
 F3 sector     sector-wide selling (rotation) vs the stock alone (company-specific news / informed selling)
 F4 speed      a sharp, recent fall = capitulation, snaps back; a slow bleed = steady distribution, continues.
               COMPETING hypothesis also tested: a bounce that already started (up days into the cutoff) continues
 F5 trend      a dip inside an uptrend gets bought; a stock in a downtrend / at 52-week lows keeps falling
 F6 volume/vol capitulation volume / volatility spike / rich options = fear already in the price -> bounce
 F7 history    stocks that usually react well to results (and did last time) vs serial disappointers
 F8 fundament. growing, profitable, cheap, low-debt companies get bought on a dip; weak/expensive ones de-rate
 F9 size       large caps have institutional support and mean-revert; small caps keep sliding (no prior on
               financials vs companies -> two-sided)
 F10 timing    early reporters tend to carry good news, late ones bad news; good peer read-through / good season
               mood / high-fear regime -> bounce
------------------------------------------------------------------------------------------------------------
DERIVED FEATURES (built in 01_build.py from cutoff-time data only):
  lag       = vs_nifty_1m
  ratio_1w  = vs_nifty_1w / vs_nifty_1m   (share of the month's lag that came in the last 5 sessions)
  worst1m   = worst single daily return in the 21 sessions ending at the cutoff
  fin       = 1 if fin_type is Bank or NBFC / financial, else 0

ALSO PRE-REGISTERED (not splits):
  C01 depth curve: lag bands 5-7.5, 7.5-10, 10-12.5, 12.5-15, 15-17.5, 17.5-20, >20 (results and placebo),
      plus the per-quarter OLS slope of three_day on lag inside the group, t across quarters.
  D01 sector table: averages by sector_index (descriptive only, NOT a tradeable split: picking a sector after
      looking would be data mining).

COMBINATION RULES (fixed now, applied mechanically after the 41 splits are computed; 3-day exit drives selection):
  COMBO-H (honest; chosen on the FIRST 14 QUARTERS ONLY, last 8 = true out-of-sample):
     eligible long splits: side A has >= 25 trades in qn 0-13, first-14 per-quarter diff t (A-B) >= 1.5,
     side A first-14 average > 0.  Rank by first-14 diff t.  Take the top split, then the next-ranked split from
     a DIFFERENT family, then a third from a third family.  Test  group AND A1 AND A2  (2-way) and
     group AND A1 AND A2 AND A3 (3-way, only if it has >= 15 first-14 trades).  Long.
     Same for SHORT with B sides: B >= 25 first-14 trades, first-14 diff t >= 1.5, B first-14 average < 0;
     test group AND B1 AND B2 short.
  COMBO-T (the task's wording; chosen AFTER seeing the last 8 -> NOT out-of-sample, reported as in-sample only):
     eligible: side A average > 0 in first 14 AND last 8, and A-B difference > 0 in both halves.
     Rank by all-22 per-quarter diff t; top 2 from different families (2-way) and top 3 (3-way).  Long.
  Every combo: all-22, first 14 vs last 8, per quarter, quarters positive, gross/net, tp3, without best 5,
  placebo (same AND rule on non-results dates; features without a placebo version are dropped from the placebo
  rule and that is stated), luck = 5,000 random same-size-per-quarter subsets of the group, and for COMBO-H the
  identical selection run on 500 outcome sets shuffled within quarter and sign-flipped around the quarter mean.

BATTERY LUCK: the whole 41-split battery is recomputed on 1,000 within-quarter shuffled + sign-flipped outcome
  sets to show how many |t| >= 2 differences and how big a best |t| appear by chance.
"""

# (id, family, name, side A expr, side B expr, short_B?, placebo_ok?, note)
# expressions are pandas .eval() strings on the group table
SPLITS = [
    # F1 depth
    ('S01', 'F1_depth', 'lag > 10% vs 5-10%', 'lag < -0.10', 'lag >= -0.10', True, True, ''),
    ('S02', 'F1_depth', 'lag > 15% vs 5-15%', 'lag < -0.15', 'lag >= -0.15', True, True, 'already known'),
    # F2 market vs stock-specific
    ('S03', 'F2_market', 'stock own 1M < 0 vs >= 0', 'r1m < 0', 'r1m >= 0', True, True, ''),
    ('S04', 'F2_market', 'Nifty 1M < 0 vs >= 0', 'nifty_1m < 0', 'nifty_1m >= 0', True, True, ''),
    ('S05', 'F2_market', 'Nifty 1M < -3% vs > +3%', 'nifty_1m < -0.03', 'nifty_1m > 0.03', True, True, ''),
    # F3 sector
    ('S06', 'F3_sector', 'sector lagged Nifty >3% vs sector kept up', 'sec_vs_nifty_1m < -0.03', 'sec_vs_nifty_1m >= 0', True, True, ''),
    ('S07', 'F3_sector', 'stock with sector (vs_sector > -5%) vs lagged own sector', 'vs_sector_1m >= -0.05', 'vs_sector_1m < -0.05', True, True, ''),
    # F4 speed / shape
    ('S08', 'F4_speed', 'last week r1w < -5% vs r1w >= 0', 'r1w < -0.05', 'r1w >= 0', True, True, ''),
    ('S09', 'F4_speed', 'most of lag in last week (ratio_1w >= 0.5) vs older', 'ratio_1w >= 0.5', 'ratio_1w < 0.5', True, True, ''),
    ('S10', 'F4_speed', '3-session drop r3d <= -3% vs r3d >= 0', 'r3d <= -0.03', 'r3d >= 0', True, True, ''),
    ('S11', 'F4_speed', 'bounce started: cutoff day up vs down', 'd0 > 0', 'd0 <= 0', True, True, 'competing hypothesis'),
    ('S12', 'F4_speed', 'streak >= 2 up days vs <= 3 down days', 'streak >= 2', 'streak <= -3', True, True, 'competing hypothesis'),
    ('S13', 'F4_speed', '4%+ off 20-day low vs at the low (<1%)', 'dist_20l >= 0.04', 'dist_20l < 0.01', True, True, 'competing hypothesis'),
    ('S14', 'F4_speed', 'news shock (a -6% day) vs slow bleed (no day < -3%)', 'worst1m <= -0.06', 'worst1m > -0.03', True, True, ''),
    # F5 long-term trend
    ('S15', 'F5_trend', 'above 200-day avg vs >10% below', 'vs_ma200 > 0', 'vs_ma200 < -0.10', True, True, ''),
    ('S16', 'F5_trend', 'within 15% of 52w high vs >30% below', 'from_52w_high > -0.15', 'from_52w_high < -0.30', True, True, ''),
    ('S17', 'F5_trend', '>20% above 52w low vs within 5% of it', 'from_52w_low > 0.20', 'from_52w_low < 0.05', True, True, ''),
    ('S18', 'F5_trend', '1Y return > +20% vs < 0', 'r1y > 0.20', 'r1y < 0', True, True, ''),
    ('S19', 'F5_trend', '3M return > 0 vs < -15%', 'r3m > 0', 'r3m < -0.15', True, True, ''),
    # F6 volume / volatility / options
    ('S20', 'F6_volvol', 'volume 5d/60d >= 1.5 vs < 1.0', 'volume_5d_vs_60d >= 1.5', 'volume_5d_vs_60d < 1.0', True, False, 'no volume in data pack -> no placebo'),
    ('S21', 'F6_volvol', 'vol60 >= 35% vs < 25%', 'vol60 >= 0.35', 'vol60 < 0.25', False, True, ''),
    ('S22', 'F6_volvol', 'vol spike vol5/60 >= 1.2 vs calm < 0.7', 'vol5_60 >= 1.2', 'vol5_60 < 0.7', True, True, ''),
    ('S23', 'F6_volvol', 'IV/realised >= 1.3 vs < 1.0', 'iv_vs_realised >= 1.3', 'iv_vs_realised < 1.0', True, False, 'options only at results -> no placebo'),
    # F7 own results history
    ('S24', 'F7_history', 'past avg results 3-day > 0 vs <= 0', 'past_avg_3d > 0', 'past_avg_3d <= 0', True, True, ''),
    ('S25', 'F7_history', 'past % up >= 60% vs <= 40%', 'past_pct_up >= 0.6', 'past_pct_up <= 0.4', True, True, ''),
    ('S26', 'F7_history', 'last results 3-day >= 0 vs < 0', 'prev1_3d >= 0', 'prev1_3d < 0', True, True, ''),
    ('S27', 'F7_history', 'drift after last results >= 0 vs < 0', 'prev1_next20 >= 0', 'prev1_next20 < 0', True, True, ''),
    # F8 fundamentals / valuation
    ('S28', 'F8_fundam', 'prev PAT YoY >= 15% vs < 0', 'prev_pat_yoy >= 0.15', 'prev_pat_yoy < 0', True, True, ''),
    ('S29', 'F8_fundam', 'prev sales YoY >= 10% vs < 5%', 'prev_sales_yoy >= 0.10', 'prev_sales_yoy < 0.05', True, True, ''),
    ('S30', 'F8_fundam', 'profit rising 4 quarters vs not', 'profit_rising_4q == 1', 'profit_rising_4q == 0', True, True, ''),
    ('S31', 'F8_fundam', 'ROE >= 15% vs < 10%', 'roe >= 0.15', 'roe < 0.10', True, True, ''),
    ('S32', 'F8_fundam', 'PE 0-25 vs PE >= 50', '(pe > 0) & (pe <= 25)', 'pe >= 50', True, True, ''),
    ('S33', 'F8_fundam', 'PE below peers vs >50% above', 'pe_vs_peers < 0', 'pe_vs_peers > 0.5', True, True, ''),
    ('S34', 'F8_fundam', 'debt/equity <= 0.1 vs >= 1.0', 'debt_equity <= 0.1', 'debt_equity >= 1.0', True, True, ''),
    # F9 size / type
    ('S35', 'F9_size', 'log mcap >= 11.5 vs < 10.8', 'log_mcap >= 11.5', 'log_mcap < 10.8', True, True, ''),
    ('S36', 'F9_size', 'financials vs companies', 'fin == 1', 'fin == 0', True, True, 'no directional prior (two-sided)'),
    # F10 timing / regime
    ('S37', 'F10_timing', 'early reporter (<=30 days) vs late (>=45)', 'days_after_quarter_end <= 30', 'days_after_quarter_end >= 45', True, False, 'no placebo meaning'),
    ('S38', 'F10_timing', 'peers already reported 3-day > 0 vs < 0', 'peers_reported_3d > 0', 'peers_reported_3d < 0', True, False, 'no placebo meaning'),
    ('S39', 'F10_timing', 'season so far 3-day > 0 vs < 0', 'season_so_far_3d > 0', 'season_so_far_3d < 0', True, False, 'no placebo meaning'),
    ('S40', 'F10_timing', 'India VIX >= 18 vs <= 13', 'india_vix >= 18', 'india_vix <= 13', True, True, ''),
    ('S41', 'F2_market', 'stock lagged Nifty last week too (vs_nifty_1w < -2%) vs outperformed (>= 0)', 'vs_nifty_1w < -0.02', 'vs_nifty_1w >= 0', True, True, ''),
]

LAG_BANDS = [(-0.075, -0.05), (-0.10, -0.075), (-0.125, -0.10), (-0.15, -0.125), (-0.175, -0.15), (-0.20, -0.175), (-9, -0.20)]
DEPTH_ADJ_BANDS = [(-0.10, -0.05), (-0.15, -0.10), (-9, -0.15)]
FIRST14 = 14
COST = 0.17   # percent per round trip
