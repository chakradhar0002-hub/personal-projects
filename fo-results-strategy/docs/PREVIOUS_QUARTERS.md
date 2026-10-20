# Does a stock's earlier three-day results moves predict its next one?

Question: for the three-day results move (Day-1 + Result day + Day+1), look at each earlier quarter of the same stock
individually. Is there any pattern?

- Every result of a stock in F&O at the time is used as the outcome: 3,278 results in 22 seasons (Jan-Mar 2021 to
  Apr-Jun 2026 results).
- The history is the same stock's earlier results of any F&O status (4,460 results). Each earlier move is measured
  against the average result of its quarter.
- "Quarters back" (lag) means exactly that many quarters earlier. Lag 4 is the same results period a year before, and
  lag 8 two years before.
- 84 tests were written down, with their pass rule, before any result was computed (plan sha256
  `9280b51459ae1b13707a14069360ce7a55e888539dc192ef4ab34edc0ac28457`):
  - each of 8 earlier quarters on its own;
  - last quarter's three days separately;
  - up/down sequences of the last 2, 3 and 4 results;
  - streaks and alternations;
  - counts and averages of the last 4 and 8;
  - the size of the move.
- A pattern counts only if it passes the correction for its group of tests in the first 14 quarters and repeats in the
  last 8.

"Rank correlation" is measured inside each quarter and averaged over the quarters. A positive value means the stocks
that did better back then also did better now.

## Answer

**No. A stock's earlier three-day results moves do not reliably tell you the direction of its next one.**

- **Each earlier quarter on its own predicts nothing usable.**
  - All 8 lags have rank correlations between +0.001 and +0.042, and none passes the correction for testing 8.
  - **Last quarter** is +0.005 (positive in only 7 of 21 quarters). After an up the next three days averaged +0.00%, and
    after a down +0.03%. This one is measured precisely: anything beyond about ±0.05 is ruled out.
  - **The same period a year ago** (+0.037) was +0.067 in the first 14 quarters and +0.001 in the last 8: it faded.
