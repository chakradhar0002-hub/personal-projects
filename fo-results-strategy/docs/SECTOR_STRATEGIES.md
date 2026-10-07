# Fresh sector strategies around results (22 quarters, Jan-Mar 2021 to Apr-Jun 2026 results)

Question: can a stock's sector, its sector peers or the sector index give a new results trade? The main target is
still a rule chosen before the numbers that averages +2% or more in the 3-day window (Day-1 + Result day + Day+1) in
every quarter. Trades over other holding periods were also accepted if they had a real edge.

## Answer

**No.** Six groups of sector ideas were tested with 619 rule variants. None gives a new edge after costs that holds
in both the early and the recent quarters and beats chance. None comes near +2% every quarter in the 3-day window.
The three strongest candidates were rebuilt from scratch by independent checkers and all three fall apart: two are
the known results-winner trade under another name, and one is a small index effect that cannot be traded cheaply.

| Idea | Variants | Best version | After costs, vs Nifty, per trade | Verdict |
|---|---:|---|---:|---|
| 1. Sector leader moves first: trade the peers that have not reported yet | 337 | One of a sector's 3 largest stocks falls > 3% vs Nifty on results: buy its unreported peers for 3 sessions | +0.71% (t 2.85; last 8 quarters +0.31%) | no: chance beats it in 36% of runs over this many rules |
| | | Sector index continues 1 day after the leader's big move | +0.23% with index futures, +0.08% with a stock basket | no (checked): index futures exist only for Bank / Fin Services, and those 7 trades lose |
| 2. Sector results drift and rotation | 120 | Buy a sector's reported stocks once their average beat over Nifty reaches +3%, hold 20 sessions | +1.56% (25 trades, t 1.8; last 8 +0.85%) | no: too few trades, random baskets do almost as well |
| | | At season end, long the 3 sector indices with the best median profit growth, short the worst 3 | +1.7% per season (21 seasons, t 1.7; last 8 +0.3%, last season -6.6%) | no: watch only |
| | | Your 3-day window, only when the sector's earlier reporters beat Nifty by +2% | -0.63% | no: worse than all stocks |
| 3. Sector-aware results-winner trade | 36 | Winner defined against its sector index (beat sector by > 4%), hold 20 | +1.55% vs +1.45% for the plain rule | no: the gain is chance-sized (t 1.5) |
| | | Winner that reports before 2 of its sector peers | +2.15% (88 trades, t 3.4) | no (checked): a random 88 of the plain winners does as well 1 time in 6 |
| | | Buy the sector peers of a big winner (catch-up) | 0.0% over 20 sessions | no |
| 4. Busy weeks for a sector, reporting order | 32 | Stock in its 3-day window during a busy sector week | -0.22% | no |
| | | First reporter of its sector this season | -0.64% (t -2.7) | no: does worse, but shorting does not pay after costs |
| 5. Stocks that usually beat their sector; sector timing by quarter | 26 | Stock whose past results windows beat its sector by > 1% on average | +0.28% (t 1.3; 1 of 18 quarters at +2%) | no |
| | | Sector x quarter-of-year seasonality (from earlier years only) | -0.02% | no |
| 6. Pairs within a sector after both report | 68 | Long the peer with the better reaction, short the worse, 20 sessions | +0.71% per pair (t 1.3) | no |
| | | Bet that a gap between peers' reactions closes | -0.6% to -1.5% per pair | no: the gaps do not close |
| | | Better profit growth than peers but a worse reaction: buy | loses in 7 of 8 versions | no: the price reaction counts more than the numbers |

How it was tested (each group by a separate agent, under the same rules):

- Only information public at the decision time. A peer's results count only after its reaction-day close; results
  dates are taken as known 2 sessions before the result session.
