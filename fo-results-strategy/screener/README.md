# Results screener

A dated screener for the F&O stocks that report quarterly results in the next few days. For each stock it shows its
past results quarter by quarter (reported growth and the three-day move around each one), a summary of how its
three-day results move has behaved, and the project's tested signals before and after results, labelled with what
the research found.

## What it shows

For every stock in today's NSE F&O list with a results board meeting from `--start` to `--start + --days`:

- **Calendar**: meeting date, how the company's past results came out (after the close, during market hours, on
  non-trading days), and the expected window under the project's convention: cutoff close, Day-1, Result day, Day+1,
  the expected reaction day, any holiday inside, and whether the pre-results entry (the cutoff close) is missed,
  today or still ahead.
- **History**: every past result in the project data (Jan-Mar 2021 to Apr-Jun 2026 results): Sales and PAT growth
  YoY and QoQ, Day-1 / Result day / Day+1 moves, the three-day sum, against Nifty, the reaction-day move against
  Nifty and whether it was a results winner (more than 4% above Nifty).
- **Summary**: average, median, share up and average size of the three-day moves, best and worst quarter, the last
  one, the last-4 average and its rank among all current F&O stocks, the average after good (PAT YoY > 0) and bad
  (PAT YoY <= 0) numbers, and how often it was a results winner.
- **Signals**: the lag 10% + volume rule (21-session return vs Nifty 50, 5/60 volume ratio), RSI(14) for the
  winners trade, the last-4 top-tenth and auto-sector watch items, and the run-up straddle dates. They are measured
  at the cutoff close when it is already in the data, else at the latest close (provisional).

## Run it

```
LAB_ROOT=<project scratch data> python3 -P screener/results_screener.py --start 2026-10-20 --days 7
```

- `--start` first meeting date (default today, IST); `--days` calendar days after it (default 7, both ends included);
  `--today` the run date for the entry status (default today, IST); `--offline` uses only files already downloaded.
- `LAB_ROOT` must hold `sector_lab/data` (events.csv, returns.csv, index_close.csv, sessions.csv), `ta/build`
  (adjusted_ohlcv.csv.gz, events_ta.csv for the checks) and `dl_nifty_sector_lists/ind_nifty500list.csv`.
- `SCREENER_DL` is the download folder (default `LAB_ROOT/dl_screener_<run date>`); `OUT` the output folder (default
  `plans/screener_<start>_to_<end>`).
- Re-run it each evening after NSE publishes the bhavcopy (about 18:00-19:00 IST): provisional signals become final
  as cutoff closes pass, and meeting dates can change.

Outputs in `OUT`: `screener.md` (main table and dated actions), `summary.csv`, `calendar.csv`, `history.csv`,
`stocks/<SYMBOL>.md` (one page per company), `screener.json` (everything, for a web page), `notes.md` (sources,
as-of times, conventions, what the research says, data checks) and `validation_qn_last.csv`.

## Data sources

- NSE results calendar (`api/event-calendar`) and board meetings for the window (`api/corporate-board-meetings`),
  only meetings whose purpose includes financial results.
- NSE trading holidays (`api/holiday-master?type=trading`), F&O list (`fo_mktlots.csv`), corporate actions since the
  project data (`api/corporates-corporateActions`).
- Prices: the project's data pack up to its last session (30 Sep 2026), then NSE cash bhavcopies (series EQ close
  and total traded quantity) and `ind_close_all` index files (Nifty 50) up to the latest close. Splits and bonuses
  adjust earlier closes and volumes; demergers blank that day's return; moves beyond +-35% are flagged.
- Past results: `events.csv` (NSE results times, XBRL filings). NSE index sector from
  `results/nifty_sector_3day/results_3day.csv`, else the Nifty 500 list.

Downloads are untrusted data: they are saved in `SCREENER_DL` and parsed with json / pandas only.

## Conventions (as in report_builder/analyze_events.py)

- Result session: the meeting date if it is a trading session, else the next session. Day-1, Result day, Day+1:
  the sessions before, of and after it. Cutoff: 2 sessions before it.
- Three-day sum: Day-1 + Result day + Day+1 daily returns, i.e. cutoff close to Day+1 close.
- Reaction day: Day+1 for results after the close on a trading day, else the Result day. For an upcoming meeting it
  follows the company's usual timing on trading days; mixed histories are marked.
- Lag: 21-session stock return minus Nifty 50's. Volume ratio: mean volume of the last 5 sessions over the last 60.
  RSI(14): Wilder, on adjusted closes. All three reproduce the project's `events_ta.csv` values at the latest
  quarter's cutoffs (checked on every run; see `notes.md`).

## Honest use

- **The history is a record, not a forecast.** The project found that a stock's earlier three-day results moves do
  not predict the direction of its next one (rank correlation +0.005 with the previous quarter; up 49% after an up
  quarter and 48% after a down one). With about 20 results per stock, a +1% or -1% average is within chance. Size
  persists a little, mostly because volatile stocks move more.
- **Good or bad numbers are known only on the results day**, inside the three-day window. The good / bad split per
  stock is descriptive; trading on reported numbers after results gave no edge beyond any result.
- **Two trades held up, both to paper-trade first:** lag 10% + volume before results (realistic +1% to +1.5% a
  trade after costs; cut-offs chosen after looking) and results winners after results (buy at the next open, hold
  20 sessions against Nifty; realistic about +1% over Nifty; stronger with RSI(14) above 50 at the cutoff).
- **Watch items only:** last-4 three-day average in the top tenth (about +0.45% after costs, found after the fact),
  auto and auto-parts stocks (well under +1%), the run-up straddle (marginal, needs fills near mid).
- A provisional signal measured before the cutoff can change by the cutoff close. Meeting dates can move; check the
  company's filing.
- The average F&O stock earns about zero in the three-day window (+0.04%, a loss after costs), and no short worked.

See [docs/SUMMARY.md](../docs/SUMMARY.md) for the research behind these labels.
