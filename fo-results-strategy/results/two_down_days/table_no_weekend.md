# Two down days, away from weekends and holidays

PLAN_NO_WEEKEND.txt: the MAIN sample of PLAN.txt (ordinary days, F&O stocks while in F&O, May 2021 .. Sep 2026), restricted to stretches with no weekend or holiday. "Not near": day 0 (Monday) to day 3 (Thursday) on four calendar days in a row, and the Friday a normal session. "No break inside": four calendar weekdays in a row (day 3 a Thursday or Friday). A weekend session (Muhurat, special Saturday) counts as a break.

## Not near a weekend or holiday (Mon..Thu, Friday open)

| Group | Triples | Day 3 down | ± (date-clustered SE) | Day 3 up | Mean day 3 | Day 3 vs Nifty (pts) |
|---|---:|---:|---:|---:|---:|---:|
| All days | 24,251 | 49.3% | ±1.6 | 50.2% | +0.04% | +0.05 |
| After two up days | 6,728 | 50.6% | ±2.0 | 49.1% | -0.00% | +0.03 |
| After one down day | 11,335 | 47.4% | ±1.9 | 52.1% | +0.07% | +0.08 |
| After two down days | 5,390 | 46.1% | ±2.2 | 53.4% | +0.12% | +0.12 |

| Two-down minus same-day peers | Two-down triples | Dates | Each date equal (pts) | Weighted by count (pts) | p (t) | p (month bootstrap) |
|---|---:|---:|---:|---:|---:|---:|
| Share down | 5,390 | 210 | -2.77 | -2.60 | 0.024 | 0.008 |
| Mean day 3 | 5,390 | 210 | +0.03 | +0.05 | 0.458 | 0.464 |

| Half | Day 3 dates | Two-down triples | Day 3 down | vs same-day peers (pts) | p (t) | p (bootstrap) |
|---|---:|---:|---:|---:|---:|---:|
| First half | 2021-04-29 .. 2024-06-13 | 2,577 | 42.8% | -3.01 | 0.058 | 0.032 |
| Second half | 2024-06-27 .. 2026-09-24 | 2,813 | 49.1% | -2.46 | 0.210 | 0.167 |

CONFIRMED by the plan's rule (significant in the first half and again in the second): **no**.

| Bigger falls | Triples | Day 3 down | Mean day 3 | vs peers, dates equal (pts) | p | vs peers, weighted (pts) |
|---|---:|---:|---:|---:|---:|---:|
| Both days below -1% | 1,125 | 43.2% | +0.27% | -2.08 | 0.358 | -2.04 |
| Both days below -2% | 194 | 33.0% | +0.68% | -5.58 | 0.274 | -7.32 |

| Part of day 3 | After two down days | Other stocks | Difference, same day (pts) | p |
|---|---:|---:|---:|---:|
| Opening gap | +0.11% | +0.15% | -0.00 | 0.989 |
| Open to close | +0.02% | -0.14% | +0.03 | 0.490 |
| Whole day 3 | +0.12% | +0.01% | +0.03 | 0.436 |

| Trade, after 0.17% costs | Trades | Avg net | Winning | Without the 5 best | First half | Second half |
|---|---:|---:|---:|---:|---:|---:|
| Buy at the day-2 close, sell at the day-3 close | 5,390 | -0.05% | 48.1% | -0.05% | +0.02% | -0.11% |
| Short at the day-2 close, cover at the day-3 close | 5,390 | -0.29% | 41.2% | -0.31% | -0.36% | -0.23% |

## No weekend or holiday inside (day 3 Thu or Fri)

| Group | Triples | Day 3 down | ± (date-clustered SE) | Day 3 up | Mean day 3 | Day 3 vs Nifty (pts) |
|---|---:|---:|---:|---:|---:|---:|
| All days | 50,811 | 49.9% | ±1.2 | 49.7% | +0.02% | +0.01 |
| After two up days | 13,625 | 50.7% | ±1.3 | 48.9% | +0.01% | +0.01 |
| After one down day | 24,215 | 48.9% | ±1.4 | 50.7% | +0.02% | +0.01 |
| After two down days | 11,225 | 49.2% | ±1.8 | 50.4% | -0.01% | +0.02 |

