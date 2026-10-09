# Past performance around results

Question: does a stock's own past performance help the results trades? Two kinds of past performance were tested:

- **Results track record**: how the stock did around its earlier results: its earlier 3-day results windows, its
  reaction-day moves against Nifty, and its 20-session drift after earlier results.
- **Price performance**: its 1-, 3-, 6- and 12-month return against Nifty 50 and against its sector index, its rank
  among F&O stocks, and its distance from the 52-week high.

Both were tested on the two trades studied so far:

- **Trade A, the 3-day pre-results window**: buy at the cutoff close (2 sessions before the result session), sell at
  the Day+1 close. The working rule is lag 10% + volume (85 trades, +2.13%).
- **Trade B, the post-results drift**: buy at the reaction-day close, hold 20 sessions, short Nifty against it. Plain
  winners (beat Nifty by 4%+ on the day) make +1.45%; winners with RSI above 50 make +2.42%.

Every history item used ended before the decision (checked twice, independently). Each test set was written down
before any outcome was computed (71 tests in all), corrected for the number of tests, compared with the same signal on
ordinary days without results, and then rebuilt and stress-tested by a separate agent. Only stocks in F&O at the time
are traded.

## Answer

- **Price performance (1 to 12 months, sector, 52-week high) helps neither trade.** Every test has an adjusted p of
  1.00.
- **The results track record does not improve either existing rule.** No split of the lag rule or of the winners trade
  holds up, and nothing can replace the lag or volume filters.
- **One new trade showed up: stocks that habitually keep rising after their results.** If a stock's last 4
  post-results drifts are in the top fifth of the quarter, buying it after this quarter's results (whatever the
  reaction) made +1.80% a trade over Nifty in 20 sessions (569 trades). It passed every pre-set test, but it faded in
  the last 8 quarters. Realistic: about **+0.5% a trade**, a watch item to paper-trade, not a rule.
- A milder version for trade A: stocks that habitually rise into their own results. It is real but small and did not
  pay after costs in the last 8 quarters.

## Trade A: the 3-day pre-results window

33 pre-registered tests (all F&O results average +0.04%; ordinary 3-day windows of the same stocks +0.24%):

| Signal | Trades | 3-day avg | Quarters positive | First / last part | Adjusted p |
|---|---:|---:|---:|---|---:|
| Rose in the last results window | 1,548 | +0.03% | 9 of 21 | +0.32% / -0.31% | 1.00 |
| Rose in 3 or 4 of the last 4 results windows | 816 | +0.39% | 12 of 18 | +0.95% / -0.10% | 0.42 |
| Best average of the last 4 windows (top fifth) | 569 | +0.53% | 12 of 18 | +1.08% / +0.04% | 0.34 |
| Biggest average results-day move, last 4 (top fifth) | 569 | +0.53% | 9 of 18 | +1.18% / -0.05% | 0.34 |
| Last results winner (beat Nifty by 4%+) | 383 | -0.04% | 11 of 21 | +0.59% / -0.61% | 1.00 |
| Last results loser, buy for a rebound | 408 | +0.06% | 10 of 21 | -0.23% / +0.41% | 1.00 |
| 3-month return vs Nifty, top fifth | 663 | +0.04% | 10 of 22 | +0.15% / -0.09% | 1.00 |
| 12-month return vs Nifty, top fifth | 658 | +0.20% | 13 of 22 | +0.47% / -0.15% | 1.00 |
| 12-month leader with a 1-month pullback | 230 | -0.17% | 12 of 22 | +0.74% / -1.09% | 1.00 |
| Within 5% of the 52-week high | 694 | +0.33% | 12 of 22 | +0.14% / +0.74% | 1.00 |

(First part: the first 14 quarters, or quarters 5-14 where 4 earlier results are needed; last part: the last 8
quarters.)

