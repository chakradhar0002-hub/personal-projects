# EMA and SMA against the three-day results move

Question: is there any correlation between a stock's EMA / SMA position before results and its three-day results move?

- **EMA**: exponential moving average, which weights recent closes more. **SMA**: simple moving average, all N closes
  equal.
- Measured at the cutoff close (2 sessions before the result session), using only prices up to that close.
- Outcome: the three-day sum (Day-1 + Result day + Day+1 daily returns) of every result of a stock in F&O at the time,
  3,278 results in 22 seasons (Jan-Mar 2021 to Apr-Jun 2026 results).
- Prices are split- and bonus-adjusted, with the same conventions as [TECHNICAL_ANALYSIS.md](TECHNICAL_ANALYSIS.md).

59 signals were written down, with their tests, before any outcome was looked at (plan sha256
`4cab04cbe5b326bffd68be03025dad84aefe4c531cf1cc0f9e38b06b12149198`):

- **27 measured values**:
  - the close against the EMA and the SMA of 5, 10, 20, 50, 100 and 200 days;
  - the 5-day slope of the 20, 50 and 200-day averages;
  - EMA against SMA of the same length;
  - six fast-against-slow spreads: EMA 9/21, 12/26, 20/50, 50/200 and SMA 20/50, 50/200.
- **32 yes/no signals**:
  - close above the 20, 50 or 200-day EMA or SMA;
  - fast above slow for the six pairs;
  - a fresh cross up or down in the last 5 days, which includes the golden and death crosses;
  - the close crossing the 20-day average in the last 3 days;
  - all averages stacked up or stacked down.

"IC" is the rank correlation between a signal and the three-day move inside one quarter. A positive IC means a higher
signal value goes with a higher three-day move. The tables average it over the 22 quarters.

## Answer

**There is a small negative correlation, but it is the market, not the stock, and it adds nothing you can use.**

- **The raw link is weak and points against the textbook.**
  - Stocks stretched above their averages, or with rising averages, did slightly worse over the three days; stocks
    below falling averages did slightly better. 26 of 27 measured values have a negative IC, all of them small (at most
    -0.052).
  - The strongest is the 5-day slope of the 50-day SMA (IC -0.052, positive in only 8 of 22 quarters). Its bottom fifth
    made +0.65% and its top fifth -0.17%.
- **None of the 59 signals passes the test set in advance.** That test needed a signal to be significant in the first 14
  quarters and to repeat in the last 8.
  - The 50-day SMA slope passes the correction for the 27 measured values (p 0.037), but not the correction for all 59
    signals (p 0.11), and not in either half on its own.
- **The link is market timing.** In seasons where most stocks had run up above their averages, every stock did worse over
  the next three days.
  - The Nifty 50's own distance from its 50-day SMA at the cutoff has an IC of -0.157 (positive in 2 of 22 quarters).
  - Compare each result only with others that have the same cutoff date, and the link is gone: average IC +0.007, and 0
    of 27 values are significant. So on any given day, a stock above its EMA or SMA does no better or worse than one
    below it.
- **It is not specific to results.** The same negative ICs (-0.005 to -0.064) show up on ordinary days, and results days
  are never significantly different from them.
- **Plain past return does the same job.** The 50-day return has an IC of -0.045, and the 50-day SMA slope moves with it
  almost one for one (rank correlation 0.96). Once the 50- or 100-day return is allowed for, the moving-average values
  add about nothing (-0.03 to +0.02).
- **EMA and SMA carry the same information.** The close-vs-EMA and close-vs-SMA values of the same length have a rank
  correlation of about 0.97, and neither does clearly better.
- **The yes/no signals show nothing.**
  - Every adjusted p is 1.000.
  - Close above the 50-day EMA or SMA: -0.14 against the quarter's average result (p 0.044 / 0.046).
  - Golden cross state (50-day above 200-day): +0.02.
  - The death crosses look good (+2.05% and +1.53% over the average), but they rest on only 27 and 41 results.
- **The tradable version is the lag rule again.**
  - Buying the bottom fifth of the 50-day SMA slope made +0.48% a trade after 0.17% costs (665 trades).
  - But 60 of the 85 lag 10% + volume trades are inside it. Without them it makes +0.25%, which is less than the same rule
    earns on ordinary days (+0.32%).

