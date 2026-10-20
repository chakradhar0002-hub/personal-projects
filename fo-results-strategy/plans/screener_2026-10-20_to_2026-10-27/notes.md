# Notes: F&O results screener

Meetings Tue 20-Oct-2026 to Tue 27-Oct-2026; run date Tue 20-Oct-2026 (Tue 20-Oct-2026 is not a trading session (Dussehra)).

## Data and as-of times

- Prices: the project's data pack (`LAB_ROOT/sector_lab/data`: returns.csv, index_close.csv, sessions.csv; `LAB_ROOT/ta/build/adjusted_ohlcv.csv.gz` for adjusted closes and volumes) to Wed 30-Sep-2026, then NSE cash bhavcopies (series EQ close and total traded quantity) and NSE index closes (Nifty 50) for Thu 01-Oct, Mon 05-Oct, Tue 06-Oct, Wed 07-Oct, Thu 08-Oct, Fri 09-Oct, Mon 12-Oct, Tue 13-Oct, Wed 14-Oct, Thu 15-Oct, Fri 16-Oct, Mon 19-Oct. **Latest close: Mon 19-Oct-2026.**
- Results meetings: NSE event calendar (downloaded 2026-10-20 17:07:23 IST) and NSE board-meeting list for the window (downloaded 2026-10-20 17:07:24 IST); only meetings whose purpose includes financial results. Dates can change: check the company's filing.
- F&O list: today's NSE fo_mktlots.csv (downloaded 2026-10-20 17:07:25 IST), 213 stocks.
- Trading holidays: NSE holiday master (capital market). Corporate actions since the project data: NSE corporate actions list (splits / bonuses adjust earlier closes and volumes; demergers leave that day's return blank; moves beyond +-35% are flagged).
- Past results: `LAB_ROOT/sector_lab/data/events.csv` (4,462 results, Jan-Mar 2021 to Apr-Jun 2026 results, NSE results times and XBRL filings). Sector: NSE index sector from results/nifty_sector_3day/results_3day.csv, else the Nifty 500 list.
- Growth units: percent (events.csv stores fractions). PAT = profit attributable to owners (consolidated where filed; banks standalone); Sales = revenue from operations (banks: interest earned). YoY / QoQ growth is blank when the base quarter was zero or a loss, so those results count as neither good nor bad numbers.
- Downloads are kept in SCREENER_DL and parsed as data only.

## Conventions

- **result session**: the results (board-meeting) date if it is a trading session, else the next session.
- **window**: cutoff = 2 sessions before the result session; Day-1, Result day, Day+1 = the sessions before, of and after the result session.
- **three day**: Day-1 + Result day + Day+1 daily close-to-close returns (= cutoff close to Day+1 close), percent.
- **reaction day**: Day+1 for results after the close on a trading day, else the Result day.
- **winner**: reaction-day return minus Nifty 50's return that day > +4%.
- **lag**: 21-session return minus Nifty 50's 21-session return, at the close.
- **volume ratio**: mean volume of the last 5 sessions / mean of the last 60 (split / bonus adjusted).
- **rsi14**: Wilder RSI(14) on adjusted closes.
- **growth**: Sales / PAT growth in percent; PAT = profit attributable to owners (consolidated where filed; banks standalone); Sales = revenue from operations (banks: interest earned); blank when the base quarter was zero or a loss.
- **Upcoming windows** assume the results come out on the meeting date. The window does not depend on the timing; the reaction day does (Day+1 if the company usually reports after the close, else the Result day).
- **Entry status**: missed = the cutoff close is before the run date; today = the cutoff is the run date; otherwise the cutoff date. Signals are measured at the cutoff close when it is in the data (final), else at the latest close (provisional, must be re-checked at the cutoff close).
- **Last-4 rank**: average of each current F&O stock's last 4 three-day sums in events.csv, ranked among all 212 current F&O stocks with 4+ results (top tenth = rank percentile above 90%). Results reported in October 2026 by early reporters are not in events.csv and are not counted.
- **Auto**: hand-made 'Auto & auto parts' sector or NSE 'Automobile and Auto Components'.
- **Run-up straddle**: the last close before the numbers is the Result day for usual after-close reporters on a trading day, else Day-1; entry 5 sessions earlier; front expiry = last Tuesday of the month at least 3 sessions after the reaction day (as in fo_results_strategy/timeline.py); check the listed expiries and price it live.

## How to read it

1. The history (average, median, share up, best / worst, good vs bad numbers) shows how the stock has moved around its results. It is description, not a forecast: the project found no link between a stock's earlier three-day moves and the direction of its next one. The average size tells you how much it tends to move.
2. The only pre-results trade is the lag 10% + volume rule. Check it at the cutoff close; a provisional 'fires' on an earlier close can disappear, and a 'no' can turn into a 'fires'.
3. After the numbers, watch the reaction day: a close more than 4% above Nifty's move makes a results winner (buy at the next open, hold 20 sessions against Nifty); RSI(14) above 50 at the cutoff is the stronger version.
4. Watch items (last-4 top tenth, auto) are for paper-trading only.

## What the research says

| Signal | Label | Tested result | Source |
|---|---|---|---|
| Lag 10% + volume (before results) | TRADE (paper-trade) | 21-session return minus Nifty's below -10% and 5/60 volume >= 1.0x at the cutoff close; buy at the cutoff close, sell at the Day+1 close: 85 trades, +2.13% (+1.96% after costs), 18 of 19 quarters with trades positive; 1.3x version 44 trades, +2.77%. Cut-offs chosen after looking; without the best 5 trades +1.36%. Realistic +1% to +1.5% a trade after costs. | docs/SUMMARY.md, docs/LAG10_VOLUME.md |
| Same lag on quiet volume (below 1.0x) | NOT a trade | 109 trades, -0.37% over the three days. | docs/LAG10_VOLUME.md |
| Results winners (after results) | TRADE (paper-trade) | Reaction-day return beats Nifty by more than 4%: buy at the next open, hold 20 sessions against Nifty. All winners +1.45% a trade over Nifty (392 trades, 15 of 22 quarters); with RSI(14) > 50 at the cutoff +2.42% (232 trades, 17 of 22), +2.04% at the next open with 0.40% cost. Realistic about +1% over Nifty. Winners with RSI 50 or below: +0.04%, skip. | docs/SUMMARY.md, docs/WINNERS_RSI50.md |
| Hold results winners 60 sessions instead of 20 | WATCH | +5.10% vs +1.85% on unseen quarters, but the same per day; not significant. About +2% per 60-session trade. | docs/HIGHER_AVERAGE.md |
| Pre-results IV run-up straddle | MARGINAL | Buy the ATM straddle 5 sessions before the last close before the numbers, sell at that close, only if the front expiry is within 14 sessions: +0.065R in 2023-25; +2.2% a trade out of sample (556 trades), two of five seasons slightly negative. Needs fills near mid. | docs/SUMMARY.md, docs/REAL_DATA_RESULTS.md |
| Last-4 three-day average in the top tenth | WATCH | Stocks that habitually rise into their results: 292 trades, +1.07% before costs (+0.90% after), found after the fact; five stocks give 60% of it. Realistic about +0.45% after costs. | docs/PAST_PERFORMANCE.md, docs/QUARTER_CORRELATION.md |
| Auto and auto-parts stocks (cutoff close to Day+1 close) | WATCH | +1.20% a result (264 results), above the quarter's average in 18 of 22 quarters; with NSE's auto sector +1.10%, resting on three stocks and on 2021-23 (adjusted p 0.06-0.23). Realistic well under +1%. | docs/SECTOR_3DAY.md, docs/NIFTY_SECTOR_3DAY.md |
| A stock's earlier three-day moves -> direction of its next one | NOT PREDICTIVE | Rank correlation with last quarter's move +0.005 (3,177 results); up after an up quarter 49%, after a down quarter 48%; no lag of 1-8 quarters and none of 84 pattern tests confirmed. | results/prev_quarter_patterns/, docs/QUARTER_CORRELATION.md |
| Size of a stock's earlier three-day moves -> size of its next one | DESCRIPTIVE (options only) | Persists a little (rank correlation about +0.05 with last quarter's absolute move), mostly because volatile stocks move more (60-day volatility alone +0.12). Says nothing about direction; no cash trade. | results/prev_quarter_patterns/table_magnitude.md |
| Last result a winner / a loser | NOT PREDICTIVE | Next three-day window -0.04% after a winner, +0.06% after a loser. | docs/PAST_PERFORMANCE.md |
| Good or bad reported numbers | NOT PREDICTIVE (known only after the numbers) | No fundamental screen before results works (44 screens within about +-0.3%); after results, strong numbers bought +0.52% over 20 sessions vs +0.43% for all results, and shorting bad numbers lost money. The per-stock 'after good / bad numbers' columns here are descriptive. | docs/FUNDAMENTAL_ANALYSIS.md |
| Technical analysis, EMA / SMA at the cutoff | NOT PREDICTIVE | 44 textbook signals and 59 EMA / SMA signals: none passes; the small negative EMA / SMA link is market timing and vanishes among results on the same day. | docs/TECHNICAL_ANALYSIS.md, docs/EMA_SMA_3DAY.md |
| Last season's best / worst sector | NOT PREDICTIVE | No memory between seasons; buying last quarter's best sector made -0.24% a result. | docs/QUARTER_CORRELATION.md |
| The average F&O stock in the three-day window | BASELINE | +0.04% a result (-0.05% vs Nifty), a loss after 0.17% round-trip costs; no short works. | docs/SUMMARY.md, docs/NEGATIVE_AVERAGE.md |

