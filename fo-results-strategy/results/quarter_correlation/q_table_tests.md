# Quarter-level tests

Every test of quarter_level.py. p: permutation p; Holm p: Holm adjustment within the section (the family named in the heading). n: quarters (or quarter pairs) used. Null in brackets: the average of the statistic over the shuffles.

## Section 2, persistence of good and bad quarters (family: 13 tests)

Null: 20,000 shuffles of the order of the 22 quarters; two-sided (twice the smaller tail).

| Test | Statistic | n | p | Holm p | Meaning |
|---|---|---:|---:|---:|---|
| Autocorrelation of Q, lag 1, Pearson | r = -0.03 (null -0.05) | 21 | 0.938 | 1.000 | Is a good quarter followed by a good one 1 quarter later? No: within what a random order of the 22 quarters gives. |
| Autocorrelation of Q, lag 1, Spearman | r = -0.06 (null -0.05) | 21 | 0.959 | 1.000 | Is a good quarter followed by a good one 1 quarter later? No: within what a random order of the 22 quarters gives. |
| Autocorrelation of Q, lag 2, Pearson | r = -0.19 (null -0.05) | 20 | 0.539 | 1.000 | Is a good quarter followed by a good one 2 quarters later? No: within what a random order of the 22 quarters gives. |
| Autocorrelation of Q, lag 2, Spearman | r = -0.23 (null -0.05) | 20 | 0.422 | 1.000 | Is a good quarter followed by a good one 2 quarters later? No: within what a random order of the 22 quarters gives. |
| Autocorrelation of Q, lag 3, Pearson | r = -0.08 (null -0.05) | 19 | 0.884 | 1.000 | Is a good quarter followed by a good one 3 quarters later? No: within what a random order of the 22 quarters gives. |
| Autocorrelation of Q, lag 3, Spearman | r = -0.12 (null -0.05) | 19 | 0.750 | 1.000 | Is a good quarter followed by a good one 3 quarters later? No: within what a random order of the 22 quarters gives. |
| Autocorrelation of Q, lag 4, Pearson | r = -0.35 (null -0.05) | 18 | 0.197 | 1.000 | Is a good quarter followed by a good one 4 quarters later? No: within what a random order of the 22 quarters gives. |
| Autocorrelation of Q, lag 4, Spearman | r = -0.25 (null -0.05) | 18 | 0.394 | 1.000 | Is a good quarter followed by a good one 4 quarters later? No: within what a random order of the 22 quarters gives. |
| Runs of Q above / below its median | runs = 13 (expected 12) | 22 | 0.816 | 1.000 | Do good and bad quarters come in streaks (fewer runs than expected)? No: within what a random order of the 22 quarters gives. |
| Next-quarter Q after the 5 best minus after the 5 worst quarters | +0.16 pp (null -0.08) | 21 | 0.561 | 1.000 | Is the quarter after a top-5 quarter better than the one after a bottom-5 quarter (+0.05% vs -0.11%)? No: within what a random order of the 22 quarters gives. |
| Autocorrelation of the stock part, lag 1, Pearson | r = +0.34 (null -0.05) | 21 | 0.070 | 0.845 | Is a quarter whose results beat Nifty followed by another that beats Nifty? No: within what a random order of the 22 quarters gives. |
| Autocorrelation of the stock part, lag 1, Spearman | r = +0.27 (null -0.05) | 21 | 0.147 | 1.000 | Is a quarter whose results beat Nifty followed by another that beats Nifty? No: within what a random order of the 22 quarters gives. |
| Next-quarter stock part after the 5 best minus the 5 worst stock-part quarters | +0.47 pp (null -0.06) | 21 | 0.061 | 0.799 | Is the stock part higher after the top-5 stock-part quarters than after the bottom 5 (+0.13 vs -0.34)? No: within what a random order of the 22 quarters gives. |

Runs: the 22 quarters in order, above (+) or below (-) the median Q (+0.12%): `+----+--+-++++--+-++-+`. Next-quarter check: of the 21 quarters that have a next one, the 5 best and the 5 worst; Q of the last quarter (Apr-Jun 2026, +0.17%) is mid-table, so leaving it out changes no pick.