- **Last quarter's three days separately** predict nothing either: Day-1 -0.014, Result day -0.020, Day+1 +0.015.
- **Sequences look tempting but do not pass.**
  - Up-up-up before a result made +0.76% (322 results; corrected p 0.066).
  - Down-down-down made -0.28%.
  - Four or more ups in a row made +0.85%, and four or more downs -0.53%.
  - None passes the correction. The good ones are the same handful of consistently strong stocks, and the bad ones rest on
    five stocks (Vodafone Idea, Divi's, Manappuram, Inox Wind and Asian Paints).
- **The one recurring signal is the stock's track record, which is already known.**
  - The more of its last 4 results beat the quarter, the better it did next: 0 ups -0.53%, 4 ups +0.85%.
  - The best of the last 4 and the average of the last 8 pass their own correction over all quarters (p 0.019 and 0.047).
    But they fade in the last 8 quarters, and no test passes the rule set in advance.
  - This is the past-performance finding again ([PAST_PERFORMANCE.md](PAST_PERFORMANCE.md): top tenth of the last-4
    average, 292 trades, +1.07%). Outside that top tenth these versions make about nothing (-0.03% after costs). It rests
    on a few long-running winners: Trent, REC, Cummins, BEL and Hitachi Energy India.
- **In the last two years, last quarter's winners leaned to lose next time.** The correlation was negative in all of the
  last 8 quarters. But it comes from the cutoff date, not the stock: compared only with results on the same cutoff date,
  it shrinks to -0.03.
- **Size does carry over a little, but that is just volatility.**
  - Stocks with a big three-day move before tend to have a bigger one again (+0.03 to +0.07).
  - Allowing for the stock's ordinary volatility and its sector takes this to about +0.02. Adding beta, size and India VIX
    takes it to +0.01.
  - Option prices already include the stock's volatility, so this is no edge for straddles.
- **No trade comes out of it.** Picking the best earlier quarter or pattern using only past quarters, then trading it in
  the next quarter:
  - each earlier quarter on its own: +0.07% a trade after costs, and -0.11% in the last 8 quarters;
  - any test: -0.05%.

**Bottom line:** looking up a stock's earlier three-day results moves, one quarter at a time or as a sequence, does not
tell you which way it will go next. The only useful part is the existing track-record watch item.

## Each earlier quarter on its own

| Quarters back | Results | Rank correlation | Quarters positive | p | Corrected p | Avg 3-day after an up / a down | First 14 q / last 8 q |
|---|---:|---:|---:|---:|---:|---|---|
| 1 (last quarter) | 3,177 | +0.005 | 7 of 21 | 0.785 | 1.000 | +0.00% / +0.03% | +0.040 / -0.053 |
| 2 | 3,060 | +0.026 | 10 of 20 | 0.174 | 0.787 | +0.17% / -0.12% | +0.031 / +0.020 |
| 3 | 2,934 | +0.042 | 14 of 19 | 0.028 | 0.185 | +0.30% / -0.16% | +0.009 / +0.087 |
| 4 (same period, 1 year ago) | 2,801 | +0.037 | 12 of 18 | 0.054 | 0.360 | +0.28% / -0.07% | +0.067 / +0.001 |
| 5 | 2,669 | +0.020 | 10 of 17 | 0.306 | 0.945 | +0.11% / +0.15% | +0.018 / +0.022 |
| 6 | 2,528 | +0.008 | 8 of 16 | 0.692 | 1.000 | +0.12% / +0.07% | -0.023 / +0.038 |
| 7 | 2,387 | +0.027 | 9 of 15 | 0.187 | 0.817 | +0.18% / +0.04% | +0.030 / +0.025 |
| 8 (same period, 2 years ago) | 2,247 | +0.001 | 7 of 14 | 0.952 | 1.000 | -0.01% / +0.23% | +0.046 / -0.032 |

Corrected p: allows for having tested 8 lags (5,000 shuffles within each quarter). Avg 3-day after an up / a down: the
next three-day move when the stock beat its quarter at that lag, or did not.

## Every quarter, every lag (rank correlation)

| Results for | Lag 1 | Lag 2 | Lag 3 | Lag 4 | Lag 5 | Lag 6 | Lag 7 | Lag 8 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Apr-Jun 2021 | +0.046 | - | - | - | - | - | - | - |
| Jul-Sep 2021 | -0.059 | +0.118 | - | - | - | - | - | - |
| Oct-Dec 2021 | +0.059 | -0.042 | -0.185 | - | - | - | - | - |
| Jan-Mar 2022 | +0.137 | -0.003 | -0.004 | -0.027 | - | - | - | - |
| Apr-Jun 2022 | +0.229 | +0.271 | +0.003 | +0.057 | +0.111 | - | - | - |
| Jul-Sep 2022 | +0.052 | -0.159 | +0.039 | +0.157 | +0.008 | -0.004 | - | - |
| Oct-Dec 2022 | +0.208 | +0.103 | -0.155 | +0.000 | +0.141 | -0.074 | +0.024 | - |
| Jan-Mar 2023 | -0.105 | -0.227 | +0.110 | +0.081 | -0.056 | -0.062 | +0.090 | +0.191 |
| Apr-Jun 2023 | -0.046 | -0.058 | -0.016 | +0.143 | +0.102 | +0.047 | -0.027 | -0.193 |
| Jul-Sep 2023 | -0.034 | -0.044 | +0.063 | +0.053 | +0.021 | -0.029 | +0.044 | +0.202 |
| Oct-Dec 2023 | +0.108 | +0.169 | +0.020 | +0.206 | -0.016 | -0.120 | +0.068 | -0.027 |
| Jan-Mar 2024 | -0.039 | +0.107 | +0.053 | -0.037 | -0.112 | -0.058 | +0.031 | +0.040 |
| Apr-Jun 2024 | -0.036 | +0.133 | +0.173 | +0.032 | -0.039 | +0.118 | -0.021 | +0.060 |
| Jul-Sep 2024 | -0.032 | -0.090 | +0.042 | -0.084 | +0.064 | -0.110 | -0.010 | +0.012 |
| Oct-Dec 2024 | -0.002 | -0.079 | +0.003 | +0.036 | +0.049 | +0.151 | +0.083 | -0.164 |
| Jan-Mar 2025 | -0.062 | +0.151 | -0.032 | -0.060 | +0.048 | +0.029 | +0.089 | +0.028 |
| Apr-Jun 2025 | -0.017 | -0.051 | +0.086 | -0.008 | -0.072 | +0.088 | +0.097 | +0.029 |
| Jul-Sep 2025 | -0.038 | +0.120 | +0.135 | +0.040 | -0.031 | +0.020 | -0.065 | -0.018 |
| Oct-Dec 2025 | -0.145 | +0.115 | +0.120 | +0.063 | +0.101 | +0.042 | -0.050 | -0.051 |
| Jan-Mar 2026 | -0.029 | +0.014 | +0.141 | +0.014 | +0.019 | -0.021 | -0.010 | -0.066 |
| Apr-Jun 2026 | -0.096 | -0.025 | +0.202 | +0.007 | -0.004 | +0.104 | +0.064 | -0.029 |
| Mean | +0.005 | +0.026 | +0.042 | +0.037 | +0.020 | +0.008 | +0.027 | +0.001 |
| Quarters positive | 7 of 21 | 10 of 20 | 14 of 19 | 12 of 18 | 10 of 17 | 8 of 16 | 9 of 15 | 7 of 14 |

Each cell is one quarter's rank correlation between the stocks' moves that many quarters earlier and their move in that
quarter. There is no row, column or diagonal that stays on one side.

## Each quarter: last quarter and a year earlier

| Results for | Quarter | Results | Avg y | Lag-1 IC (n) | Lag-4 IC (n) | Up after up (n) | Up after down (n) | Avg y after up | Avg y after down |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Apr-Jun 2021 | Q1 FY22 | 117 | +0.06% | +0.046 (117) | - | 57% (44) | 53% (73) | +0.66% | -0.30% |
| Jul-Sep 2021 | Q2 FY22 | 125 | -0.84% | -0.059 (125) | - | 35% (60) | 46% (65) | -1.20% | -0.52% |
| Oct-Dec 2021 | Q3 FY22 | 132 | -0.64% | +0.059 (132) | - | 51% (61) | 42% (71) | -0.12% | -1.08% |
| Jan-Mar 2022 | Q4 FY22 | 131 | -0.83% | +0.137 (131) | -0.027 (131) | 44% (71) | 37% (60) | -0.33% | -1.42% |
| Apr-Jun 2022 | Q1 FY23 | 134 | +0.75% | +0.229 (134) | +0.057 (134) | 63% (59) | 44% (75) | +1.56% | +0.12% |
| Jul-Sep 2022 | Q2 FY23 | 133 | +0.03% | +0.052 (133) | +0.157 (133) | 49% (67) | 50% (66) | +0.39% | -0.34% |
| Oct-Dec 2022 | Q3 FY23 | 133 | -0.16% | +0.208 (133) | +0.000 (133) | 59% (56) | 34% (77) | +1.11% | -1.08% |
| Jan-Mar 2023 | Q4 FY23 | 134 | +0.61% | -0.105 (134) | +0.081 (134) | 49% (59) | 61% (75) | +0.12% | +0.99% |
| Apr-Jun 2023 | Q1 FY24 | 133 | -0.30% | -0.046 (133) | +0.143 (133) | 39% (66) | 45% (67) | -0.53% | -0.06% |
| Jul-Sep 2023 | Q2 FY24 | 132 | +0.41% | -0.034 (130) | +0.053 (131) | 54% (54) | 53% (76) | +0.27% | +0.48% |
| Oct-Dec 2023 | Q3 FY24 | 135 | +0.48% | +0.108 (135) | +0.206 (134) | 60% (60) | 47% (75) | +0.85% | +0.18% |
| Jan-Mar 2024 | Q4 FY24 | 135 | +0.88% | -0.039 (135) | -0.037 (134) | 51% (71) | 56% (64) | +0.72% | +1.05% |
| Apr-Jun 2024 | Q1 FY25 | 135 | +0.53% | -0.036 (135) | +0.032 (133) | 53% (55) | 54% (80) | +0.53% | +0.53% |
| Jul-Sep 2024 | Q2 FY25 | 134 | -1.12% | -0.032 (134) | -0.084 (134) | 41% (66) | 43% (68) | -1.23% | -1.01% |
| Oct-Dec 2024 | Q3 FY25 | 172 | -0.79% | -0.002 (172) | +0.036 (172) | 45% (78) | 46% (94) | -0.90% | -0.70% |
| Jan-Mar 2025 | Q4 FY25 | 178 | +0.96% | -0.062 (178) | -0.060 (178) | 54% (90) | 52% (88) | +0.74% | +1.18% |
| Apr-Jun 2025 | Q1 FY26 | 191 | -0.56% | -0.017 (191) | -0.008 (191) | 43% (89) | 48% (102) | -0.96% | -0.22% |
| Jul-Sep 2025 | Q2 FY26 | 191 | +0.67% | -0.038 (191) | +0.040 (191) | 55% (92) | 54% (99) | +0.47% | +0.85% |
| Oct-Dec 2025 | Q3 FY26 | 196 | +0.18% | -0.145 (196) | +0.063 (196) | 45% (91) | 47% (105) | -0.01% | +0.35% |
| Jan-Mar 2026 | Q4 FY26 | 203 | -0.31% | -0.029 (203) | +0.014 (203) | 44% (93) | 47% (110) | -0.71% | +0.03% |
| Apr-Jun 2026 | Q1 FY27 | 206 | +0.17% | -0.096 (205) | +0.007 (206) | 47% (96) | 53% (109) | -0.25% | +0.53% |

## Up/down sequences of the last 3 results

| Pattern (oldest to latest) | Results | Avg 3-day | Share up | Over the quarter average | p | Holm p | First 14 q / last 8 q |
|---|---:|---:|---:|---:|---:|---:|---|
| UUU | 322 | +0.76% | 54% | +0.70 | 0.008 | 0.066 | +0.82 / +0.58 |
| UUD | 331 | +0.13% | 47% | +0.10 | 0.695 | 1.000 | -0.27 / +0.52 |
| UDU | 335 | -0.04% | 47% | -0.05 | 0.845 | 1.000 | +0.09 / -0.17 |
| DUU | 336 | -0.33% | 46% | -0.40 | 0.139 | 0.964 | -0.31 / -0.49 |
| UDD | 373 | +0.34% | 48% | +0.23 | 0.354 | 1.000 | -0.30 / +0.78 |
| DUD | 377 | +0.18% | 53% | +0.11 | 0.638 | 1.000 | +0.27 / -0.01 |
| DDU | 380 | -0.19% | 50% | -0.23 | 0.342 | 1.000 | +0.43 / -0.90 |
| DDD | 477 | -0.28% | 46% | -0.31 | 0.138 | 0.964 | -0.44 / -0.17 |

U = beat its quarter's average result, D = did not; oldest first, so "DDU" means up last quarter after two downs.
Over the quarter average: the next move minus that quarter's average result. p: 5,000 shuffles of the patterns within each
quarter. Holm p: corrected for the 8 patterns. The 2- and 4-result tables are in
[table_sequences.md](../results/prev_quarter_patterns/table_sequences.md).

## Streaks

| Streak before this result | Results | Avg 3-day | Share up | Over the quarter average | p | Holm p | First 14 q / last 8 q |
|---|---:|---:|---:|---:|---:|---:|---|
| 4+ ups | 165 | +0.85% | 53% | +0.77 | 0.039 | 0.315 | +0.71 / +0.82 |
| 3 ups | 148 | +0.77% | 57% | +0.67 | 0.105 | 0.627 | +1.05 / +0.25 |
| 2 ups | 336 | -0.33% | 46% | -0.40 | 0.123 | 0.627 | -0.31 / -0.49 |
| 1 up | 750 | -0.15% | 48% | -0.14 | 0.213 | 0.852 | +0.26 / -0.54 |
| 1 down | 733 | +0.21% | 50% | +0.19 | 0.381 | 1.000 | +0.16 / +0.22 |
| 2 downs | 373 | +0.34% | 48% | +0.23 | 0.357 | 1.000 | -0.30 / +0.78 |
| 3 downs | 194 | +0.18% | 49% | +0.04 | 0.918 | 1.000 | -0.16 / +0.26 |
| 4+ downs | 257 | -0.53% | 44% | -0.54 | 0.069 | 0.481 | -0.63 / -0.46 |

## Track record: how many of the last 4 beat their quarter

| Ups | Results | Avg y | Share up | Avg x | x first 14 q | x last 8 q |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 257 | -0.53% | 44% | -0.54 | -0.63 (120) | -0.46 (137) |
| 1 | 756 | -0.02% | 49% | -0.13 | -0.38 (358) | +0.10 (398) |
| 2 | 1,042 | +0.09% | 49% | -0.01 | +0.06 (512) | -0.08 (530) |
| 3 | 577 | +0.28% | 50% | +0.23 | +0.55 (265) | -0.05 (312) |
| 4 | 165 | +0.85% | 53% | +0.77 | +0.71 (72) | +0.82 (93) |

| Feature | Results | Quarters | Mean IC | t | Quarters positive | p | maxT p | IC first 14 q | p | maxT p | IC last 8 q | p | Confirmed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Ups in the last 4 | 2,797 | 18 | +0.043 | +1.85 | 9 of 18 | 0.029 | 0.132 | +0.058 (10 q) | 0.037 | 0.169 | +0.024 (8 q) | 0.375 | no |
| Ups in the last 8 | 2,239 | 14 | +0.041 | +2.66 | 10 of 14 | 0.068 | 0.266 | +0.045 (6 q) | 0.215 | 0.658 | +0.037 (8 q) | 0.170 | no |
| Average h of the last 2 | 3,058 | 20 | +0.012 | +0.45 | 9 of 20 | 0.544 | 0.972 | +0.041 (12 q) | 0.110 | 0.416 | -0.032 (8 q) | 0.220 | no |
| Average h of the last 4 | 2,797 | 18 | +0.048 | +2.13 | 12 of 18 | 0.016 | 0.077 | +0.080 (10 q) | 0.006 | 0.025 | +0.007 (8 q) | 0.800 | no |
| Average h of the last 8 | 2,239 | 14 | +0.056 | +2.89 | 11 of 14 | 0.011 | 0.047 | +0.085 (6 q) | 0.018 | 0.089 | +0.034 (8 q) | 0.199 | no |
| Best of the last 4 | 2,797 | 18 | +0.057 | +2.60 | 11 of 18 | 0.004 | 0.019 | +0.074 (10 q) | 0.008 | 0.043 | +0.035 (8 q) | 0.200 | no |
| Worst of the last 4 | 2,797 | 18 | +0.029 | +1.65 | 12 of 18 | 0.136 | 0.477 | +0.047 (10 q) | 0.092 | 0.358 | +0.007 (8 q) | 0.794 | no |

Corrected (maxT) p: over these 7 measures. Rank correlations are between the measure and the next move's excess.

## Size of the move

| Quarters back | Results | Size correlation | p | Holm p | After removing ordinary volatility | p |
|---|---:|---:|---:|---:|---:|---:|
| 1 (last quarter) | 3,177 | +0.053 | 0.003 | 0.020 | +0.029 | 0.106 |
| 2 | 3,060 | +0.047 | 0.008 | 0.042 | +0.033 | 0.070 |
| 3 | 2,934 | +0.029 | 0.132 | 0.264 | +0.016 | 0.402 |
| 4 (same period, 1 year ago) | 2,801 | +0.049 | 0.010 | 0.042 | +0.036 | 0.060 |
| 5 | 2,669 | +0.050 | 0.011 | 0.042 | +0.038 | 0.055 |
| 6 | 2,528 | +0.028 | 0.155 | 0.264 | +0.015 | 0.468 |
| 7 | 2,387 | +0.068 | 0.001 | 0.011 | +0.056 | 0.006 |
| 8 (same period, 2 years ago) | 2,247 | +0.060 | 0.006 | 0.034 | +0.042 | 0.056 |

Size correlation: the size of this three-day move against the size of the one that many quarters back, ignoring
direction. After removing ordinary volatility: the same after allowing for the stock's daily volatility over the 60
sessions before the cutoff. The stock's ordinary volatility alone has a size correlation of +0.117, much stronger than
any earlier results move.

## Checks

- **All tests together.** Correcting for all 84 tests, the smallest adjusted p is 0.118, and 0.245 for direction only.
  Under the rule set in advance, 0 of 84 pass.
- **Power.** That rule needed a correlation of about 0.09-0.12 to pass reliably. Weaker effects of 0.03-0.05 cannot be
  ruled out, except for last quarter, which is measured tightly.
- **A post-hoc variant.** Compare both the history and the next move with other results on the same cutoff date. The
  number of ups in the last 4 then passes the rule (+0.094 in the first 14 quarters, +0.057 in the last 8). This version
  was chosen after looking, and it rests on the same stocks: of its 180 "4 of 4 up" trades, 108 are already in the
  track-record top tenth, and the other 72 make +0.17% after costs. Treat it only as something to watch on new quarters.
- **Independent rebuild.** A second build from the raw data matched every value. The one correction was storing the
  history with 10 digits instead of 6: two results had been rounded into a false tie. No conclusion changed.

## Conclusion

A stock's three-day results move has no memory that you can trade. Last quarter's move, the move a year ago, any single
earlier quarter, and up/down sequences or streaks do not predict the direction of the next one once you allow for the
number of patterns tried. The only consistent lean is the stock's own track record over several results. That is the
existing past-performance watch item, and it is carried by a few strong stocks. Bigger movers do stay bigger movers, but
that is ordinary volatility, which option prices already include.

Files: scripts in `pattern_tests/prev_quarter_patterns/` and outputs in
[results/prev_quarter_patterns/](../results/prev_quarter_patterns/):

- PLAN.txt and PLAN.sha256: the plan written before any result.
- build_history.py: one row per result with its earlier moves.
- run_tests.py: the 84 tests.
- skeptic/: all-tests correction and power, the patterns' stocks and quarters, the cutoff-date check, size against
  volatility, walk-forward and comparison with earlier studies. Its logs are in results/prev_quarter_patterns/skeptic/.

The scripts read `LAB_ROOT` (the scratch data folder) and `REPO_ROOT`.