Key point: **a stock's past three-day results moves do not predict the direction of its next one.** The per-stock averages, best / worst quarters and good / bad numbers splits are a record, not a signal; with about 20 results per stock, a +1% or -1% average is well within chance.

## Data checks

- first appended day 2026-10-01: NSE previous close differs from the project's last close for 0 symbols
- window convention: recomputed cutoff / Day-1 / Result day / Day+1 / reaction day from results date and timing for all 4462 past results; mismatches with events.csv: 0
- three-day sum: recomputed from returns.csv for 4460 results; max abs difference vs events.csv 6.5e-07
- 21-session lag vs Nifty at the 212 cutoffs of the latest project quarter (qn 21, cutoffs 2026-07-07 to 2026-08-12): max abs difference vs events_ta.csv 4.8e-05 on 212 values, 0 present in only one
- 5/60 volume ratio at the 212 cutoffs of the latest project quarter (qn 21, cutoffs 2026-07-07 to 2026-08-12): max abs difference vs events_ta.csv 4.9e-06 on 212 values, 0 present in only one
- RSI(14) at the 212 cutoffs of the latest project quarter (qn 21, cutoffs 2026-07-07 to 2026-08-12): max abs difference vs events_ta.csv 5.0e-05 on 212 values, 0 present in only one
- source check on 2026-09-30: bhavcopy close equals the project's raw close for 213 of 213 symbols, volume equals (to 1e-7, the project file keeps 8 digits) for 213; Nifty 50 22620.45 vs project 22620.45
- appended 12 bhavcopy sessions 2026-10-01 to 2026-10-19 (series EQ close and total traded quantity); Nifty 50 from ind_close_all
- history.csv: 1022 rows; three-day % equal to events.csv three_day x 100 (2-decimal rounding) on 1022 of 1022; rows per stock equal to its events.csv results: True
- Validation detail for the latest project quarter: validation_qn_last.csv.
