# Are best and worst results quarters related?

Question: in the quarter tables of [SECTOR_3DAY.md](SECTOR_3DAY.md) and [NIFTY_SECTOR_3DAY.md](NIFTY_SECTOR_3DAY.md),
some seasons are good and some bad, and each has a best and a worst sector. Is there any correlation?

- Does a good quarter follow a good one, or a bad one?
- Are some results periods better every year?
- What do the good and bad quarters have in common?
- Does the best sector stay best, or flip to worst, the next quarter?
- Which sectors are best and worst together?
- Does a stock that does well on one result do well on the next?

Same data as before: the three-day sum (Day-1 + Result day + Day+1 daily returns) of every result of a stock in F&O at
the time, 3,278 results in 22 seasons (Jan-Mar 2021 to Apr-Jun 2026 results). "Q" is a quarter's average over all its
results. A sector's "excess" is its average minus Q. Sectors are NSE's index sectors, and the hand-made sectors are
used as a check. All p values come from shuffles (the same data in random order). "Adjusted p" allows for the number of
tests in that group.

## Answer

**No: best and worst quarters, and best and worst sectors, do not predict each other.**

- **A good quarter does not follow a good one.**
  - The correlation with the previous quarter is -0.03.
  - After the 5 best quarters the next one averaged +0.05%, and after the 5 worst -0.11%.
  - For example, the worst quarter (Jul-Sep 2024 results, -1.12%) was followed by -0.79%, and the best (Jan-Mar 2025,
    +0.96%) by -0.56%.
  - The same results period a year later leans the other way (r -0.35, negative in both halves of the data), but it is
    within chance (p 0.20).
- **No season is reliably better.** Jan-Mar results average +0.35%, Apr-Jun +0.11%, Jul-Sep -0.17% and Oct-Dec -0.18%,
  but with 5-6 quarters each this is what chance gives (p 0.47).
- **Good and bad quarters are mostly the market on the same days.**
  - Q moves with the Nifty 50's move over the same three sessions (r +0.71), which explains half of the swing.
  - That is known only afterwards. Nothing known before the season predicts it: not the Nifty trend over the 20 or 60
    sessions before, the India VIX level or its change.
  - Used as forecasts on later quarters, every one of these did worse than simply using the past average.
- **The best and worst sector of a quarter are not linked.**
  - The best sector's average and the worst sector's average are uncorrelated (r +0.03; random sector labels give +0.15).
  - The gap between them (+6.5 points on average) is the same as with random sector labels (+6.7).
  - So which sector comes top or bottom in a quarter is mostly noise, and small sectors with 4-5 results land there most
    often.