## Is it the stock or the market?

| Feature at the cutoff | Raw three-day: IC (p) | Minus Nifty 50 same days: IC (p) | Minus same-cutoff results: IC (p) |
|---|---:|---:|---:|
| SMA 50 slope over 5 days | -0.052 (0.004) | -0.041 (0.020) | -0.019 (0.309) |
| EMA 20 slope over 5 days | -0.047 (0.010) | -0.011 (0.527) | +0.007 (0.692) |
| Close vs SMA 100 | -0.045 (0.011) | -0.024 (0.190) | +0.002 (0.927) |
| EMA 50 slope over 5 days | -0.045 (0.010) | -0.017 (0.341) | +0.004 (0.837) |
| Close vs EMA 50 | -0.043 (0.016) | -0.010 (0.594) | +0.011 (0.563) |
| Close vs SMA 50 | -0.037 (0.034) | -0.005 (0.809) | +0.012 (0.485) |
| Close vs EMA 20 | -0.038 (0.044) | +0.001 (0.918) | +0.015 (0.410) |
| Close vs SMA 20 | -0.033 (0.074) | +0.006 (0.695) | +0.020 (0.273) |
| Close vs SMA 200 | -0.029 (0.096) | -0.013 (0.467) | +0.002 (0.889) |
| Close vs EMA 200 | -0.026 (0.152) | -0.008 (0.689) | +0.009 (0.601) |
| Nifty 50 vs its SMA 50 | -0.157 (<0.001) | -0.040 (0.032) | - (-) |

The first column is the correlation as most people would measure it. The second removes the Nifty's move on the same
three days. The third compares each result only with results that have the same cutoff date. That third view is the
only one that would help you choose between two stocks, and there every value is about zero. About three quarters of the
variation in these values is within dates, so this is not over-correction: the link simply comes from which dates the
results fell on.

## All 27 measured values

| Feature at the cutoff | Mean IC | Quarters IC > 0 | p | Family p (27) | First 14 q / last 8 q IC | Ordinary days IC |
|---|---:|---:|---:|---:|---|---:|
| SMA 50 slope over 5 days | -0.052 | 8 of 22 | 0.003 | 0.037 | -0.056 / -0.045 | -0.044 |
| EMA 20 slope over 5 days | -0.047 | 7 of 22 | 0.008 | 0.074 | -0.054 / -0.036 | -0.064 |
| Close vs SMA 100 | -0.045 | 7 of 22 | 0.008 | 0.103 | -0.035 / -0.063 | -0.051 |
| EMA 50 slope over 5 days | -0.045 | 7 of 22 | 0.009 | 0.105 | -0.041 / -0.052 | -0.058 |
| Close vs EMA 50 | -0.043 | 10 of 22 | 0.015 | 0.143 | -0.040 / -0.047 | -0.063 |
| EMA 200 vs SMA 200 | -0.042 | 8 of 22 | 0.024 | 0.164 | -0.030 / -0.063 | -0.016 |
| Close vs EMA 100 | -0.041 | 8 of 22 | 0.019 | 0.176 | -0.034 / -0.054 | -0.053 |
| Close vs SMA 10 | -0.039 | 8 of 22 | 0.032 | 0.232 | -0.049 / -0.020 | -0.051 |
| EMA 9 vs EMA 21 | -0.038 | 9 of 22 | 0.031 | 0.251 | -0.041 / -0.033 | -0.061 |
| Close vs EMA 20 | -0.038 | 9 of 22 | 0.034 | 0.252 | -0.048 / -0.020 | -0.062 |
| EMA 20 vs EMA 50 | -0.037 | 9 of 22 | 0.032 | 0.264 | -0.028 / -0.053 | -0.044 |
| Close vs SMA 50 | -0.037 | 10 of 22 | 0.036 | 0.271 | -0.037 / -0.038 | -0.061 |
| EMA 12 vs EMA 26 | -0.035 | 9 of 22 | 0.048 | 0.332 | -0.035 / -0.036 | -0.057 |
| Close vs SMA 20 | -0.033 | 11 of 22 | 0.063 | 0.406 | -0.046 / -0.010 | -0.063 |
| Close vs EMA 10 | -0.032 | 8 of 22 | 0.079 | 0.448 | -0.043 / -0.011 | -0.054 |
| Close vs SMA 200 | -0.029 | 9 of 22 | 0.096 | 0.547 | -0.022 / -0.042 | -0.036 |
| SMA 20 vs SMA 50 | -0.026 | 9 of 22 | 0.148 | 0.698 | -0.018 / -0.039 | -0.035 |
| Close vs EMA 200 | -0.026 | 11 of 22 | 0.149 | 0.698 | -0.018 / -0.039 | -0.038 |
| SMA 20 slope over 5 days | -0.026 | 10 of 22 | 0.150 | 0.703 | -0.029 / -0.020 | -0.042 |
| EMA 200 slope over 5 days | -0.025 | 9 of 22 | 0.151 | 0.714 | -0.015 / -0.044 | -0.033 |
| EMA 20 vs SMA 20 | -0.019 | 8 of 22 | 0.283 | 0.905 | -0.033 / +0.004 | -0.034 |
| SMA 50 vs SMA 200 | -0.013 | 11 of 22 | 0.476 | 0.989 | +0.001 / -0.038 | -0.005 |
| Close vs EMA 5 | -0.013 | 12 of 22 | 0.494 | 0.991 | -0.019 / -0.001 | -0.040 |
| EMA 50 vs SMA 50 | -0.008 | 11 of 22 | 0.667 | 1.000 | -0.024 / +0.020 | -0.032 |
| EMA 50 vs EMA 200 | -0.004 | 13 of 22 | 0.842 | 1.000 | +0.011 / -0.029 | -0.009 |
| SMA 200 slope over 5 days | -0.003 | 10 of 22 | 0.875 | 1.000 | -0.005 / +0.000 | -0.013 |
| Close vs SMA 5 | +0.001 | 11 of 22 | 0.975 | 1.000 | -0.001 / +0.003 | -0.032 |

