| test | dir | signal (at cutoff close, delivery to cutoff-1) | n | avg gross | net | vs all F&O (excess) | q+ / q | first14 n, net, excess | last8 n, net, excess | w/o best5 net | luck p | Holm p | maxT p | placebo days n, excess | DiD | placebo p | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A01 | L | 5-day delivery % above its 60-day average (ACC > 0) | 1641 | +0.05 | -0.12 | -0.01 | 11/22 | 969, -0.05, -0.01 | 672, -0.21, -0.01 | -0.17 | 0.5411 | 1.000 | 1.000 | 65645, -0.01 | -0.00 | 0.5191 | NO (halves,Holm,placebo,w/o best 5) |
| A02 | L | ACC top quintile of the quarter | 684 | +0.16 | -0.01 | +0.13 | 11/22 | 380, +0.11, +0.14 | 304, -0.18, +0.10 | -0.12 | 0.2350 | 1.000 | 1.000 | 25015, +0.07 | +0.06 | 0.3077 | NO (halves,Holm,placebo,w/o best 5) |
| A03 | S | ACC bottom quintile (delivery drying up), short | 534 | +0.14 | -0.03 | +0.16 | 10/22 | 295, +0.13, +0.41 | 239, -0.22, -0.15 | -0.21 | 0.2175 | 1.000 | 1.000 | 20720, +0.04 | +0.07 | 0.3007 | NO (halves,Holm,placebo,w/o best 5) |
| A04 | L | delivery qty 5/60 ratio >= 1.5 | 224 | +0.34 | +0.17 | +0.31 | 10/22 | 141, +0.31, +0.46 | 83, -0.06, +0.06 | -0.23 | 0.1745 | 1.000 | 1.000 | 11751, +0.08 | +0.39 | 0.0533 | NO (halves,Holm,w/o best 5) |
| A05 | L | delivery qty 5/60 ratio top quintile | 456 | +0.23 | +0.06 | +0.18 | 13/22 | 265, +0.31, +0.37 | 191, -0.29, -0.08 | -0.12 | 0.2082 | 1.000 | 1.000 | 21396, +0.04 | +0.21 | 0.0975 | NO (halves,Holm,w/o best 5) |
| A06 | L | last published day delivery % vs 60-day avg top quintile | 639 | +0.28 | +0.11 | +0.23 | 12/22 | 368, +0.13, +0.15 | 271, +0.09, +0.35 | -0.02 | 0.0996 | 1.000 | 1.000 | 24282, +0.06 | +0.17 | 0.0932 | NO (Holm,w/o best 5) |
| A07 | L | price down + delivery up (PR5 < 0, ACC > 0) | 849 | +0.12 | -0.05 | +0.17 | 11/22 | 478, +0.05, +0.20 | 371, -0.19, +0.13 | -0.16 | 0.1311 | 1.000 | 1.000 | 32258, +0.07 | +0.06 | 0.3049 | NO (halves,Holm,placebo,w/o best 5) |
| A08 | L | price up + delivery up (PR5 > 0, ACC > 0) | 792 | -0.01 | -0.18 | -0.20 | 10/22 | 491, -0.16, -0.21 | 301, -0.22, -0.18 | -0.28 | 0.9055 | 1.000 | 1.000 | 33387, -0.08 | -0.09 | 0.7875 | NO (halves,Holm,placebo,w/o best 5) |
| A09 | S | price up + delivery down (PR5 > 0, ACC < 0), short | 932 | +0.06 | -0.11 | +0.16 | 9/22 | 505, -0.04, +0.31 | 427, -0.19, -0.03 | -0.20 | 0.1286 | 1.000 | 1.000 | 28894, +0.05 | +0.12 | 0.1206 | NO (halves,Holm,placebo,w/o best 5) |
| A10 | L | 60-day delivery % level top quintile | 681 | +0.34 | +0.17 | +0.32 | 13/22 | 370, +0.08, +0.14 | 311, +0.28, +0.52 | +0.06 | 0.0368 | 0.958 | 0.517 | 23739, -0.01 | +0.35 | 0.0002 | WATCH (Holm) |

REPLACEMENT (separate family of 2)

| test | signal | n | avg gross | net | q+ / q | first14 net | last8 net | w/o best5 net | luck p | Holm p (2) | placebo DiD, p | overlap with 85 | IN-OUT within lag<-10 (p) | verdict vs rule +2.13 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| RA1 | lag < -10 AND delivery qty 5/60 >= 1.0 (delivery volume replaces total volume) | 89 | +1.87 | +1.70 | 16/18 | +1.14 | +2.66 | +0.95 | 0.0006 | 0.001 | +1.60, 0.0003 | 75 | +2.11 (0.0042) | WORKS, below rule |
| RA2 | lag < -10 AND ACC > 0 (rising delivery % replaces volume) | 106 | +0.21 | +0.04 | 11/20 | +0.55 | -1.09 | -0.52 | 0.2278 | 0.228 | +0.04, 0.4521 | 47 | -1.14 (0.9224) | NO |
