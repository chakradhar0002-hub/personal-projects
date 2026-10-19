# The 6 strongest EMA / SMA features, quarter by quarter

Chosen by the smallest overall p (permutation p for continuous features, luck p for yes/no signals) out of all 59. Confirmed by the split rule: none. Familywise p < 0.05 over all 22 quarters: slope_sma_50. Continuous: Spearman IC between the feature and three_day inside the quarter (positive = higher feature, higher three-day move). Yes/no: average three_day of results with the signal minus the average of all results that quarter (%), with the number of signal results in brackets. The "All 22 quarters" row is the mean IC / the trade-weighted excess.

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