p: 5,000 shuffles of the value within each quarter. Family p: the same, corrected for having tested all 27. Ordinary
days: the same IC on quiet F&O stock-days with no result within 10 sessions (120,238 days). No value is missing: every
result has at least 205 traded days before its cutoff.

## Three-day move by fifth of each value

| Feature | Bottom fifth | 2nd | 3rd | 4th | Top fifth | Top - bottom | Quarters top > bottom |
|:---|---:|---:|---:|---:|---:|---:|---:|
| SMA 50 slope over 5 days (`slope_sma_50`) | +0.65 | -0.01 | -0.07 | -0.21 | -0.17 | -0.82 | 6 of 22 |
| EMA 20 slope over 5 days (`slope_ema_20`) | +0.31 | +0.48 | -0.11 | -0.39 | -0.08 | -0.40 | 9 of 22 |
| Close vs SMA 100 (`dist_sma_100`) | +0.69 | -0.14 | -0.21 | -0.23 | +0.09 | -0.59 | 7 of 22 |
| EMA 50 slope over 5 days (`slope_ema_50`) | +0.45 | 0.00 | -0.12 | +0.09 | -0.22 | -0.67 | 9 of 22 |
| Close vs EMA 50 (`dist_ema_50`) | +0.53 | -0.01 | -0.12 | -0.07 | -0.12 | -0.65 | 9 of 22 |
| EMA 200 vs SMA 200 (`ema_vs_sma_200`) | +0.21 | +0.33 | +0.00 | +0.05 | -0.38 | -0.59 | 8 of 22 |
| Close vs EMA 100 (`dist_ema_100`) | +0.59 | -0.13 | -0.32 | +0.05 | +0.00 | -0.59 | 10 of 22 |
| Close vs SMA 10 (`dist_sma_10`) | +0.63 | -0.14 | -0.08 | -0.18 | -0.03 | -0.67 | 10 of 22 |
| EMA 9 vs EMA 21 (`spread_ema9_21`) | +0.42 | +0.14 | -0.02 | -0.20 | -0.15 | -0.58 | 8 of 22 |
| Close vs EMA 20 (`dist_ema_20`) | +0.45 | +0.14 | -0.35 | -0.11 | +0.06 | -0.39 | 10 of 22 |
| EMA 20 vs EMA 50 (`spread_ema20_50`) | +0.49 | -0.02 | -0.08 | -0.02 | -0.17 | -0.67 | 7 of 22 |
| Close vs SMA 50 (`dist_sma_50`) | +0.50 | +0.12 | -0.42 | -0.03 | +0.02 | -0.48 | 8 of 22 |
| EMA 12 vs EMA 26 (`spread_ema12_26`) | +0.53 | +0.03 | -0.27 | +0.13 | -0.22 | -0.74 | 8 of 22 |
| Close vs SMA 20 (`dist_sma_20`) | +0.55 | -0.10 | -0.19 | +0.00 | -0.07 | -0.62 | 7 of 22 |
| Close vs EMA 10 (`dist_ema_10`) | +0.45 | +0.06 | -0.16 | -0.15 | +0.00 | -0.45 | 9 of 22 |
| Close vs SMA 200 (`dist_sma_200`) | +0.28 | -0.04 | -0.01 | +0.04 | -0.07 | -0.35 | 10 of 22 |
| SMA 20 vs SMA 50 (`spread_sma20_50`) | +0.32 | -0.07 | +0.22 | -0.22 | -0.05 | -0.36 | 8 of 22 |
| Close vs EMA 200 (`dist_ema_200`) | +0.52 | -0.43 | +0.11 | -0.03 | +0.04 | -0.48 | 10 of 22 |
| SMA 20 slope over 5 days (`slope_sma_20`) | +0.32 | +0.14 | -0.16 | -0.13 | +0.03 | -0.29 | 11 of 22 |
| EMA 200 slope over 5 days (`slope_ema_200`) | +0.28 | -0.02 | -0.04 | +0.08 | -0.10 | -0.39 | 9 of 22 |
| EMA 20 vs SMA 20 (`ema_vs_sma_20`) | +0.32 | -0.12 | +0.01 | -0.01 | 0.00 | -0.32 | 8 of 22 |
| SMA 50 vs SMA 200 (`spread_sma50_200`) | -0.06 | +0.17 | +0.29 | -0.23 | +0.03 | +0.09 | 12 of 22 |
| Close vs EMA 5 (`dist_ema_5`) | +0.66 | -0.43 | -0.10 | -0.27 | +0.35 | -0.31 | 10 of 22 |
| EMA 50 vs SMA 50 (`ema_vs_sma_50`) | +0.15 | -0.01 | +0.14 | +0.20 | -0.28 | -0.43 | 8 of 22 |
| EMA 50 vs EMA 200 (`spread_ema50_200`) | +0.00 | +0.04 | +0.17 | -0.06 | +0.06 | +0.06 | 13 of 22 |
| SMA 200 slope over 5 days (`slope_sma_200`) | +0.04 | +0.03 | -0.07 | +0.26 | -0.06 | -0.10 | 13 of 22 |
| Close vs SMA 5 (`dist_sma_5`) | +0.35 | -0.14 | -0.30 | +0.04 | +0.26 | -0.08 | 11 of 22 |

