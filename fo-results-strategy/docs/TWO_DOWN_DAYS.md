# Two down days: is the third day down too?

Question: for an F&O stock on an ordinary day, with no results and no events, if it closes down two days in a row,
does it close down on the third day?

- **Main sample:**
  - The 206 F&O stocks while they were in F&O, May 2021 to Sep 2026.
  - Only ordinary days: no result or reaction session within 5 sessions, and no split, bonus, demerger, dividend or other
    NSE ex-date on the three days.
  - 151,513 three-day stretches, of which 35,679 are two down days.
- **Down** means the adjusted close is below the previous close.
- **Same-day peers:** each two-down stock is compared with every other eligible stock on the same day 3. This takes out
  market days, which a raw average mixes in.
- The tests and the pass rule were written down before any result was computed (plan sha256
  `57cb69805022ed8248c9e7b8f115ddcc24f8b883e8b175dfa29686cc2e523bc5`).

## Answer

**No: after two down days the third day is slightly *less* likely to be down, not more. The effect is too small to
trade.**

The same holds away from weekends and holidays: on Monday-to-Thursday stretches with the Friday open, the third day fell
46.1% of the time after two down days, against 49.3% on all such days (details below).

- **The raw odds are close to a coin flip.** After two down days, day 3 closed down 47.6% of the time and up 52.1%.
  On all days it was 48.7% down and 50.9% up.
- **Against other stocks on the same day, there is a small, steady bounce.**
  - Two-down stocks fell 2.4 points less often than the other stocks that day.
  - It holds in both halves of the data, so it passes the rule set in advance.
  - It leaned this way in 17 of 22 quarters, and leaving out any one quarter keeps it between -2.2 and -2.6 points.
- **In money it is tiny.** Day 3 averages +0.05%, only +0.04 points above same-day peers.
  - Buying at the day-2 close and selling the next close loses -0.12% a trade after 0.17% costs.
  - Shorting for a third down day loses -0.22%.
- **A bigger fall bounces more often, but that is mostly the market.**
  - When both days fell more than 2%, day 3 closed down only 37.8% of the time and averaged +0.53%.
  - But other stocks fell only 42.1% of the time on those same days: big falls bunch on sell-off days, and the whole
    market tends to bounce the next day.
  - Against those peers the gap is about -4 points, and it is not significant when each date counts equally.
- **Longer losing streaks change little.** After 3, 4, 5 or 6+ down days, the next day was down 45.6% to 47.9% of the
  time.
  - Up streaks lean the other way: after 1 to 4 up days, the next day fell 1.6 to 3.4 points more often than peers.
  - So individual stocks show a small short-term reversal in both directions.
- **The bounce happens during the session, not at the open.** Day 3's opening gap is the same as peers', and the
  difference comes from open to close. It does not reverse on day 4, so it is not a quirk of closing prices.
- **The index itself is different.** After the Nifty 50 fell two days in a row, it fell on the third day 50.6% of the
  time, against 44.6% on other days (p 0.011). Its average third day is still about zero, so this is not a trade either.
- **No single stock has a reliable pattern.**
  - Of 196 stocks tested, none passes the correction for testing 196.
  - Stocks such as BSE (60% down after two down days) or NHPC (39%) are within chance for that many tests.

## Away from weekends and holidays

Stretches that touch a weekend or a holiday were dropped, under a second plan written before computing it (plan sha256 `32a125dce1696dd09c8887bf5a09d50d2e7365f26a774c49e2d090901bacff40`):

- **Not near a weekend or holiday:** day 0 (Monday) to day 3 (Thursday) on four calendar days in a row, with the Friday a normal session. 24,251 stretches, 5,390 of them two down days.
- **No break inside:** four calendar weekdays in a row, so day 3 is a Thursday or a Friday.
- A weekend session (Muhurat, a special Saturday) counts as a break.

### Not near a weekend or holiday (Mon..Thu, Friday open)

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

### No weekend or holiday inside (day 3 Thu or Fri)

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

### All ordinary days (earlier result)

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

### Every quarter (not near a weekend or holiday)

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

### What weekends and holidays do (all ordinary days)

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


- **Away from weekends and holidays the answer is the same.**
  - Not near a break, the third day fell 46.1% of the time after two down days, against 49.3% on all such days.
  - That is 2.8 points below other stocks the same day (p 0.008 to 0.024).
  - It is not significant in each half on its own (210 dates in all), and it is worth +0.03% on the day.
  - Buying after two down days loses -0.05% a trade after costs, and shorting loses -0.29%.
