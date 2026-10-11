Discovery qn 0-13 (1,807 results; base: avg three_day +0.12%, base short net -0.29, base hedged short net -0.12; criterion 3 needs short net >= +0.21). Short net = -three_day - 0.17; hedged = -(three_day - Nifty) - 0.19.

| id | rule | n | avg ret | avg vs Nifty | short net | short w/o 5 biggest falls | hedged short | hedged w/o 5 | qtrs short+ / with trades | H1 qn0-6 n, short | H2 qn7-13 n, short | luck p | crit 1/2/3 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|---:|---|
| S01 | lag 10% quiet volume (KNOWN group, contaminated) | 64 | -0.12 | -0.52 | -0.05 | -0.76 | +0.33 | -0.40 | 7/13 | 39, +0.45 | 25, -0.83 | 0.457 | y/n/n |
| S02 | lag 10%, volume < 0.8 | 36 | -0.86 | -1.23 | +0.69 | -0.49 | +1.04 | -0.04 | 7/9 | 24, +1.14 | 12, -0.21 | 0.138 | n/n/y |
| S03 | lag 15%, volume < 1.0 | 13 | +1.88 | +1.56 | -2.05 | -5.74 | -1.75 | -5.07 | 1/7 | 12, -2.02 | 1, -2.41 | 0.938 | n/n/n |
| S04 | lag 15%, volume < 0.8 | 8 | +2.54 | +1.94 | -2.71 | -8.88 | -2.13 | -7.11 | 1/6 | 7, -2.75 | 1, -2.41 | 0.931 | n/n/n |
| S05 | lag 20%, volume < 1.0 | 2 | -0.59 | +1.77 | +0.42 |  | -1.96 |  | 1/1 | 2, +0.42 | 0,  | 0.492 | n/n/y |
| S06 | lag 20%, volume < 0.8 | 1 | -8.42 | -3.96 | +8.25 |  | +3.77 |  | 1/1 | 1, +8.25 | 0,  | 0.069 | n/n/y |
| S07 | long unwinding 5 sessions (to i_cut-1): price down, futures OI down > 10% | 54 | +0.14 | +0.12 | -0.31 | -1.23 | -0.31 | -1.24 | 5/13 | 28, -1.16 | 26, +0.60 | 0.600 | y/n/n |
| S08 | short build-up 5 sessions: price down, futures OI up > 10% | 211 | +0.35 | +0.24 | -0.52 | -0.86 | -0.43 | -0.77 | 3/14 | 115, -0.91 | 96, -0.06 | 0.850 | y/n/n |
| S09 | put IV run-up: ATM put IV up > 8.5 vol points over 20 sessions (about top quintile) | 296 | -0.07 | -0.25 | -0.10 | -0.35 | +0.06 | -0.18 | 5/14 | 152, +0.69 | 144, -0.93 | 0.342 | y/n/n |
| S10 | high put-call ratio by OI (about top quintile) | 364 | +0.50 | +0.25 | -0.67 | -0.86 | -0.44 | -0.62 | 4/14 | 109, -0.83 | 255, -0.60 | 0.718 | y/n/n |
| S11 | futures at an (annualised) discount to spot and the discount widening on the day | 234 | -0.24 | -0.58 | +0.07 | -0.25 | +0.39 | +0.09 | 6/14 | 140, +0.07 | 94, +0.06 | 0.200 | y/y/n |
| S12 | puts priced above calls: call-put IV spread below -3.1 (about bottom quintile) | 310 | +0.37 | -0.01 | -0.54 | -0.83 | -0.18 | -0.45 | 4/14 | 166, -0.66 | 144, -0.40 | 0.870 | y/n/n |
| S13 | overbought RSI(14) > 70 with falling volume | 71 | -0.06 | -0.58 | -0.11 | -0.71 | +0.39 | -0.21 | 5/10 | 28, +0.35 | 43, -0.41 | 0.210 | y/n/n |
| S14 | overbought RSI(14) > 70 | 158 | +0.13 | -0.03 | -0.30 | -0.69 | -0.16 | -0.53 | 8/14 | 58, +0.94 | 100, -1.02 | 0.300 | y/n/n |
| S15 | stretched: close > 10% above its 50-day average | 236 | +0.05 | -0.15 | -0.22 | -0.57 | -0.04 | -0.37 | 7/14 | 104, +0.84 | 132, -1.06 | 0.252 | y/n/n |
| S16 | stretched: close > 30% above its 200-day average | 198 | +0.40 | +0.40 | -0.57 | -0.94 | -0.59 | -0.94 | 6/14 | 76, +0.11 | 122, -0.99 | 0.620 | y/n/n |
| S17 | stretched above the 50-day average on falling volume | 110 | +0.34 | -0.10 | -0.51 | -1.07 | -0.09 | -0.63 | 4/12 | 46, +0.24 | 64, -1.06 | 0.542 | y/n/n |
| S18 | big run-up: last 5 sessions beat Nifty by > 5 points | 155 | +0.01 | +0.14 | -0.18 | -0.68 | -0.33 | -0.81 | 7/14 | 73, +1.37 | 82, -1.56 | 0.394 | y/n/n |
| S19 | 5-session run-up on falling volume | 49 | +0.88 | +0.83 | -1.05 | -1.98 | -1.02 | -1.99 | 6/13 | 24, +0.84 | 25, -2.87 | 0.845 | y/n/n |
| S20 | habitually falls into results: all of the last 4 results windows negative | 100 | -0.41 | -0.87 | +0.24 | -0.41 | +0.68 | +0.02 | 5/10 | 33, +1.06 | 67, -0.17 | 0.082 | y/n/y |
| S21 | habitually falls: mean of the last 4 results windows below -2% (about bottom quintile) | 260 | +0.14 | -0.30 | -0.31 | -0.58 | +0.11 | -0.17 | 4/10 | 95, -0.06 | 165, -0.46 | 0.342 | y/n/n |
| S22 | habitually reacts badly: mean reaction vs Nifty of the last 4 results below -2% | 215 | -0.34 | -0.61 | +0.17 | -0.14 | +0.42 | +0.10 | 7/10 | 80, +0.80 | 135, -0.19 | 0.033 | y/n/n |
| S23 | last results were a loser (reaction vs Nifty < -4%) | 221 | -0.23 | -0.40 | +0.06 | -0.30 | +0.21 | -0.14 | 8/13 | 109, +0.37 | 112, -0.24 | 0.190 | y/n/n |
| S24 | late reporter: results date > 7 days later (vs quarter end) than the same quarter last year | 104 | -0.67 | -0.93 | +0.50 | -0.11 | +0.74 | +0.12 | 6/11 | 35, +1.62 | 69, -0.07 | 0.034 | y/n/y |
| S25 | news silence: substantive news in 30 days at most half the stock's own norm | 207 | +0.72 | +0.55 | -0.89 | -1.23 | -0.74 | -1.06 | 3/13 | 83, -0.26 | 124, -1.31 | 0.979 | y/n/n |
| S26 | no press release in 30 days and no earnings call announced in 21 days | 486 | +0.26 | +0.15 | -0.43 | -0.60 | -0.34 | -0.50 | 3/14 | 292, -0.17 | 194, -0.81 | 0.872 | y/n/n |
| S27 | board-meeting date intimated >= 7 days later than the stock's habit | 75 | -0.02 | -0.27 | -0.15 | -0.70 | +0.08 | -0.38 | 7/14 | 32, -0.15 | 43, -0.14 | 0.322 | y/n/n |
| S28 | sector index fell > 5% over the last 21 sessions | 163 | +0.24 | -0.40 | -0.41 | -0.79 | +0.21 | -0.17 | 7/13 | 100, -0.57 | 63, -0.14 | 0.899 | y/n/n |
| S29 | sector index fell > 3% over the last 5 sessions | 203 | +0.53 | +0.22 | -0.70 | -1.06 | -0.41 | -0.73 | 5/13 | 104, -0.78 | 99, -0.62 | 0.974 | y/n/n |
| S30 | weak fundamentals: last reported quarter's profit down > 20% YoY | 242 | -0.09 | -0.31 | -0.08 | -0.32 | +0.12 | -0.10 | 6/14 | 100, -0.05 | 142, -0.10 | 0.244 | y/n/n |
| S31 | profit down YoY in each of the last 2 reported quarters | 184 | +0.05 | -0.33 | -0.22 | -0.56 | +0.14 | -0.20 | 5/13 | 72, -0.54 | 112, -0.02 | 0.327 | y/n/n |
| S32 | high debt non-financial (balance sheets exist only from qn 7) | 70 | +1.01 | +1.02 | -1.18 | -1.79 | -1.21 | -1.77 | 1/7 | 0,  | 70, -1.18 | 0.886 | y/n/n |
| S33 | a loss in any of the last 4 reported quarters | 228 | +0.31 | +0.02 | -0.48 | -0.76 | -0.21 | -0.49 | 5/14 | 131, -0.83 | 97, -0.00 | 0.700 | y/n/n |
| S34 | lag-quiet + sector falling | 17 | -0.08 | -0.75 | -0.09 | -1.97 | +0.56 | -1.33 | 4/6 | 12, -0.49 | 5, +0.86 | 0.572 | n/n/n |
| S35 | lag-quiet + last quarter's profit down | 18 | +2.30 | +1.14 | -2.47 | -4.68 | -1.33 | -3.49 | 1/8 | 7, -2.25 | 11, -2.61 | 0.975 | n/n/n |
| S36 | lag-quiet + habitually falls into results | 27 | +1.38 | +0.88 | -1.55 | -2.80 | -1.07 | -2.28 | 2/8 | 10, -1.37 | 17, -1.67 | 0.916 | n/n/n |
| S37 | lag-quiet + long unwinding | 0 | | | | | | | | | | | n/n/n |
| S38 | lag-quiet + delivery % below its 60-day norm | 26 | +0.47 | -0.11 | -0.64 | -1.99 | -0.08 | -1.43 | 5/10 | 15, +0.47 | 11, -2.15 | 0.694 | n/n/n |
| S39 | stretched + habitually falls into results | 83 | -0.30 | -0.63 | +0.13 | -0.51 | +0.44 | -0.18 | 4/8 | 25, +0.67 | 58, -0.10 | 0.084 | y/n/n |
| S40 | 5-session run-up + habitually falls into results | 54 | +0.07 | -0.22 | -0.24 | -1.16 | +0.03 | -0.93 | 4/10 | 18, +0.09 | 36, -0.41 | 0.426 | y/n/n |