The pattern is not a smooth slope. The bottom fifth (furthest below the average, or the average falling fastest) is
usually the best, and the middle fifths are often the weakest. Most of the bottom-fifth gain comes from a few big
rebounds: without its 10 best results, the bottom fifth of the 20-day EMA slope drops from +0.31% to +0.06%.

## The six strongest values, quarter by quarter

| Quarter | Results | Avg three_day | SMA 50 slope over 5 days (`slope_sma_50`): IC | EMA 20 slope over 5 days (`slope_ema_20`): IC | Close vs SMA 100 (`dist_sma_100`): IC | EMA 50 slope over 5 days (`slope_ema_50`): IC | Close vs EMA 50 (`dist_ema_50`): IC | Close vs EMA 100 (`dist_ema_100`): IC |
|:---|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 Jan-Mar 2021 | 98 | +0.82 | -0.151 | -0.135 | -0.111 | -0.142 | -0.142 | -0.110 |
| 1 Apr-Jun 2021 | 117 | +0.06 | +0.129 | +0.113 | +0.101 | +0.136 | +0.085 | +0.126 |
| 2 Jul-Sep 2021 | 125 | -0.84 | -0.105 | -0.219 | -0.112 | -0.171 | -0.186 | -0.137 |
| 3 Oct-Dec 2021 | 132 | -0.64 | -0.202 | -0.210 | -0.137 | -0.148 | -0.186 | -0.171 |
| 4 Jan-Mar 2022 | 131 | -0.83 | -0.152 | -0.208 | -0.147 | -0.188 | -0.169 | -0.168 |
| 5 Apr-Jun 2022 | 134 | +0.75 | +0.002 | +0.031 | +0.001 | +0.015 | +0.012 | +0.025 |
| 6 Jul-Sep 2022 | 133 | +0.03 | -0.039 | +0.074 | +0.020 | +0.061 | +0.056 | +0.033 |
| 7 Oct-Dec 2022 | 133 | -0.16 | -0.084 | -0.049 | -0.063 | -0.071 | -0.065 | -0.068 |
| 8 Jan-Mar 2023 | 134 | +0.61 | -0.030 | -0.082 | -0.028 | -0.048 | -0.045 | -0.066 |
| 9 Apr-Jun 2023 | 133 | -0.30 | -0.009 | +0.009 | -0.006 | -0.010 | +0.011 | -0.019 |
| 10 Jul-Sep 2023 | 132 | +0.41 | -0.139 | -0.059 | -0.075 | -0.083 | -0.032 | -0.031 |
| 11 Oct-Dec 2023 | 135 | +0.48 | -0.063 | -0.026 | +0.016 | -0.006 | +0.002 | +0.013 |
| 12 Jan-Mar 2024 | 135 | +0.88 | +0.021 | +0.011 | +0.051 | +0.046 | +0.093 | +0.060 |
| 13 Apr-Jun 2024 | 135 | +0.53 | +0.043 | -0.005 | +0.006 | +0.038 | +0.005 | +0.039 |
| 14 Jul-Sep 2024 | 134 | -1.12 | -0.073 | -0.041 | -0.099 | -0.079 | -0.040 | -0.098 |
| 15 Oct-Dec 2024 | 172 | -0.79 | +0.022 | -0.063 | -0.027 | -0.012 | -0.085 | -0.037 |
| 16 Jan-Mar 2025 | 178 | +0.96 | -0.202 | -0.222 | -0.245 | -0.257 | -0.224 | -0.264 |
| 17 Apr-Jun 2025 | 191 | -0.56 | +0.014 | -0.008 | -0.011 | -0.009 | -0.011 | -0.007 |
| 18 Jul-Sep 2025 | 191 | +0.67 | -0.065 | -0.018 | -0.050 | -0.055 | +0.014 | +0.007 |
| 19 Oct-Dec 2025 | 196 | +0.18 | -0.124 | -0.016 | -0.103 | -0.081 | -0.078 | -0.075 |
| 20 Jan-Mar 2026 | 203 | -0.31 | +0.049 | +0.043 | +0.035 | +0.045 | +0.029 | +0.052 |
| 21 Apr-Jun 2026 | 206 | +0.17 | +0.023 | +0.041 | -0.007 | +0.031 | +0.017 | -0.007 |
| All 22 quarters | 3,278 | +0.04 | -0.052 | -0.047 | -0.045 | -0.045 | -0.043 | -0.041 |
| Quarters positive |  |  | 8 of 22 | 7 of 22 | 7 of 22 | 7 of 22 | 10 of 22 | 8 of 22 |
| p |  |  | 0.003 | 0.008 | 0.008 | 0.009 | 0.015 | 0.019 |

