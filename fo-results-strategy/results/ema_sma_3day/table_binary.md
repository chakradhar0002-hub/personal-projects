# EMA / SMA yes/no signals vs the three-day results move

3,278 F&O results, 22 quarters. Avg with / without = average three_day (%, gross) of results with / without the signal at the cutoff close. Excess = signal results minus the same-quarter average of all results. Quarters beating all results = quarters where the signal group averaged more than all results (of quarters with the signal). Luck p: 20,000 random picks of the same number of results inside each quarter, two-sided. Holm p: adjusted over the 32 signals. q0-13 / q14-21: first 14 / last 8 quarters. Placebo diff: the signal's excess on ordinary F&O stock-days (no results within 10 sessions). Results - placebo: per quarter (results excess - placebo excess), averaged, one-sample t-test. Confirmed = Holm p < 0.05 in q0-13 AND same sign with luck p < 0.05 in q14-21. Sorted by luck p. "Crossed" signals look back 5 traded days (MA pairs) or 3 (close vs MA20).

| Signal | Results with signal | Avg with | Avg without | Excess | Quarters beating all results | Luck p | Holm p (32) | q0-13 excess (p) | Holm p q0-13 | q14-21 excess (p) | Placebo diff | Results - placebo (p) | Confirmed |
|:---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| EMA 20 above EMA 50 (`state_ema20_50`) | 1,994 | -0.03 | +0.16 | -0.15 | 8 of 22 | 0.033 | 1.000 | -0.10 (0.224) | 1.000 | -0.21 (0.071) | -0.08 | -0.07 (0.360) | no |
| SMA 50 crossed below SMA 200 (last 5 days) (`xdn_sma50_200`) | 27 | +1.84 | +0.03 | +2.05 | 10 of 11 | 0.041 | 1.000 | +0.90 (0.591) | 1.000 | +2.63 (0.034) | +0.04 | +2.37 (0.008) | no |
| Close above EMA 50 (`above_ema_50`) | 1,904 | +0.02 | +0.07 | -0.14 | 9 of 22 | 0.044 | 1.000 | -0.14 (0.106) | 1.000 | -0.15 (0.223) | -0.10 | -0.06 (0.377) | no |
| Close above SMA 50 (`above_sma_50`) | 1,881 | +0.03 | +0.06 | -0.14 | 8 of 22 | 0.046 | 1.000 | -0.11 (0.217) | 1.000 | -0.19 (0.110) | -0.10 | -0.04 (0.478) | no |
| EMA 9 above EMA 21 (`state_ema9_21`) | 1,854 | +0.04 | +0.04 | -0.14 | 7 of 22 | 0.048 | 1.000 | -0.15 (0.112) | 1.000 | -0.14 (0.233) | -0.11 | -0.10 (0.248) | no |
| EMA 50 crossed below EMA 200 (last 5 days) (`xdn_ema50_200`) | 41 | +1.25 | +0.03 | +1.53 | 11 of 16 | 0.066 | 1.000 | +3.40 (0.007) | 0.214 | +0.21 (0.852) | +0.33 | +1.79 (0.035) | no |
| Close < EMA20 < EMA50 < EMA200 (`bear_stack_ema`) | 440 | +0.27 | +0.01 | +0.40 | 14 of 22 | 0.074 | 1.000 | +0.24 (0.500) | 1.000 | +0.52 (0.077) | +0.22 | -0.06 (0.815) | no |
| SMA 20 crossed below SMA 50 (last 5 days) (`xdn_sma20_50`) | 209 | -0.70 | +0.09 | -0.57 | 11 of 22 | 0.100 | 1.000 | -0.85 (0.052) | 1.000 | -0.12 (0.828) | +0.03 | +0.01 (0.978) | no |
| EMA 12 above EMA 26 (`state_ema12_26`) | 1,920 | +0.06 | +0.02 | -0.11 | 8 of 22 | 0.112 | 1.000 | -0.05 (0.603) | 1.000 | -0.21 (0.073) | -0.11 | +0.01 (0.914) | no |
| SMA 20 above SMA 50 (`state_sma20_50`) | 1,968 | -0.01 | +0.12 | -0.11 | 10 of 22 | 0.125 | 1.000 | -0.06 (0.481) | 1.000 | -0.17 (0.137) | -0.08 | -0.00 (0.971) | no |
| Close < SMA20 < SMA50 < SMA200 (`bear_stack_sma`) | 328 | +0.17 | +0.03 | +0.41 | 13 of 21 | 0.127 | 1.000 | -0.08 (0.853) | 1.000 | +0.72 (0.034) | +0.26 | -0.12 (0.728) | no |
| Close above EMA 200 (`above_ema_200`) | 2,174 | -0.00 | +0.13 | -0.09 | 9 of 22 | 0.138 | 1.000 | -0.07 (0.289) | 1.000 | -0.12 (0.305) | -0.08 | -0.02 (0.754) | no |
| Close above EMA 20 (`above_ema_20`) | 1,789 | +0.07 | +0.01 | -0.11 | 8 of 22 | 0.141 | 1.000 | -0.11 (0.266) | 1.000 | -0.12 (0.339) | -0.10 | -0.09 (0.325) | no |
| EMA 9 crossed below EMA 21 (last 5 days) (`xdn_ema9_21`) | 390 | +0.29 | +0.01 | +0.35 | 13 of 22 | 0.148 | 1.000 | +0.73 (0.035) | 1.000 | -0.05 (0.899) | +0.08 | +0.34 (0.158) | no |
| SMA 20 crossed above SMA 50 (last 5 days) (`xup_sma20_50`) | 200 | +0.57 | +0.01 | +0.46 | 13 of 21 | 0.184 | 1.000 | +0.03 (0.942) | 1.000 | +0.88 (0.073) | +0.07 | -0.01 (0.985) | no |
| EMA 12 crossed below EMA 26 (last 5 days) (`xdn_ema12_26`) | 303 | +0.23 | +0.02 | +0.37 | 15 of 22 | 0.189 | 1.000 | +0.74 (0.062) | 1.000 | +0.00 (0.996) | +0.09 | +0.18 (0.590) | no |
| EMA 9 crossed above EMA 21 (last 5 days) (`xup_ema9_21`) | 350 | -0.15 | +0.06 | -0.29 | 9 of 22 | 0.261 | 1.000 | -0.19 (0.591) | 1.000 | -0.39 (0.286) | -0.06 | -0.49 (0.124) | no |
| Close above SMA 200 (`above_sma_200`) | 2,105 | +0.03 | +0.07 | -0.06 | 9 of 22 | 0.355 | 1.000 | -0.03 (0.654) | 1.000 | -0.10 (0.402) | -0.06 | -0.01 (0.884) | no |
| Close crossed below SMA 20 (last 3 days) (`pxdn_sma20`) | 574 | -0.17 | +0.09 | -0.18 | 9 of 22 | 0.366 | 1.000 | -0.32 (0.239) | 1.000 | -0.02 (0.942) | +0.07 | -0.29 (0.198) | no |
| Close above SMA 20 (`above_sma_20`) | 1,756 | +0.12 | -0.05 | -0.07 | 16 of 22 | 0.372 | 1.000 | -0.07 (0.483) | 1.000 | -0.07 (0.590) | -0.11 | -0.03 (0.800) | no |
| Close crossed above EMA 20 (last 3 days) (`pxup_ema20`) | 634 | +0.22 | -0.00 | +0.15 | 12 of 22 | 0.423 | 1.000 | +0.17 (0.484) | 1.000 | +0.12 (0.660) | +0.12 | +0.02 (0.929) | no |
| EMA 50 crossed above EMA 200 (last 5 days) (`xup_ema50_200`) | 41 | +0.95 | +0.03 | +0.57 | 9 of 16 | 0.454 | 1.000 | +0.60 (0.551) | 1.000 | +0.55 (0.636) | -0.19 | +2.80 (0.062) | no |
| Close crossed above SMA 20 (last 3 days) (`pxup_sma20`) | 565 | +0.22 | +0.00 | +0.13 | 10 of 22 | 0.498 | 1.000 | +0.08 (0.769) | 1.000 | +0.19 (0.499) | +0.12 | -0.07 (0.776) | no |
| Close > EMA20 > EMA50 > EMA200 (`bull_stack_ema`) | 1,095 | +0.11 | +0.01 | -0.06 | 9 of 22 | 0.622 | 1.000 | -0.06 (0.679) | 1.000 | -0.06 (0.772) | -0.12 | -0.04 (0.765) | no |
| EMA 12 crossed above EMA 26 (last 5 days) (`xup_ema12_26`) | 284 | +0.27 | +0.02 | +0.11 | 13 of 22 | 0.700 | 1.000 | +0.45 (0.240) | 1.000 | -0.28 (0.508) | -0.08 | +0.05 (0.888) | no |
| SMA 50 above SMA 200 (`state_sma50_200`) | 2,070 | +0.05 | +0.03 | +0.02 | 11 of 22 | 0.734 | 1.000 | +0.01 (0.827) | 1.000 | +0.03 (0.802) | -0.02 | +0.04 (0.720) | no |
| EMA 20 crossed above EMA 50 (last 5 days) (`xup_ema20_50`) | 177 | +0.28 | +0.03 | +0.11 | 10 of 21 | 0.771 | 1.000 | -0.09 (0.857) | 1.000 | +0.32 (0.563) | -0.07 | +0.31 (0.548) | no |
| EMA 20 crossed below EMA 50 (last 5 days) (`xdn_ema20_50`) | 182 | -0.13 | +0.05 | +0.10 | 11 of 20 | 0.781 | 1.000 | +0.55 (0.265) | 1.000 | -0.48 (0.402) | -0.05 | +0.39 (0.399) | no |
| EMA 50 above EMA 200 (`state_ema50_200`) | 2,205 | +0.04 | +0.05 | +0.01 | 12 of 22 | 0.899 | 1.000 | +0.01 (0.879) | 1.000 | +0.00 (0.977) | -0.04 | +0.04 (0.555) | no |
| Close crossed below EMA 20 (last 3 days) (`pxdn_ema20`) | 651 | -0.00 | +0.05 | +0.01 | 10 of 22 | 0.960 | 1.000 | -0.05 (0.838) | 1.000 | +0.07 (0.779) | +0.03 | -0.01 (0.946) | no |
| SMA 50 crossed above SMA 200 (last 5 days) (`xup_sma50_200`) | 39 | +0.20 | +0.04 | +0.02 | 7 of 15 | 0.977 | 1.000 | -0.26 (0.827) | 1.000 | +0.22 (0.825) | -0.24 | -0.08 (0.920) | no |
| Close > SMA20 > SMA50 > SMA200 (`bull_stack_sma`) | 804 | +0.16 | +0.00 | +0.00 | 10 of 22 | 0.997 | 1.000 | -0.13 (0.437) | 1.000 | +0.30 (0.308) | -0.15 | +0.06 (0.760) | no |