- **The next quarter is a fresh draw.**
  - Last quarter's best sector lands mid-table (average rank 47 on a 0-100 scale, chance 50) and its lead is gone
    (+0.05).
  - The worst sector bounces a little (+0.53 over the quarter's average), but that is within chance (p 0.24) and appears
    only in the second half of the data.
  - The best stayed best twice and flipped to worst once; the worst stayed worst never and flipped to best 3 times. Chance
    gives about 2 of each.
  - Sector gaps do not carry over: the rank correlation is +0.02 to the next quarter and +0.09 to the same period a year
    later.
- **Sectors moving together: one pair, and only with the hand-made sectors.**
  - Capital goods and IT tend to be good and bad together (r +0.64, adjusted p 0.03 for having looked at all 78 pairs).
    With NSE's sectors the same pair is only +0.31, and it does not survive a correction for everything tested here.
  - Financial services and Metals come close (+0.52, adjusted p 0.08).
  - No pair moves in opposite directions (one best while the other is worst) beyond chance. The closest is Auto and IT
    (-0.48, p 0.06 before adjustment).
- **Stocks: one result does not carry into the next.**
  - Over 3,050 pairs of consecutive results the correlation is -0.01.
  - Last quarter's top fifth of movers averaged -0.02 over the quarter at their next result, and the bottom fifth +0.07.
  - Only the extreme four-result track record already in [PAST_PERFORMANCE.md](PAST_PERFORMANCE.md) shows up: the top
    tenth, 292 trades, +1.07%. That was found after the fact, and five stocks give 60% of it.
- **No trade comes out of it.**
  - Buying last quarter's best sector made -0.24% a result before costs.
  - Buying last quarter's worst made +0.57% (p 0.10). That is not reliable: it is +0.28 and +0.99 in the two halves, and
    -0.10% with the hand-made sectors.

Over the 244 tests run here, the only links that survive correction are Q against the Nifty's move on the same days
and over the season. Both are the market itself, not a pattern you can trade.

## Each quarter: average, market part, best and worst sector

| Results for | Quarter | Results | Avg (Q) | Median | Up | Nifty part | Stock part | Sd | Best sector | Worst sector | Best - worst |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|---:|
| Jan-Mar 2021 | Q4 FY21 | 98 | +0.82% | -0.21% | 48% | +0.78% | +0.04 | 6.02 | Auto +4.19% (10) | IT -1.83% (6) | +6.03 |
| Apr-Jun 2021 | Q1 FY22 | 117 | +0.06% | +0.35% | 55% | +0.64% | -0.57 | 4.97 | IT +4.54% (8) | Healthcare -2.49% (11) | +7.03 |
| Jul-Sep 2021 | Q2 FY22 | 125 | -0.84% | -1.25% | 41% | -0.42% | -0.42 | 5.29 | Auto +1.32% (10) | Fin services -2.42% (31) | +3.74 |
| Oct-Dec 2021 | Q3 FY22 | 132 | -0.64% | -0.36% | 46% | -0.80% | +0.17 | 5.54 | Cons services +2.50% (4) | Constr mat -3.04% (4) | +5.54 |
| Jan-Mar 2022 | Q4 FY22 | 131 | -0.83% | -0.98% | 40% | -0.28% | -0.55 | 5.81 | Cons services +7.43% (4) | Oil & gas -3.17% (8) | +10.60 |
| Apr-Jun 2022 | Q1 FY23 | 134 | +0.75% | +0.63% | 52% | +1.50% | -0.75 | 4.63 | Cap goods +2.54% (9) | Cons dur -1.45% (6) | +3.99 |
| Jul-Sep 2022 | Q2 FY23 | 133 | +0.03% | -0.07% | 50% | +0.93% | -0.90 | 4.67 | Metals +1.49% (9) | Cons services -2.73% (4) | +4.22 |
| Oct-Dec 2022 | Q3 FY23 | 133 | -0.16% | -0.49% | 44% | -0.04% | -0.12 | 5.25 | Services +3.29% (4) | Cons dur -4.98% (6) | +8.26 |
| Jan-Mar 2023 | Q4 FY23 | 134 | +0.61% | +0.40% | 56% | +0.63% | -0.02 | 4.28 | Cap goods +3.30% (9) | Services -2.66% (4) | +5.95 |
| Apr-Jun 2023 | Q1 FY24 | 133 | -0.30% | -0.51% | 42% | -0.31% | +0.01 | 4.26 | FMCG +1.26% (9) | Cons dur -3.61% (6) | +4.87 |
| Jul-Sep 2023 | Q2 FY24 | 132 | +0.41% | +0.38% | 53% | -0.03% | +0.44 | 4.01 | Services +3.24% (4) | IT -1.75% (9) | +4.99 |
| Oct-Dec 2023 | Q3 FY24 | 135 | +0.48% | +0.54% | 53% | +0.12% | +0.36 | 6.39 | Cons services +4.45% (4) | Chemicals -2.62% (4) | +7.07 |
| Jan-Mar 2024 | Q4 FY24 | 135 | +0.88% | +0.23% | 53% | +0.23% | +0.65 | 5.51 | Cap goods +4.99% (9) | IT -2.11% (10) | +7.10 |
| Apr-Jun 2024 | Q1 FY25 | 135 | +0.53% | +0.82% | 53% | -0.02% | +0.55 | 4.77 | Cons services +7.79% (4) | Constr mat -3.55% (4) | +11.34 |
| Jul-Sep 2024 | Q2 FY25 | 134 | -1.12% | -0.95% | 42% | -0.76% | -0.36 | 5.44 | Cons services +1.51% (4) | Cons dur -5.71% (6) | +7.22 |
| Oct-Dec 2024 | Q3 FY25 | 172 | -0.79% | -0.51% | 45% | -0.01% | -0.77 | 5.64 | Chemicals +3.70% (5) | Power -4.45% (7) | +8.15 |
| Jan-Mar 2025 | Q4 FY25 | 178 | +0.96% | +0.70% | 53% | +0.47% | +0.49 | 4.66 | IT +4.33% (12) | Cons services -1.87% (7) | +6.20 |
| Apr-Jun 2025 | Q1 FY26 | 191 | -0.56% | -0.35% | 46% | -0.35% | -0.21 | 5.53 | Cons services +3.03% (7) | Cons dur -2.81% (10) | +5.84 |
| Jul-Sep 2025 | Q2 FY26 | 191 | +0.67% | +0.47% | 54% | +0.24% | +0.43 | 4.44 | FMCG +2.40% (12) | Services -1.39% (5) | +3.79 |
| Oct-Dec 2025 | Q3 FY26 | 196 | +0.18% | -0.37% | 46% | -0.12% | +0.30 | 5.43 | Services +5.66% (5) | Power -3.35% (7) | +9.01 |
| Jan-Mar 2026 | Q4 FY26 | 203 | -0.31% | -0.50% | 46% | -0.17% | -0.14 | 5.67 | Chemicals +3.83% (5) | IT -3.36% (12) | +7.19 |
| Apr-Jun 2026 | Q1 FY27 | 206 | +0.17% | +0.08% | 50% | +0.26% | -0.09 | 4.87 | Auto +2.85% (15) | Power -2.79% (8) | +5.64 |
| All 22 quarters | | 3,278 | +0.05% | -0.09% | 49% | +0.11% | -0.07 | 5.14 | +3.62% | -2.92% | +6.54 |

Nifty part: the Nifty 50's three-day sum on the same sessions as each result, averaged over the quarter. Stock part: Q
minus the Nifty part. Sd: how widely the quarter's results were spread. Best and worst sector: among NSE sectors with at
least 4 results that quarter (results in brackets). The last row averages the 22 quarters.

## Quarter-level tests

| Question | Value | Chance level | Quarters | p | Adjusted p |
|---|---:|---:|---:|---:|---:|
| Good quarter after a good one? (r with the previous quarter) | -0.03 | -0.05 | 21 | 0.938 | 1.000 |
| Same, two quarters back | -0.19 | -0.05 | 20 | 0.539 | 1.000 |
| Same, three quarters back | -0.08 | -0.05 | 19 | 0.884 | 1.000 |
| Same results period a year earlier (r) | -0.35 | -0.05 | 18 | 0.197 | 1.000 |
| Streaks: runs above / below the median | 13 | 12 | 22 | 0.816 | 1.000 |
| Next quarter after the 5 best minus after the 5 worst (points) | +0.16 | -0.08 | 21 | 0.561 | 1.000 |
| Stock part (Q minus Nifty part) after a good one (r) | +0.34 | -0.05 | 21 | 0.070 | 0.845 |
| Seasonality: share of the swing explained by results period | 0.13 | 0.14 | 22 | 0.473 | 0.947 |
| Nifty 50 move on the same three days (r) | +0.71 | +0.00 | 22 | <0.001 | 0.006 |
| Nifty 50 over the whole season (r) | +0.72 | +0.00 | 22 | <0.001 | 0.009 |
| Nifty 50 over the 20 sessions before the season (r) | -0.10 | -0.00 | 22 | 0.655 | 1.000 |
| Nifty 50 over the 60 sessions before the season (r) | -0.16 | -0.00 | 22 | 0.485 | 1.000 |
| India VIX at the start of the season (r) | -0.10 | +0.00 | 22 | 0.639 | 1.000 |
| India VIX change over the 20 sessions before (r) | +0.03 | +0.00 | 22 | 0.921 | 1.000 |
| Spread of results that quarter (r) | -0.32 | -0.00 | 22 | 0.147 | 1.000 |
| Stock part vs India VIX at the start (r) | -0.37 | +0.00 | 22 | 0.094 | 1.000 |
| Best sector average vs worst sector average (r) | +0.03 | +0.15 | 22 | 0.529 | 1.000 |
| Best minus worst sector, average gap (points) | +6.54 | +6.67 | 22 | 0.751 | 1.000 |

Chance level: the average of the statistic over random shuffles. Adjusted p: Holm within each group of tests (13 for
quarter-to-quarter, 2 for seasonality, 32 for the market variables, 6 for best vs worst). The two Nifty links are
partly built in, because Q is the Nifty part plus the stock part, and neither is known before the season.

With only 22 quarters, a correlation has to be about 0.58 or larger to be found reliably. So "no correlation" here means
no strong correlation, not proof of none. The 95% range for the previous-quarter correlation is -0.46 to +0.41.

## The market around each season

| Results for | Quarter | First cutoff | Last Day+1 | Nifty 20 sessions before | Nifty 60 sessions before | VIX at first cutoff | VIX change, 20 sessions | Nifty over the season |
|---|---|---|---|---:|---:|---:|---:|---:|
| Jan-Mar 2021 | Q4 FY21 | 2021-04-08 | 2021-07-01 | -0.55% | +3.67% | 20.31 | -4.37 | +5.42% |
| Apr-Jun 2021 | Q1 FY22 | 2021-07-06 | 2021-08-17 | +0.50% | +6.35% | 12.28 | -2.95 | +5.03% |
| Jul-Sep 2021 | Q2 FY22 | 2021-10-06 | 2021-11-16 | +1.64% | +12.47% | 17.33 | +2.43 | +2.00% |
| Oct-Dec 2021 | Q3 FY22 | 2022-01-10 | 2022-02-18 | +3.66% | -0.87% | 17.68 | +1.11 | -4.04% |
| Jan-Mar 2022 | Q4 FY22 | 2022-04-07 | 2022-05-31 | +7.92% | -2.02% | 19.00 | -8.47 | -5.98% |
| Apr-Jun 2022 | Q1 FY23 | 2022-07-06 | 2022-08-17 | -2.24% | -10.09% | 20.27 | +0.43 | +12.22% |
| Jul-Sep 2022 | Q2 FY23 | 2022-10-06 | 2022-11-21 | -1.66% | +6.85% | 19.32 | -0.05 | +4.78% |
| Oct-Dec 2022 | Q3 FY23 | 2023-01-05 | 2023-02-15 | -3.32% | +5.94% | 14.98 | +1.58 | +0.13% |
| Jan-Mar 2023 | Q4 FY23 | 2023-04-10 | 2023-05-31 | -0.73% | -2.64% | 12.27 | -0.18 | +5.17% |
| Apr-Jun 2023 | Q1 FY24 | 2023-07-10 | 2023-08-16 | +4.27% | +8.67% | 11.46 | +0.34 | +0.56% |
| Jul-Sep 2023 | Q2 FY24 | 2023-10-09 | 2023-11-16 | -1.09% | +0.66% | 11.40 | +0.53 | +1.30% |
| Oct-Dec 2023 | Q3 FY24 | 2024-01-09 | 2024-02-21 | +2.61% | +8.85% | 13.26 | +0.50 | +2.37% |
| Jan-Mar 2024 | Q4 FY24 | 2024-04-09 | 2024-05-31 | +0.66% | +4.60% | 11.36 | -2.25 | -0.49% |
| Apr-Jun 2024 | Q1 FY25 | 2024-07-09 | 2024-08-16 | +5.05% | +7.38% | 14.28 | -2.12 | +0.44% |
| Jul-Sep 2024 | Q2 FY25 | 2024-10-08 | 2024-11-18 | +0.31% | +2.87% | 14.59 | +0.35 | -6.23% |
| Oct-Dec 2024 | Q3 FY25 | 2025-01-07 | 2025-02-18 | -3.70% | -5.16% | 14.66 | +0.55 | -3.22% |
| Jan-Mar 2025 | Q4 FY25 | 2025-04-08 | 2025-06-02 | -0.07% | -3.82% | 20.44 | +6.97 | +9.68% |
| Apr-Jun 2025 | Q1 FY26 | 2025-07-08 | 2025-08-18 | +1.67% | +13.94% | 12.20 | -1.82 | -2.53% |
| Jul-Sep 2025 | Q2 FY26 | 2025-10-07 | 2025-11-17 | +1.35% | -0.97% | 10.05 | -0.79 | +3.60% |
| Oct-Dec 2025 | Q3 FY26 | 2026-01-07 | 2026-02-20 | +1.17% | +3.38% | 9.95 | -1.00 | -2.18% |
| Jan-Mar 2026 | Q4 FY26 | 2026-04-07 | 2026-06-04 | -6.63% | -11.67% | 24.70 | +6.84 | +1.27% |
| Apr-Jun 2026 | Q1 FY27 | 2026-07-07 | 2026-08-17 | +5.52% | +1.67% | 11.65 | -5.38 | -0.46% |

## By results period

| Results for | Quarters | Results | Mean Q | Median Q | Quarters with Q > 0 | Nifty part | Stock part | Lowest / highest Q |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Jan-Mar | 6 | 879 | +0.35% | +0.71% | 4 of 6 | +0.28% | +0.08 | -0.83% / +0.96% |
| Apr-Jun | 6 | 916 | +0.11% | +0.12% | 4 of 6 | +0.29% | -0.18 | -0.56% / +0.75% |
| Jul-Sep | 5 | 715 | -0.17% | +0.03% | 3 of 5 | -0.01% | -0.16 | -1.12% / +0.67% |
| Oct-Dec | 5 | 768 | -0.18% | -0.16% | 2 of 5 | -0.17% | -0.01 | -0.79% / +0.48% |

Jan-Mar results come out highest in both halves of the data, but with 5-6 quarters in each period the spread between
periods is what random order gives.

## Best and worst sector of each quarter, and the next quarter

| Results for | Quarter | All F&O avg | Best sector (avg, n) | Its rank next quarter | Its avg next quarter | Worst sector (avg, n) | Its rank next quarter | Its avg next quarter | All F&O avg next quarter |
|---|---|---:|---|---:|---:|---|---:|---:|---:|
| Jan-Mar 2021 | Q4 FY21 | +0.82% | Auto +4.19% (10) | 11 of 12 | -1.23% | IT -1.83% (6) | 1 of 12 | +4.54% | +0.06% |
| Apr-Jun 2021 | Q1 FY22 | +0.06% | IT +4.54% (8) | 2 of 12 | +1.12% | Healthcare -2.49% (11) | 4 of 12 | -0.24% | -0.84% |
| Jul-Sep 2021 | Q2 FY22 | -0.84% | Auto +1.32% (10) | 3 of 13 | +1.07% | Fin services -2.42% (31) | 6 of 13 | -0.23% | -0.64% |
| Oct-Dec 2021 | Q3 FY22 | -0.64% | Cons services +2.50% (4) | 1 of 13 | +7.43% | Constr mat -3.04% (4) | 12 of 13 | -2.94% | -0.83% |
| Jan-Mar 2022 | Q4 FY22 | -0.83% | Cons services +7.43% (4) | 3 of 13 | +2.02% | Oil & gas -3.17% (8) | 11 of 13 | -0.99% | +0.75% |
| Apr-Jun 2022 | Q1 FY23 | +0.75% | Cap goods +2.54% (9) | 10 of 13 | -0.90% | Cons dur -1.45% (6) | 12 of 13 | -1.34% | +0.03% |
| Jul-Sep 2022 | Q2 FY23 | +0.03% | Metals +1.49% (9) | 11 of 13 | -1.55% | Cons services -2.73% (4) | 4 of 13 | +0.92% | -0.16% |
| Oct-Dec 2022 | Q3 FY23 | -0.16% | Services +3.29% (4) | 13 of 13 | -2.66% | Cons dur -4.98% (6) | 2 of 13 | +3.18% | +0.61% |
| Jan-Mar 2023 | Q4 FY23 | +0.61% | Cap goods +3.30% (9) | 5 of 13 | +0.55% | Services -2.66% (4) | 12 of 13 | -2.29% | -0.30% |
| Apr-Jun 2023 | Q1 FY24 | -0.30% | FMCG +1.26% (9) | 8 of 13 | +0.21% | Cons dur -3.61% (6) | 11 of 13 | -1.63% | +0.41% |
| Jul-Sep 2023 | Q2 FY24 | +0.41% | Services +3.24% (4) | 5 of 13 | +2.29% | IT -1.75% (9) | 2 of 13 | +4.33% | +0.48% |
| Oct-Dec 2023 | Q3 FY24 | +0.48% | Cons services +4.45% (4) | 4 of 13 | +1.39% | Chemicals -2.62% (4) | 10 of 13 | -0.19% | +0.88% |
| Jan-Mar 2024 | Q4 FY24 | +0.88% | Cap goods +4.99% (9) | 3 of 13 | +1.81% | IT -2.11% (10) | 5 of 13 | +1.73% | +0.53% |
| Apr-Jun 2024 | Q1 FY25 | +0.53% | Cons services +7.79% (4) | 1 of 13 | +1.51% | Constr mat -3.55% (4) | 6 of 13 | -0.16% | -1.12% |
| Jul-Sep 2024 | Q2 FY25 | -1.12% | Cons services +1.51% (4) | 14 of 15 | -4.22% | Cons dur -5.71% (6) | 11 of 15 | -1.27% | -0.79% |
| Oct-Dec 2024 | Q3 FY25 | -0.79% | Chemicals +3.70% (5) | 10 of 15 | -0.22% | Power -4.45% (7) | 13 of 15 | -0.62% | +0.96% |
| Jan-Mar 2025 | Q4 FY25 | +0.96% | IT +4.33% (12) | 14 of 15 | -1.89% | Cons services -1.87% (7) | 1 of 15 | +3.03% | -0.56% |
| Apr-Jun 2025 | Q1 FY26 | -0.56% | Cons services +3.03% (7) | 12 of 15 | -1.03% | Cons dur -2.81% (10) | 9 of 15 | -0.37% | +0.67% |
| Jul-Sep 2025 | Q2 FY26 | +0.67% | FMCG +2.40% (12) | 13 of 15 | -2.12% | Services -1.39% (5) | 1 of 15 | +5.66% | +0.18% |
| Oct-Dec 2025 | Q3 FY26 | +0.18% | Services +5.66% (5) | 7 of 15 | +0.26% | Power -3.35% (7) | 10 of 15 | -0.49% | -0.31% |
| Jan-Mar 2026 | Q4 FY26 | -0.31% | Chemicals +3.83% (5) | 14 of 15 | -2.53% | IT -3.36% (12) | 4 of 15 | +0.75% | +0.17% |
| Apr-Jun 2026 | Q1 FY27 | +0.17% | Auto +2.85% (15) | - | - | Power -2.79% (8) | - | - | - |

| | Best sector of quarter t | Worst sector of quarter t |
|---|---:|---:|
| Mean rank percentile next quarter (100 = best, 0 = worst) | 47.2 (49.8) | 52.3 (49.9) |
| Mean excess over all F&O next quarter | +0.05% (-0.01%) | +0.53% (-0.00%) |
| Best again next quarter | 2 (1.85) | 3 (1.89) |
| Worst next quarter | 1 (1.90) | 0 (1.87) |

Brackets: the value expected by chance (2,000 shuffles of the results across sector labels within each quarter). Rank
percentile: 100 = best sector next quarter, 0 = worst.

## Do sector gaps carry over?

Next quarter:

| | Mean Spearman | Null mean | p | Pairs positive | Slope | Null mean | p |
|---|---:|---:|---:|---:|---:|---:|---:|
| NSE sectors | +0.02 | -0.00 | 0.785 | 11 of 21 | +0.01 | +0.00 | 0.860 |
| Custom sectors | +0.05 | +0.00 | 0.431 | 12 of 21 | +0.00 | +0.00 | 0.996 |
| Sectoral index members (vs own index) | -0.11 | -0.00 | 0.127 | 8 of 21 | -0.08 | -0.00 | 0.229 |

Same results period a year later:

| | Mean Spearman | Null mean | p | Pairs positive | Slope | Null mean | p |
|---|---:|---:|---:|---:|---:|---:|---:|
| NSE sectors | +0.09 | -0.00 | 0.222 | 8 of 18 | +0.09 | -0.00 | 0.129 |
| Custom sectors | -0.06 | -0.00 | 0.393 | 8 of 18 | -0.03 | -0.00 | 0.605 |
| Sectoral index members (vs own index) | +0.06 | +0.00 | 0.517 | 10 of 18 | +0.02 | -0.01 | 0.683 |

Spearman: rank correlation of the sector excesses in one quarter and the next. Slope: how much of a sector's excess
carries over (0.01 = 1%). Index members: members of the Nifty sectoral indices, measured against their own index.
These tests could detect a carry-over of about a sixth of a sector's excess or more, so a smaller one is not ruled out.

## Which sectors move together

NSE index sectors (13 sectors with at least 4 results in 18 or more quarters):

| | Pair | r | Null mean r | Quarters | Pair p | Familywise p |
|---|---|---:|---:|---:|---:|---:|
| Most negative | Cons services / Constr mat | -0.49 | -0.03 | 20 | 0.041 | 0.956 |
| Most negative | Auto / IT | -0.48 | -0.08 | 22 | 0.060 | 0.999 |
| Most negative | Fin services / Cons services | -0.48 | -0.11 | 21 | 0.117 | 1.000 |
| Most negative | IT / FMCG | -0.45 | -0.07 | 22 | 0.089 | 1.000 |
| Most negative | FMCG / Services | -0.44 | -0.05 | 21 | 0.074 | 0.999 |
| Most positive | Fin services / Metals | +0.52 | -0.15 | 22 | <0.001 | 0.082 |
| Most positive | FMCG / Chemicals | +0.43 | -0.04 | 21 | 0.029 | 0.932 |
| Most positive | Auto / FMCG | +0.43 | -0.08 | 22 | 0.017 | 0.798 |
| Most positive | FMCG / Oil & gas | +0.34 | -0.06 | 22 | 0.063 | 0.999 |
| Most positive | Healthcare / Cons services | +0.34 | -0.05 | 21 | 0.079 | 0.999 |

Hand-made sectors of [SECTOR_3DAY.md](SECTOR_3DAY.md):

| | Pair | r | Null mean r | Quarters | Pair p | Familywise p |
|---|---|---:|---:|---:|---:|---:|
| Most negative | Auto / IT | -0.47 | -0.08 | 22 | 0.076 | 1.000 |
| Most negative | NBFC/Fin / Cons dur | -0.39 | -0.09 | 20 | 0.219 | 1.000 |
| Most negative | Cap goods / Chem/agro | -0.39 | -0.05 | 21 | 0.147 | 1.000 |
| Most positive | Cap goods / IT | +0.64 | -0.07 | 22 | <0.001 | 0.030 |
| Most positive | Banks / Metals | +0.57 | -0.09 | 22 | 0.001 | 0.109 |
| Most positive | NBFC/Fin / Cement | +0.39 | -0.07 | 21 | 0.039 | 0.945 |

r: correlation of the two sectors' excesses across quarters. It is slightly negative by chance (null mean r), because
the sector excesses add up to zero each quarter. Familywise p allows for having looked at all 78 pairs.

- **Capital goods and IT** (hand-made sectors) is the only pair that passes: +0.72 and +0.61 in the two halves, +0.60 to
  +0.76 leaving out any one quarter. It is not just shared market days. But it depends on the labels: with NSE's sectors it
  is +0.31. Over all 244 tests here the adjusted p is about
  0.09.
- **Financial services / Banks with Metals** is positive in both halves (+0.52 NSE, +0.57 hand-made) but does not pass
  the correction.
- No pair is reliably "one best, the other worst".

The full correlation matrices are in [s_table_sector_corr.md](../results/quarter_correlation/s_table_sector_corr.md).

## Stocks: does one result carry into the next?

Next result, by fifth of this quarter's excess (x = a result's three-day sum minus that quarter's average):

| Fifth of x(t) | Pairs | Avg x(t) | Avg x next | Next up | First 14 q | Last 8 q |
|---|---:|---:|---:|---:|---:|---:|
| Bottom | 600 | -6.88 | +0.07 | 47% | -0.36 (323) | +0.58 (277) |
| 2 | 610 | -2.57 | +0.01 | 49% | -0.07 (331) | +0.11 (279) |
| 3 | 606 | -0.19 | -0.34 | 46% | -0.34 (329) | -0.34 (277) |
| 4 | 615 | +2.32 | +0.23 | 51% | +0.32 (335) | +0.12 (280) |
| Top | 619 | +7.17 | -0.02 | 50% | +0.17 (335) | -0.24 (284) |

Compared with the stock's four-result track record ([PAST_PERFORMANCE.md](PAST_PERFORMANCE.md), rebuilt here):

| Signal | Results | Avg three-day | Avg x | x first 14 q | x last 8 q | p |
|---|---:|---:|---:|---:|---:|---:|
| Last-4 average, top fifth (set in advance) | 569 | +0.53% | +0.45 | +0.84 | +0.10 | 0.021 |
| Last-4 average, top tenth | 292 | +1.07% | +0.99 | +1.00 | +0.98 | <0.001 |

- With 3,050 pairs this test is powerful: the correlation is -0.01 with a 95% range of about ±0.035. A stock's one
  result says nothing about its next.
- Only the extreme tail of the four-result average (the top tenth) holds. The top fifth was the rule set in advance, and
  it fades (+0.10 in the last 8 quarters). Five stocks (REC, Hitachi Energy India, Trent, Cummins, BEL) give 60% of the
  top tenth's excess, so expect about half of +1.07% going forward, as that doc says.
- Looked at by halves (after the fact), the first half had slight momentum (r +0.05) and the second slight reversal
  (r -0.05). Both are far too small to trade after costs.

## Trading rules built from it

| Rule (NSE sectors unless noted) | Results | Avg 3-day | After 0.17% costs | Over all results | p |
|---|---:|---:|---:|---:|---:|
| Buy last quarter's best sector | 151 | -0.24% | -0.41% | -0.19 | 0.644 |
| Buy last quarter's worst sector | 175 | +0.57% | +0.40% | +0.62 | 0.101 |
| Buy last quarter's top 3 sectors | 582 | -0.01% | -0.18% | -0.03 | 0.882 |
| Buy last quarter's bottom 3 sectors | 576 | +0.15% | -0.02% | +0.10 | 0.619 |
| Buy the best sector of the same period a year ago | 144 | +0.50% | +0.33% | +0.36 | 0.374 |
| Buy the worst sector of the same period a year ago | 160 | +0.16% | -0.01% | +0.06 | 0.885 |
| Buy last quarter's best, sectors with 8+ results only | 223 | +0.30% | +0.13% | +0.25 | 0.443 |
| Buy last quarter's worst, sectors with 8+ results only | 241 | -0.04% | -0.21% | +0.03 | 0.925 |
| Buy last quarter's best sector (hand-made sectors) | 206 | -0.40% | -0.57% | -0.36 | 0.294 |
| Buy last quarter's worst sector (hand-made sectors) | 193 | -0.10% | -0.27% | -0.13 | 0.698 |

The quarters run from Apr-Jun 2021 to Apr-Jun 2026 results (21 quarters with a previous one; 18 for the "year ago"
rules). Over all results is the average excess over each quarter's average result. p: against random picks of the same
size in each quarter. None is significant, and all F&O results averaged +0.02% a result in the same quarters
(-0.15% after costs).

## Caveats

- **Few quarters.** 22 quarters can only show strong links. The sector tests rule out large carry-overs only, and the
  stock test is the only one with enough data to show there is essentially none.
- **Many tests.** 244 tests were run in total (53 quarter-level, 35 sector and stock level, 156 sector pairs). A few
  results with p below 0.05 are expected by chance alone; only the market link survives a correction for all of them.
- **Today's lists.** Sector labels and the F&O list are today's, the same caveat as the sector studies.
- **Shuffles.** The shuffles treat results in a quarter as interchangeable. Sector labels alone explain no more of a
  quarter's spread than random labels do (ratio 1.00), so this matters little here.

## Conclusion

The quarter tables have no memory. A good or bad results season, and the best or worst sector in it, does not tell you
anything about the next season or the same season next year. Good and bad seasons are mostly the market moving on the
same days, which is not known in advance. The only carry-over in this data is the stock-level four-result track record
already found in [PAST_PERFORMANCE.md](PAST_PERFORMANCE.md), and even that rests on a few stocks. Do not pick sectors
for the next results season from last season's table.

Files: scripts in `pattern_tests/quarter_correlation/`, outputs in
[results/quarter_correlation/](../results/quarter_correlation/):

- quarter_level.py: the quarter-level tests (q_ files).
- sector_stock_level.py: the sector, index-member and stock tests (s_ files).
- skeptic/: the halves, leave-one-quarter-out, walk-forward forecasts, trading rules and the all-tests correction. Its
  outputs are in results/quarter_correlation/skeptic/.

The scripts read `LAB_ROOT` (the scratch data folder) and `REPO_ROOT`. Every number was rebuilt independently from the
raw data. That re-check found and fixed one error: the sector-pair p values had not been centred on the chance level,
which moved Capital goods / IT from an adjusted p of 0.21 to 0.03.