Most of the overall link comes from a few quarters: Jan-Mar 2025 (about -0.2 to -0.26 on every value) and the 2021-22
seasons. Leaving out the three most negative quarters cuts the 50-day SMA slope from -0.052 to -0.030.

## All 32 yes/no signals

| Signal at the cutoff | Results | Avg 3-day with / without | Over the quarter average | Quarters beating | p | Holm p | Ordinary days |
|---|---:|---|---:|---:|---:|---:|---:|
| EMA 20 above EMA 50 | 1,994 | -0.03% / +0.16% | -0.15 | 8 of 22 | 0.033 | 1.000 | -0.08 |
| SMA 50 crossed below SMA 200 (last 5 days) | 27 | +1.84% / +0.03% | +2.05 | 10 of 11 | 0.041 | 1.000 | +0.04 |
| Close above EMA 50 | 1,904 | +0.02% / +0.07% | -0.14 | 9 of 22 | 0.044 | 1.000 | -0.10 |
| Close above SMA 50 | 1,881 | +0.03% / +0.06% | -0.14 | 8 of 22 | 0.046 | 1.000 | -0.10 |
| EMA 9 above EMA 21 | 1,854 | +0.04% / +0.04% | -0.14 | 7 of 22 | 0.048 | 1.000 | -0.11 |
| EMA 50 crossed below EMA 200 (last 5 days) | 41 | +1.25% / +0.03% | +1.53 | 11 of 16 | 0.066 | 1.000 | +0.33 |
| Close < EMA20 < EMA50 < EMA200 | 440 | +0.27% / +0.01% | +0.40 | 14 of 22 | 0.074 | 1.000 | +0.22 |
| SMA 20 crossed below SMA 50 (last 5 days) | 209 | -0.70% / +0.09% | -0.57 | 11 of 22 | 0.100 | 1.000 | +0.03 |
| EMA 12 above EMA 26 | 1,920 | +0.06% / +0.02% | -0.11 | 8 of 22 | 0.112 | 1.000 | -0.11 |
| SMA 20 above SMA 50 | 1,968 | -0.01% / +0.12% | -0.11 | 10 of 22 | 0.125 | 1.000 | -0.08 |
| Close < SMA20 < SMA50 < SMA200 | 328 | +0.17% / +0.03% | +0.41 | 13 of 21 | 0.127 | 1.000 | +0.26 |
| Close above EMA 200 | 2,174 | -0.00% / +0.13% | -0.09 | 9 of 22 | 0.139 | 1.000 | -0.08 |
| Close above EMA 20 | 1,789 | +0.07% / +0.01% | -0.11 | 8 of 22 | 0.141 | 1.000 | -0.10 |
| EMA 9 crossed below EMA 21 (last 5 days) | 390 | +0.29% / +0.01% | +0.35 | 13 of 22 | 0.148 | 1.000 | +0.08 |
| SMA 20 crossed above SMA 50 (last 5 days) | 200 | +0.57% / +0.01% | +0.46 | 13 of 21 | 0.184 | 1.000 | +0.07 |
| EMA 12 crossed below EMA 26 (last 5 days) | 303 | +0.23% / +0.02% | +0.37 | 15 of 22 | 0.189 | 1.000 | +0.09 |
| EMA 9 crossed above EMA 21 (last 5 days) | 350 | -0.15% / +0.06% | -0.29 | 9 of 22 | 0.262 | 1.000 | -0.06 |
| Close above SMA 200 | 2,105 | +0.03% / +0.07% | -0.06 | 9 of 22 | 0.355 | 1.000 | -0.06 |
| Close crossed below SMA 20 (last 3 days) | 574 | -0.17% / +0.09% | -0.18 | 9 of 22 | 0.366 | 1.000 | +0.07 |
| Close above SMA 20 | 1,756 | +0.12% / -0.05% | -0.07 | 16 of 22 | 0.372 | 1.000 | -0.11 |
| Close crossed above EMA 20 (last 3 days) | 634 | +0.22% / -0.00% | +0.15 | 12 of 22 | 0.423 | 1.000 | +0.12 |
| EMA 50 crossed above EMA 200 (last 5 days) | 41 | +0.95% / +0.03% | +0.57 | 9 of 16 | 0.454 | 1.000 | -0.19 |
| Close crossed above SMA 20 (last 3 days) | 565 | +0.22% / +0.00% | +0.13 | 10 of 22 | 0.498 | 1.000 | +0.12 |
| Close > EMA20 > EMA50 > EMA200 | 1,095 | +0.11% / +0.01% | -0.06 | 9 of 22 | 0.622 | 1.000 | -0.12 |
| EMA 12 crossed above EMA 26 (last 5 days) | 284 | +0.27% / +0.02% | +0.11 | 13 of 22 | 0.700 | 1.000 | -0.08 |
| SMA 50 above SMA 200 | 2,070 | +0.05% / +0.03% | +0.02 | 11 of 22 | 0.734 | 1.000 | -0.02 |
| EMA 20 crossed above EMA 50 (last 5 days) | 177 | +0.28% / +0.03% | +0.11 | 10 of 21 | 0.771 | 1.000 | -0.07 |
| EMA 20 crossed below EMA 50 (last 5 days) | 182 | -0.13% / +0.05% | +0.10 | 11 of 20 | 0.780 | 1.000 | -0.05 |
| EMA 50 above EMA 200 | 2,205 | +0.04% / +0.05% | +0.01 | 12 of 22 | 0.899 | 1.000 | -0.04 |
| Close crossed below EMA 20 (last 3 days) | 651 | -0.00% / +0.05% | +0.01 | 10 of 22 | 0.960 | 1.000 | +0.03 |
| SMA 50 crossed above SMA 200 (last 5 days) | 39 | +0.20% / +0.04% | +0.02 | 7 of 15 | 0.977 | 1.000 | -0.24 |
| Close > SMA20 > SMA50 > SMA200 | 804 | +0.16% / +0.00% | +0.00 | 10 of 22 | 0.997 | 1.000 | -0.15 |