For comparison, stock level (docs/PAST_PERFORMANCE.md, trade A, same three-day window): stocks whose last 4 results windows averaged in the top tenth of the quarter made +1.07% over 292 trades against +0.04% for all F&O results (after-the-fact pick, expect about half). A stock's own results-window record carries a little; this section asks the same of the whole quarter.

## Section 3, seasonality by results period (family: 2 tests)

Null: 20,000 shuffles of the period labels across the 22 quarters; upper tail (between-period sum of squares, reported as eta^2 = its share of the total).

| Test | Statistic | n | p | Holm p | Meaning |
|---|---|---:|---:|---:|---|
| Seasonality of Q by results period (4 periods) | eta^2 = 0.13 (null 0.14) | 22 | 0.473 | 0.947 | Do the results periods differ (means Jan-Mar +0.35, Apr-Jun +0.11, Jul-Sep -0.17, Oct-Dec -0.18)? No: within what random period labels gives. |
| Seasonality of stock part by results period (4 periods) | eta^2 = 0.06 (null 0.14) | 22 | 0.772 | 0.947 | Do the results periods differ (means Jan-Mar +0.08, Apr-Jun -0.18, Jul-Sep -0.16, Oct-Dec -0.01)? No: within what random period labels gives. |

## Section 4, what good and bad quarters have in common (family: 32 tests)

Null: 20,000 shuffles of the 22 values of Q (or of the stock part) against the variable; two-sided.