| Two-down minus same-day peers | Two-down triples | Dates | Each date equal (pts) | Weighted by count (pts) | p (t) | p (month bootstrap) |
|---|---:|---:|---:|---:|---:|---:|
| Share down | 11,225 | 445 | -1.49 | -1.91 | 0.067 | 0.028 |
| Mean day 3 | 11,225 | 445 | -0.00 | +0.03 | 0.945 | 0.943 |

| Half | Day 3 dates | Two-down triples | Day 3 down | vs same-day peers (pts) | p (t) | p (bootstrap) |
|---|---:|---:|---:|---:|---:|---:|
| First half | 2021-04-29 .. 2024-06-13 | 5,421 | 46.6% | -1.42 | 0.204 | 0.158 |
| Second half | 2024-06-14 .. 2026-09-25 | 5,804 | 51.7% | -1.58 | 0.181 | 0.057 |

CONFIRMED by the plan's rule (significant in the first half and again in the second): **no**.

| Bigger falls | Triples | Day 3 down | Mean day 3 | vs peers, dates equal (pts) | p | vs peers, weighted (pts) |
|---|---:|---:|---:|---:|---:|---:|
| Both days below -1% | 2,324 | 48.7% | +0.01% | +0.70 | 0.670 | -1.17 |
| Both days below -2% | 381 | 44.4% | +0.14% | -2.46 | 0.424 | -3.87 |

| Part of day 3 | After two down days | Other stocks | Difference, same day (pts) | p |
|---|---:|---:|---:|---:|
| Opening gap | +0.11% | +0.15% | +0.00 | 0.654 |
| Open to close | -0.12% | -0.13% | -0.01 | 0.766 |
| Whole day 3 | -0.01% | +0.03% | -0.00 | 0.956 |

| Trade, after 0.17% costs | Trades | Avg net | Winning | Without the 5 best | First half | Second half |
|---|---:|---:|---:|---:|---:|---:|
| Buy at the day-2 close, sell at the day-3 close | 11,225 | -0.18% | 45.7% | -0.18% | -0.11% | -0.24% |
| Short at the day-2 close, cover at the day-3 close | 11,225 | -0.16% | 44.4% | -0.17% | -0.23% | -0.10% |

## All ordinary days (earlier result)

| Group | Triples | Day 3 down | ± (date-clustered SE) | Day 3 up | Mean day 3 | Day 3 vs Nifty (pts) |
|---|---:|---:|---:|---:|---:|---:|
| All days | 151,513 | 48.7% | ±0.7 | 50.9% | +0.07% | +0.04 |
| After two up days | 39,138 | 49.0% | ±0.8 | 50.6% | +0.08% | +0.04 |
| After one down day | 73,768 | 48.4% | ±0.9 | 51.3% | +0.04% | +0.03 |
| After two down days | 35,679 | 47.6% | ±1.0 | 52.1% | +0.05% | +0.04 |

| Two-down minus same-day peers | Two-down triples | Dates | Each date equal (pts) | Weighted by count (pts) | p (t) | p (month bootstrap) |
|---|---:|---:|---:|---:|---:|---:|
| Share down | 35,678 | 1,328 | -2.40 | -2.27 | <0.001 | <0.001 |
| Mean day 3 | 35,678 | 1,328 | +0.04 | +0.04 | 0.026 | 0.015 |

| Half | Day 3 dates | Two-down triples | Day 3 down | vs same-day peers (pts) | p (t) | p (bootstrap) |
|---|---:|---:|---:|---:|---:|---:|
| First half | 2021-04-27 .. 2024-06-27 | 16,945 | 46.3% | -2.52 | <0.001 | <0.001 |
| Second half | 2024-06-28 .. 2026-09-30 | 18,734 | 48.7% | -2.24 | 0.001 | <0.001 |

CONFIRMED by the plan's rule (significant in the first half and again in the second): **yes**.

| Bigger falls | Triples | Day 3 down | Mean day 3 | vs peers, dates equal (pts) | p | vs peers, weighted (pts) |
|---|---:|---:|---:|---:|---:|---:|
| Both days below -1% | 8,974 | 44.2% | +0.19% | -0.96 | 0.362 | -2.90 |
| Both days below -2% | 2,117 | 37.8% | +0.53% | -1.78 | 0.198 | -4.30 |

