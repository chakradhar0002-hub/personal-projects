# Summary: trading NSE F&O stocks around quarterly results

**What was studied.** 22 results seasons, from Jan-Mar 2021 to Apr-Jun 2026 results. The data covers 4,462 results of
212 stocks, of which 3,280 came while the stock was in F&O. The 22-season studies use only NSE data: results dates and
times, prices, filings, F&O bhavcopies, option prices, delivery data and corporate announcements. (The original straddle
test used Yahoo Finance prices and results dates, with NSE option prices.) Only stocks in F&O at the time are traded.

**The two trading windows.**
- **Before results (3-day window).** Buy at the close 2 sessions before the result session (the cutoff) and sell at the
  Day+1 close. Cost 0.17% a round trip.
- **After results (20 sessions).** Buy at the close of the reaction day (the first session that trades on the numbers),
  hold 20 sessions and short Nifty against it. Cost 0.19%.

**How things were tested.** The two trades below were found by looking at the data: the lag rule's 10% and 1.0x
cut-offs were picked after seeing results, and RSI above 50 was the best of 117 tests, so neither is a clean
out-of-sample result. The later studies wrote each rule down before its result was computed and checked it:
- in both halves of the data (first 14 quarters and last 8);
- against random picks;
- against the same signal on ordinary days without results;
- without its best 5 trades;
- after correcting for the number of tests run.

Most findings were then rebuilt from scratch by a separate agent, and the later searches were tested once on quarters
they had never seen.

## Bottom line

1. **No rule reaches the original targets honestly.** None makes +2% in every quarter, a +5% average, or 100% winning
   trades or quarters. Rules that look like that, or close to it, exist in hindsight (the best +2% rules hit 11-12 of 14
   search quarters), but random data produces them just as easily, and they did about half as well or worse on quarters
   they were not chosen on.
2. **Two trades hold up**, and both are worth paper-trading:
   - **Before results, "lag 10% + volume":** deeply beaten-down stocks on above-average volume bounce through results.
     Realistic **+1% to +1.5% a trade**.
   - **After results, results winners:** stocks that beat Nifty by more than 4% on the reaction day keep drifting up
     for 20 sessions, best when the stock was already strong before the results (RSI above 50). Realistic **about +1% a
     trade over Nifty**.
3. **Nothing else adds to them.** Over 1,000 further tests found no improvement: technical analysis, fundamentals, both
   together, sectors, valuation, past performance, F&O open interest, implied volatility, delivery %, company news,
   machine-learning models and options.
4. **No short works.** The average F&O stock earns nothing in the 3-day window (+0.04%, a loss after costs) and drifts
   up after results. Nothing found picks the stocks that will fall well enough to pay for a short.
5. **Expect less than the backtests.** The cut-offs of both trades were chosen after looking at the data. The stock list
   is today's F&O list, so stocks that fell out of F&O are missing, which flatters buy-the-dip and momentum trades
   alike. A few big moves carry much of the profit: crash rebounds (Feb 2023, Jan 2025, Jan 2026) for the lag rule, and
   2023 alone gives 46% of the winners trade's profit.

## Trade 1: lag 10% + volume (before results)

At the cutoff close, for each stock in F&O:

1. **Lag**: its 21-session return minus Nifty 50's 21-session return is below **-10%**.
2. **Volume**: its average daily volume over the last 5 sessions is at least **1.0x** its 60-session average (stricter:
   **1.3x**). Adjust volume for any bonus or split in that window.
3. Buy at the cutoff close and sell at the Day+1 close. A take-profit version exits early: at the Day-1 close if that
   day is up more than 3%, else at the result-day close if the two days add to more than 3%, else at the Day+1 close.

| Version | Trades | Up | 3-day avg | After costs | Take-profit avg | Quarters with trades | Positive | Without best 5 trades |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Volume 1.0x or more | 85 | 64% | +2.13% | +1.96% | +2.14% | 19 of 22 | 18 | +1.36% |
| Volume 1.3x or more | 44 | 77% | +2.77% | +2.60% | +3.00% | 18 of 22 | 16 | +1.53% |
| Same lag, quiet volume (below 1.0x) | 109 | 47% | -0.37% | -0.54% | -0.18% | 21 of 22 | 11 | -0.98% |

Why it is believable:

- **Volume splits the laggards.** On above-average volume they bounced (+2.13%); on quiet volume they slipped slightly
  (-0.37%), although the deepest laggards (15%+) still rose on quiet volume (+1.06%).
- **It beats luck.** Random picks among all stocks that lagged Nifty by 10%+ do as well about 4-6 times in 1,000 (1.2x
  and 1.3x versions).
- **It is linked to results.** The same setup on ordinary days makes only about +0.7% to +0.8% over 3 days.
- **There is no cliff at the cut-offs.** Lag 8-12% and volume 0.8-1.5x give similar results. A shallower lag earns
  nothing beyond the 10%+ trades inside it.
