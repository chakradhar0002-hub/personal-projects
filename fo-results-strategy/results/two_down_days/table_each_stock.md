# Two and three down days, stock by stock

PLAN_STOCKS.txt. F&O stocks while in F&O, ordinary days (no result within 5 sessions, no split/bonus/ex-date), May 2021 .. Sep 2026. "Normal": the stock's own share of down days over all its windows in that sample. "vs peers": the stock's next-day share down minus that of the other stocks (without the signal) on the same dates, in percentage points; negative = a bounce. Stocks with fewer than 30 signal windows are listed but not tested. BH / Holm: corrected for the number of stocks tested.

## Summary

| Signal | Version | Stocks tested | Lean to keep falling / to bounce | Pass BH vs peers | Pass BH vs own normal | Confirmed in both halves | Spread of stock results vs chance | First half vs second half (rank corr.) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Two down days, then day 3 | All ordinary days | 196 | 61 / 135 | 0 | 0 | 0 | 1.14 vs 1.08 (p 0.267) | +0.22 (136 stocks, p 0.011) |
| Two down days, then day 3 | Away from weekends and holidays (Mon..Thu, Friday open) | 112 | 40 / 72 | 1 | 0 | 0 | 1.06 vs 1.02 (p 0.373) | -0.11 (76 stocks, p 0.343) |
| Three down days, then day 4 | All ordinary days | 179 | 62 / 117 | 0 | 0 | 0 | 1.14 vs 1.05 (p 0.211) | +0.16 (134 stocks, p 0.071) |
| Three down days, then day 4 | No holiday nearby (weekends allowed) | 152 | 57 / 95 | 0 | 0 | 0 | 1.05 vs 1.02 (p 0.387) | +0.07 (133 stocks, p 0.413) |

Spread of stock results vs chance: the variance of the per-stock z-scores against 1,000 shuffles of the signal among stocks on each date (if stocks had their own patterns, the spread would be wider than chance). First half vs second half: whether the stocks that bounced most in the first half also did in the second (Spearman, permutation p).

## Stocks that pass a correction in any version

| Signal | Version | Stock | Times | Next day down | Normal | vs peers (pts) | BH q vs peers | BH q vs own | First half / second half | Confirmed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Two down days, then day 3 | Away from weekends and holidays (Mon..Thu, Friday open) | CIPLA | 38 | 26.3% | 48.5% | -26.7 | 0.004 | 0.953 | -14.2 / -36.9 | no |

## Every stock (all ordinary days; * = passes BH vs peers or vs its own normal)