| Part of day 3 | After two down days | Other stocks | Difference, same day (pts) | p |
|---|---:|---:|---:|---:|
| Opening gap | +0.10% | +0.14% | +0.00 | 0.794 |
| Open to close | -0.05% | -0.07% | +0.04 | 0.014 |
| Whole day 3 | +0.05% | +0.07% | +0.04 | 0.014 |

| Trade, after 0.17% costs | Trades | Avg net | Winning | Without the 5 best | First half | Second half |
|---|---:|---:|---:|---:|---:|---:|
| Buy at the day-2 close, sell at the day-3 close | 35,679 | -0.12% | 47.4% | -0.12% | -0.08% | -0.15% |
| Short at the day-2 close, cover at the day-3 close | 35,679 | -0.22% | 43.0% | -0.23% | -0.26% | -0.19% |

## Every quarter (not near a weekend or holiday)

| Quarter | Two-down triples | Day 3 down | Other stocks down | vs same-day peers (pts) | Mean day 3 |
|---|---:|---:|---:|---:|---:|
| 2021 Q2 | 119 | 45.4% | 44.1% | +1.74 | +0.16% |
| 2021 Q3 | 175 | 45.1% | 43.5% | -6.87 | +0.12% |
| 2021 Q4 | 182 | 45.6% | 42.6% | +4.34 | +0.03% |
| 2022 Q1 | 134 | 55.2% | 51.9% | -2.39 | -1.21% |
| 2022 Q2 | 267 | 46.4% | 51.0% | -3.36 | -0.13% |
| 2022 Q3 | 172 | 52.3% | 40.7% | +9.75 | +0.15% |
| 2022 Q4 | 248 | 51.6% | 52.8% | -10.68 | -0.03% |
| 2023 Q1 | 252 | 44.0% | 51.8% | -4.35 | +0.08% |
| 2023 Q2 | 133 | 48.1% | 58.6% | -9.75 | +0.09% |
| 2023 Q3 | 199 | 45.7% | 55.1% | +0.99 | +0.18% |
| 2023 Q4 | 193 | 24.9% | 40.8% | -12.94 | +0.88% |
| 2024 Q1 | 383 | 22.7% | 36.7% | -2.06 | +1.17% |
| 2024 Q2 | 167 | 55.1% | 42.4% | -2.86 | -0.27% |
| 2024 Q3 | 260 | 43.1% | 43.0% | -5.85 | +0.18% |
| 2024 Q4 | 223 | 69.1% | 62.9% | +1.05 | -0.59% |
| 2025 Q1 | 281 | 36.7% | 33.6% | -1.46 | +0.62% |
| 2025 Q2 | 274 | 59.9% | 55.1% | -2.23 | -0.57% |
| 2025 Q3 | 335 | 60.3% | 58.4% | -1.24 | -0.16% |
| 2025 Q4 | 408 | 34.3% | 43.1% | -3.86 | +0.41% |
| 2026 Q1 | 212 | 58.5% | 69.1% | -6.16 | -0.40% |
| 2026 Q2 | 176 | 49.4% | 51.8% | -4.84 | +0.14% |
| 2026 Q3 | 597 | 45.7% | 56.6% | +0.13 | +0.29% |

Below its same-day peers (a bounce) in 16 of 22 quarters.

## What weekends and holidays do (all ordinary days)

| Split | Value | Two-down triples | Day 3 down | Other stocks down | vs same-day peers (pts) | p | Mean day 3 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Day 3 weekday | Mon | 7,620 | 47.5% | 48.9% | -3.00 | 0.007 | -0.06% |
| Day 3 weekday | Tue | 7,671 | 44.0% | 49.7% | -2.86 | 0.002 | +0.27% |
| Day 3 weekday | Wed | 6,858 | 46.5% | 46.3% | -2.79 | 0.010 | +0.13% |
| Day 3 weekday | Thu | 6,845 | 47.1% | 50.1% | -2.23 | 0.029 | +0.10% |
| Day 3 weekday | Fri | 6,630 | 53.6% | 50.5% | -0.54 | 0.532 | -0.20% |
| Day 0 .. day 3 window | no break | 11,225 | 49.2% | 50.1% | -1.49 | 0.026 | -0.01% |
| Day 0 .. day 3 window | weekend inside | 23,303 | 46.0% | 48.2% | -2.89 | <0.001 | +0.11% |
| Day 0 .. day 3 window | holiday inside | 1,151 | 62.4% | 55.0% | -2.43 | 0.435 | -0.57% |
