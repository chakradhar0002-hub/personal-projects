# Is there a pre-results rule that is 100% positive?

Question: a rule decided at the cutoff (the close 2 sessions before the result session) whose 3-day window (Day-1 +
Result day + Day+1) is always positive. Two readings were tested on stocks in F&O at the time, 22 quarters (Jan-Mar 2021
to Apr-Jun 2026 results), buying or shorting, with the plain 3-day exit, your take-profit exit and after costs:

- **Every trade positive** (100% winners).
- **Every quarter positive** (the picks' average is above zero in every quarter).

## Answer

**No, on both readings.** Looking back, thousands of rules have only winning trades or only positive quarters, but
random data produces them just as easily, and rules that were perfect in 2021 to early 2024 were right only about
half the time afterwards. A realistic good rule wins 55-70% of trades and is positive in 55-65% of quarters.

For comparison: a single 3-day trade in an F&O stock is up about 50% of the time, and buying every F&O stock was
positive in 13 of 22 quarters.

## Every trade positive

| | Long rules | Short rules |
|---|---:|---:|
| Rules with only winners over all 22 quarters, 10+ trades | 21,172 | 29,462 |
| ... 20+ trades | 19 | 33 |
| ... 30+ trades | 0 | 0 |
| Rules with only winners on the first 14 quarters | 42,592 | 39,493 |
| Their win rate on the last 8 quarters | 47.8% | 52.7% |
| Any trade in the last 8 quarters (coin-flip level) | 48.1% | 51.9% |

- The biggest all-winner rule chosen on the first 14 quarters won **25 of 25**: buy when the stock has paid no dividend
  for 154+ days, its overnight gaps over the last 5 sessions add to -1.68% or worse, and it usually does not rise the
  day before results. In the next 8 quarters it won **23 of 33 (70%)**, +0.79% a trade, worst trade -19%
  (BANDHANBNK), and only 7 of 15 in the last 4 quarters. The condition that made it 100% did nothing afterwards.
- On random data the same search finds an all-winner rule of 25 or more trades in 8-27% of runs, so 25 of 25 is
  luck-sized.
- Picking the latest all-winner rule each quarter and trading it won 46-48% of trades.
- Take-profit and after-costs versions give the same picture.

## Every quarter positive

- Over all 22 quarters, 130 rules had picks and a positive average in every quarter (only 2 after costs). 73% of
  searches on random data also found at least one, some with over 1,000 trades.
- 22,452 rules were positive in every one of the first 14 quarters. In the next 8 they were positive in 4.3 quarters
  on average (random data: 4.0), and only 11 of them (0.05%) in all 8.
- The rule ranked first in advance (short a stock that fell 2.8%+ in the 3 sessions before the cutoff and 0.9%+ on the
  cutoff day while its sector did not fall more than 1.3%) was 14 of 14 quarters, then 5 of 8 (+1.04% a trade, 55% of
  trades won). Two crashes (PGEL, IEX) made most of that profit; without them it was +0.2%, and all three 2026 seasons
  lost.
- Picking the best perfect rule each quarter and trading it: positive in 9 of 14 quarters, +0.58% a trade.

## The closest thing: lagged Nifty by more than 15% over the month, with take-profit

Buy when the stock's 1-month return trails Nifty's by more than 15%, exit with your take-profit rule:

| | Trades | Up | Quarters positive | Average |
|---|---:|---:|---:|---:|
| All 22 quarters | 51 | 72.5% | 15 of 16 with picks (6 had none) | +2.24% |
| First 14 quarters | 29 | 69% | 9 of 10 | +2.12% |
| Last 8 quarters | 22 | 77% | 6 of 6 (2 had none) | +2.39% |

It beats random picks of the same size (p < 0.001) and the same filter on dates without results (+0.5%). But it is not
100%: 14 trades lost (worst -10%), one quarter lost 2.8%, the -15% threshold was chosen after seeing all the data, it
gives about 2 trades a quarter, and nearby thresholds are weaker (-10%: 17 of 22 quarters, +0.84%; -12%: 15 of 21).
Without its best 5 trades it averages +1.19%. Worth paper-trading, not betting on as a sure thing.
Quarter-by-quarter detail: [LAGGED_NIFTY_1M.md](LAGGED_NIFTY_1M.md).

## Files

Scripts: `pattern_tests/hundred_pct/` (W_every_trade, Q_every_quarter and the two independent checks). Outputs:
[results/hundred_pct/](../results/hundred_pct/). They read `LAB_ROOT` as described in [TARGET_5PCT.md](TARGET_5PCT.md)
(plus `five_pct/A_rule_search/features_all.csv`) and should be run from their output folder.
