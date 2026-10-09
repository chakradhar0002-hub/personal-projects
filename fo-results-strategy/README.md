# F&O Results Strategy

Rules for trading NSE F&O stocks around quarterly results, organised by day:
**Day-1**, **Result Day** and **Day+1**. A small Python tool turns the rules into a dated
checklist and concrete trades, and backtests them on your data.

**Short version of all the findings: [docs/SUMMARY.md](docs/SUMMARY.md).** The playbook: [docs/STRATEGY.md](docs/STRATEGY.md).

> **Tested on real data (2023–2025, 72 F&O stocks, real NSE option prices):**
> - **One trade made money: the pre-results IV run-up straddle.** Buy the ATM straddle 5 sessions before the
>   last close before the numbers, sell at that close: +0.065R a trade after costs, 280 trades, all 9 seasons positive; out of sample
>   (Jun 2025 – Aug 2026, all F&O stocks) +2.2% a trade, so treat it as marginal.
> - **A second edge, in stock futures: results winners keep winning.** Buy a stock that beat Nifty by more than 4% on
>   its reaction day and hold 20 sessions: +2.3% a trade over Nifty after costs (300 trades, 13 of 15 quarters positive,
>   +1.9% in the last 6 quarters). Losers don't keep falling, and the direction can't be predicted before the numbers.
>   See [docs/PATTERNS.md](docs/PATTERNS.md). Over 22 quarters it is weaker: +1.45% a trade, and it lost in 2021-22.
> - **No pre-results screen averaged 2% in the 3-day window every quarter** over 22 quarters (2021-26) on quarters it
>   was not fitted to; the average stock never reached 2% in any quarter. See [docs/TARGET_2PCT.md](docs/TARGET_2PCT.md).
> - **Sector ideas add nothing:** 619 variants (sector leaders, sector drift and rotation, busy sector weeks, peer pairs,
>   sector-aware winner trade) gave no new edge. Stocks in F&O at the time averaged only +0.04% in the 3-day window.
>   See [docs/SECTOR_STRATEGIES.md](docs/SECTOR_STRATEGIES.md).
> - **No rule averages more than 5% in the 3-day window** on quarters it was not chosen on. Rules showing +6% over all 22
>   quarters exist, but random data gives equally good ones; the best honest picks make about +1.5-2% a trade.
>   See [docs/TARGET_5PCT.md](docs/TARGET_5PCT.md).
> - **No rule is 100% positive**, per trade or per quarter, on quarters it was not chosen on: rules perfect in 2021-24
>   were right about half the time afterwards. See [docs/TARGET_100PCT.md](docs/TARGET_100PCT.md).
>   The closest rule (stock lagged Nifty by > 15% over the month, take-profit exit): 51 trades, 72.5% up, +2.2%, 15 of 16
>   quarters with trades positive, no trade in 6 quarters. See [docs/LAGGED_NIFTY_1M.md](docs/LAGGED_NIFTY_1M.md).
>   Inside the wider "lagged by more than 5%" group (+0.05% on average) only the deeply beaten-down names bounce; no
>   short works. See [docs/LAG5_PATTERNS.md](docs/LAG5_PATTERNS.md).
>   Lagged by more than 10% on above-average volume: 85 trades, +2.1%, 18 of 19 quarters with trades positive (cut
>   points chosen after looking). See [docs/LAG10_VOLUME.md](docs/LAG10_VOLUME.md).
> - **Technical analysis adds nothing:** 44 textbook signals (RSI, Stochastic, Bollinger, CCI, MFI, MACD, moving averages,
>   candles, OBV) neither work alone nor improve the lag + volume rule. See [docs/TECHNICAL_ANALYSIS.md](docs/TECHNICAL_ANALYSIS.md).
> - **Fundamental analysis adds nothing either:** value, quality, growth, GARP, Piotroski and margin screens do not work before
>   results, do not improve the lag + volume rule, and reported numbers give no post-results drift. See [docs/FUNDAMENTAL_ANALYSIS.md](docs/FUNDAMENTAL_ANALYSIS.md).
> - **TA and FA together add nothing:** 40 combined screens, 12 filters on the lag + volume rule, a walk-forward model on
>   both (AUC 0.52) and 117 post-results tests; nothing survives. See [docs/TA_FA_COMBINED.md](docs/TA_FA_COMBINED.md).
>   Watch item: results winners with RSI above 50 before results made +2.42% a trade over Nifty (232 trades, 17 of 22
>   quarters positive), realistic about +1%. See [docs/WINNERS_RSI50.md](docs/WINNERS_RSI50.md).
>   Raising its average: of 136 versions, only holding 60 sessions instead of 20 kept a higher average on unseen
>   quarters, and it earns the same per day. See [docs/HIGHER_AVERAGE.md](docs/HIGHER_AVERAGE.md).
> - **Past performance adds nothing to either trade:** results track record and 1-12 month price performance (71 tests).
>   Watch item: habitual post-results drifters, about +0.5% a trade. See [docs/PAST_PERFORMANCE.md](docs/PAST_PERFORMANCE.md).
> - **The original trades lost money after costs:** the condor/straddle across the numbers and the Day+1 follow-through.
>
> See [docs/REAL_DATA_RESULTS.md](docs/REAL_DATA_RESULTS.md). It's a small edge that depends on fills near mid, so paper-trade it first.