- None of the 33 works. Shorts (momentum or reversal) also lose.
- **Track record is a real but small effect.** Stocks that habitually rise into their own results beat random picks
  (p about 0.01) and beat the same signal on ordinary days, and the effect is not the lag rule or momentum in disguise.
  But it made all its money in Jan-Mar 2022 to Apr-Jun 2024 results; in the last 8 quarters it earned nothing after
  costs. A few stocks (ADANIPORTS, CUMMINSIND, RECLTD) give about half of it.
- After the fact, the checker found that only the very top tenth holds up (292 trades, +1.07%, +0.92% in the last 8
  quarters), driven by stocks that qualify quarter after quarter. Expect about half of that; it needs a forward test.

**On the lag 10% + volume rule** (85 trades): no past-performance condition splits it significantly (all adjusted p
1.00). Two hints point the same way, both too small to act on:

| Condition inside the rule | Yes: trades, avg | No: trades, avg |
|---|---|---|
| 30%+ below the 52-week high | 41, +3.08% | 44, +1.25% |
| 3-month return in the bottom fifth | 54, +2.65% | 31, +1.23% |
| Habitually drifts up after results (top fifth) | 18, +4.23% | 51, +1.65% |

Deeper long-term laggards bounced more, but the other half still made +1.25% (+1.08% after costs), so filtering them
out would lose profitable trades.

**Replacing a filter fails.** Using 3-month weakness instead of the 1-month lag gives 207 trades at +0.69%, but all of
that comes from the 54 trades it shares with the lag rule; its other 153 trades make 0.00%. Using the track record or
the 12-month trend instead of volume picks worse trades. Volume remains what turns "lagged Nifty" (+0.73%) into the rule
(+2.13%).

## Trade B: the post-results drift

35 pre-registered tests. **No past-performance split improves the winners trade** (32 splits of plain winners and of
winners with RSI above 50; all adjusted p 1.00):

| Condition (at the reaction close) | Plain winners (392, +1.45%) | Winners with RSI > 50 (232, +2.42%) |
|---|---|---|
| Repeat winner (last quarter also a winner) | 60, +1.13% | 32, +3.04% |
| First winner in 4 results | 187, +1.64% | 104, +2.86% |
| Last win kept running afterwards | 33, +2.51% | 19, +4.50% |
| Drift record, top half | 189, +2.01% | 113, +2.85% |
| 3-month return rank, top half | 280, +1.79% | 196, +2.69% |
| 6-month return rank, bottom half | 122, +1.93% | 55, +3.63% |
| 12-month return rank, top half | 239, +1.63% | 156, +2.69% |
| Within 5% of the 52-week high | 176, +2.42% | 137, +2.61% |
| 12-month return above its sector | 255, +1.52% | 163, +2.36% |

The closest, winners near their 52-week high (+0.60% over all winners), holds only in the last 8 quarters, disappears
without its best 5 trades, and mostly repeats the RSI > 50 filter.

### The one new finding: habitual post-results drifters

**Rule**: at each result's reaction-day close, take the stock's last 4 post-results 20-session drifts against Nifty
(all finished before that day). If their average is in the top fifth of that quarter's F&O results, buy at the close
whatever the reaction, hold 20 sessions, and short Nifty.

| | Trades | Avg vs Nifty | Gain over all results, same quarter | Quarters positive |
|---|---:|---:|---:|---:|
| All quarters | 569 | +1.80% | +1.11 | 13 of 18 |
| First part (Jan-Mar 2022 to Apr-Jun 2024 results) | 270 | +2.88% | +1.66 | |
| Last 8 quarters | 299 | +0.81% | +0.62 | |
| Without the best 5 trades | | +1.52% | +0.85 | |