- No ranking of stocks against stocks that report later in the same quarter (the flaw behind the earlier "hot sectors
  do worse" result). Thresholds were fixed in advance or set from earlier quarters only.
- Every variant written down before looking at outcomes, and counted. Costs 0.17% a stock round trip, +0.02% for a
  Nifty hedge. Only stocks in F&O at the time are traded.
- Evidence counted per quarter (trades on the same days share market moves). Each rule judged on the first 14 quarters
  and checked on the last 8. Luck checks: shuffled signals, random peers, random dates, and the best of all rules on
  shuffled data.

## The three candidates that were checked independently

Each checker rebuilt the rule from scratch before reading the original code; all three matched the original numbers
exactly and found no look-ahead bug. They then tried to break it.

1. **Results winner that reports before 2 of its sector peers** (beat Nifty by > 4%, hold 20 sessions, Nifty hedge):
   88 trades, +2.15% a trade, t 3.4. The sector part adds nothing measurable: against all winners it is +0.8% a quarter
   (t 1.2) and +0.2% in the last 8 quarters; random groups instead of true sectors do almost as well; moving the limit
   to 3 or 4 peers, or the hold to 10 days, drops the last 2 years to +0.1-0.4%; without the 5 best trades it is +1.27%.
   In 2021-22 the data has fewer F&O stocks than were really traded, so "few peers reported" was true too often there.
   Realistic: about +1.3% a trade, i.e. the old winner trade.
2. **Sector index continues the day after a big leader move**: +0.23% a trade looks real (chance rarely matches it),
   but it is the big reporting stock's own drift passing through its index weight (HAL, MAZDOCK, NESTLEIND, BRITANNIA,
   RELIANCE); the same stocks' big moves on other days predict nothing for the index. It needs the index's closing
   price on the day, disappears with a one-day delay, and only Bank and Fin Services have index futures (those trades
   lose). Realistic edge: about 0.
3. **Stricter winner bar, beat Nifty by > 6%** (not a sector idea, found along the way): 211 trades, +1.88% a trade,
   t 2.9, 17 of 22 quarters positive. But 6% is not reliably better than 4% (random subsets of the 4% winners match it
   1 time in 9), the gain sits in mid-2022 to mid-2024 results, the last 8 quarters average +1.3% (not significant on
   its own) and almost nothing unhedged. Realistic: about +1% a trade, anywhere from 0 to 2%.

## Two corrections to earlier figures

**1. The 3-day window has no premium on stocks you could actually trade.** The "+0.28% for all F&O stocks" in
[TARGET_2PCT.md](TARGET_2PCT.md) mixes in results from before a stock joined F&O. The universe is today's F&O list,
and stocks that later joined it were usually the ones that grew:

| Results | Count | Average 3-day | vs Nifty |
|---|---:|---:|---:|
| Stock was in F&O at the time | 3,278 | +0.04% | -0.05% |
| Stock joined F&O later | 1,182 | +0.94% | +0.77% |

So buying every F&O stock into its results loses money after costs; the best quarter for in-F&O stocks was +0.96%.

**2. The results-winner trade is weaker over 22 quarters than over the first 15.** Rule as in
[PATTERNS.md](PATTERNS.md): F&O stock beats Nifty by > 4% on its reaction day, buy at that close, hold 20 sessions,
Nifty hedge, after costs.

| Quarters | Trades | Per trade (hedged) | Per trade (unhedged) | Quarters positive | t across quarters |
|---|---:|---:|---:|---:|---:|
| All 22 (Jan-Mar 2021 to Apr-Jun 2026 results) | 392 | +1.45% | +1.55% | 15 of 22 | 2.15 |
| 2021-22 results (the 7 quarters added later) | 87 | -1.20% | -0.79% | 2 of 7 | -1.8 |
| The 15 quarters in PATTERNS.md | 305 | +2.20% | +2.22% | 13 of 15 | 3.2 |
| Last 8 quarters | 200 | +1.20% | +0.42% | 6 of 8 | 2.1 |

It is still the best trade found, but it did not work in 2021-22, it pays mainly when hedged with Nifty, and lately
it has been only a little better than buying any F&O stock after a non-results jump of more than 4% (+0.76% over 20
sessions). Expect about +1% a trade, not +2.3%. Paper-trade before sizing up.

## Worth watching, not trading

Found or kept only as forward tests (each was one of many tries, so luck is likely):

- After one of a sector's 3 largest stocks falls more than 3% vs Nifty on its results, its unreported F&O peers
  recover about 0.7-1% vs Nifty over 3-5 sessions (shrinking: +0.3% in the last 8 quarters; reverses at > 5%).
- Season-end rotation into the sector indices with the best median profit growth (+1.7% a season long-short, t 1.7).
- A stock whose profit growth was far worse than its peers' but whose reaction still beat theirs: +1.95% vs Nifty over
  20 sessions (121 trades, t 2.24); found after the fact.

## Files and re-running

Scripts: `pattern_tests/sector_lab_data.py` (data pack) and `pattern_tests/sector_lab/<group>/` (one folder per idea
group, plus the three `verify_*` checks). Outputs (summaries, logs, smaller trade lists):
[results/sector_lab/](../results/sector_lab/).

```bash
export SECTOR_LAB=/path/to/lab                     # any empty folder
python3 pattern_tests/sector_lab_data.py DATA features.csv $SECTOR_LAB/data   # DATA = report_builder data folder
mkdir -p $SECTOR_LAB/F1_bellwether                 # one folder per script group, then e.g.
python3 pattern_tests/sector_lab/F1_bellwether/bellwether.py
```