Over the quarter average: results with the signal minus the average of all results that quarter. p: 20,000 random picks
of the same number of results in each quarter. Holm p: corrected for the 32 signals. Ordinary days: the same difference
on quiet stock-days.

## Checks

- **Halves.** The 50-day SMA slope is -0.056 in the first 14 quarters (corrected p 0.16) and -0.045 in the last 8 (p
  0.09). Neither half passes on its own.
- **Big results.** The ICs barely move when the 10 best and 10 worst results are dropped (the 50-day SMA slope stays at
  -0.049). It is not a few outliers.
- **Day by day.** For the 20-day EMA slope the link sits on Day-1 and the result day (-0.074 and -0.041; Day+1 +0.001).
  For the 50-day SMA slope it is spread evenly (-0.030 / -0.036 / -0.034).
- **Timing of the result (after the fact, so not a finding).** The 50-day SMA slope link is concentrated in results
  announced after the close (IC -0.096, 1,954 results) and absent for results during market hours (+0.009, 1,025
  results). After comparing within cutoff dates it is -0.055, and neither half is significant. This is the only thing
  worth writing down in advance and watching on new quarters.
- **Walk-forward.** Picking the best value and side using only earlier quarters, then trading it in the next quarter,
  made +0.16% to +0.55% after costs, depending on how the pick was made. Without the lag-rule trades it is -0.03% to
  +0.33%, and against results with the same cutoff date -0.02% to +0.21%; none of it is clearly above zero.