**22-quarter results report (Jan-Mar 2021 to Apr-Jun 2026 results; all NSE data, every F&O stock, no filters):**
[reports/results_report_last_22_quarters.xlsx](reports/results_report_last_22_quarters.xlsx), or open
[reports/results_report_last_22_quarters.html](reports/results_report_last_22_quarters.html) in any browser (same data,
with filters, sorting and CSV download). It shows results timing, 3-day moves, financials, cash flow, ratios, peers and
options, plus a cross-check against BSE prices and Yahoo Finance financials
([reports/results_cross_check.csv](reports/results_cross_check.csv)). Builder: [report_builder/](report_builder/).

| When | What you do |
|---|---|
| 5 sessions before the last close before the numbers | **Buy the ATM straddle** (front expiry within 14 sessions of that close; debit ≤ 2% of capital, ≤ 10 open) |
| Day-1, or Result Day for after-close results | **Sell it at the close**: never hold through the numbers. Check eligibility (ban, liquidity) |
| Result Day / Day+1 | Nothing recommended: trades across the numbers and the follow-through tested negative; the opening-range trade is untested |

No directional position is ever carried across the announcement.

## Quick start

Python 3.10+ (tested on 3.11). There are no third-party dependencies.

```bash
cd fo-results-strategy
pip install -e .            # optional: gives the `fo-results` command
# or run it in place:  python -m fo_results_strategy <command> ...

# 0. What to do in the next 3 sessions across the F&O universe (needs internet):
#    run-up straddles to buy / sell, with strikes, expiry and size from the latest NSE prices
fo-results upcoming --days 3 --capital 2500000 --holidays my_nse_holidays.txt

# 1. Plan one stock's results (all percentages in %)
fo-results plan --symbol XYZ --date 2026-10-15 --timing AMC --spot 1500 --lot-size 550 \
  --strike-step 10 --hist-moves 3.1,-2.4,4.2,-1.8,2.7,-3.5,2.2,-3.3 \
  --front-iv 34 --back-iv 26 --run-up 2 --capital 2500000

# 2. After the reaction session closes: follow-through plan
fo-results classify --symbol XYZ --prev-close 1500 --open 1560 --high 1600 --low 1550 \
  --close 1592 --volume 5000000 --avg-volume 1500000 --hm 2.9 --lot-size 550

# 3. Reaction-session opening-range trade on 5-minute bars
fo-results orb --bars examples/reaction_5min_example.csv --prev-close 1000 --hm 3

# 4. Real data: Yahoo prices + results dates/times, NSE option bhavcopy (needs internet)
fo-results fetch --out-dir real_data            # or --symbols TCS,INFY,...  (~15 min first run)
# Yahoo's results calendar ends in May 2025; add later seasons from your own list:
#   fo-results fetch --results-file my_results.csv   (symbol,announce_date,announce_time|timing)
fo-results backtest --prices real_data/prices.csv --events real_data/events.csv \
  --quotes real_data/quotes.csv --out trades.csv

# Pipeline check on synthetic data (says nothing about real-market edge)
fo-results demo
```

`plan` options worth knowing:
- `--straddle` takes the ATM straddle premium instead of `--front-iv`.
- `--base-iv` replaces `--back-iv` when there is no usable next month.
- `--mwpl` / `--atm-spread` apply the ban and liquidity filters.
- `--holidays` takes a file of exchange holidays, one date per line.

Front and back expiries are picked automatically: the last Tuesday of the month, rolling
to the next month when the reaction session falls in expiry week. Check the current NSE
expiry rule and change `expiry_weekday` in `config.py` if needed.

## Data formats

- `prices.csv`: `date,symbol,open,high,low,close,volume` (daily).
- `events.csv`: `symbol,announce_date,timing` plus optional `front_iv,front_days,back_iv,back_days,post_iv,lot_size,strike_step,front_expiry,base_iv`.
  - `timing` is `BMO`, `DURING`, `AMC` or `UNKNOWN`. IVs are in %.
  - The `*_days` columns count sessions from the pre-results close to each expiry.
  - `post_iv` is the front IV after the results (at the reaction-session close when built by `fetch`).
  - `base_iv` is the normal (ex-results) vol; it overrides the back-month estimate.
  - Rows without IVs only test the follow-through trade.
- `quotes.csv` (optional): `symbol,date,expiry,kind,strike,close,settle,volume` closing option prices.
  With it, event trades are replayed at real prices instead of a Black-Scholes model.

## Layout

```
fo_results_strategy/
  config.py     every threshold (StrategyConfig)
  timeline.py   Day-1 / Result Day / Day+1, reaction session, expiry selection
  metrics.py    historical move, term-structure implied move, candle reading
  pricing.py    Black-Scholes, implied vol, structure max loss
  strategy.py   event trade (condor / straddle / flat), reaction classification, follow-through
  playbook.py   dated checklist
  intraday.py   reaction-session opening-range rules
  backtest.py   event-study backtest (no look-ahead), real-quote replay, calibration table
  realdata.py   `fetch`: Yahoo prices and results dates, NSE F&O bhavcopy -> IVs and quotes
  upcoming.py   `upcoming`: next results dates -> dated buy/sell actions for the next N sessions
  synthetic.py  fake data for the demo and tests
  cli.py        command line
docs/STRATEGY.md           the playbook
docs/REAL_DATA_RESULTS.md  real-data backtest: data, results, what was tried
results/                   results calendar used (2023-2025) and the trade list of that run
plans/                     saved `upcoming` plans
tests/            python -m unittest discover -s tests -t .
```

Educational material, not investment advice.
