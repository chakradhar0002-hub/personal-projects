# Stock level: does a stock's results move carry over?

x = a result's three-day sum minus the average of all F&O results that quarter (pp). Pairs: the same stock in quarter t and t+1 (consecutive results) or t+4 (same results period a year later).

| Statistic | Observed | Within-stock null mean | p | Across-stock null mean | p | Pairs |
|---|---:|---:|---:|---:|---:|---:|
| Pearson r, t vs t+1 | -0.01 | +0.01 | 0.316 | -0.00 | 0.790 | 3,050 |
| Pearson r, t vs t+4 | +0.04 | +0.02 | 0.280 | -0.00 | 0.061 | 2,470 |
| Spearman, t vs t+1 | +0.00 | +0.02 | 0.497 | -0.00 | 0.790 | 3,050 |
| Spearman, t vs t+4 | +0.03 | +0.02 | 0.402 | +0.00 | 0.093 | 2,470 |

Within-stock null: 2,000 shuffles of each stock's own quarters (keeps each stock's average, so it asks whether neighbouring quarters are more alike than any two quarters of the same stock). Across-stock null: shuffles of x across stocks within each quarter (no carry-over of any kind). p two-sided, before Holm.

## Quintiles of x in quarter t and x at the next result (quarter t+1)

| Fifth of x(t) | Pairs | Avg x(t) | Avg x next | Next up | First 14 q | Last 8 q |
|---|---:|---:|---:|---:|---:|---:|
| Bottom | 600 | -6.88 | +0.07 | 47% | -0.36 (323) | +0.58 (277) |
| 2 | 610 | -2.57 | +0.01 | 49% | -0.07 (331) | +0.11 (279) |
| 3 | 606 | -0.19 | -0.34 | 46% | -0.34 (329) | -0.34 (277) |
| 4 | 615 | +2.32 | +0.23 | 51% | +0.32 (335) | +0.12 (280) |
| Top | 619 | +7.17 | -0.02 | 50% | +0.17 (335) | -0.24 (284) |

Top fifth next: p 0.998; bottom fifth next: p 0.675; top minus bottom -0.09: p 0.772 (random-pick null: next-quarter x shuffled across the stocks with results in both quarters, within quarter). Next up = share of next results with x > 0. First 14 q / last 8 q: next result in Apr-Jun 2021 .. Apr-Jun 2024 results / Jul-Sep 2024 .. Apr-Jun 2026 results.

## Comparison: the last-4 track record of docs/PAST_PERFORMANCE.md (rebuilt here)

| Signal | Results | Avg three-day | Avg x | x first 14 q | x last 8 q | p |
|---|---:|---:|---:|---:|---:|---:|
| Last-4 average, top fifth (TR05) | 569 | +0.53% | +0.45 | +0.84 | +0.10 | 0.021 |
| Last-4 average, top tenth | 292 | +1.07% | +0.99 | +1.00 | +0.98 | <0.001 |

Last-4 average = mean three-day sum of the stock's 4 previous results (any F&O status, as in pattern_tests/past_performance/features/build_panel.py), ranked within the quarter among results with 4 earlier results. The top tenth reproduces the 292 trades at +1.07% of PAST_PERFORMANCE.md.