- **Fridays are the exception.** With day 3 a Monday to Thursday, the bounce is 2.2 to 3.0 points. With day 3 a Friday it is -0.5 (not significant), which is why the 'no break inside' version, half of it Fridays, is weaker (-1.5 points).
- **Stretches with a weekend inside** show the clearest bounce (-2.9 points). Those with a holiday inside are few (1,151) and fell 62.4% of the time, but so did other stocks on those days, so against peers they are within chance.

## The main numbers

| Sample | Group | Triples | Day 3 down | ± (date-clustered SE) | Day 3 up | Mean day 3 | Median day 3 | Day 3 vs Nifty (pts) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| MAIN | All days | 151,513 | 48.7% | ±0.7 | 50.9% | +0.07% | +0.03% | +0.04 |
| MAIN | After two up days | 39,138 | 49.0% | ±0.8 | 50.6% | +0.08% | +0.02% | +0.04 |
| MAIN | After one down day | 73,768 | 48.4% | ±0.9 | 51.3% | +0.04% | +0.05% | +0.03 |
| MAIN | After two down days | 35,679 | 47.6% | ±1.0 | 52.1% | +0.05% | +0.08% | +0.04 |
| ALL21 | All days | 207,076 | 49.0% | ±0.6 | 50.5% | +0.10% | +0.02% | +0.06 |
| ALL21 | After two up days | 53,006 | 49.0% | ±0.7 | 50.6% | +0.15% | +0.03% | +0.09 |
| ALL21 | After one down day | 101,542 | 49.1% | ±0.8 | 50.5% | +0.04% | +0.02% | +0.02 |
| ALL21 | After two down days | 49,830 | 48.3% | ±0.9 | 51.3% | +0.06% | +0.05% | +0.05 |
| LONG | All days | 504,834 | 49.5% | ±0.4 | 49.9% | +0.09% | +0.00% | +0.04 |
| LONG | After two up days | 126,039 | 49.6% | ±0.4 | 50.0% | +0.16% | +0.00% | +0.09 |
| LONG | After one down day | 250,013 | 49.5% | ±0.5 | 49.9% | +0.03% | +0.00% | -0.01 |
| LONG | After two down days | 123,899 | 48.9% | ±0.6 | 50.6% | +0.05% | +0.03% | +0.02 |

### Against other stocks on the same day

| Sample | Outcome | Two-down triples | Dates | Two-down minus same-day peers (each date equal) | Weighted by two-down count | p (t over dates) | p (month bootstrap) |
|---|---:|---:|---:|---:|---:|---:|---:|
| MAIN | share down | 35,678 | 1,328 | -2.40 | -2.27 | <0.001 | <0.001 |
| MAIN | mean day-3 return | 35,678 | 1,328 | +0.04 | +0.04 | 0.026 | 0.015 |
| ALL21 | share down | 49,829 | 1,343 | -1.93 | -2.12 | <0.001 | <0.001 |
| ALL21 | mean day-3 return | 49,829 | 1,343 | +0.04 | +0.04 | 0.021 | 0.016 |
| LONG | share down | 123,899 | 2,688 | -1.77 | -2.14 | <0.001 | <0.001 |
| LONG | mean day-3 return | 123,899 | 2,688 | +0.03 | +0.05 | 0.007 | 0.004 |

## Down (and up) streaks

| Days in a row before (ending day 2) | Triples | Next day down | Mean next day | vs same-day peers (pts) | p (t) | p (bootstrap) |
|---|---:|---:|---:|---:|---:|---:|
| 1 down | 38,089 | 49.1% | +0.03% | -0.40 | 0.393 | 0.362 |
| 2 down | 18,646 | 47.7% | +0.05% | -1.69 | 0.005 | 0.009 |
| 3 down | 8,925 | 47.5% | +0.07% | -1.87 | 0.017 | 0.032 |
| 4 down | 4,269 | 47.9% | +0.03% | -1.13 | 0.292 | 0.262 |
| 5 down | 2,042 | 47.4% | -0.00% | -2.17 | 0.107 | 0.098 |
| 6+ down | 1,797 | 45.6% | +0.14% | -2.46 | 0.085 | 0.070 |
| 1 up | 38,022 | 49.0% | +0.10% | +1.78 | <0.001 | <0.001 |
| 2 up | 19,280 | 48.6% | +0.09% | +1.64 | 0.011 | 0.012 |
| 3 up | 9,867 | 49.6% | +0.04% | +2.83 | <0.001 | <0.001 |
| 4 up | 4,962 | 49.4% | +0.09% | +3.42 | 0.001 | <0.001 |
| 5 up | 2,491 | 48.6% | +0.14% | -1.29 | 0.356 | 0.382 |
| 6+ up | 2,538 | 49.6% | +0.07% | +1.19 | 0.380 | 0.370 |

