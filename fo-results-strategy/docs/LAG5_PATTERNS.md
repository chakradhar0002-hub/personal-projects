# Inside "lagged Nifty by more than 5% over the month": patterns and strategies

Group: at the cutoff (2 sessions before the result session), the stock's 21-session return is more than 5 points
below Nifty 50's. Stocks in F&O at the time: **679 results, 3-day average +0.05%** (take-profit +0.06%), 49% up,
positive in 10 of 22 quarters. That is the same as every F&O result (+0.04%), so the group as a whole has no edge.
Two searches looked for what separates the stocks that bounce through results from those that keep falling: 49
trading-logic splits with fixed cut points, and a rule search over about 12 million rules a side plus
machine-learning models. The strongest candidates were rebuilt and checked independently.

## Answer

**No new strategy, and no short.** The only thing that separates bouncers from fallers is **how beaten down the stock
already is**: a deeper lag, a long downtrend before it, and heavy selling volume. That is the known "deeply oversold
into results" trade. Everything else (market vs stock-specific fall, sector, uptrend, waiting for a bounce, past
results, profit growth, valuation, size, timing) made no reliable difference. About 70% of the group, the mild 5-10%
laggards, slightly lose through results.

## Depth of the lag

| Lag vs Nifty | Trades | 3-day avg | Same stocks on dates without results |
|---|---:|---:|---:|
| 5-7.5% | 296 | -0.04% | about +0.2% |
| 7.5-10% | 189 | -0.50% | |
| 10-12.5% | 88 | +0.24% | |
| 12.5-15% | 55 | +0.24% | |
| 15-17.5% | 22 | +1.23% | |
| 17.5-20% | 13 | +1.17% | |
| more than 20% | 16 | +4.03% | about +0.8% |

Up to a 15% lag, the results window is no better (often worse) than an ordinary 3 days; beyond 15% results add about
+0.5% to +3%.

## What separates bouncers from fallers

| Inside the group | Trades | 3-day avg | First 14 q / last 8 q | Dates without results | The other side |
|---|---:|---:|---|---:|---|
| Price 17.6%+ below its 200-day average | 88 | +2.38% | +3.16% / +1.79% | +0.55% | rest of group -0.29% (591) |
| Down 20%+ over 6 months | 105 | +2.03% | +2.17% / +1.95% | | 6-month return above -10%: about -0.3% |
| Heavy volume: last 5 days 1.5x+ the 60-day average | 63 | +1.75% | +1.87% / +1.64% | +0.67% | quiet volume (below 1x) -0.16% (455) |
| Lag 10%+ and volume above its 60-day average | 85 | +2.13% | +1.65% / +2.86% | +0.67% | lag 10%+ on quiet volume -0.37% (109) |
| Stock rose on the month but lagged a strong rally | 28 | -1.99% | | +0.88% | |

- Heavy volume only helps when the lag is deep; among 5-10% laggards it adds nothing.
- The "lag 10%+ and above-average volume" rule is the steadiest-looking: positive in 18 of 19 quarters with trades,
  all 7 of the last 8 that had trades, +1.36% without its best 5 trades, about 4 trades a quarter. But its 10% and 1x
  cut points were chosen after seeing the data, and it was not independently checked.
  Quarter-by-quarter detail: [LAG10_VOLUME.md](LAG10_VOLUME.md).
- Waiting for the bounce to start (cutoff day up, 2+ up days) did slightly worse (-0.2% to -0.4%) than buying stocks
  still falling (+0.2% to +0.4%).
- Shorting the mild laggards nets only +0.05% after costs; every short combination failed in the last 8 quarters.
- The take-profit exit changed averages by about 0.04 points.

## The candidates that were checked independently

| Candidate | Trades | Average | Last 8 quarters | Check |
|---|---:|---:|---:|---|
| Lag over 15% and a volatile stock (60-day volatility 35%+), the only combination fixed before seeing the last 8 quarters | 34 | +2.54% | +2.14% (14 trades) | weak: the volatility filter adds nothing (34 random picks of the 51 lag-over-15% trades do as well 1 time in 3); without its best 5 trades +0.43%; realistic about +1% |
| Random-forest "likely to jump 3%+" score, top 10%, retrained each quarter | 29 | +2.67% | +2.53% (24) | weak: 5 big winners (+9% each) carry it, the other picks average +0.9%; best of 12 model versions, and random-direction data matches it 1 time in 4; realistic +0.5% to +1% |

In the rule search, rules chosen on the first 14 quarters showed +3.5% to +7.7% (random data showed the same), made
about +0.95% on the last 8 quarters for longs and -0.6% for shorts, and re-choosing every quarter made -0.07%.

## What to do with it

- Skip mild laggards (5-10% behind Nifty, not in a long downtrend): about -0.3% to -0.4% a trade.
- If you trade this group at all, trade only the deeply beaten-down names: lag over 15%, or lag over 10% on
  above-average volume, or 17-18%+ below the 200-day average. Expect roughly +1% to +1.5% a trade after costs, a few
  trades a quarter, single trades from about -10% to +19%, and half or more of the gain coming from a handful of big
  bounces. Paper-trade 2-4 seasons first.

Files: scripts in `pattern_tests/lag5/` (A_splits with the frozen pre-registration and its hash, B_search, and the two
independent checks), outputs in [results/lag5/](../results/lag5/). The group's trade list is
`results/lagged_nifty/trades_lag5.csv`. Scripts read `LAB_ROOT` (see [TARGET_5PCT.md](TARGET_5PCT.md)) and
`REPO_ROOT` (this repository).