- **It held up recently.** In the last 8 quarters, all 7 with a trade were positive.
- **Independent rebuilds agree.** They matched every trade once volume was adjusted for splits (the 1.5x check caught
  one split-inflated trade, COFORGE). Separately, using delivery volume instead of total volume picks mostly the same
  trades (75 of its 89) but earns less (+1.87%).

Why to stay cautious:

- **The cut-offs were chosen after looking.** More than 100 lag and volume combinations were checked in all.
- **A few crash rebounds carry much of it**, such as the Adani fall in Feb 2023 and the January 2025 and 2026
  sell-offs: without its best 5 trades the average falls from +2.13% to +1.36%. Single trades ranged from about -11%
  to +19%.
- **Some quarters have no trade.**

Stricter versions are the same stocks with fewer trades. Without their best 5 trades they all land around +0.3% to
+1.5%, so use a deeper lag or higher volume as extra conviction, not as a separate rule. Details:
[LAG10_VOLUME.md](LAG10_VOLUME.md).

No filter from any later study improved this rule. That covers technical analysis, fundamentals, past performance,
F&O positioning, delivery and news.

## Trade 2: results winners (after results)

At the reaction-day close, take stocks whose reaction-day return beat Nifty 50's by more than **4%**. Buy and hold
**20 sessions**, short Nifty for the same value. The stronger version also needs **RSI(14) above 50** at the cutoff
close, 2 sessions before the results.

| Version | Trades | Avg over Nifty after costs | Quarters positive |
|---|---:|---:|---:|
| All results winners | 392 | +1.45% | 15 of 22 |
| **Winners with RSI above 50** | **232** | **+2.42%** | **17 of 22** |
| Winners with RSI 50 or below | 160 | +0.04% | 10 of 22 |
| RSI above 50, entered at the next open, 0.40% all-in cost | 232 | +2.04% | 14 of 22 |

- **It traded in every quarter.** The RSI > 50 version traded in all 22 quarters, with 3 to 23 trades a quarter. It
  made +2.65% in the first 14 quarters and +2.16% in the last 8.
- **It is not every year.** It lost in 2021 and 2022, and 2023 gives 46% of the profit. Without 2023 it makes +1.54%.
- **The RSI filter adds less than it seems.** Its fair same-quarter gain over all winners is +0.63% a trade, and only
  about +0.2% to +0.4% after allowing for having picked it from 117 tests. Skipping winners with RSI 50 or below still
  looks sensible: they earn nothing, and lose money with a realistic entry.
- **Enter at the next open.** You only know a stock beat Nifty by 4% near the close, so the next open is the safe
  entry. Use stock futures, or allow about 0.40% for delivery costs.
- **Survivor bias inflates it.** On stocks already in F&O in 2021, at the next open and 0.40% cost, it made +1.41%.

Details: [WINNERS_RSI50.md](WINNERS_RSI50.md), [PATTERNS.md](PATTERNS.md).

**Holding 60 sessions instead of 20** was the only way to raise the average per trade on unseen quarters: +5.10%
against +1.85% on the same trades. It was not a blind test (its 60-session figures had been published before) and it
is not significant (adjusted p 0.13). It earns the same per day and keeps the money in the market three times as long
(about 12 positions open at once on average, against about 5), and much of the extra is F&O stocks drifting above
Nifty. Realistic: about +2% per 60-session trade ([HIGHER_AVERAGE.md](HIGHER_AVERAGE.md)).

## A third, marginal trade