## Size of the fall

| Fifth of day 1 + day 2 (within each date) | Triples | Avg two-day move | Day 3 down | Mean day 3 | Day 3 vs Nifty |
|---|---:|---:|---:|---:|---:|
| Bottom (fell most) | 30,848 | -2.54% | 47.3% | +0.09% | +0.07 |
| 2 | 30,026 | -0.85% | 48.1% | +0.08% | +0.06 |
| 3 | 30,035 | +0.04% | 48.8% | +0.05% | +0.02 |
| 4 | 30,026 | +1.00% | 49.7% | +0.05% | +0.02 |
| Top (rose most) | 30,568 | +3.05% | 49.6% | +0.05% | +0.03 |

| Signal | Triples | Day 3 down | Mean day 3 | Share down vs peers (pts) | p | Mean day 3 vs peers (pts) | p |
|---|---:|---:|---:|---:|---:|---:|---:|
| Two down days | 35,679 | 47.6% | +0.05% | -2.40 | <0.001 | +0.04 | 0.014 |
| Both days below -1% | 8,974 | 44.2% | +0.19% | -0.96 | 0.379 | -0.01 | 0.693 |
| Both days below -2% | 2,117 | 37.8% | +0.53% | -1.78 | 0.180 | -0.02 | 0.848 |
| Two down days vs Nifty (stock minus Nifty < 0 both days) | 38,625 | 46.7% | +0.12% | -2.12 | <0.001 | +0.06 | <0.001 |

The plain share down after big falls (44.2% and 37.8%) is mostly the market: on those days most stocks bounced. The
size of the fall adds little once the stock is compared with others on the same day.

## Where day 3 moves

| Part of day 3 | After two down days | Other stocks | Difference, same day (pts) | p (t) | p (bootstrap) |
|---|---:|---:|---:|---:|---:|
| Overnight gap (open day 3 / close day 2) | +0.10% | +0.14% | +0.00 | 0.781 | 0.793 |
| During day 3 (close / open) | -0.05% | -0.07% | +0.04 | 0.024 | 0.008 |
| Whole day 3 | +0.05% | +0.07% | +0.04 | 0.026 | 0.015 |

## Market state, and the index itself

| Market state | Two-down triples | Day 3 down | Other stocks down | Mean day 3 | vs same-day peers (pts) | p |
|---|---:|---:|---:|---:|---:|---:|
| Nifty 50 also down both days | 16,565 | 47.9% | 52.8% | +0.04% | -2.24 | <0.001 |
| Nifty 50 not down both days | 19,114 | 47.3% | 48.3% | +0.07% | -2.46 | <0.001 |
| India VIX at the day-2 close above 13.8 | 18,946 | 46.3% | 48.4% | +0.10% | -2.39 | <0.001 |
| India VIX at or below 13.8 | 16,733 | 49.0% | 49.7% | -0.00% | -2.42 | <0.001 |

| Index | Sessions | Count | Next day down | Mean next day | p (vs all sessions) |
|---|---:|---:|---:|---:|---:|
| Nifty 50 | all sessions | 2,659 | 46.0% | +0.04% | - |
| Nifty 50 | after two down days | 605 | 50.6% | -0.00% | 0.025 |
| Nifty 50 | after two up days | 819 | 41.1% | +0.09% | 0.006 |
| Nifty Bank | all sessions | 2,659 | 46.5% | +0.05% | - |
| Nifty Bank | after two down days | 601 | 47.9% | +0.02% | 0.487 |
| Nifty Bank | after two up days | 789 | 44.4% | +0.15% | 0.239 |

## Every quarter

