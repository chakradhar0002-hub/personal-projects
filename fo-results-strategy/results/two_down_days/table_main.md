# After two down days: is day 3 down?

Ordinary days only (see PLAN.txt): MAIN = F&O stocks while in F&O, May 2021 .. Sep 2026, no result within 5 sessions, no split/bonus/demerger or NSE ex-date on the three days; ALL21 = the same, any F&O status; LONG = 2016 .. 2026, only split/bonus/demerger days removed (results and dividends before 2021 not known).

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

Shares in %; returns in %, gross. Day 3 vs Nifty: day-3 return minus Nifty 50's, percentage points.

## Against other stocks on the same day

| Sample | Outcome | Two-down triples | Dates | Two-down minus same-day peers (each date equal) | Weighted by two-down count | p (t over dates) | p (month bootstrap) |
|---|---:|---:|---:|---:|---:|---:|---:|
| MAIN | share down | 35,678 | 1,328 | -2.40 | -2.27 | <0.001 | <0.001 |
| MAIN | mean day-3 return | 35,678 | 1,328 | +0.04 | +0.04 | 0.026 | 0.015 |
| ALL21 | share down | 49,829 | 1,343 | -1.93 | -2.12 | <0.001 | <0.001 |
| ALL21 | mean day-3 return | 49,829 | 1,343 | +0.04 | +0.04 | 0.021 | 0.016 |
| LONG | share down | 123,899 | 2,688 | -1.77 | -2.14 | <0.001 | <0.001 |
| LONG | mean day-3 return | 123,899 | 2,688 | +0.03 | +0.05 | 0.007 | 0.004 |

Share down in percentage points, return in percentage points. Each day-3 date gives one difference (two-down stocks minus every other eligible stock that day); the mean is over dates. p: t-test over dates, and a 5,000-draw bootstrap of calendar months (two-sided).