| Test | Statistic | n | p | Holm p | Meaning |
|---|---|---:|---:|---:|---|
| Q (all-results average) vs (a) Nifty 50 three-day sum on the same sessions, Pearson | r = +0.71 | 22 | <0.001 | 0.006 | Is Q higher when the Nifty 50 three-day sum on the same sessions is higher? Yes, holds after Holm. |
| Q (all-results average) vs (a) Nifty 50 three-day sum on the same sessions, Spearman | r = +0.74 | 22 | <0.001 | 0.006 | Is Q higher when the Nifty 50 three-day sum on the same sessions is higher? Yes, holds after Holm. |
| Q (all-results average) vs (b) Nifty 50 return, 20 sessions before the first cutoff, Pearson | r = -0.10 | 22 | 0.655 | 1.000 | Is Q higher when the Nifty 50 return, 20 sessions before the first cutoff is higher? No: within what random pairing of the 22 values gives. |
| Q (all-results average) vs (b) Nifty 50 return, 20 sessions before the first cutoff, Spearman | r = -0.13 | 22 | 0.561 | 1.000 | Is Q higher when the Nifty 50 return, 20 sessions before the first cutoff is higher? No: within what random pairing of the 22 values gives. |
| Q (all-results average) vs (b) Nifty 50 return, 60 sessions before the first cutoff, Pearson | r = -0.16 | 22 | 0.485 | 1.000 | Is Q higher when the Nifty 50 return, 60 sessions before the first cutoff is higher? No: within what random pairing of the 22 values gives. |
| Q (all-results average) vs (b) Nifty 50 return, 60 sessions before the first cutoff, Spearman | r = -0.15 | 22 | 0.506 | 1.000 | Is Q higher when the Nifty 50 return, 60 sessions before the first cutoff is higher? No: within what random pairing of the 22 values gives. |
| Q (all-results average) vs (c) India VIX at the first cutoff, Pearson | r = -0.10 | 22 | 0.639 | 1.000 | Is Q higher when the India VIX at the first cutoff is higher? No: within what random pairing of the 22 values gives. |
| Q (all-results average) vs (c) India VIX at the first cutoff, Spearman | r = -0.13 | 22 | 0.541 | 1.000 | Is Q higher when the India VIX at the first cutoff is higher? No: within what random pairing of the 22 values gives. |
| Q (all-results average) vs (c) India VIX change, 20 sessions before the first cutoff, Pearson | r = +0.03 | 22 | 0.921 | 1.000 | Is Q higher when the India VIX change, 20 sessions before the first cutoff is higher? No: within what random pairing of the 22 values gives. |
| Q (all-results average) vs (c) India VIX change, 20 sessions before the first cutoff, Spearman | r = -0.19 | 22 | 0.405 | 1.000 | Is Q higher when the India VIX change, 20 sessions before the first cutoff is higher? No: within what random pairing of the 22 values gives. |
| Q (all-results average) vs (d) Nifty 50 return over the season, Pearson | r = +0.72 | 22 | <0.001 | 0.009 | Is Q higher when the Nifty 50 return over the season is higher? Yes, holds after Holm. |
| Q (all-results average) vs (d) Nifty 50 return over the season, Spearman | r = +0.66 | 22 | 0.001 | 0.043 | Is Q higher when the Nifty 50 return over the season is higher? Yes, holds after Holm. |
| Q (all-results average) vs (e) cross-sectional sd of the three-day sums, Pearson | r = -0.32 | 22 | 0.147 | 1.000 | Is Q higher when the cross-sectional sd of the three-day sums is higher? No: within what random pairing of the 22 values gives. |
| Q (all-results average) vs (e) cross-sectional sd of the three-day sums, Spearman | r = -0.33 | 22 | 0.125 | 1.000 | Is Q higher when the cross-sectional sd of the three-day sums is higher? No: within what random pairing of the 22 values gives. |
| Q (all-results average) vs (f) number of results in the quarter, Pearson | r = -0.03 | 22 | 0.897 | 1.000 | Is Q higher when the number of results in the quarter is higher? No: within what random pairing of the 22 values gives. |
| Q (all-results average) vs (f) number of results in the quarter, Spearman | r = +0.18 | 22 | 0.417 | 1.000 | Is Q higher when the number of results in the quarter is higher? No: within what random pairing of the 22 values gives. |
| stock part (Q minus Nifty part) vs (a) Nifty 50 three-day sum on the same sessions, Pearson | r = -0.21 | 22 | 0.346 | 1.000 | Is the stock part higher when the Nifty 50 three-day sum on the same sessions is higher? No: within what random pairing of the 22 values gives. |
| stock part (Q minus Nifty part) vs (a) Nifty 50 three-day sum on the same sessions, Spearman | r = -0.04 | 22 | 0.859 | 1.000 | Is the stock part higher when the Nifty 50 three-day sum on the same sessions is higher? No: within what random pairing of the 22 values gives. |
| stock part (Q minus Nifty part) vs (b) Nifty 50 return, 20 sessions before the first cutoff, Pearson | r = +0.23 | 22 | 0.299 | 1.000 | Is the stock part higher when the Nifty 50 return, 20 sessions before the first cutoff is higher? No: within what random pairing of the 22 values gives. |
| stock part (Q minus Nifty part) vs (b) Nifty 50 return, 20 sessions before the first cutoff, Spearman | r = +0.30 | 22 | 0.175 | 1.000 | Is the stock part higher when the Nifty 50 return, 20 sessions before the first cutoff is higher? No: within what random pairing of the 22 values gives. |
| stock part (Q minus Nifty part) vs (b) Nifty 50 return, 60 sessions before the first cutoff, Pearson | r = +0.11 | 22 | 0.629 | 1.000 | Is the stock part higher when the Nifty 50 return, 60 sessions before the first cutoff is higher? No: within what random pairing of the 22 values gives. |
| stock part (Q minus Nifty part) vs (b) Nifty 50 return, 60 sessions before the first cutoff, Spearman | r = +0.07 | 22 | 0.753 | 1.000 | Is the stock part higher when the Nifty 50 return, 60 sessions before the first cutoff is higher? No: within what random pairing of the 22 values gives. |
| stock part (Q minus Nifty part) vs (c) India VIX at the first cutoff, Pearson | r = -0.37 | 22 | 0.094 | 1.000 | Is the stock part higher when the India VIX at the first cutoff is higher? No: within what random pairing of the 22 values gives. |
| stock part (Q minus Nifty part) vs (c) India VIX at the first cutoff, Spearman | r = -0.40 | 22 | 0.061 | 1.000 | Is the stock part higher when the India VIX at the first cutoff is higher? No: within what random pairing of the 22 values gives. |
| stock part (Q minus Nifty part) vs (c) India VIX change, 20 sessions before the first cutoff, Pearson | r = +0.13 | 22 | 0.570 | 1.000 | Is the stock part higher when the India VIX change, 20 sessions before the first cutoff is higher? No: within what random pairing of the 22 values gives. |
| stock part (Q minus Nifty part) vs (c) India VIX change, 20 sessions before the first cutoff, Spearman | r = -0.02 | 22 | 0.919 | 1.000 | Is the stock part higher when the India VIX change, 20 sessions before the first cutoff is higher? No: within what random pairing of the 22 values gives. |
| stock part (Q minus Nifty part) vs (d) Nifty 50 return over the season, Pearson | r = -0.01 | 22 | 0.955 | 1.000 | Is the stock part higher when the Nifty 50 return over the season is higher? No: within what random pairing of the 22 values gives. |
| stock part (Q minus Nifty part) vs (d) Nifty 50 return over the season, Spearman | r = +0.05 | 22 | 0.828 | 1.000 | Is the stock part higher when the Nifty 50 return over the season is higher? No: within what random pairing of the 22 values gives. |
| stock part (Q minus Nifty part) vs (e) cross-sectional sd of the three-day sums, Pearson | r = -0.08 | 22 | 0.702 | 1.000 | Is the stock part higher when the cross-sectional sd of the three-day sums is higher? No: within what random pairing of the 22 values gives. |
| stock part (Q minus Nifty part) vs (e) cross-sectional sd of the three-day sums, Spearman | r = -0.15 | 22 | 0.506 | 1.000 | Is the stock part higher when the cross-sectional sd of the three-day sums is higher? No: within what random pairing of the 22 values gives. |
| stock part (Q minus Nifty part) vs (f) number of results in the quarter, Pearson | r = +0.15 | 22 | 0.520 | 1.000 | Is the stock part higher when the number of results in the quarter is higher? No: within what random pairing of the 22 values gives. |
| stock part (Q minus Nifty part) vs (f) number of results in the quarter, Spearman | r = +0.24 | 22 | 0.264 | 1.000 | Is the stock part higher when the number of results in the quarter is higher? No: within what random pairing of the 22 values gives. |

