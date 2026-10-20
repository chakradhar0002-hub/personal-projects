# Size of the move: do big movers stay big movers?

Direction left aside: the size of this result's three-day move |y| against the size of the same stock's move k quarters back (raw |three-day|, %). "Partial" removes the stock's ordinary volatility (sd of daily returns over the 60 sessions to the cutoff, vol60): rank correlation of what is left of each after the volatility rank. This is the straddle question; no cash trade can use it and no option prices are used here.

| Lag | Results | Quarters | Raw IC | t | Quarters positive | p | Holm p | First 14 q | Last 8 q | Partial IC | t | Quarters positive | p | Holm p | First 14 q | Last 8 q | Partial, vol w/o results days | Confirmed (raw / partial) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 (last quarter) | 3,177 | 21 | +0.053 | +3.05 | 15 of 21 | 0.003 | 0.020 | +0.048 | +0.060 | +0.029 | +1.80 | 13 of 21 | 0.106 | 0.388 | +0.029 | +0.030 | +0.040 | no / no |
| 2 | 3,060 | 20 | +0.047 | +3.26 | 15 of 20 | 0.008 | 0.042 | +0.056 | +0.034 | +0.033 | +2.07 | 13 of 20 | 0.070 | 0.388 | +0.045 | +0.016 | +0.034 | no / no |
| 3 | 2,934 | 19 | +0.029 | +1.71 | 12 of 19 | 0.132 | 0.264 | +0.029 | +0.028 | +0.016 | +0.87 | 10 of 19 | 0.402 | 0.804 | +0.017 | +0.014 | +0.017 | no / no |
| 4 (same period, 1 year ago) | 2,801 | 18 | +0.049 | +2.09 | 13 of 18 | 0.010 | 0.042 | +0.073 | +0.019 | +0.036 | +1.56 | 11 of 18 | 0.060 | 0.388 | +0.065 | +0.001 | +0.037 | no / no |
| 5 | 2,669 | 17 | +0.050 | +3.44 | 13 of 17 | 0.011 | 0.042 | +0.036 | +0.066 | +0.038 | +2.65 | 13 of 17 | 0.055 | 0.388 | +0.026 | +0.052 | +0.039 | no / no |
| 6 | 2,528 | 16 | +0.028 | +1.73 | 10 of 16 | 0.155 | 0.264 | +0.025 | +0.032 | +0.015 | +0.84 | 9 of 16 | 0.468 | 0.804 | +0.018 | +0.012 | +0.016 | no / no |
| 7 | 2,387 | 15 | +0.068 | +3.55 | 13 of 15 | 0.001 | 0.011 | +0.077 | +0.060 | +0.056 | +2.89 | 12 of 15 | 0.006 | 0.046 | +0.072 | +0.041 | +0.057 | no / no |
| 8 (same period, 2 years ago) | 2,247 | 14 | +0.060 | +3.80 | 12 of 14 | 0.006 | 0.034 | +0.055 | +0.063 | +0.042 | +2.78 | 11 of 14 | 0.056 | 0.388 | +0.045 | +0.041 | +0.043 | no / no |

For comparison, vol60 alone against |y|: mean IC +0.117 (p <0.001); with the stock's own results days removed from the window +0.111.

p: 5,000 within-quarter shuffles (raw: of |y|; partial: of |y|'s volatility residual), two-sided; Holm over the 8 lags. Confirmed: Holm p < 0.05 in the first 14 quarters and same sign with p < 0.05 in the last 8.

## Average size |y| by fifth of the size of last quarter's move |three-day(t-1)| (fifths within each quarter)

| Fifth | Results | Avg feature | Avg abs y | Median abs y | Share abs y > 5% | First 14 q | Last 8 q |
|---|---:|---:|---:|---:|---:|---:|---:|
| Bottom | 628 | +0.60% | +3.88% | +3.04% | 30% | +3.81% | +3.95% |
| 2 | 636 | +1.76% | +3.45% | +2.83% | 26% | +3.33% | +3.59% |
| 3 | 634 | +3.12% | +4.01% | +3.24% | 31% | +3.86% | +4.19% |
| 4 | 636 | +5.00% | +3.84% | +2.97% | 28% | +3.75% | +3.95% |
| Top | 643 | +9.25% | +4.40% | +3.44% | 35% | +4.28% | +4.54% |

## Average size |y| by fifth of the ordinary volatility vol60 (fifths within each quarter)

| Fifth | Results | Avg feature | Avg abs y | Median abs y | Share abs y > 5% | First 14 q | Last 8 q |
|---|---:|---:|---:|---:|---:|---:|---:|
| Bottom | 647 | +1.24% | +3.28% | +2.70% | 22% | +3.14% | +3.44% |
| 2 | 656 | +1.53% | +3.66% | +2.73% | 29% | +3.68% | +3.62% |
| 3 | 654 | +1.76% | +3.87% | +2.98% | 29% | +3.82% | +3.94% |
| 4 | 656 | +2.04% | +4.37% | +3.51% | 36% | +4.44% | +4.29% |
| Top | 665 | +2.63% | +4.43% | +3.44% | 34% | +4.04% | +4.91% |

## Inside each volatility fifth: last quarter's bigger half vs smaller half of moves

| vol60 fifth | Results | Avg abs y, last quarter big | Avg abs y, last quarter small | Difference |
|---|---:|---:|---:|---:|
| Bottom | 628 | +3.07% | +3.40% | -0.32 |
| 2 | 636 | +3.89% | +3.50% | +0.39 |
| 3 | 634 | +4.10% | +3.61% | +0.49 |
| 4 | 636 | +4.34% | +4.39% | -0.05 |
| Top | 643 | +4.52% | +4.32% | +0.20 |
