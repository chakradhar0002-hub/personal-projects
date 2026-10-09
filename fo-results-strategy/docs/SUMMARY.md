# Summary: trading NSE F&O stocks around quarterly results

What was studied: 22 results seasons (Jan-Mar 2021 to Apr-Jun 2026 results), 4,462 results of 212 F&O stocks, all
from NSE data (results dates and times, prices, filings, option prices). The main trade is the **3-day window**: buy
at the close 2 sessions before the result session (the cutoff), sell at the Day+1 close. A take-profit version exits
at the Day-1 close if Day-1 is up more than 3%, else at the Result-day close if the two days add to more than 3%, else
at the Day+1 close. Costs are 0.17% a round trip.

## Bottom line

1. **No rule chosen before the numbers reaches your targets honestly**: not +2% in every quarter, not a +5% average,
   not 100% winning trades or quarters. Rules that look like that exist in hindsight, but random data produces them
   just as easily, and they did about half as well or worse on quarters they were not chosen on.
2. **One pattern holds up: deeply beaten-down stocks with rising volume bounce through results.** The working rule is
   "lagged Nifty by more than 10% over the month, with volume at or above normal" (below). Expect roughly **+1% to
   +1.5% a trade after costs**, a few trades a quarter, not +2-3%.
3. Two separate trades also showed an edge: buying results winners for 20 sessions, and the pre-results option IV
   run-up straddle. Both are smaller than first measured.
4. The average F&O stock earns nothing in the 3-day window (+0.04% for stocks that were in F&O at the time, a loss
   after costs), and nothing found predicts which stocks will fall.

## The rule to paper-trade: lag 10% + volume

At the cutoff close (2 sessions before the result session), for each stock that is in F&O:

1. **Lag**: the stock's 21-session return minus Nifty 50's 21-session return is below **-10%**.
2. **Volume**: the average daily volume of the last 5 sessions is at least **1.0x** (or, stricter, **1.3x**) the
   average of the last 60 sessions (adjust volume for any bonus or split in that window).
3. Buy at the cutoff close; sell at the Day+1 close (or use the take-profit exit).

| Version | Trades | Up | 3-day avg | After costs | Take-profit avg | Quarters with trades | Positive | Without best 5 trades |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Volume 1.0x or more | 85 | 64% | +2.13% | +1.96% | +2.14% | 19 of 22 | 18 | +1.36% |
| Volume 1.3x or more | 44 | 77% | +2.77% | +2.60% | +3.00% | 18 of 22 | 16 | +1.53% |
| Same lag, quiet volume (below 1.0x) | 109 | 47% | -0.37% | -0.54% | -0.18% | 21 of 22 | 11 | -0.98% |

Why it is believable:

- Volume splits the deep laggards cleanly: on rising volume they bounced, on quiet volume they kept drifting down.
- It beats random picks from all stocks that lagged Nifty by 10%+ (for the 1.2x and 1.3x versions, chance of doing as
  well by luck about 4-6 in 1,000).
- The same setup on ordinary days without results makes only about +0.7% to +0.8% over 3 days, so about +1.5% a trade
  is linked to the results.
- Nearby cut-offs (lag 8-12%, volume 0.8-1.5x) give similar numbers; there is no cliff.
- A shallower lag does not work: below about 10% behind Nifty the trades earn roughly nothing (lag 2-7% with volume
  1.0x+: +0.4% to +1.1% a trade, and only because the 10%+ trades are still inside; stocks 4-8% behind lost money).
- In the last 8 quarters, all 7 that had a trade were positive (Jan-Mar 2026 had none): 1.0x +2.86% a trade, 1.3x
  +3.00%.

Why to stay cautious:

- The 10% and 1.0x cut-offs were chosen after looking at the data, and 100+ lag/volume combinations were checked in
  all, so the headline averages are optimistic.
- The stock list is today's F&O list: stocks that crashed and were later dropped from F&O are missing, which flatters
  any buy-the-dip rule.
- A handful of crash rebounds (Adani fall Feb 2023, January sell-offs) give much of the profit; without the best 10
  trades the 1.2x version makes about +0.7%.