R^2 of Q on (a), the Nifty 50 three-day sum on the same sessions, alone: 0.50 (Q = -0.05 + 0.82 x Nifty part). Variance of Q: Nifty part 74%, stock part 52%, twice their covariance -26%. Q = Nifty part + stock part by construction, so Q vs (a) is partly mechanical; the stock-part rows say whether the excess over Nifty also moves with the market. (f) number of results rises over time (98 to 206), so it is close to a time trend.

## Section 5, best vs worst sector (family: 6 tests)

Null: 2,000 within-quarter shuffles of the three-day sums across the NSE sector labels (every sector-quarter cell keeps its size, Q unchanged), best / worst recomputed among sectors with at least 4 results; two-sided (twice the smaller tail of the shuffled values, which are not centred on 0).

| Test | Statistic | n | p | Holm p | Meaning |
|---|---|---:|---:|---:|---|
| Best sector avg vs worst sector avg | r = +0.03 (null +0.15) | 22 | 0.529 | 1.000 | Do the best and the worst sector rise and fall together beyond the mechanical link? No: within what random sector labels within each quarter gives. |
| Best sector excess vs worst sector excess (both minus Q) | r = -0.21 (null -0.09) | 22 | 0.560 | 1.000 | Are the best sector's lead and the worst sector's gap linked? No: within what random sector labels within each quarter gives. |
| Q vs best-minus-worst spread | r = -0.14 (null -0.16) | 22 | 0.942 | 1.000 | Do good quarters have a wider best-worst spread than chance gives? No: within what random sector labels within each quarter gives. |
| Q vs best sector avg | r = +0.25 (null +0.38) | 22 | 0.454 | 1.000 | Does the best sector follow Q more closely than chance gives? No: within what random sector labels within each quarter gives. |
| Q vs worst sector avg | r = +0.67 (null +0.56) | 22 | 0.441 | 1.000 | Does the worst sector follow Q more closely than chance gives? No: within what random sector labels within each quarter gives. |
| Average best-minus-worst spread over 22 quarters | +6.54 pp (null +6.67) | 22 | 0.751 | 1.000 | Is the gap between best and worst sector wider than random sector labels give? No: within what random sector labels within each quarter gives. |
