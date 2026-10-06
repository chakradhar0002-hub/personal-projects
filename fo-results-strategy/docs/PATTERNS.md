# Patterns in 15 quarters of F&O results (Oct-Dec 2022 to Apr-Jun 2026)

Data: the 15-quarter report (3,103 results, 212 F&O stocks, all NSE data), with daily returns from 10 sessions before
to 20 sessions after each reaction day and NSE option prices.

## Bottom line

1. **You cannot tell before the numbers whether a stock will go up or down.** Nine different signals were tested
   (momentum, run-up, past reactions, peers that reported earlier, valuation, season timing). None held in both halves
   of the data. The direction of the reaction is a coin toss.
2. **One pattern holds: results winners keep winning for about a month.** If a stock beats Nifty by more than 4% on
   its reaction day, buying at that close and holding 20 sessions made **+2.3% a trade over Nifty after costs**
   (300 trades, 60% winners, 13 of 15 quarters positive; +1.9% a trade in the last 6 quarters, which were not used
   to find it). Details below.
3. **Losers do not keep falling.** Shorting stocks that fell more than 4% on the numbers lost money against Nifty.
   Only buy the winners.
4. **Do not sell options across the numbers.** Selling the ATM straddle at the last close before results and buying
   it back at the reaction close lost 3.3% of the premium a trade after costs, in 14 of 15 quarters.
5. The pre-results IV run-up straddle ([STRATEGY.md](STRATEGY.md) section 5) is still the only options trade with
   an edge. The winner drift is a second, independent trade, in stock futures.

## How it was tested

- 22 ideas were written down before testing (table below). Each was measured on the first 9 quarters
  (Q3 FY23 - Q3 FY25) and checked on the last 6 (Q4 FY25 - Q1 FY27).
- Returns are measured against Nifty 50, close to close, so a market rally or fall does not count as an edge.
- For "signal -> outcome" ideas: each quarter, the top third of stocks by the signal against the bottom third.
  For "average" ideas: the average per quarter. The t-value is across the 15 quarter results.
- An idea "holds" only if |t| >= 3 (needed when 22 ideas are tried), the two halves agree, and at least 70% of
  quarters go the same way.
- Costs: 0.15% per stock-futures round trip (+0.02% for a Nifty hedge); options 2% slippage per leg per side plus
  Rs 20 an order.

| # | Idea | Effect | t | First 9 q | Last 6 q | Quarters same way | Verdict |
|---|---|---:|---:|---:|---:|---:|---|
| H1 | Stocks drift up in the 5 sessions before results (vs their normal drift) | +0.22% | 1.2 | +0.10% | +0.41% | 80% | no |
| H1b | Same, raw excess vs Nifty | +0.50% | 2.7 | +0.45% | +0.58% | 80% | no (it's their normal drift) |
| H2 | Last session before results | +0.05% | 0.9 | -0.00% | +0.12% | 67% | no |
| H3 | 1-month momentum -> reaction | +0.21% | 1.0 | +0.02% | +0.48% | 60% | no |
| H4 | 3-month momentum -> reaction | -0.09% | -0.5 | +0.06% | -0.31% | 60% | no |
| H5 | Run-up in the last 5 sessions -> reaction | +0.32% | 1.8 | +0.19% | +0.51% | 73% | no |
| H6 | Stock's average past reaction -> reaction | +0.09% | 0.4 | +0.51% | -0.26% | 55% | no |
| H7 | Reaction of peers that reported earlier -> reaction | -0.01% | -0.0 | +0.31% | -0.50% | 67% | no |
| H8 | P/E vs peers -> reaction | +0.40% | 1.7 | +0.39% | +0.42% | 67% | no |
| H9 | Reporting early vs late in the season -> reaction | +0.08% | 0.4 | +0.12% | +0.03% | 60% | no |
| H10 | Option-implied move vs past moves -> size of move | -0.66% | -3.3 | -0.79% | -0.55% | 91% | holds, but no trade in it (H22) |
| H11 | Reaction -> next session | +0.67% | 5.0 | +0.89% | +0.33% | 80% | holds, but too small after costs and shrinking |
| H12 | Reaction -> next 5 sessions | +0.60% | 2.5 | +0.63% | +0.55% | 80% | no |
| **H13** | **Reaction -> next 20 sessions** | **+1.32%** | **3.8** | **+1.25%** | **+1.44%** | **80%** | **holds** |
| H14 | Reaction -> sessions 2-20 (enter a day late) | +0.68% | 2.2 | +0.35% | +1.17% | 80% | no |
| H15 | Profit growth YoY -> next 20 sessions | +0.22% | 0.5 | +0.31% | +0.08% | 53% | no |
| H16 | Sales growth YoY -> next 20 sessions | +0.48% | 1.4 | +0.60% | +0.30% | 53% | no |
| H17 | Reaction + profit growth together -> next 20 sessions | +0.71% | 1.6 | +0.87% | +0.48% | 53% | no |
| H18 | Close position in the reaction-day range -> next 5 sessions | +0.45% | 1.8 | +0.74% | +0.01% | 60% | no |
| H19 | Opening gap on the numbers -> rest of the day (fade or follow) | -0.07% | -0.2 | -0.56% | +0.67% | 47% | no |
| H20 | Stock's past post-results drift -> this drift | +0.32% | 1.9 | +0.23% | +0.40% | 73% | no |
| H21 | Sell the ATM straddle across the numbers (per premium, after costs) | -3.27% | -4.1 | -3.24% | -3.32% | 93% | holds: it loses |
| H22 | Sell the straddle only when options look rich vs history | +2.47% | 1.3 | +3.72% | +1.43% | 64% | no |

"Effect" for a signal is top third minus bottom third; for H1, H1b, H2, H21 it is the average.

Notable "no"s: profit and sales growth (H15, H16) do not predict what the stock does next. The price reaction
already carries the information; the drift follows the reaction, not the numbers.

## The trade: results-winner drift

**Rule**

1. On a stock's reaction day (the result day for results before or during market hours; the next session for results
   after the close), check its move against Nifty 50 near the close.