| Results for | Quarter | Trades | Avg vs Nifty | Gain over all results |
|---|---|---:|---:|---:|
| Jan-Mar 2022 | Q4 FY22 | 27 | -3.11% | -1.85 |
| Apr-Jun 2022 | Q1 FY23 | 27 | +3.49% | +1.82 |
| Jul-Sep 2022 | Q2 FY23 | 27 | -1.55% | -1.08 |
| Oct-Dec 2022 | Q3 FY23 | 27 | +4.38% | +3.25 |
| Jan-Mar 2023 | Q4 FY23 | 27 | +6.32% | +2.82 |
| Apr-Jun 2023 | Q1 FY24 | 27 | +4.89% | +2.58 |
| Jul-Sep 2023 | Q2 FY24 | 27 | +7.09% | +4.57 |
| Oct-Dec 2023 | Q3 FY24 | 27 | +2.81% | +1.15 |
| Jan-Mar 2024 | Q4 FY24 | 27 | +5.73% | +4.18 |
| Apr-Jun 2024 | Q1 FY25 | 27 | -1.21% | -0.86 |
| Jul-Sep 2024 | Q2 FY25 | 27 | +1.31% | +1.70 |
| Oct-Dec 2024 | Q3 FY25 | 35 | -3.78% | -1.64 |
| Jan-Mar 2025 | Q4 FY25 | 36 | +3.78% | +1.33 |
| Apr-Jun 2025 | Q1 FY26 | 39 | +0.41% | +0.34 |
| Jul-Sep 2025 | Q2 FY26 | 39 | -1.89% | +0.21 |
| Oct-Dec 2025 | Q3 FY26 | 40 | +2.54% | +1.18 |
| Jan-Mar 2026 | Q4 FY26 | 41 | +2.30% | +1.27 |
| Apr-Jun 2026 | Q1 FY27 | 42 | +1.58% | +0.69 |

(It needs 4 earlier results, so it starts with Jan-Mar 2022 results.)

Why it is believable:

- It is the only one of the 71 tests to pass every pre-set check without being an existing rule in disguise: adjusted
  p 0.002, better than all results in both parts, and still +0.85 over all results without its best 5 trades.
- It is a results effect: the same flag adds only +0.07 on ordinary days, -0.87 in the 20 sessions before the
  cutoff and -0.07 in the 20 sessions after the trade ends.
- It is not momentum (controlling for the 12-month trend leaves +0.94) or the size of the current reaction (+1.12).
- Nearby cut-offs agree (top 10% to 30%: +1.57 to +0.68), a version using only the previous quarter's cut-off gives
  +1.21, and it holds for stocks in F&O since 2021 (+1.17) as well as later joiners (+0.86).

Why to stay cautious:

- **It faded**: +2.88% a trade in the first part, +0.81% in the last 8 quarters (against +0.19% for all results).
- **2023 carries it**: 56% of the gain; without 2023 the gain is +0.60.
- **It is the same stocks again and again**: HAL, IDEA, ABB, BHEL, GMRAIRPORT, PFC, RECLTD, DIXON, mostly PSU,
  defence and capital-goods names. Stocks also picked the quarter before gain +1.68; first-time picks +0.22 (-0.25 in
  the last 8 quarters). Without the 20 most frequent stocks the gain is about zero. Within the same sector the gain
  is +0.58.
- **Only the top fifth works**; the other four fifths all do worse than average, and shorting the bottom fifth fails.
- **It does not help the winners trade**: winners with a strong drift record gained -0.38 in the last 8 quarters.
- Up to 38 positions can be open at once, and the stock list is today's F&O list (survivorship).

Realistic expectation: about **+0.5% a trade over Nifty** after costs, before any survivorship effect.

## Conclusion

- Keep the lag 10% + volume rule and the winners trade unchanged; past performance does not improve them.
- Price performance over 1 to 12 months, the sector and the 52-week high add nothing to either trade.
- New watch item: **habitual post-results drifters** (top fifth of the last-4 drift record, any reaction, 20 sessions,
  short Nifty), about +0.5% a trade realistic. Paper-trade it from the Jul-Sep 2026 results together with the
  "top tenth of the last-4 results windows" version for trade A.

Files: scripts in `pattern_tests/past_performance/` (features: the point-in-time panel and its checks; A_pre_results
and B_post_results: the pre-registered tests with `prereg.txt`; verify_A_pre_results and verify_B_post_results: the
independent rebuilds and stress tests), outputs in [results/past_performance/](../results/past_performance/). The
scripts read `LAB_ROOT` (the scratch data folder) and `REPO_ROOT`.
