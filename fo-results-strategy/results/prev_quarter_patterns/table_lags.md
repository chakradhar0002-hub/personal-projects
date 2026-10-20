# Each previous quarter, one at a time

For every result of a stock in F&O (3,278 results, 22 quarters), the same stock's three-day results move k quarters earlier (any F&O status), measured against that quarter's average (h). Outcome: this result's three-day move y and its excess x over the quarter's F&O average. Pre-registered in `pattern_tests/prev_quarter_patterns/PLAN.txt`.

## Rank correlation (A1) and direction (A2), all quarters

| Lag (quarters back) | Results | Quarters | Mean IC | t | Quarters positive | p | maxT p | Up after up | Up after down | Avg y after up | Avg y after down | Difference | Luck p | Holm p | IC first 14 q | IC last 8 q | Confirmed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 (last quarter) | 3,177 | 21 | +0.005 | +0.22 | 7 of 21 | 0.785 | 1.000 | 49% (1,478) | 48% (1,699) | +0.00% | +0.03% | -0.02 | 0.959 | 1.000 | +0.040 (13 q) | -0.053 (8 q) | IC no, direction no |
| 2 | 3,060 | 20 | +0.026 | +0.94 | 10 of 20 | 0.174 | 0.787 | 50% (1,416) | 47% (1,644) | +0.17% | -0.12% | +0.29 | 0.144 | 0.865 | +0.031 (12 q) | +0.020 (8 q) | IC no, direction no |
| 3 | 2,934 | 19 | +0.042 | +1.83 | 14 of 19 | 0.028 | 0.185 | 49% (1,361) | 49% (1,573) | +0.30% | -0.16% | +0.45 | 0.018 | 0.143 | +0.009 (11 q) | +0.087 (8 q) | IC no, direction no |
| 4 (same period, 1 year ago) | 2,801 | 18 | +0.037 | +2.11 | 12 of 18 | 0.054 | 0.360 | 49% (1,308) | 49% (1,493) | +0.28% | -0.07% | +0.35 | 0.063 | 0.438 | +0.067 (10 q) | +0.001 (8 q) | IC no, direction no |
| 5 | 2,669 | 17 | +0.020 | +1.15 | 10 of 17 | 0.306 | 0.945 | 50% (1,243) | 49% (1,426) | +0.11% | +0.15% | -0.04 | 0.764 | 1.000 | +0.018 (9 q) | +0.022 (8 q) | IC no, direction no |
| 6 | 2,528 | 16 | +0.008 | +0.37 | 8 of 16 | 0.692 | 1.000 | 50% (1,183) | 49% (1,345) | +0.12% | +0.07% | +0.06 | 0.666 | 1.000 | -0.023 (8 q) | +0.038 (8 q) | IC no, direction no |
| 7 | 2,387 | 15 | +0.027 | +1.93 | 9 of 15 | 0.187 | 0.817 | 51% (1,111) | 48% (1,276) | +0.18% | +0.04% | +0.14 | 0.526 | 1.000 | +0.030 (7 q) | +0.025 (8 q) | IC no, direction no |
| 8 (same period, 2 years ago) | 2,247 | 14 | +0.001 | +0.04 | 7 of 14 | 0.952 | 1.000 | 48% (1,044) | 50% (1,203) | -0.01% | +0.23% | -0.23 | 0.229 | 1.000 | +0.046 (6 q) | -0.032 (8 q) | IC no, direction no |

## The two halves

| Lag | First 14 q: results | IC | p | maxT p | Diff y | p | Holm p | Last 8 q: results | IC | p | Diff y | p |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1,707 (13 q) | +0.040 | 0.100 | 0.556 | +0.38 | 0.089 | 0.621 | 1,470 (8 q) | -0.053 | 0.045 | -0.48 | 0.067 |
| 2 | 1,589 (12 q) | +0.031 | 0.240 | 0.884 | +0.30 | 0.278 | 1.000 | 1,471 (8 q) | +0.020 | 0.476 | +0.27 | 0.336 |
| 3 | 1,463 (11 q) | +0.009 | 0.742 | 1.000 | +0.12 | 0.677 | 1.000 | 1,471 (8 q) | +0.087 | <0.001 | +0.80 | 0.004 |
| 4 | 1,330 (10 q) | +0.067 | 0.014 | 0.114 | +0.70 | 0.011 | 0.091 | 1,471 (8 q) | +0.001 | 0.991 | +0.04 | 0.819 |
| 5 | 1,200 (9 q) | +0.018 | 0.528 | 0.997 | -0.24 | 0.424 | 1.000 | 1,469 (8 q) | +0.022 | 0.396 | +0.12 | 0.769 |
| 6 | 1,066 (8 q) | -0.023 | 0.488 | 0.995 | -0.39 | 0.228 | 1.000 | 1,462 (8 q) | +0.038 | 0.140 | +0.39 | 0.131 |
| 7 | 933 (7 q) | +0.030 | 0.343 | 0.967 | +0.13 | 0.743 | 1.000 | 1,454 (8 q) | +0.025 | 0.353 | +0.15 | 0.590 |
| 8 | 800 (6 q) | +0.046 | 0.199 | 0.825 | -0.03 | 0.960 | 1.000 | 1,447 (8 q) | -0.032 | 0.230 | -0.35 | 0.148 |

Mean IC: Spearman rank correlation between h(t-k) and x(t) inside each quarter (quarters with 20+ results having lag k), averaged over the quarters. t: mean / standard error over quarters. p: 5,000 within-quarter shuffles (two-sided). maxT p: corrected for the 8 lags. Up after up / down: share of results with y > 0 when the lag-k result beat its quarter (h > 0) or not, with counts. Difference: avg y after up minus after down (points); luck p: 20,000 within-quarter random splits of the same sizes; Holm over the 8 lags. Confirmed: familywise p < 0.05 in the first 14 quarters (qn 0-13) and the same sign with p < 0.05 in the last 8 (qn 14-21). Lag k exists only from quarter k on (no data before Jan-Mar 2021 results), so lag 8 has 6 quarters in the first part.