2. If the stock beat Nifty by **more than 4%** (e.g. stock +5.5%, Nifty +1.0%) and it is an F&O stock, **buy the
   stock future at the close**. Optionally sell Nifty futures of the same value to remove market risk.
3. **Hold 20 sessions**, then exit at the close. No stop was tested.
4. Do not short the stocks that fell.

**Results** (only events where the stock already had F&O options, so stocks are not counted before they joined F&O)

| | Trades | Avg per trade after costs | Median | Winners | First 9 q | Last 6 q | Quarters positive |
|---|---:|---:|---:|---:|---:|---:|---:|
| Beat Nifty by > 3% | 449 | +1.6% | +1.2% | 57% | +2.8% | +1.3% | 12/15 |
| **Beat Nifty by > 4%** | **300** | **+2.3%** | **+1.7%** | **60%** | **+4.1%** | **+1.9%** | **13/15** |
| Beat Nifty by > 5% | 214 | +2.5% | +1.9% | 61% | +4.9% | +1.9% | 13/15 |
| Short: fell > 4% vs Nifty | 286 | -0.3% | -0.1% | 49% | -0.8% | +0.1% | 5/15 |

Against the average F&O stock in the same quarter (removing the mid-cap rally that lifted the whole universe), the
> 4% winners still beat it by 1.6% over 20 sessions (t = 3.1).

By quarter (> 4% rule, average per trade after costs): +2.8%, +5.7%, +10.4%, +12.5%, +1.6%, +3.6%, +0.8%, +0.4%,
-0.7% | +3.3%, +3.8%, -0.8%, +2.0%, +1.1%, +2.1% (last six after the bar).

**What to expect**

- The edge has shrunk: +4.1% a trade in the first 9 quarters, +1.9% in the last 6, and in the last 4 quarters the
  median trade was between -2.0% and +0.8%. A minority of big continuers carries the average.
- Single trades swing a lot: standard deviation 7.4%, worst -20.6%, best +26.5%; 1 in 10 trades lost more than 6%.
- The drift is slow: on average +0.2% after 1 session, +0.5% after 5, +0.8% after 10, +2.4% after 20. Entering one
  session later gave +2.0% instead of +2.3%.
- About 20 trades a quarter, bunched in results season: up to 29 open at once, typically 8.
- Works for after-close and during-market results, banks, NBFCs and companies alike.

**Caveats**

- The universe is today's F&O list. Requiring options at the time removes stocks before they joined F&O, but stocks
  that later left F&O (often after falling) are missing, which may flatter long trades.
- 2023-24 was a strong mid-cap market; the hedged numbers remove the Nifty 50 move but not a mid-cap tilt.
- Long-only was chosen after seeing that the short side does not work, although the 3%, 4% and 5% thresholds all
  agree. Paper-trade a season before using real money.

Trade list: [results/pattern_tests/drift_trades.csv](../results/pattern_tests/drift_trades.csv).

## Re-running

```bash
cd pattern_tests
python3 build_panel.py DATA panel.csv                 # DATA = the report_builder data folder
python3 tests.py panel.csv DATA/report/events.json out # 22 tests -> out_results.csv, out_panel_features.csv
python3 drift.py out_panel_features.csv ../results/pattern_tests
```