- **Power.** With 22 quarters the uncertainty on a mean IC is about ±0.018. The data rule out a true IC above about 0.09
  in size, but they cannot rule out a weak 0.03-0.05.
- **Independent rebuild.** A second build from the raw prices matched every signal value and every test. The one
  correction was to store the signal values with 8 digits instead of 5-6, which removed some artificial ties; no
  conclusion changed.

## Conclusion

Moving averages do not help pick results stocks. The small negative link (stocks above rising averages doing slightly
worse) comes from the market's state on the cutoff date, not from the stock. Compared with other results on the same
day, a stock's EMA or SMA position predicts nothing. EMA and SMA say the same thing, and plain past return says it too.
The only usable part, buying stocks that have fallen well below their averages, is the existing lag 10% + volume rule.
This agrees with [TECHNICAL_ANALYSIS.md](TECHNICAL_ANALYSIS.md), where the 20/50/200-day averages, golden and death
crosses and MACD also showed nothing.

Files: scripts in `pattern_tests/ema_sma_3day/` and outputs in
[results/ema_sma_3day/](../results/ema_sma_3day/):

- PLAN.txt and PLAN.sha256: the plan written before any outcome.
- build_features.py: the 59 signals at every cutoff and every ordinary day.
- run_tests.py: the tests.
- market_timing_table.py: the stock-or-market table above.
- skeptic/: the checks: all-tests correction and power, robustness, ordinary days and timing, EMA vs SMA, walk-forward,
  and comparing within cutoff dates. Its logs are in results/ema_sma_3day/skeptic/.

The scripts read `LAB_ROOT` (the scratch data folder), `TA_BUILD` (the adjusted price panel of the TA study) and
`REPO_ROOT`. The ordinary-day signal file (features_placebo.csv.gz, 18 MB) is not committed; build_features.py rebuilds
it.