| Quarter | Two-down triples | Day 3 down | Other stocks down | Difference, same day (pts) | Mean day 3 | Others mean day 3 |
|---|---:|---:|---:|---:|---:|---:|
| 2021 Q2 | 550 | 43.5% | 51.6% | -5.11 | +0.31% | +0.11% |
| 2021 Q3 | 1,084 | 43.2% | 46.6% | -5.83 | +0.19% | +0.23% |
| 2021 Q4 | 1,551 | 49.4% | 49.5% | +0.25 | -0.10% | +0.03% |
| 2022 Q1 | 1,387 | 48.1% | 47.4% | -3.33 | -0.02% | +0.10% |
| 2022 Q2 | 1,648 | 52.1% | 52.8% | -1.07 | -0.14% | -0.14% |
| 2022 Q3 | 1,467 | 46.3% | 46.7% | -0.59 | +0.12% | +0.17% |
| 2022 Q4 | 1,503 | 47.2% | 50.1% | -1.45 | +0.05% | +0.07% |
| 2023 Q1 | 1,713 | 52.0% | 52.1% | -2.30 | -0.15% | -0.02% |
| 2023 Q2 | 957 | 36.1% | 41.9% | -4.03 | +0.40% | +0.26% |
| 2023 Q3 | 1,348 | 40.7% | 48.8% | -4.86 | +0.31% | +0.12% |
| 2023 Q4 | 1,076 | 42.3% | 43.7% | -4.47 | +0.23% | +0.27% |
| 2024 Q1 | 1,450 | 44.1% | 49.6% | +0.30 | +0.20% | +0.06% |
| 2024 Q2 | 1,241 | 47.4% | 43.8% | -1.39 | +0.15% | +0.31% |
| 2024 Q3 | 1,315 | 45.1% | 46.5% | +0.52 | +0.16% | +0.16% |
| 2024 Q4 | 1,799 | 56.0% | 50.7% | +0.33 | -0.29% | -0.06% |
| 2025 Q1 | 2,102 | 50.0% | 50.7% | -5.09 | -0.07% | -0.01% |
| 2025 Q2 | 1,614 | 39.8% | 46.2% | -2.15 | +0.36% | +0.16% |
| 2025 Q3 | 2,420 | 53.5% | 50.2% | +0.76 | -0.08% | +0.04% |
| 2025 Q4 | 2,268 | 45.4% | 50.4% | -4.54 | +0.14% | +0.05% |
| 2026 Q1 | 2,339 | 51.8% | 55.4% | -1.72 | -0.25% | -0.34% |
| 2026 Q2 | 1,987 | 43.9% | 46.2% | -0.73 | +0.38% | +0.27% |
| 2026 Q3 | 2,860 | 49.4% | 56.0% | -7.16 | +0.02% | -0.15% |

## By sector

| Sector | Two-down triples | Day 3 down | Other stocks down | Difference, same day (pts) | Mean day 3 | Others mean day 3 |
|---|---:|---:|---:|---:|---:|---:|
| Automobile and Auto Components | 2,733 | 48.0% | 49.2% | -3.09 | +0.02% | +0.08% |
| Capital Goods | 2,538 | 46.4% | 48.2% | -2.10 | +0.09% | +0.07% |
| Chemicals | 1,065 | 48.2% | 50.1% | -1.20 | +0.04% | +0.05% |
| Construction | 401 | 48.9% | 51.4% | -6.60 | +0.05% | +0.07% |
| Construction Materials | 935 | 47.2% | 48.9% | -7.02 | -0.00% | +0.06% |
| Consumer Durables | 1,658 | 48.3% | 49.8% | -2.59 | +0.00% | +0.06% |
| Consumer Services | 1,266 | 48.7% | 50.0% | -4.05 | +0.04% | +0.07% |
| Fast Moving Consumer Goods | 2,472 | 46.9% | 50.3% | -5.09 | +0.04% | +0.03% |
| Financial Services | 9,240 | 48.2% | 49.0% | -0.59 | +0.07% | +0.07% |
| Healthcare | 3,078 | 45.8% | 49.3% | -4.40 | +0.12% | +0.06% |
| Information Technology | 2,601 | 49.9% | 49.8% | -2.05 | -0.01% | +0.03% |
| Metals & Mining | 2,030 | 45.4% | 47.6% | -2.98 | +0.03% | +0.13% |
| Oil Gas & Consumable Fuels | 1,863 | 45.7% | 47.6% | -6.36 | +0.08% | +0.09% |
| Power | 1,003 | 46.7% | 48.7% | +0.68 | +0.10% | +0.11% |
| Realty | 897 | 49.5% | 47.1% | +1.66 | +0.01% | +0.11% |
| Services | 1,012 | 48.1% | 48.7% | -5.64 | -0.02% | +0.11% |
| Telecommunication | 694 | 47.3% | 50.3% | -6.17 | +0.12% | +0.06% |
| Textiles | 193 | 45.1% | 51.9% | - | +0.12% | +0.02% |