- Single trades ranged from about -11% (ETERNAL) to +19% (ADANIPORTS). Some quarters have no trade.

### Tighter versions: same stocks, fewer trades

Each stricter version is a subset of the looser one with the same lag or the same volume cut (a stock that lagged 15%
also lagged 10%; volume above 1.5x is also above 1.3x). Tightening mostly keeps the same big winners (ADANIPORTS,
KALYANKJIL) and drops other, mostly good, trades, so the headline average rises while the trade count and the number
of trading quarters fall. Without their best 5 trades they land between about +0.3% and +1.5%: the lag-10% versions
+1.2% to +1.5%, the deeper lag-15% versions only +0.35% to +0.7%.

| Rule | Trades | Quarters with trades | Positive | 3-day avg | Without best 5 |
|---|---:|---:|---:|---:|---:|
| Lag 10%, volume 1.0x+ | 85 | 19 | 18 | +2.13% | +1.36% |
| Lag 10%, volume 1.2x+ | 54 | 18 | 16 | +2.51% | +1.40% |
| Lag 10%, volume 1.3x+ | 44 | 18 | 16 | +2.77% | +1.53% |
| Lag 10%, volume 1.4x+ | 38 | 14 | 12 | +2.67% | +1.19% |
| Lag 10%, volume 1.5x+ | 32 | 12 | 10 | +3.05% | +1.31% |
| Lag 10%, volume 2x+ | 16 | 8 | 7 | +4.38% | +1.43% |
| Lag 15%, volume 1.0x+ | 32 | 11 | 10 | +2.71% | +0.68% |
| Lag 15%, volume 1.5x+ | 16 | 8 | 6 | +3.77% | +0.52% |
| Lag 15%, volume 2x+ | 9 | 6 | 6 | +5.99% | +0.35% |
| Lag 20%, volume 1.5x+ | 9 | 4 | 4 | +6.26% | +1.46% |
| Lag 20%, volume 2x+ | 6 | 3 | 3 | +7.01% | too few |

Use a deeper lag or higher volume as extra conviction on a trade, not as a separate rule. Volume between 1.0x and 2.0x
earns about the same (+1.4% to +2.0% a band); only the 2x+ band stands out, because that is where the crash rebounds
sit.

## Other trades with an edge

| Trade | Result | Caveat |
|---|---|---|
| **Results-winner drift**: a stock beats Nifty by more than 4% on its reaction day; buy at that close, hold 20 sessions, short Nifty against it | +1.45% a trade over Nifty after costs, 392 trades, 15 of 22 quarters positive | Lost in 2021-22 (-1.2% a trade); +1.2% in the last 8 quarters but only +0.4% unhedged. Expect about +1% |
| **Winners with RSI above 50**: the same trade, only for winners whose RSI(14) was above 50 two sessions before the results | +2.42% a trade over Nifty after costs, 232 trades, traded in all 22 quarters, 17 positive (winners with RSI 50 or below: +0.04%) | Picked from 117 tests; lost in 2021-22; 2023 gives 46% of the profit. Expect about +1%, entering at the next open ([WINNERS_RSI50.md](WINNERS_RSI50.md)) |
| **Pre-results IV run-up straddle**: buy the ATM straddle 5 sessions before the last close before the numbers, sell at that close | +0.065R a trade after costs, 280 trades, all 9 seasons positive (2023-25) | Out of sample +2.2% a trade; depends on fills near mid. Marginal |

## What did not work