| Stock | Sector | 2D: times | Day 3 down | Normal | vs peers (pts) | Day 3 down, away from weekends (times) | 3D: times | Day 4 down | Normal | vs peers (pts) | Day 4 down, no holiday nearby (times) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 360ONE | Financial Services | 68 | 44.1% | 53.4% | -5.7 | 14.3% (7) | 30 | 30.0% | 52.8% | -14.5 | 33.3% (18) |
| ABB | Capital Goods | 160 | 46.2% | 44.5% | -2.9 | 50.0% (26) | 71 | 45.1% | 44.6% | -5.5 | 45.1% (51) |
| ABCAPITAL | Financial Services | 187 | 42.2% | 47.1% | -9.0 | 29.0% (31) | 77 | 40.3% | 47.2% | -10.7 | 39.3% (56) |
| ADANIENSOL | Power | 68 | 44.1% | 46.4% | -5.7 | 46.2% (13) | 29 | 41.4% | 46.1% | -9.6 | 50.0% (24) |
| ADANIENT | Metals & Mining | 253 | 51.4% | 48.4% | +1.6 | 42.1% (38) | 125 | 51.2% | 48.5% | +4.0 | 53.9% (89) |
| ADANIGREEN | Power | 85 | 48.2% | 48.6% | -1.6 | 71.4% (14) | 40 | 45.0% | 49.4% | -3.7 | 50.0% (34) |
| ADANIPORTS | Services | 255 | 48.2% | 49.3% | -3.8 | 51.2% (43) | 119 | 49.6% | 49.7% | -3.6 | 53.3% (90) |
| ADANIPOWER | Power | 28 | 46.4% | 56.5% | -4.2 | 100.0% (3) | 13 | 53.8% | 57.8% | +0.5 | 55.6% (9) |
| ALKEM | Healthcare | 182 | 42.9% | 47.8% | -5.8 | 42.3% (26) | 78 | 37.2% | 48.3% | -10.4 | 36.5% (52) |
| AMBER | Consumer Durables | 59 | 50.8% | 50.4% | -0.8 | 66.7% (12) | 30 | 46.7% | 50.7% | -0.3 | 50.0% (24) |
| AMBUJACEM | Construction Materials | 239 | 48.1% | 47.5% | -3.2 | 40.9% (44) | 113 | 45.1% | 47.2% | -6.8 | 44.4% (81) |
| ANGELONE | Financial Services | 101 | 54.5% | 52.8% | +3.0 | 46.2% (13) | 55 | 56.4% | 52.1% | +6.2 | 55.6% (36) |
| APLAPOLLO | Capital Goods | 69 | 37.7% | 46.0% | -10.1 | 20.0% (10) | 26 | 38.5% | 45.5% | -11.6 | 21.4% (14) |
| APOLLOHOSP | Healthcare | 237 | 49.8% | 50.0% | +0.4 | 45.7% (35) | 116 | 46.6% | 50.3% | -1.9 | 48.7% (78) |
| ASHOKLEY | Capital Goods | 231 | 45.9% | 47.4% | -3.7 | 52.8% (36) | 105 | 41.0% | 47.5% | -6.1 | 41.3% (75) |
| ASIANPAINT | Consumer Durables | 231 | 46.3% | 48.9% | -1.7 | 42.4% (33) | 100 | 41.0% | 49.5% | -5.4 | 41.1% (73) |
| ASTRAL | Capital Goods | 218 | 54.6% | 50.4% | +6.5 | 40.6% (32) | 114 | 50.0% | 50.2% | +3.1 | 52.1% (73) |
| AUBANK | Financial Services | 243 | 46.9% | 48.7% | -1.6 | 48.8% (41) | 113 | 38.1% | 48.4% | -9.8 | 40.5% (84) |
| AUROPHARMA | Healthcare | 276 | 51.1% | 52.2% | +0.6 | 51.2% (43) | 137 | 48.9% | 52.5% | -1.1 | 48.5% (99) |
| AXISBANK | Financial Services | 231 | 47.2% | 46.9% | -3.9 | 36.1% (36) | 107 | 40.2% | 46.6% | -8.0 | 34.6% (78) |
| BAJAJ-AUTO | Automobile and Auto Components | 236 | 48.7% | 46.8% | -1.7 | 53.3% (30) | 112 | 50.0% | 47.3% | +1.2 | 45.5% (77) |
| BAJAJFINSV | Financial Services | 244 | 51.2% | 49.8% | +0.9 | 61.5% (39) | 119 | 45.4% | 49.9% | -1.4 | 42.7% (89) |
| BAJAJHLDNG | Financial Services | 32 | 46.9% | 52.5% | -7.4 | 50.0% (4) | 15 | 46.7% | 52.2% | -5.6 | 30.0% (10) |
| BAJFINANCE | Financial Services | 234 | 48.7% | 48.4% | -1.4 | 61.5% (39) | 108 | 48.1% | 48.2% | -1.1 | 48.8% (80) |
| BANDHANBNK | Financial Services | 254 | 49.6% | 49.2% | -0.9 | 48.9% (45) | 124 | 52.4% | 48.9% | +2.4 | 53.4% (88) |
| BANKBARODA | Financial Services | 216 | 50.9% | 47.5% | +0.9 | 50.0% (26) | 108 | 50.0% | 47.6% | +0.5 | 46.6% (73) |
| BANKINDIA | Financial Services | 64 | 51.6% | 46.5% | -5.3 | 42.9% (7) | 31 | 54.8% | 47.6% | -3.7 | 60.0% (20) |
| BDL | Capital Goods | 64 | 46.9% | 50.0% | -5.4 | 55.6% (9) | 30 | 43.3% | 49.3% | -6.3 | 45.8% (24) |
| BEL | Capital Goods | 202 | 43.1% | 47.4% | -7.2 | 50.0% (32) | 83 | 36.1% | 47.1% | -11.6 | 33.9% (62) |
| BHARATFORG | Automobile and Auto Components | 223 | 46.6% | 46.5% | -3.5 | 51.2% (41) | 103 | 46.6% | 46.3% | -3.0 | 46.8% (79) |
| BHARTIARTL | Telecommunication | 219 | 42.9% | 47.6% | -9.7 | 46.4% (28) | 91 | 47.3% | 47.5% | -7.8 | 50.0% (56) |
| BHEL | Capital Goods | 194 | 37.6% | 44.0% | -9.4 | 50.0% (24) | 71 | 35.2% | 44.2% | -11.6 | 37.7% (53) |
| BIOCON | Healthcare | 254 | 47.2% | 49.4% | -1.5 | 48.4% (31) | 119 | 41.2% | 49.7% | -4.7 | 40.4% (89) |
| BLUESTARCO | Consumer Durables | 55 | 49.1% | 50.0% | +0.3 | 60.0% (5) | 26 | 53.8% | 50.0% | +11.8 | 53.3% (15) |
| BOSCHLTD | Automobile and Auto Components | 217 | 48.4% | 47.8% | -2.7 | 50.0% (22) | 102 | 40.2% | 47.6% | -7.5 | 39.4% (66) |
| BPCL | Oil Gas & Consumable Fuels | 247 | 49.8% | 48.4% | +1.2 | 51.5% (33) | 121 | 49.6% | 48.4% | +0.1 | 50.0% (98) |
| BRITANNIA | Fast Moving Consumer Goods | 231 | 46.8% | 46.9% | -4.1 | 36.1% (36) | 104 | 47.1% | 47.2% | -3.7 | 45.0% (80) |
| BSE | Financial Services | 87 | 59.8% | 49.7% | +4.5 | 40.0% (10) | 50 | 50.0% | 49.5% | +1.2 | 47.1% (34) |
| CAMS | Financial Services | 83 | 47.0% | 51.0% | -4.2 | 46.2% (13) | 39 | 48.7% | 51.3% | -3.0 | 50.0% (24) |
| CANBK | Financial Services | 248 | 49.2% | 48.4% | -1.2 | 38.9% (36) | 120 | 50.8% | 48.6% | -0.9 | 47.1% (87) |
| CDSL | Financial Services | 83 | 53.0% | 50.3% | +1.2 | 50.0% (14) | 44 | 43.2% | 50.3% | -7.1 | 38.5% (26) |
| CGPOWER | Capital Goods | 78 | 53.8% | 51.7% | +2.2 | 40.0% (10) | 40 | 55.0% | 51.7% | +4.0 | 55.6% (27) |
| CHOLAFIN | Financial Services | 242 | 44.6% | 48.8% | -5.0 | 40.5% (37) | 103 | 45.6% | 49.2% | -4.9 | 41.7% (72) |
| CIPLA | Healthcare | 222 | 43.7% | 49.5% | -5.1 | 26.3% (38) | 93 | 45.2% | 50.0% | -3.5 | 42.9% (70) |
| COALINDIA | Oil Gas & Consumable Fuels | 209 | 41.6% | 46.7% | -6.9 | 42.4% (33) | 86 | 43.0% | 46.8% | -9.8 | 43.3% (67) |
| COCHINSHIP | Capital Goods | 20 | 40.0% | 55.7% | -13.0 | 0.0% (4) | 8 | 50.0% | 53.7% | +0.6 | 50.0% (4) |
| COFORGE | Information Technology | 240 | 50.0% | 48.6% | +1.9 | 42.1% (38) | 113 | 50.4% | 49.0% | +3.9 | 53.5% (86) |
| COLPAL | Fast Moving Consumer Goods | 254 | 45.7% | 49.9% | -4.0 | 50.0% (34) | 115 | 47.8% | 49.6% | -0.7 | 50.5% (91) |
| CONCOR | Services | 233 | 49.8% | 49.4% | -2.6 | 33.3% (36) | 113 | 46.9% | 49.3% | -7.0 | 46.8% (79) |
| CROMPTON | Consumer Durables | 234 | 51.7% | 54.4% | +1.4 | 55.9% (34) | 120 | 51.7% | 54.3% | +1.0 | 50.0% (86) |
| CUMMINSIND | Capital Goods | 207 | 46.9% | 46.1% | -2.0 | 46.2% (26) | 95 | 41.1% | 46.3% | -6.8 | 42.0% (69) |
| DABUR | Fast Moving Consumer Goods | 248 | 48.8% | 49.3% | -0.8 | 39.5% (43) | 116 | 47.4% | 49.1% | -1.4 | 42.7% (82) |
| DELHIVERY | Services | 75 | 50.7% | 47.9% | -0.8 | 63.6% (11) | 38 | 50.0% | 47.4% | -3.2 | 55.6% (27) |
| DIVISLAB | Healthcare | 226 | 48.7% | 47.9% | -0.2 | 42.1% (38) | 109 | 51.4% | 47.8% | +1.5 | 45.5% (66) |
| DIXON | Consumer Durables | 225 | 48.4% | 47.9% | -0.6 | 34.5% (29) | 105 | 53.3% | 48.1% | +5.4 | 54.1% (74) |
| DLF | Realty | 234 | 52.1% | 47.9% | +0.4 | 50.0% (38) | 118 | 50.0% | 48.3% | -1.7 | 47.6% (84) |
| DMART | Consumer Services | 77 | 48.1% | 49.0% | -3.1 | 45.5% (11) | 35 | 51.4% | 49.1% | +0.8 | 50.0% (26) |
| DRREDDY | Healthcare | 237 | 46.0% | 47.5% | -3.3 | 40.0% (40) | 104 | 50.0% | 47.8% | -0.8 | 51.3% (76) |
| EICHERMOT | Automobile and Auto Components | 258 | 46.1% | 49.8% | -3.0 | 48.8% (41) | 117 | 49.6% | 49.9% | -0.3 | 50.6% (89) |
| ETERNAL | Consumer Services | 83 | 57.8% | 48.8% | +3.3 | 53.3% (15) | 47 | 61.7% | 48.6% | +9.9 | 60.0% (35) |
| FEDERALBNK | Financial Services | 214 | 41.6% | 46.6% | -4.8 | 41.2% (34) | 89 | 43.8% | 46.6% | -2.7 | 47.1% (68) |
| FORCEMOT | Automobile and Auto Components | 26 | 34.6% | 58.0% | -14.1 | 0.0% (3) | 8 | 37.5% | 59.0% | -16.8 | 33.3% (6) |
| FORTIS | Healthcare | 44 | 52.3% | 50.7% | -0.8 | 25.0% (4) | 21 | 38.1% | 51.7% | -11.4 | 41.7% (12) |
| GAIL | Oil Gas & Consumable Fuels | 222 | 45.5% | 47.4% | -5.9 | 43.8% (32) | 99 | 43.4% | 47.4% | -8.6 | 41.4% (70) |
| GLENMARK | Healthcare | 212 | 43.9% | 45.4% | -5.7 | 32.3% (31) | 93 | 35.5% | 45.7% | -13.4 | 33.3% (57) |
| GMRAIRPORT | Services | 218 | 46.8% | 47.6% | -5.2 | 51.4% (35) | 98 | 45.9% | 47.7% | -3.7 | 47.8% (69) |
| GODFRYPHLP | Fast Moving Consumer Goods | 29 | 58.6% | 62.9% | +2.0 | 25.0% (4) | 17 | 52.9% | 61.2% | -4.5 | 54.5% (11) |
| GODREJCP | Fast Moving Consumer Goods | 241 | 45.2% | 49.7% | -4.2 | 33.3% (30) | 108 | 38.9% | 49.6% | -7.7 | 28.9% (76) |
| GODREJPROP | Realty | 228 | 50.9% | 46.0% | +1.3 | 54.5% (33) | 111 | 51.4% | 46.0% | +1.7 | 50.0% (78) |
| GRASIM | Construction Materials | 221 | 45.7% | 47.1% | -4.4 | 35.9% (39) | 97 | 48.5% | 46.8% | -4.0 | 44.6% (65) |
| GVT&D | Capital Goods | 8 | 50.0% | 57.1% | -10.5 | 50.0% (2) | 3 | 66.7% | 57.7% | +14.9 | 100.0% (2) |
| HAL | Capital Goods | 227 | 45.8% | 48.0% | -4.4 | 39.6% (48) | 102 | 40.2% | 47.3% | -7.8 | 39.5% (81) |
| HAVELLS | Consumer Durables | 238 | 45.4% | 47.8% | -4.3 | 48.6% (35) | 105 | 46.7% | 47.9% | -2.9 | 45.1% (82) |
| HCLTECH | Information Technology | 242 | 47.9% | 48.4% | -0.3 | 60.0% (30) | 114 | 49.1% | 48.5% | +1.1 | 46.9% (81) |
| HDFCAMC | Financial Services | 250 | 48.4% | 49.1% | -1.0 | 48.4% (31) | 116 | 47.4% | 49.1% | -1.4 | 47.4% (95) |
| HDFCBANK | Financial Services | 254 | 49.6% | 48.9% | -0.2 | 51.1% (47) | 122 | 45.9% | 48.6% | -4.2 | 42.6% (94) |
| HDFCLIFE | Financial Services | 267 | 51.7% | 50.9% | +1.9 | 46.2% (39) | 134 | 50.7% | 50.8% | +4.2 | 47.9% (94) |
| HEROMOTOCO | Automobile and Auto Components | 252 | 50.8% | 49.0% | +2.5 | 50.0% (42) | 127 | 49.6% | 48.9% | +4.9 | 47.4% (97) |
| HINDALCO | Metals & Mining | 201 | 41.8% | 45.0% | -6.4 | 46.4% (28) | 81 | 45.7% | 44.7% | -3.1 | 48.5% (66) |
| HINDPETRO | Oil Gas & Consumable Fuels | 220 | 47.7% | 46.0% | -1.0 | 46.2% (26) | 105 | 46.7% | 46.0% | -1.4 | 48.8% (82) |
| HINDUNILVR | Fast Moving Consumer Goods | 252 | 48.8% | 51.2% | -0.0 | 53.3% (45) | 119 | 49.6% | 51.0% | +3.5 | 47.9% (94) |
| HINDZINC | Metals & Mining | 68 | 48.5% | 51.1% | +1.4 | 70.0% (10) | 30 | 56.7% | 50.9% | +8.9 | 61.5% (26) |
| HYUNDAI | Automobile and Auto Components | 21 | 47.6% | 50.0% | -3.7 | 40.0% (5) | 9 | 55.6% | 50.0% | -3.9 | 55.6% (9) |
| ICICIBANK | Financial Services | 257 | 43.2% | 49.1% | -8.1 | 47.7% (44) | 109 | 43.1% | 48.8% | -4.8 | 41.7% (72) |
| ICICIGI | Financial Services | 245 | 47.3% | 50.9% | -1.3 | 41.5% (41) | 114 | 51.8% | 51.4% | +4.3 | 54.2% (72) |
| ICICIPRULI | Financial Services | 276 | 50.7% | 49.2% | +0.5 | 47.6% (42) | 137 | 54.0% | 49.4% | +3.1 | 54.5% (101) |
| IDEA | Telecommunication | 234 | 50.4% | 52.3% | +2.2 | 37.8% (37) | 116 | 47.4% | 52.2% | +1.4 | 44.3% (88) |
| IDFCFIRSTB | Financial Services | 257 | 48.2% | 49.1% | -1.2 | 39.5% (38) | 121 | 47.9% | 49.3% | -1.6 | 48.5% (97) |
| IEX | Financial Services | 223 | 46.2% | 49.0% | -2.7 | 41.2% (34) | 100 | 51.0% | 49.2% | +3.7 | 50.6% (77) |
| INDHOTEL | Consumer Services | 214 | 49.1% | 46.5% | -2.1 | 56.7% (30) | 103 | 46.6% | 46.2% | -5.4 | 42.1% (76) |
| INDIANB | Financial Services | 76 | 47.4% | 49.4% | -4.7 | 54.5% (11) | 35 | 51.4% | 49.2% | +1.4 | 50.0% (18) |
| INDIGO | Services | 231 | 46.8% | 48.0% | -4.9 | 51.3% (39) | 105 | 52.4% | 48.2% | -0.5 | 54.3% (81) |
| INDUSINDBK | Financial Services | 240 | 44.6% | 48.5% | -6.3 | 44.2% (43) | 104 | 42.3% | 48.4% | -7.3 | 40.7% (81) |
| INDUSTOWER | Telecommunication | 241 | 48.1% | 49.2% | -2.3 | 38.6% (44) | 114 | 46.5% | 49.5% | -4.8 | 43.0% (79) |
| INFY | Information Technology | 249 | 49.4% | 50.0% | +0.8 | 48.4% (31) | 119 | 51.3% | 50.4% | +3.5 | 54.8% (84) |
| INOXWIND | Capital Goods | 62 | 46.8% | 53.0% | -4.0 | 62.5% (8) | 27 | 44.4% | 52.9% | -6.8 | 38.9% (18) |
| IOC | Oil Gas & Consumable Fuels | 232 | 47.0% | 46.4% | -2.4 | 59.4% (32) | 108 | 50.0% | 46.4% | -1.6 | 52.9% (85) |
| IREDA | Financial Services | 81 | 51.9% | 54.3% | +1.7 | 61.5% (13) | 42 | 52.4% | 54.4% | +1.6 | 52.8% (36) |
| IRFC | Financial Services | 104 | 56.7% | 55.0% | +5.3 | 64.3% (14) | 58 | 58.6% | 55.3% | +4.2 | 60.5% (38) |
| ITC | Fast Moving Consumer Goods | 242 | 46.7% | 49.8% | -3.6 | 35.6% (45) | 109 | 47.7% | 50.0% | -3.6 | 46.0% (87) |
| JINDALSTEL | Metals & Mining | 217 | 43.8% | 46.7% | -6.1 | 47.2% (36) | 93 | 37.6% | 46.5% | -9.3 | 38.0% (71) |
| JIOFIN | Financial Services | 89 | 52.8% | 50.9% | +0.8 | 54.5% (11) | 45 | 57.8% | 50.2% | +4.9 | 57.1% (28) |
| JSWENERGY | Power | 86 | 53.5% | 51.1% | +0.4 | 87.5% (16) | 46 | 47.8% | 51.3% | -0.2 | 51.4% (35) |
| JSWSTEEL | Metals & Mining | 220 | 45.9% | 48.6% | -3.6 | 36.1% (36) | 98 | 41.8% | 49.2% | -5.7 | 40.8% (71) |
| JUBLFOOD | Consumer Services | 253 | 45.5% | 51.5% | -3.1 | 54.5% (33) | 113 | 38.9% | 51.5% | -9.5 | 39.0% (82) |
| KALYANKJIL | Consumer Durables | 77 | 55.8% | 49.8% | +2.9 | 50.0% (12) | 42 | 54.8% | 50.0% | +0.8 | 46.7% (30) |
| KAYNES | Capital Goods | 66 | 54.5% | 52.9% | +0.8 | 80.0% (5) | 36 | 44.4% | 52.3% | -9.2 | 42.3% (26) |
| KEI | Capital Goods | 77 | 49.4% | 48.9% | -2.8 | 37.5% (16) | 36 | 38.9% | 48.8% | -7.9 | 39.3% (28) |
| KFINTECH | Financial Services | 64 | 53.1% | 52.7% | -0.2 | 42.9% (14) | 34 | 50.0% | 51.4% | -4.4 | 47.8% (23) |
| KOTAKBANK | Financial Services | 245 | 44.9% | 49.2% | -7.1 | 40.9% (44) | 107 | 40.2% | 49.1% | -10.1 | 40.2% (82) |
| KPITTECH | Information Technology | 98 | 54.1% | 55.7% | +4.2 | 57.1% (14) | 52 | 51.9% | 55.8% | +7.4 | 55.0% (40) |
| LAURUSLABS | Healthcare | 199 | 44.2% | 47.1% | -3.4 | 46.4% (28) | 86 | 44.2% | 47.0% | -2.2 | 45.8% (72) |
| LICHSGFIN | Financial Services | 225 | 50.7% | 47.9% | -0.7 | 44.1% (34) | 109 | 60.6% | 48.2% | +3.5 | 60.3% (78) |
| LICI | Financial Services | 87 | 51.7% | 53.4% | -1.2 | 70.0% (10) | 45 | 48.9% | 54.0% | -4.9 | 46.4% (28) |
| LODHA | Realty | 85 | 51.8% | 50.5% | +0.6 | 61.5% (13) | 43 | 51.2% | 49.7% | +4.5 | 50.0% (32) |
| LT | Construction | 241 | 44.8% | 48.7% | -2.6 | 48.7% (39) | 107 | 47.7% | 48.9% | +1.6 | 45.6% (68) |
| LTF | Financial Services | 231 | 45.5% | 47.2% | -4.3 | 44.8% (29) | 102 | 46.1% | 46.8% | -0.8 | 44.3% (70) |
| LTM | Information Technology | 229 | 49.3% | 48.8% | +1.8 | 45.5% (33) | 109 | 49.5% | 48.7% | +2.7 | 50.0% (80) |
| LUPIN | Healthcare | 231 | 44.2% | 48.1% | -6.4 | 35.5% (31) | 99 | 45.5% | 48.0% | -6.7 | 34.4% (61) |
| M&M | Automobile and Auto Components | 229 | 42.8% | 47.9% | -9.6 | 31.2% (32) | 97 | 39.2% | 47.7% | -10.2 | 31.9% (69) |
| MANAPPURAM | Financial Services | 216 | 48.6% | 48.9% | -3.1 | 61.3% (31) | 102 | 51.0% | 48.7% | +1.4 | 47.0% (83) |
| MANKIND | Healthcare | 63 | 46.0% | 50.7% | -5.5 | 33.3% (6) | 28 | 42.9% | 50.5% | -0.6 | 58.8% (17) |
| MARICO | Fast Moving Consumer Goods | 249 | 44.2% | 49.7% | -6.3 | 44.1% (34) | 108 | 44.4% | 49.4% | -6.9 | 37.0% (73) |
| MARUTI | Automobile and Auto Components | 277 | 49.1% | 50.4% | +0.2 | 59.5% (42) | 135 | 45.2% | 50.3% | -4.3 | 42.6% (101) |
| MAXHEALTH | Healthcare | 70 | 45.7% | 48.9% | -6.0 | 30.0% (10) | 29 | 48.3% | 48.4% | +3.9 | 35.7% (14) |
| MAZDOCK | Capital Goods | 60 | 45.0% | 51.6% | -3.5 | 12.5% (8) | 27 | 37.0% | 52.3% | -7.0 | 20.0% (15) |
| MFSL | Financial Services | 197 | 47.2% | 50.7% | +1.3 | 32.4% (37) | 90 | 42.2% | 51.0% | -3.2 | 45.3% (64) |
| MOTHERSON | Automobile and Auto Components | 259 | 49.4% | 48.9% | +0.0 | 42.9% (42) | 125 | 49.6% | 49.0% | +1.2 | 48.9% (90) |
| MOTILALOFS | Financial Services | 15 | 26.7% | 42.9% | -16.7 | 50.0% (2) | 3 | 0.0% | 43.9% | -51.2 | 0.0% (1) |
| MPHASIS | Information Technology | 242 | 48.8% | 48.9% | +3.3 | 46.3% (41) | 115 | 47.0% | 48.6% | +3.4 | 46.7% (90) |
| MUTHOOTFIN | Financial Services | 230 | 45.2% | 48.2% | -2.0 | 46.9% (32) | 102 | 48.0% | 48.0% | -0.3 | 49.3% (75) |
| NAM-INDIA | Financial Services | 85 | 51.8% | 50.0% | +1.5 | 30.0% (10) | 43 | 48.8% | 50.3% | -1.6 | 51.4% (37) |
| NATIONALUM | Metals & Mining | 191 | 41.9% | 45.1% | -6.6 | 44.8% (29) | 78 | 41.0% | 45.4% | -6.7 | 38.6% (57) |
| NAUKRI | Consumer Services | 246 | 45.5% | 50.2% | -3.5 | 48.4% (31) | 108 | 48.1% | 50.5% | +1.8 | 45.7% (81) |
| NBCC | Construction | 87 | 52.9% | 53.1% | +1.7 | 66.7% (15) | 46 | 56.5% | 53.0% | +3.3 | 53.3% (30) |
| NESTLEIND | Fast Moving Consumer Goods | 123 | 48.8% | 49.9% | -2.0 | 55.6% (18) | 58 | 34.5% | 49.8% | -16.2 | 38.1% (42) |
| NHPC | Power | 79 | 39.2% | 52.1% | -7.1 | 33.3% (15) | 30 | 46.7% | 51.6% | -0.6 | 28.6% (14) |
| NMDC | Metals & Mining | 209 | 44.0% | 46.4% | -5.3 | 40.0% (30) | 89 | 47.2% | 47.1% | +0.3 | 43.3% (60) |
| NTPC | Power | 195 | 44.1% | 46.3% | -3.4 | 44.4% (27) | 81 | 42.0% | 46.4% | -5.2 | 40.7% (54) |
| NYKAA | Consumer Services | 79 | 51.9% | 47.8% | -2.3 | 81.8% (11) | 41 | 51.2% | 47.2% | -1.9 | 48.3% (29) |
| OBEROIRLTY | Realty | 214 | 47.7% | 47.8% | -1.9 | 56.7% (30) | 102 | 49.0% | 48.0% | -1.6 | 45.1% (71) |
| OFSS | Information Technology | 216 | 50.9% | 50.8% | +3.0 | 44.4% (27) | 108 | 51.9% | 51.0% | +5.2 | 49.4% (83) |
| OIL | Oil Gas & Consumable Fuels | 67 | 41.8% | 46.3% | -8.9 | 0.0% (8) | 25 | 44.0% | 46.3% | -2.2 | 33.3% (12) |
| ONGC | Oil Gas & Consumable Fuels | 203 | 46.3% | 46.9% | -1.6 | 48.4% (31) | 90 | 48.9% | 46.6% | +1.2 | 47.6% (63) |
| PAGEIND | Textiles | 193 | 45.1% | 50.1% | -3.9 | 28.1% (32) | 86 | 36.0% | 49.9% | -8.4 | 34.9% (63) |
| PATANJALI | Fast Moving Consumer Goods | 59 | 49.2% | 49.8% | -4.7 | 44.4% (9) | 27 | 51.9% | 50.8% | -5.0 | 50.0% (18) |
| PAYTM | Financial Services | 78 | 56.4% | 49.5% | +2.6 | 50.0% (14) | 43 | 51.2% | 49.7% | -1.3 | 51.5% (33) |
| PERSISTENT | Information Technology | 222 | 51.4% | 48.8% | +3.5 | 62.2% (37) | 111 | 54.1% | 49.0% | +7.1 | 55.4% (92) |
| PETRONET | Oil Gas & Consumable Fuels | 231 | 42.4% | 47.9% | -5.5 | 33.3% (30) | 96 | 46.9% | 47.6% | -2.6 | 43.7% (71) |
| PFC | Financial Services | 237 | 49.8% | 49.3% | +0.4 | 43.2% (44) | 115 | 49.6% | 49.5% | -1.5 | 51.1% (88) |
| PGEL | Consumer Durables | 64 | 54.7% | 54.9% | +3.3 | 66.7% (9) | 33 | 63.6% | 55.3% | +9.5 | 76.5% (17) |
| PHOENIXLTD | Realty | 62 | 45.2% | 46.8% | -7.3 | 62.5% (8) | 26 | 34.6% | 47.5% | -13.9 | 35.0% (20) |
| PIDILITIND | Chemicals | 264 | 50.0% | 50.3% | +1.1 | 41.7% (36) | 131 | 53.4% | 50.3% | +3.3 | 50.0% (88) |
| PIIND | Chemicals | 237 | 49.8% | 51.4% | +1.6 | 37.9% (29) | 115 | 57.4% | 51.6% | +8.4 | 49.3% (67) |
| PNB | Financial Services | 200 | 47.5% | 46.1% | -4.5 | 28.1% (32) | 90 | 53.3% | 46.1% | -1.0 | 52.4% (63) |
| PNBHOUSING | Financial Services | 64 | 45.3% | 48.2% | -2.3 | 50.0% (8) | 29 | 44.8% | 48.9% | +0.1 | 42.9% (21) |
| POLICYBZR | Financial Services | 88 | 55.7% | 52.2% | +4.7 | 70.0% (10) | 48 | 66.7% | 52.1% | +18.4 | 60.0% (35) |
| POLYCAB | Capital Goods | 191 | 40.8% | 44.7% | -7.6 | 40.9% (22) | 75 | 45.3% | 45.0% | -4.2 | 50.0% (60) |
| POWERGRID | Power | 211 | 44.1% | 48.4% | -5.3 | 39.4% (33) | 89 | 43.8% | 48.4% | -6.3 | 42.9% (63) |
| POWERINDIA | Capital Goods | 42 | 52.4% | 48.8% | +0.0 | 60.0% (10) | 21 | 42.9% | 48.5% | -12.1 | 43.8% (16) |
| PREMIERENE | Capital Goods | 28 | 39.3% | 47.0% | -13.1 | 28.6% (7) | 11 | 27.3% | 46.6% | -17.5 | 33.3% (9) |
| PRESTIGE | Realty | 74 | 43.2% | 49.4% | -6.5 | 43.8% (16) | 30 | 53.3% | 49.8% | +3.8 | 59.3% (27) |
| RADICO | Fast Moving Consumer Goods | 10 | 30.0% | 57.9% | -25.6 | 0.0% (1) | 3 | 66.7% | 59.5% | +2.3 | 66.7% (3) |
| RBLBANK | Financial Services | 240 | 50.0% | 47.7% | +0.4 | 51.4% (37) | 117 | 47.0% | 47.8% | -2.8 | 44.3% (88) |
| RECLTD | Financial Services | 225 | 48.9% | 47.3% | +0.1 | 41.7% (36) | 107 | 50.5% | 47.1% | +1.5 | 51.9% (79) |
| RELIANCE | Oil Gas & Consumable Fuels | 232 | 46.1% | 48.1% | -3.5 | 55.3% (38) | 102 | 48.0% | 47.7% | -1.5 | 46.1% (76) |
| RVNL | Construction | 73 | 57.5% | 56.9% | +4.5 | 45.5% (11) | 42 | 57.1% | 56.3% | +3.4 | 58.6% (29) |
| SAIL | Metals & Mining | 212 | 46.2% | 47.9% | -3.1 | 44.1% (34) | 94 | 45.7% | 47.7% | -4.7 | 44.8% (67) |
| SBICARD | Financial Services | 235 | 51.1% | 50.1% | -0.4 | 42.3% (26) | 117 | 47.0% | 50.1% | -0.6 | 42.3% (78) |
| SBILIFE | Financial Services | 238 | 45.8% | 48.9% | -5.0 | 35.7% (28) | 108 | 51.9% | 48.7% | +3.1 | 45.5% (77) |
| SBIN | Financial Services | 215 | 46.0% | 47.1% | -6.2 | 44.7% (38) | 99 | 47.5% | 47.1% | -2.6 | 44.2% (77) |
| SHREECEM | Construction Materials | 227 | 46.3% | 50.0% | -4.2 | 43.3% (30) | 102 | 51.0% | 49.6% | -0.4 | 47.2% (72) |
| SHRIRAMFIN | Financial Services | 241 | 46.5% | 48.1% | -3.4 | 47.6% (42) | 109 | 45.0% | 48.0% | -4.9 | 44.0% (91) |
| SIEMENS | Capital Goods | 129 | 37.2% | 45.9% | -12.8 | 31.6% (19) | 47 | 42.6% | 46.0% | -8.7 | 42.4% (33) |
| SOLARINDS | Chemicals | 73 | 46.6% | 47.5% | +0.8 | 50.0% (8) | 34 | 38.2% | 46.9% | -4.5 | 34.8% (23) |
| SONACOMS | Automobile and Auto Components | 80 | 46.2% | 51.1% | -4.8 | 27.3% (11) | 37 | 51.4% | 50.8% | +1.4 | 51.7% (29) |
| SRF | Chemicals | 246 | 46.3% | 48.0% | -2.5 | 35.3% (34) | 113 | 45.1% | 48.0% | -2.9 | 44.4% (90) |
| SUNPHARMA | Healthcare | 213 | 45.1% | 47.5% | -5.2 | 54.3% (35) | 94 | 41.5% | 47.2% | -11.2 | 43.5% (69) |
| SUPREMEIND | Capital Goods | 96 | 58.3% | 52.6% | +8.6 | 64.3% (14) | 56 | 58.9% | 52.2% | +7.6 | 62.2% (45) |
| SUZLON | Capital Goods | 72 | 58.3% | 58.0% | +7.8 | 50.0% (16) | 41 | 53.7% | 57.5% | +4.4 | 51.9% (27) |
| SWIGGY | Consumer Services | 43 | 58.1% | 58.5% | +4.3 | 50.0% (4) | 22 | 59.1% | 58.3% | +4.0 | 60.0% (15) |
| TATACONSUM | Fast Moving Consumer Goods | 227 | 45.4% | 49.3% | -4.7 | 54.5% (33) | 100 | 45.0% | 48.9% | -5.6 | 44.2% (77) |
| TATAELXSI | Information Technology | 101 | 55.4% | 53.8% | +4.8 | 28.6% (14) | 54 | 51.9% | 54.4% | +3.3 | 48.6% (35) |
| TATAPOWER | Power | 251 | 51.0% | 47.8% | +1.2 | 48.7% (39) | 125 | 55.2% | 47.5% | +3.9 | 57.5% (80) |
| TATASTEEL | Metals & Mining | 241 | 43.6% | 48.1% | -7.1 | 44.2% (43) | 102 | 39.2% | 48.0% | -9.2 | 38.3% (81) |
| TCS | Information Technology | 272 | 52.2% | 51.4% | +2.2 | 59.5% (37) | 138 | 52.2% | 51.4% | +2.4 | 53.6% (110) |
| TECHM | Information Technology | 237 | 46.4% | 50.3% | -0.8 | 35.0% (40) | 104 | 51.0% | 50.3% | +4.3 | 53.2% (77) |
| TIINDIA | Automobile and Auto Components | 97 | 52.6% | 54.8% | +1.2 | 46.7% (15) | 49 | 49.0% | 55.1% | -0.1 | 46.7% (30) |
| TITAN | Consumer Durables | 247 | 48.2% | 48.4% | -2.5 | 48.6% (37) | 114 | 50.0% | 48.7% | -2.4 | 47.2% (89) |
| TMPV | Automobile and Auto Components | 257 | 51.4% | 50.7% | +0.5 | 53.5% (43) | 128 | 51.6% | 51.1% | +1.6 | 54.0% (100) |
| TORNTPHARM | Healthcare | 180 | 42.2% | 47.2% | -4.6 | 45.8% (24) | 74 | 39.2% | 47.2% | -6.9 | 41.4% (58) |
| TRENT | Consumer Services | 248 | 48.8% | 50.0% | -0.3 | 54.1% (37) | 120 | 50.0% | 50.3% | +0.3 | 49.5% (101) |
| TVSMOTOR | Automobile and Auto Components | 243 | 44.9% | 47.1% | -6.0 | 42.4% (33) | 108 | 46.3% | 47.2% | -7.3 | 48.1% (79) |
| ULTRACEMCO | Construction Materials | 248 | 48.4% | 49.6% | -2.9 | 48.8% (43) | 116 | 49.1% | 49.4% | -2.6 | 44.8% (87) |
| UNIONBANK | Financial Services | 60 | 45.0% | 46.8% | -8.9 | 50.0% (6) | 26 | 53.8% | 47.5% | -1.1 | 41.7% (12) |
| UNITDSPR | Fast Moving Consumer Goods | 228 | 48.7% | 47.7% | -1.8 | 35.7% (28) | 107 | 52.3% | 47.7% | -0.4 | 45.3% (64) |
| UNOMINDA | Automobile and Auto Components | 58 | 51.7% | 51.8% | -3.9 | 40.0% (10) | 30 | 46.7% | 51.2% | -8.4 | 43.8% (16) |
| UPL | Chemicals | 245 | 46.9% | 49.7% | -0.4 | 54.3% (46) | 111 | 45.0% | 49.3% | -1.2 | 44.9% (89) |
| VBL | Fast Moving Consumer Goods | 79 | 46.8% | 51.9% | -8.0 | 45.5% (11) | 37 | 43.2% | 51.2% | -10.0 | 41.4% (29) |
| VEDL | Metals & Mining | 218 | 47.7% | 46.4% | -1.0 | 61.1% (36) | 100 | 44.0% | 46.6% | -2.2 | 47.0% (83) |
| VMM | Consumer Services | 23 | 56.5% | 57.9% | -2.5 | 50.0% (4) | 12 | 41.7% | 59.5% | -15.8 | 41.7% (12) |
| VOLTAS | Consumer Durables | 228 | 44.3% | 48.2% | -5.2 | 40.6% (32) | 94 | 42.6% | 48.2% | -4.8 | 41.8% (67) |
| WAAREEENER | Capital Goods | 37 | 54.1% | 53.8% | +5.8 | 71.4% (7) | 18 | 50.0% | 53.9% | -0.8 | 53.8% (13) |
| WIPRO | Information Technology | 252 | 48.8% | 49.1% | +0.6 | 50.0% (32) | 119 | 45.4% | 48.9% | -0.7 | 44.8% (87) |
| YESBANK | Financial Services | 74 | 45.9% | 49.1% | -7.6 | 55.6% (9) | 33 | 42.4% | 48.9% | -9.2 | 41.7% (24) |
| ZYDUSLIFE | Healthcare | 232 | 42.7% | 49.3% | -6.0 | 45.7% (35) | 94 | 42.6% | 49.4% | -4.5 | 40.6% (69) |
