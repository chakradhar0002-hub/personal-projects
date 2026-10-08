# Fundamental analysis around results

Question: do company fundamentals help, either before the results (for the 3-day window) or after them (trading on
the reported numbers)?

A point-in-time fundamentals table was built from the NSE filings: for each result, only filings published before
the decision were used. It covers TTM sales and profit, growth (YoY, QoQ, acceleration, 4-quarter streaks), EBITDA
and net margins and their changes, ROE, debt/equity, P/E, P/B, earnings yield, PEG, P/E against the stock's own
3-year median and against same-industry peers on the same date, market cap, a Piotroski-style score (7 of the 9 tests
the filings allow), profit consistency and dividends. It also holds the reported quarter's numbers for post-results
tests. It matches the project's existing figures on 99%+ of rows and 10 stocks' original filings exactly. Balance
sheets exist only from Sep-2022, so P/B, ROE and debt/equity start later. Only stocks in F&O at the time are traded.

## Answer

**No.** Fundamentals do not help in this trade:

- No fundamental screen known before the numbers makes money in the 3-day window (44 screens, all within about ±0.3%
  of the average result).
- None improves the lag 10% + volume rule, and none can replace it.
- After results, trading on the reported numbers (strong growth, margin expansion, turnarounds, or weak numbers as
  shorts) gives no edge beyond what any result does.

## 1. Fundamental screens before results (3-day window)

44 screens with textbook cut-offs, written down before any outcome was computed (all F&O results average +0.04%):

| Screen | Trades | 3-day avg | Quarters positive | First 14 q / last 8 q |
|---|---:|---:|---:|---|
| Value: P/E < 15 | 522 | -0.12% | 10 of 22 | +0.18% / -0.50% |
| Value: P/B < 1.5 | 278 | -0.12% | 7 of 15 | +0.23% / -0.34% |
| Value: Graham (P/E x P/B < 22.5) | 287 | -0.00% | 8 of 15 | +0.21% / -0.13% |
| P/E 20%+ below its own 3-year median | 342 | +0.20% | 8 of 16 | -0.33% / +0.45% |
| P/E 25%+ below industry peers | 611 | +0.13% | 11 of 22 | +0.38% / -0.07% |
| Quality: ROE > 15% and debt/equity < 0.5 | 788 | +0.12% | 9 of 15 | +0.74% / -0.20% |
| No loss in the last 4 quarters | 2,608 | +0.01% | 14 of 22 | +0.11% / -0.09% |
| Growth: profit +20% and sales +10% YoY | 925 | +0.04% | 12 of 22 | +0.02% / +0.07% |
| Growth accelerating | 737 | +0.14% | 12 of 21 | +0.16% / +0.11% |
| GARP: PEG < 1 with profit growth > 15% | 626 | +0.19% | 13 of 19 | +0.47% / -0.08% |
| EBITDA margin up > 1 point YoY | 975 | +0.29% | 13 of 22 | +0.53% / -0.02% |
| Turnaround (loss a year ago, profit now) | 116 | +0.46% | 11 of 21 | +0.52% / +0.23% |
| Piotroski-style score 6+ of 7 | 651 | +0.27% | 8 of 11 | +1.19% / +0.07% |
| Quality + growth (best long screen) | 237 | +0.61% | 10 of 15 | +1.45% / +0.23% |
| Quality + value (P/E < 20) | 102 | -0.83% | 6 of 15 | -0.09% / -1.20% |
| Large caps | 1,966 | +0.17% | 13 of 22 | +0.24% / +0.09% |
| Small caps | 132 | -0.61% | 10 of 22 | -0.20% / -0.96% |

- After allowing for 44 screens, none is significant: every adjusted p-value is 1.00, and the 2 screens at p < 0.05
  are exactly what chance gives.
- Cheap stocks (low P/E, low P/B, Graham) did slightly worse than average, not better.
- The best screen, quality + growth, makes +0.44% a trade after costs, and only +0.23% in the last 8 quarters.

## 2. Fundamentals as a filter on the lag 10% + volume rule

Is "buy quality on the dip" better than buying any deep laggard on volume? The rule's 85 trades, split by
fundamentals known before the trade:

| Condition | Yes: trades, avg | No: trades, avg | Gap first 14 q / last 8 q |
|---|---|---|---|
| Quality (ROE > 15%, D/E < 0.5) | 29, +2.46% | 21, +2.81% | -3.2 / +1.0 points |
| Profitable all last 4 quarters | 73, +2.29% | 5, +0.58% | too few on one side |
| Last quarter's profit growing | 53, +2.34% | 26, +1.91% | +1.9 / -5.0 |
| Profit growth accelerating | 27, +2.29% | 39, +2.49% | +0.5 / -1.5 |
| Sales growth accelerating | 37, +3.07% | 33, +1.95% | +2.0 / +0.3 |
| Margin expanding | 40, +2.36% | 43, +2.13% | +2.1 / -2.8 |
| Cheap vs own 3-year P/E | 24, +2.18% | 16, +3.10% | -2.9 / -0.3 |
| Piotroski 5+ of 7 | 34, +2.65% | 25, +2.78% | -1.2 / +0.9 |
| Large cap | 27, +3.25% | 58, +1.61% | +3.7 / -1.4 |
| "Unjustified fall" (good fundamentals) | 45, +2.48% | 33, +1.50% | +2.4 / -2.2 |

- No split helps in both halves or comes near significance (smallest p 0.30; all adjusted p-values 1.0).
- The two that looked best were rebuilt independently from the raw filings and rejected:
  - **Large caps**: +3.27% on 38 trades, but the whole gap is in 2021-24. In the last 8 quarters large and smaller
    laggards did the same, and at every nearby size cut-off large caps did worse.
  - **Sales growth accelerating**: +3.07% on 37 trades, but nearly all the gap is in 2021-24 (last 8 quarters +0.3
    points). Random picks of the same size from the rule's own trades do as well 17% of the time, and across all
    other results accelerating sales made no difference.
- **What the reported results did to these trades** (known only after entering): trades where the reported profit
  rose made +3.17%, against +1.12% where it fell. That is the same gap any result shows, and the rule beats other
  results by about the same margin either way. The bounce is about the oversold, high-volume setup, not a bet on good
  numbers.
- **Replacing the lag or volume filter with fundamentals fails**: quality + lag 10% without volume +0.59% (51 trades);
  quality + volume without lag +0.43% (307); profitable 4 quarters + lag 10% +0.75% (157); good fundamentals + volume
  +0.44% (537). None comes near the rule's +2.13%.

## 3. Trading after results on the reported numbers

Buy (or short) at the reaction-day close, hold 5, 10 or 20 sessions, hedged with Nifty, after costs (84 pre-set
tests). 20-session results:

| Signal | Trades | Over Nifty, after costs | Same for all results | Quarters positive |
|---|---:|---:|---:|---:|
| Strong results (profit +25%, sales +15% YoY), buy | 693 | +0.52% | +0.43% | 15 of 22 |
| Profit far above its own trend (top fifth), buy | 554 | +0.23% | +0.52% | 12 of 19 |
| Margin up > 2 points YoY, buy | 919 | +0.32% | +0.45% | 11 of 22 |
| Loss-to-profit turnaround, buy | 106 | +0.76% | +0.45% | 12 of 21 |
| Profit down > 25%, short | 403 | -1.46% (loss) | | 3 of 22 |
| Profit-to-loss, short | 59 | -3.06% (loss) | | 6 of 19 |
| Good numbers but weak price reaction, buy | 316 | -0.01% | +0.05% | 12 of 22 |
| Bad numbers but strong reaction, short | 159 | -2.06% (loss) | | 6 of 22 |
| Good numbers and stock beat Nifty by > 4%, buy | 103 | +2.48% | +1.64% (all such winners) | 12 of 22 |
| Plain results-winner drift (reference) | 392 | +1.45% | | 15 of 22 |

- Good numbers add nothing beyond what any result does; bad numbers do not lead to falls (every short lost money).
- Adding good numbers to the results-winner trade is chance-sized: random subsets of the winners do as well 11-18% of
  the time.
- Found after the fact (watch only): buying a stock whose profit came in far below its own trend but whose price still
  beat Nifty on the day made +2.09% over 20 sessions (143 trades), not significant after the 120 tests run.

## Conclusion

Fundamental analysis does not improve the results trades in this data. Keep:

- the lag 10% + volume rule for the 3-day window, unfiltered (realistic +1% to +1.5% a trade after costs);
- the plain results-winner drift after results (about +1% a trade over Nifty).

Files: scripts in `pattern_tests/fa/` (build: the point-in-time fundamentals panel and its checks; A_pre_results;
B_on_lag_rule with the pre-registration; C_post_results; verify_0 and verify_1: the independent checks), outputs in
[results/fa/](../results/fa/). The scripts read `LAB_ROOT` (the scratch data folder with `report/nse_fin.db`,
`search22/`, `sector_lab/data`) and `REPO_ROOT`.