**Pre-results IV run-up straddle.** Buy the at-the-money straddle of the front expiry 5 sessions before the last close
before the numbers, only when that expiry falls within 14 sessions after that close, and sell at that close. In the
original test (72 stocks) it made +0.065R a trade after costs over 280 trades (R = the straddle's cost, so +6.5% of it),
and all 9 seasons (2023-25) were positive. The expiry filter was chosen after looking; the version planned before
testing made +3.5% over 485 trades. On five new seasons from June 2025 to August 2026, on all 213 F&O stocks, it made
+2.2% a trade (556 trades), about 40% of its earlier size, and two of the five seasons were slightly negative. It
depends on getting fills near the mid price, so treat it as marginal ([REAL_DATA_RESULTS.md](REAL_DATA_RESULTS.md),
[STRATEGY.md](STRATEGY.md)).

## Watch list: paper-trade with no money, definitions fixed now

| Idea | Trade | Backtest | Realistic | Source |
|---|---|---|---|---|
| Hold results winners 60 sessions instead of 20 | After | 215 trades, +4.84% (Jan-Mar 2021 to Jan-Mar 2026 results; +5.10% on the 93 trades of the last 8 quarters) | about +2% per 60-session trade (the backtest earns the same per day as the 20-session hold) | [HIGHER_AVERAGE.md](HIGHER_AVERAGE.md) |
| Winners whose put-call ratio is in the top fifth at the reaction close (cut-off from the previous quarter), bought at the next open | After | 213 trades, +2.34% vs +0.39% for other winners (same-quarter cut-off, bought at the reaction close); +0.85% over all winners with previous-quarter cut-offs, +0.95% at the next open | about +0.3% over plain winners | [MORE_SIGNALS.md](MORE_SIGNALS.md) |
| Habitual post-results drifters: average of the last 4 post-results drifts in the quarter's top fifth, bought after any result | After | 569 trades, +1.80% (18 quarters from Jan-Mar 2022 results; +0.81% in the last 8) | about +0.5% | [PAST_PERFORMANCE.md](PAST_PERFORMANCE.md) |
| Stocks that habitually rise into their results: average of the last 4 results windows in the quarter's top tenth (found after the fact) | Before | 292 trades, +1.07% before costs (+0.90% after) | about half that: +0.45% after costs | [PAST_PERFORMANCE.md](PAST_PERFORMANCE.md) |
| A press release or regular business update in the 30 days before the cutoff | Before | Press releases: 1,023 trades, +0.25% after costs; business-update issuers (found after the fact): 323 results, +0.87% over the average result | about +0.1% | [MORE_SIGNALS.md](MORE_SIGNALS.md) |
| Short results losers already below their 50- and 200-day averages, 20 sessions against Nifty | After (short) | +0.30% on unseen quarters | about 0 | [NEGATIVE_AVERAGE.md](NEGATIVE_AVERAGE.md) |

## What did not work

**Targets**

| Idea | Result |
|---|---|
| A pre-results rule averaging +2% in every quarter | None on unseen quarters; the average stock never reached +2% in any quarter ([TARGET_2PCT.md](TARGET_2PCT.md)) |
| A +5% average over all quarters | Rules showing +6% exist only in hindsight, and random data finds equally good ones ([TARGET_5PCT.md](TARGET_5PCT.md)) |
| 100% winning trades or quarters | Perfect records appear in hindsight and in random data; afterwards about half were right ([TARGET_100PCT.md](TARGET_100PCT.md)) |
| A higher average for the winners trade: 136 versions with stricter entry, exits, market backdrop, ranking models and options | Only the 60-session hold kept a higher average on unseen quarters; stricter filters fell back to the base trade, and options lost 10-27% of premium a trade ([HIGHER_AVERAGE.md](HIGHER_AVERAGE.md)) |

**Signals, before and after results**

| Idea | Result |
|---|---|
| Open searches (about 350,000 rules, later about 30 million a run) and machine-learning models | Strong in the quarters used to find them, about -2% to +2% a trade afterwards (the 2%-target score model -3.8% to +0.7%) ([TARGET_2PCT.md](TARGET_2PCT.md), [TARGET_5PCT.md](TARGET_5PCT.md)) |
| Technical analysis: 44 signals (RSI, Stochastic, Bollinger, CCI, MFI, MACD, moving averages, ADX, candles, OBV) | No signal holds up; none improves or replaces the lag rule ([TECHNICAL_ANALYSIS.md](TECHNICAL_ANALYSIS.md)) |
| Fundamental analysis (value, quality, growth, GARP, Piotroski, margins, turnarounds) | No screen works before results; reported numbers give no drift beyond what any result does ([FUNDAMENTAL_ANALYSIS.md](FUNDAMENTAL_ANALYSIS.md)) |
| Technical and fundamental analysis together (40 screens, 12 lag-rule filters, walk-forward models, 117 post-results tests) | Nothing passes the correction for the number of tests, and the models rank results like a coin flip (AUC 0.52). The one lead, winners with RSI above 50, is Trade 2 above ([TA_FA_COMBINED.md](TA_FA_COMBINED.md)) |
| Past performance: results track record, 1-12 month return vs Nifty and sector, 52-week high (71 tests) | Improves neither trade; two watch items ([PAST_PERFORMANCE.md](PAST_PERFORMANCE.md)) |
| F&O positioning (OI build-up, futures premium, put-call ratio, implied vol), delivery %, company news (98 tests) | Improves neither trade; two small watch items ([MORE_SIGNALS.md](MORE_SIGNALS.md)) |
| Sector performance, six sector strategies (619 variants), valuation within peer groups | No edge ([SECTOR_STRATEGIES.md](SECTOR_STRATEGIES.md); sector performance and peer-group valuation in [TARGET_2PCT.md](TARGET_2PCT.md)) |
| Your Condition A / B; early reporters with a strong week | A: +3.1% on 32 picks (14 stocks), but it trailed the average stock in results up to May 2023 and was designed on the same years; B: +0.96% on 76 picks; early reporters realistic about +1% above the market, zero not ruled out ([TARGET_2PCT.md](TARGET_2PCT.md)) |

**Shorts and option selling**

| Idea | Result |
|---|---|
| Shorting: 131 rules before and after results (fall into results, losers keep falling, fade big jumps, fall models), searched on the first 14 quarters; the 3 finalists were tested once on the last 8 | Nothing works: stocks drifted up, big moves kept going, losers did not keep falling; the best short makes about zero after realistic entry ([NEGATIVE_AVERAGE.md](NEGATIVE_AVERAGE.md)) |
| Selling the straddle across the numbers | Lost about 3.3% of the premium a trade after costs, in 14 of 15 quarters (Oct-Dec 2022 to Apr-Jun 2026 results) ([PATTERNS.md](PATTERNS.md)) |
| Trading the Day+1 follow-through in futures (long or short) | Lost money even before costs (-0.12R long, -0.08R short at zero cost) ([REAL_DATA_RESULTS.md](REAL_DATA_RESULTS.md)) |

## Corrections along the way

- **The average stock earns less than first quoted.** The often-quoted "+0.28% for all stocks" in the 3-day window
  included results from before stocks joined F&O. For stocks in F&O at the time it is +0.04% (-0.05% vs Nifty), a
  loss after costs ([SECTOR_STRATEGIES.md](SECTOR_STRATEGIES.md)).
- **The results-winner drift is weaker over the full sample.** It makes +1.45% over 22 quarters, against +2.3% over the
  15 quarters first tested (Oct-Dec 2022 to Apr-Jun 2026 results). The 7 earlier quarters added later (2021-22
  results) lost 1.2% a trade ([SECTOR_STRATEGIES.md](SECTOR_STRATEGIES.md)).
- **The volume rule needed a split adjustment.** One stock split (COFORGE) had inflated a volume ratio. Volume is now
  adjusted for splits and bonuses. This dropped COFORGE from the 1.5x version (33 to 32 trades) and trimmed two looser
  nearby variants; the main 1.0x rule (85 trades) did not change ([LAG10_VOLUME.md](LAG10_VOLUME.md)).

## Next steps

1. **Paper-trade the two trades** with the rules above fixed in advance, starting with the Jul-Sep 2026 results
   (October-November 2026):
   - lag 10% + volume before results;
   - results winners with RSI above 50, entered at the next open, held 20 sessions against Nifty.
2. **Log the watch list alongside**, with no money on it.
3. **Size small.** A single trade can lose 10% or more, and some seasons give no trade before results.
4. **Re-check after every season** that the live trades match the realistic estimates, which are well below the
   backtests: about +1% to +1.5% a trade after costs for the lag rule, and about +1% over Nifty for the winners trade.
   No stop rule was tested: judge each trade over 4-6 new seasons, against Nifty and against other stocks reporting the
   same week. In the backtest the winners trade lost 3 seasons in a row in 2021-22 before its best years.

## Details

- [LAG10_VOLUME.md](LAG10_VOLUME.md): the lag + volume rule, every version, quarter-by-quarter tables, independent checks
- [LAG5_PATTERNS.md](LAG5_PATTERNS.md), [LAGGED_NIFTY_1M.md](LAGGED_NIFTY_1M.md): how the lag pattern was found
- [WINNERS_RSI50.md](WINNERS_RSI50.md): results winners with RSI above 50, quarter by quarter
- [HIGHER_AVERAGE.md](HIGHER_AVERAGE.md): attempts to raise the winners trade's average
- [PAST_PERFORMANCE.md](PAST_PERFORMANCE.md): results track record and price performance on both trades
- [MORE_SIGNALS.md](MORE_SIGNALS.md): F&O positioning, delivery % and company news on both trades
- [NEGATIVE_AVERAGE.md](NEGATIVE_AVERAGE.md): the search for stocks that fall (shorts)
- [TECHNICAL_ANALYSIS.md](TECHNICAL_ANALYSIS.md), [FUNDAMENTAL_ANALYSIS.md](FUNDAMENTAL_ANALYSIS.md), [TA_FA_COMBINED.md](TA_FA_COMBINED.md): TA, FA and both together
- [TARGET_2PCT.md](TARGET_2PCT.md), [TARGET_5PCT.md](TARGET_5PCT.md), [TARGET_100PCT.md](TARGET_100PCT.md): the target searches
- [SECTOR_STRATEGIES.md](SECTOR_STRATEGIES.md), [PATTERNS.md](PATTERNS.md), [REAL_DATA_RESULTS.md](REAL_DATA_RESULTS.md): sector ideas, winner drift, option trades
- [reports/results_report_last_22_quarters.html](../reports/results_report_last_22_quarters.html): the full 22-quarter results report
