# Can a pre-results rule average more than 5% in the 3-day window over all 22 quarters?

Question: find stocks, picked at the cutoff (the close 2 sessions before the result session), whose 3-day window
(Day-1 + Result day + Day+1, sold at the Day+1 close) averages **more than +5% per trade over all 22 quarters**
(Jan-Mar 2021 to Apr-Jun 2026 results). Not every quarter, any number of picks, buying or shorting.

## Answer

**No, not honestly.** A rule showing more than +5% can be found by looking back over all 22 quarters, but random data
gives rules that look just as good, and every rule chosen on earlier quarters made between about -2% and +2% on the
quarters after. The best honest result is about +1.5% to +2% a trade before costs.

Why it is hard: among stocks that were in F&O at the time, 16% of results windows rise more than 5% and the average
window is +0.04%. To average +5%, a rule must pick those big risers about 60% of the time. The best model managed
26-30%.

| Approach | What was tried | Looks like on past data | On quarters not used to choose it |
|---|---|---|---|
| Every rule of 1-3 conditions on 95 pre-results features, buy or short | about 30 million rules per run | best +13.1% (10 trades), +8.2% (20), +6.7% (30) on the first 14 quarters | +1.83% (26 trades), +0.59% (91), +0.54% (125); re-chosen every quarter: -2.2% to +0.9% |
| Machine-learning models (random forest, boosting, logistic, ridge), retrained each quarter on earlier quarters only | 319 settings | +4.6% (25 trades) for the pre-chosen setting | +1.93% (40 trades); fixed model fitted once on the first 14 quarters: +0.86% (96 trades) |
| Big-move setups from trading logic, thresholds fixed in advance | 96 setups | best: stock fell 8% or more in the 3 sessions before the cutoff, +3.2% (30 trades, 70% up) | +1.36% (11 trades); re-chosen every quarter +1.57% (22 trades) |

All returns are before the 0.17% cost unless stated. Only stocks in F&O at the time were traded.

## The rule that shows +6% over all 22 quarters, and why not to trust it

Buy at the cutoff when the stock is at least 16.85% below its 200-day average, at least 10.18% below its 20-session
high, and at most 1 company in its industry has already reported: **32 trades, +6.08% a trade (+5.91% after costs), 84%
up.** An independent check rebuilt it from the raw data and got the same numbers, but:

- It was the best of about 682 million rules tried on all the data. The same search on data where each stock keeps
  its size of move but gets a random direction finds an equally good best rule 6 times in 10 (+6.2% vs +6.1%), and
  about as many rules above +5% (398 vs 412).
- Chosen honestly (using only 2021 to early 2024), the best rule of this size made +0.5% afterwards.
- The 32 trades come from 4 market sell-offs (May 2022, the Feb 2023 Adani fall, Jan 2025, Jan 2026), 5 of them on a
  single day, so it is really 4-6 bets on "the market bounces after a crash".
- The peer condition is fragile: counting peers by sector index or peer group instead of industry drops it to 2-4%.
  Without it the rule gives +3.0% on 73 trades.

Of about 518,000 rules that were above +5% in 2021 to early 2024, 1.9% stayed above +5% afterwards, and on average
they made about 0%. How a rule did before told almost nothing about how it did later (correlation 0.03).

## What is real, but small

Each of these beats shuffled data and a same-stock placebo on dates without results, but none comes near +5%:

1. **Machine-learning "likely to jump" picks.** A random forest estimating the chance of a window above +5% picks
   volatile, richly valued stocks with a strong past year, good past results reactions and a small dip in the week
   before. Buying the top 2 a quarter made +3.09% on 32 trades in the walk-forward test, but that was a lucky random
   seed: the same model with 30 other seeds averages +2.1%, the clean fixed-model holdout made +1.3%, and without the
   5 best trades (ADANIPORTS +19%, CROMPTON +17%, IREDA +16%, ADANIENT +10%, PGEL +9%) it is +1.0%. Expect about +1.5% a
   trade. Shorting the "likely to fall" picks does not work at all.
2. **Deeply oversold into results.**
   - Stock fell 8% or more in the 3 sessions before the cutoff: +3.2% on 30 trades. On quarters not used to choose
     it, +1.4% to +1.6%. The same stocks bounce +1.6% over 3 days with no results, and the trades bunch in market
     sell-offs.
   - Stock lagged Nifty by more than 15% over the month, with your take-profit rule: +2.2% on 51 trades, +2.4% in the
     last 8 quarters (22 trades), positive in 15 of 16 quarters with picks. About +0.5% of that is the ordinary bounce.
   - The earlier "lagged Nifty by more than 10% in the week" idea (+3.3% on 47 picks): 25 of the 47 picks were stocks
     not yet in F&O. On tradeable stocks it is +2.2% on 22 trades, +0.7% in the last 8 quarters, and -0.4% without
     its best 5 trades.

Realistic expectation for the best of these: about +1.5% to +2% a trade before costs, a few trades a quarter, with
large swings (single trades from about -9% to +19%) and most of the profit from a handful of big winners.

## Files and re-running

Scripts: `pattern_tests/five_pct/` (A_rule_search, B_models, C_setups, and the two independent checks). Outputs:
[results/five_pct/](../results/five_pct/). The scripts read `LAB_ROOT`, a folder that holds `search22/features.csv`
(from `features22.py`), `sector/sector_features.csv` (from `sector.py`) and `sector_lab/data/` (from
`sector_lab_data.py`). Some write next to themselves, others to `LAB_ROOT/five_pct/<folder>/`, and a few read files
from the current folder, so run each from its output folder. They need numpy, pandas, scipy and scikit-learn.

```bash
export LAB_ROOT=/path/to/lab
python3 pattern_tests/five_pct/C_setups/build_features.py   # writes events_feat.csv etc. next to the script
python3 pattern_tests/five_pct/C_setups/evaluate.py
```
