# Tradable versions

Item H of the plan: anything CONFIRMED (familywise significant in the first 14 quarters and same sign, p < 0.05 in the last 8) or with a familywise p below 0.05 on all quarters, traded as buy (or short) at the cutoff close, sell at the Day+1 close, after 0.17% round-trip costs.

| Signal (test) | Confirmed | Familywise p | Side | Trades | Avg gross | Avg net | Win rate | Quarters positive | Without 5 best | First 14 q | Last 8 q | Luck p | Overlap lag 10% + volume | Overlap last-4 top tenth | Other trades: net |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Top fifth of average of the last 8 (D-mean_h8) | no | 0.047 | long | 452 | +0.56% | +0.39% | 53% | 9 of 14 | +0.19% | +1.12% (161) | -0.01% (291) | 0.040 | 10 | 170 | -0.07% (279) |
| Top fifth of best of the last 4 (D-best4) | no | 0.019 | long | 567 | +0.47% | +0.30% | 51% | 9 of 18 | +0.14% | +0.56% (269) | +0.07% (298) | 0.038 | 17 | 220 | -0.16% (339) |

0 of 2 confirmed. Avg gross / net: per trade, % (net = gross - 0.17). Without 5 best: net average after dropping the 5 best trades. First 14 q / last 8 q: net, with trade counts. Luck p: against random picks of the same size in each quarter (5,000). Overlap: trades that are also lag 10% + volume rule trades (results/lag10_volume/trades.csv) or in the last-4 top tenth of PAST_PERFORMANCE.md; other trades: the net average of the trades in neither.

### Per quarter (net of 0.17%, trades in brackets; q0 = Jan-Mar 2021 results ... q21 = Apr-Jun 2026)

| Signal | q0 | q1 | q2 | q3 | q4 | q5 | q6 | q7 | q8 | q9 | q10 | q11 | q12 | q13 | q14 | q15 | q16 | q17 | q18 | q19 | q20 | q21 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| D-mean_h8 | - | - | - | - | - | - | - | - | +0.77 (27) | -0.29 (27) | +1.21 (26) | +1.56 (27) | +1.63 (27) | +1.85 (27) | -2.56 (27) | -0.39 (34) | +1.35 (35) | -0.29 (38) | +0.45 (38) | +0.96 (39) | -0.96 (40) | +0.66 (40) |
| D-best4 | - | - | - | - | -2.04 (27) | +0.26 (27) | -0.91 (27) | -2.16 (27) | +2.35 (27) | -0.48 (27) | +1.38 (26) | +4.09 (27) | +1.06 (27) | +2.03 (27) | -1.30 (27) | -0.76 (35) | +2.56 (36) | -0.65 (39) | +0.58 (39) | +1.09 (40) | -1.02 (41) | -0.18 (41) |

## Size of the move (item E)

7 magnitude tests passed (E-raw-lag1, E-raw-lag2, E-raw-lag4, E-raw-lag5, E-raw-lag7, E-part-lag7, E-raw-lag8). They say how BIG the next results move tends to be, not which way, so there is no buy/sell version in cash. Using it needs option prices (a straddle on stocks whose results moves have been big), which this study does not have; see table_magnitude.md for the sizes by fifth.
