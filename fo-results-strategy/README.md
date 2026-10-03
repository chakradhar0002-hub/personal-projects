# F&O Results Strategy

Rules for trading NSE F&O stocks around quarterly results, organised by day:
**Day-1**, **Result Day** and **Day+1**. A small Python tool turns the rules into a dated
checklist and concrete trades, and backtests them on your data.

**Read the playbook first: [docs/STRATEGY.md](docs/STRATEGY.md).**

> **Tested on real data: no edge after costs.** Over Apr 2024 – May 2025 (71 F&O stocks, every
> option leg at real NSE closing prices), the event trades were about break-even before costs
> and lost money after them. The follow-through trade lost money even before costs.
> See [docs/REAL_DATA_RESULTS.md](docs/REAL_DATA_RESULTS.md). Use the rules as a risk framework, not a profit source.

| Day | What you do |
|---|---|
| Day-1 | Check eligibility. Compare the options' **implied move** with the stock's **historical move**. Rich → short iron condor, cheap → long straddle, fair → flat. Enter 14:45–15:20 (on Result Day instead if results come after the close) |
| Result Day | Reaction session: exit the event trade (IV crush), then trade the opening range (gap-and-go or failed gap). After-close results: this is the entry day |
| Day+1 | Classify the reaction candle. Trade a continuation or a failed-gap fade with a stop at the reaction-day midpoint, a 1.5R target and a time stop |

No directional position is ever carried across the announcement.

## Quick start

Python 3.10+ (tested on 3.11). There are no third-party dependencies.

```bash
cd fo-results-strategy
pip install -e .            # optional: gives the `fo-results` command
# or run it in place:  python -m fo_results_strategy <command> ...

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
  synthetic.py  fake data for the demo and tests
  cli.py        command line
docs/STRATEGY.md           the playbook
docs/REAL_DATA_RESULTS.md  real-data backtest: data, results, what was tried
results/                   results calendar used (2023-2025) and the trade list of that run
tests/            python -m unittest discover -s tests -t .
```

Educational material, not investment advice.