| Idea | Result |
|---|---|
| A pre-results rule averaging +2% in every quarter | None on unseen quarters; the average stock never reached +2% in any quarter |
| Open searches (about 350,000 rules, later about 30 million a run) and machine-learning models | Strong in the quarters used to find them, about -2% to +2% afterwards |
| Your Condition A / B | A: +3.1% on 32 picks, but only since 2023 and on 14 stocks; A or B: +1.7% |
| Early reporters with a strong week | +3.4% on 42 trades; realistic about +1% above the market |
| Valuation (P/B for financials, P/E for consumer, IT, pharma; cheapest or middle of the peer group) | No edge |
| Sector performance before results | The "hot sectors do worse" result was a flaw in the test; no edge |
| Six fresh sector strategies (619 variants: sector leaders, rotation, busy weeks, peer pairs) | No new edge |
| A +5% average over all quarters | Rules showing +6% exist only in hindsight, and random data finds equally good ones |
| 100% winning trades or quarters | Perfect records appear in hindsight and in random data; afterwards about half were right |
| Technical analysis (RSI, Stochastic, Bollinger, CCI, MFI, MACD, moving averages, ADX, candles, OBV; 44 signals) | No signal holds up; none improves or replaces the lag rule ([TECHNICAL_ANALYSIS.md](TECHNICAL_ANALYSIS.md)) |
| Fundamental analysis (value, quality, growth, GARP, Piotroski, margins, turnarounds; before or after results) | No screen works; none improves or replaces the lag rule; reported numbers give no drift ([FUNDAMENTAL_ANALYSIS.md](FUNDAMENTAL_ANALYSIS.md)) |
| Technical and fundamental analysis together (40 combined screens, 12 filters on the lag rule, a model on both, 117 post-results tests) | Nothing survives; the model ranks results like a coin flip; none improves the lag rule or the winner drift ([TA_FA_COMBINED.md](TA_FA_COMBINED.md)) |
| A higher average for the winners trade (136 versions: stricter entry, exits, market backdrop, ranking models, options) | Only holding 60 sessions instead of 20 kept a higher average on unseen quarters (+5.10% vs +1.85% a trade), but it earns the same per day; options lost money ([HIGHER_AVERAGE.md](HIGHER_AVERAGE.md)) |
| Shorting (mild laggards, results losers, model "fall" picks) | Nothing worked |
| Selling the straddle across the numbers | Lost about 3.3% of the premium a trade after costs |

Two corrections along the way: the often-quoted "+0.28% for all stocks" in the 3-day window was inflated by results
from before stocks joined F&O (stocks in F&O at the time: +0.04%); and the results-winner drift is weaker over 22
quarters (+1.45%) than over the first 15 tested (+2.3%).

## Next steps

1. Paper-trade "lag 10% + volume 1.0x (or 1.3x)" for the next 2-4 results seasons with the rules fixed in advance,
   recording entry at the cutoff close and exit at the Day+1 close, against Nifty.
2. Size small: a single trade can lose 8-11%, and some seasons give no trade.
3. Re-check after each season whether the live trades match the backtest (+1% to +1.5% a trade after costs).

## Details

- [LAG10_VOLUME.md](LAG10_VOLUME.md): the lag + volume rule, every version, quarter-by-quarter tables, independent checks
- [LAG5_PATTERNS.md](LAG5_PATTERNS.md), [LAGGED_NIFTY_1M.md](LAGGED_NIFTY_1M.md): how the lag pattern was found
- [TARGET_2PCT.md](TARGET_2PCT.md), [TARGET_5PCT.md](TARGET_5PCT.md), [TARGET_100PCT.md](TARGET_100PCT.md): the target searches
- [WINNERS_RSI50.md](WINNERS_RSI50.md): results winners with RSI above 50, quarter by quarter, with independent checks
- [HIGHER_AVERAGE.md](HIGHER_AVERAGE.md): attempts to raise that trade's average, tested on unseen quarters
- [TECHNICAL_ANALYSIS.md](TECHNICAL_ANALYSIS.md), [FUNDAMENTAL_ANALYSIS.md](FUNDAMENTAL_ANALYSIS.md), [TA_FA_COMBINED.md](TA_FA_COMBINED.md): TA, FA and both together
- [SECTOR_STRATEGIES.md](SECTOR_STRATEGIES.md), [PATTERNS.md](PATTERNS.md), [REAL_DATA_RESULTS.md](REAL_DATA_RESULTS.md): sector ideas, winner drift, option trades
- [reports/results_report_last_22_quarters.html](../reports/results_report_last_22_quarters.html): the full results report
