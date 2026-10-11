| split of the 85 lag-rule trades | prediction | n IN / OUT | IN avg (net) | OUT avg (net) | IN - OUT | IN first14 n, avg | IN last8 n, avg | OUT first14 avg | OUT last8 avg | better side w/o best5 net | perm p (2-sided) | Holm p | separates |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A01 LATE: results date > 7 days later than the same quarter last year | IN worse | 7 / 67 | +1.36 (+1.19) | +2.47 (+2.30) | -1.11 | 4, +1.93 | 3, +0.60 | +1.96 | +3.08 | +1.39 | 0.5996 | 1.000 | no |
| A02 EARLY: results date > 7 days earlier than last year | IN better | 16 / 58 | +1.23 (+1.06) | +2.68 (+2.51) | -1.45 | 7, +2.69 | 9, +0.11 | +1.80 | +3.85 | -1.39 | 0.3338 | 1.000 | no |
| A03 NOTICE_SHORT: intimation lead time >= 7 days shorter than the stock's habit | IN worse | 5 / 74 | +8.00 (+7.83) | +1.53 (+1.36) | +6.47 | 3, +5.22 | 2, +12.17 | +1.23 | +1.97 | +0.63 | 0.0049 | 0.069 | no |
| A04 NOTICE_LONG: lead time >= 7 days longer than habit | IN better | 6 / 73 | +2.83 (+2.66) | +1.87 (+1.70) | +0.96 | 5, +3.01 | 1, +1.93 | +1.30 | +2.63 | -1.62 | 0.6518 | 1.000 | no |
| A05 NOTICE_MIN: lead time <= 7 days (near the legal minimum) | IN worse | 18 / 61 | +1.61 (+1.44) | +2.03 (+1.86) | -0.42 | 8, +0.28 | 10, +2.68 | +1.73 | +2.58 | +0.91 | 0.7588 | 1.000 | no |
| A06 NEWS_HI: 30-day news flow >= 1.5x the stock's norm | IN better | 22 / 59 | +2.27 (+2.10) | +2.17 (+2.00) | +0.10 | 14, -0.16 | 8, +6.53 | +2.53 | +1.73 | -0.19 | 0.9430 | 1.000 | no |
| A07 NEWS_LO: 30-day news flow <= 0.5x norm (silence) | IN worse | 9 / 72 | +0.22 (+0.05) | +2.45 (+2.28) | -2.23 | 4, +2.52 | 5, -1.62 | +1.65 | +3.63 | +1.42 | 0.2269 | 1.000 | no |
| A08 PRESS: press release(s) in the 30 days before the cutoff | IN better | 31 / 54 | +1.58 (+1.41) | +2.45 (+2.28) | -0.87 | 21, +2.11 | 10, +0.46 | +1.33 | +3.85 | +0.10 | 0.4777 | 1.000 | no |
| A09 ORDER: order win(s) in the 30 days before | IN better | 3 / 82 | -1.34 (-1.51) | +2.26 (+2.09) | -3.60 | 0, n/a | 3, -1.34 | +1.65 | +3.26 | n/a | not tested (<5) | n/a | no |
| A10 ACQ: acquisition announcement(s) in the 30 days before | IN worse | 5 / 80 | +2.86 (+2.69) | +2.09 (+1.92) | +0.77 | 3, +3.83 | 2, +1.40 | +1.51 | +2.95 | +1.09 | 0.7578 | 1.000 | no |
| A11 NOCALL: no earnings call / analyst meet announced in the 21 days before | IN worse | 27 / 58 | +2.88 (+2.71) | +1.79 (+1.62) | +1.09 | 18, +2.25 | 9, +4.14 | +1.33 | +2.39 | +0.62 | 0.3897 | 1.000 | no |
| A12 BIZ_UP: business update(s) in 45 days, market reaction > 0 | IN better | 3 / 82 | +6.83 (+6.66) | +1.96 (+1.79) | +4.87 | 2, +7.45 | 1, +5.58 | +1.41 | +2.77 | n/a | not tested (<5) | n/a | no |
| A13 BIZ_DOWN: business update(s), market reaction < 0 | IN worse | 6 / 79 | +4.96 (+4.79) | +1.92 (+1.75) | +3.04 | 3, +3.21 | 3, +6.70 | +1.55 | +2.48 | +0.90 | 0.1816 | 1.000 | no |
| A14 PROM_BUY: promoter acquisition (SAST Reg 29) in the 90 days before | IN better | 7 / 78 | +2.45 (+2.28) | +2.10 (+1.93) | +0.35 | 3, +2.88 | 4, +2.12 | +1.57 | +2.95 | -2.12 | 0.8677 | 1.000 | no |
| A15 PROM_SELL: promoter sale in the 90 days before | IN worse | 5 / 80 | +2.87 (+2.70) | +2.09 (+1.92) | +0.78 | 2, +2.17 | 3, +3.33 | +1.63 | +2.81 | +1.09 | 0.7508 | 1.000 | no |
| A16 HOLD_BUY: large non-promoter holder buying in 90 days | IN better | 6 / 79 | +5.49 (+5.32) | +1.88 (+1.71) | +3.61 | 5, +6.05 | 1, +2.65 | +1.17 | +2.86 | -0.34 | 0.1136 | 1.000 | no |
| A17 HOLD_SELL: large non-promoter holder selling in 90 days | IN worse | 4 / 81 | +4.91 (+4.74) | +2.00 (+1.83) | +2.91 | 4, +4.91 | 0, n/a | +1.37 | +2.86 | +1.11 | not tested (<5) | n/a | no |