## As a trade

| Trade (MAIN, after 0.17% a round trip) | Trades | Avg net | Winning trades | Without the 5 best | First half | Second half |
|---|---:|---:|---:|---:|---:|---:|
| Buy at the day-2 close, sell at the day-3 close | 35,679 | -0.12% | 47.4% | -0.12% | -0.08% | -0.15% |
| Short at the day-2 close, cover at the day-3 close | 35,679 | -0.22% | 43.0% | -0.23% | -0.26% | -0.19% |
| Buy, hold 2 sessions (day 3 + day 4) | 35,547 | -0.04% | 49.2% | -0.05% | +0.04% | -0.12% |
| Buy, hold 5 sessions (day 3 .. day 7) | 35,373 | +0.17% | 51.6% | +0.17% | +0.37% | -0.01% |
| Reference: buy every eligible stock-day, sell next close | 151,513 | -0.10% | 45.9% | - | - | - |

| Half | Day 3 dates | Two-down triples | Day 3 down | Share down vs peers (pts) | p (t) | p (bootstrap) | Mean day 3 vs peers (pts) | p |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| First half | 2021-04-27 .. 2024-06-27 | 16,945 | 46.3% | -2.52 | <0.001 | <0.001 | +0.04 | 0.023 |
| Second half | 2024-06-28 .. 2026-09-30 | 18,734 | 48.7% | -2.24 | 0.001 | 0.002 | +0.04 | 0.182 |

## Checks and caveats

- **Day 4.** The day-3 bounce does not reverse on day 4: share down vs peers +0.3 points (p 0.53), day 3 + day 4
  together +0.05 points (p 0.035). So it is a real small move, not a quirk of the closing price.
- **Raw versus peers.** Measured raw, part of any "bounce" is the market rising after a weak day. The same-day peer
  comparison removes that. This matters most for big falls.
- **Long history.** On all days since 2016, the third day after two down days was down 48.9% of the time, against 49.5%
  on all days. Same-day peers give -1.8 points. Results and dividends before 2021 are not excluded in that sample.
- **Independent rebuild.** A second build from the raw data, sharing only the plan, matched: 47.6% down after two down days, -2.4 points against same-day peers, both halves significant, the index and the trade results. The only difference was two results with no F&O flag recorded (Reliance and Vedanta, both always in F&O). Counting them as in F&O, as here, the counts are identical.
- **Survivorship.** The stocks are today's F&O list. Stocks that fell out of F&O, often after long declines, are missing,
  and that could understate how often weak stocks kept falling.
- **What a trader can use.** A third down day is not more likely after two down days, so two red days alone are no
  reason to short or to buy. The odds stay close to 50/50, and the small edge is a quarter of one trade's costs.

## Conclusion

After two down days, an F&O stock's third day is close to a coin flip, with a small tilt towards a bounce: about 2
points less likely to fall than other stocks the same day. That tilt is steady across quarters and both halves, but it
is worth only about +0.04% on the day, far below the 0.17% cost of a round trip. Neither buying the dip nor shorting the
continuation makes money on it. Bigger falls bounce more often mainly because the whole market tends to bounce after a
sell-off. Only the index shows the opposite, a slightly higher chance of a third down day, with no average move to
trade.

Files: scripts in `pattern_tests/two_down_days/` and outputs in
[results/two_down_days/](../results/two_down_days/):

- PLAN.txt and PLAN.sha256: the plan written before any result.
- build_days.py: every three-day stretch with the exclusion flags.
- run_tests.py: the tests.
- skeptic/checks.py: day 4, market vs stock, the index, and quarters.
- PLAN_NO_WEEKEND.txt and no_weekend.py: the version away from weekends and holidays.

The scripts read `LAB_ROOT` (the scratch data folder), `TA_BUILD` (the adjusted prices) and `CA_DIR` (NSE corporate
actions, downloaded). The file of stretches (days.csv.gz, 23 MB) is not committed; build_days.py rebuilds it.
