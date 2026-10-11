# More signals: F&O positioning, delivery % and company news

Question: do three kinds of data not used so far help the results trades?

- **F&O positioning**, from the daily NSE F&O bhavcopies: futures open interest (OI) build-up before results (long
  build-up, short build-up, short covering, long unwinding), OI against its 20-day average, the futures premium (basis)
  against the stock's own norm, the put-call ratio (PCR) by OI and its change, and at-the-money implied volatility (IV)
  rich or cheap, call-put IV spread and IV run-ups.
- **Delivery %**, from the daily NSE security-wise delivery files: delivery % and delivery quantity against their own
  60-day average, "price down + delivery up" (accumulation into weakness), and delivery on the results day itself.
- **Company news flow**, from NSE corporate announcements, board-meeting intimations and SAST disclosures: results
  date earlier or later than the same quarter last year, how far ahead the board meeting was announced, news flow
  against the stock's norm, press releases, order wins, acquisitions, analyst calls announced, monthly business
  updates, and promoter or large-holder buying and selling.

Each was tested on both trades:

- **Trade A, the 3-day pre-results window** (buy at the cutoff close, sell at the Day+1 close), as a rule on its own
  and as a filter on the lag 10% + volume rule (85 trades, +2.13%).
- **Trade B, the post-results drift** (buy at the reaction-day close, hold 20 sessions, short Nifty), as a filter on
  plain winners (+1.45%) and on winners with RSI above 50 (+2.42%).

98 tests were written down before any outcome was computed (36 F&O, 35 delivery, 27 news). Each test was checked in
both halves of the data, against random picks, against the same signal on ordinary days without results, without its
best 5 trades, and corrected for the number of tests. Each family was then checked by a separate agent. Those checks
re-downloaded the raw NSE files (every F&O bhavcopy, 30 delivery files and 40 announcement windows, all matching),
rebuilt every feature with its own code and looked for any use of data published after the decision.

## Answer

**None of the three improves either trade, and none gives a new rule.** No test passed every check. The lag 10% +
volume rule and the winners trade stay as they are.

Three small watch items came out of it, none tradeable on this evidence:

| Watch item | Trade | Result | Realistic |
|---|---|---|---|
| Winners with a high put-call ratio on the results day | B | 213 trades, +2.34% vs +0.39% for other winners | about +0.3% over plain winners (0 to +0.6%) |
| A press release in the 30 days before the cutoff | A | 1,023 trades, +0.25% after costs | about +0.1% |
| Stocks that publish monthly or quarterly business updates (found after the fact) | A | 323 results, +0.87% over the average result | needs a fresh test |

## 1. F&O positioning (36 tests)

All 1,434 available F&O bhavcopies from Dec 2020 to Sep 2026 were used (one day, 30 Mar 2021, is missing on NSE's
archive). All but one result have the OI data; implied volatility could be solved on 97% of stock-days.

**Trade A** (all F&O results average +0.04%; net is after 0.17% cost, shorts shown as the short's profit):

| Signal at the cutoff | Side | Trades | Net avg | Quarters positive | First 14 / last 8 quarters | Adjusted p |
|---|---|---:|---:|---:|---|---:|
| Long build-up (5 sessions: price up, OI up 10%+) | Buy | 285 | -0.01% | 12 of 22 | +0.21% / -0.34% | 1.00 |
| Short build-up (5 sessions: price down, OI up 10%+) | Short | 317 | -0.15% | 12 of 22 | -0.29% / +0.05% | 1.00 |
| Short covering (10 sessions: price up, OI down) | Buy | 370 | +0.09% | 11 of 22 | -0.23% / +0.63% | 1.00 |
| Long unwinding (10 sessions: price down, OI down) | Short | 194 | -0.41% | 8 of 21 | -0.24% / -0.61% | 1.00 |
| Futures premium cheap against its own norm | Short | 650 | +0.17% | 11 of 22 | -0.23% / +0.67% | 0.52 |
| Put-call ratio, top fifth | Buy | 659 | -0.06% | 12 of 22 | +0.06% / -0.20% | 1.00 |
| Put-call ratio rising (5 sessions), top fifth | Buy | 659 | +0.20% | 13 of 22 | +0.47% / -0.13% | 1.00 |
| Implied volatility cheap against its own norm | Buy | 626 | +0.02% | 9 of 22 | +0.24% / -0.25% | 1.00 |
| Implied volatility rich | Short | 624 | -0.30% | 12 of 22 | +0.04% / -0.70% | 1.00 |
| Put IV run-up over 20 sessions | Short | 578 | +0.12% | 12 of 22 | +0.05% / +0.19% | 1.00 |

- None works. The two that beat their ordinary-day placebo (cheap futures premium and put-IV run-up, both shorts) are
  worth +0.1% to +0.2% and fall apart in the first half, without their best 5 trades, or when measured one session
  earlier.
- None of the 22 conditions splits the lag rule's 85 trades (all adjusted p 1.00). Most lag-rule trades are short
  build-ups (53 of 85 over 10 sessions), and they do no worse than the rest.

**Trade B** (plain winners, 392 trades, +1.45%):

| Condition at the reaction close | Yes: trades, avg | No: trades, avg |
|---|---|---|
| Futures OI up on the results day | 230, +1.59% | 162, +1.24% |
| Futures OI up 10%+ on the results day (fresh longs) | 88, +2.72% | 304, +1.08% |
| Long build-up in the 5 sessions to the results day | 128, +2.27% | 264, +1.05% |
| Short build-up before results | 44, -1.46% | 348, +1.81% |
| **Put-call ratio in the top fifth** | **213, +2.34%** | **179, +0.39%** |
| Implied volatility cheap | 65, +0.88% | 309, +1.52% |
| Call IV run-up over 20 sessions | 92, +2.93% | 280, +0.84% |

- "Fresh longs vs short covering" on the winner day makes no difference (+1.59% vs +1.24%).
- Short build-up before results went the opposite way to the pre-registered idea (a squeeze): those winners lost
  1.46%. It can only be tracked as a possible "avoid" flag.
- The call-IV run-up collapses when its cut-off uses only earlier quarters.
- **High put-call ratio on the winner day** is the best of the 36 tests but fails the multiple-testing correction
  (adjusted p 0.20-0.23). In its favour: better in both halves (+0.74 / +0.93 over all winners), holds with cut-offs
  from earlier quarters only (+0.85), every quarter left out keeps it, and a wider or narrower cut gives a steady
  dose-response (top 10% +1.29, top 20% +0.83, top third +0.42). Entering at the next morning's open, after the
  bhavcopy is out, keeps all of it (+0.95). Against it: no edge in 2021-22, without its 5 best stocks it is +0.29,
  stocks in F&O since 2021 show only +0.57 (later joiners +1.39), and it shows nothing inside the habitual drifters.
  Inside winners with RSI above 50: 142 trades +3.04% vs 90 trades +1.44%.

## 2. Delivery % (35 tests)

All 1,447 delivery files from Dec 2020 to Sep 2026 were used. NSE publishes each day's file after the close, so trade A
uses delivery up to the day before the cutoff, and any trade-B signal that needs the results day's delivery has to be
entered a day later.

**Trade A:**

| Signal | Side | Trades | Net avg | Quarters positive | First 14 / last 8 quarters | Adjusted p |
|---|---|---:|---:|---:|---|---:|
| 5-day delivery % above its 60-day average (accumulation) | Buy | 1,641 | -0.12% | 11 of 22 | -0.05% / -0.21% | 1.00 |
| Delivery quantity 1.5x its 60-day average | Buy | 224 | +0.17% | 10 of 22 | +0.31% / -0.06% | 1.00 |
| Price down + delivery up (accumulation into weakness) | Buy | 849 | -0.05% | 11 of 22 | +0.05% / -0.19% | 1.00 |
| Price up + delivery up | Buy | 792 | -0.18% | 10 of 22 | -0.16% / -0.22% | 1.00 |
| Structurally high delivery % (top fifth) | Buy | 681 | +0.17% | 13 of 22 | +0.08% / +0.28% | 0.96 |

- Nothing works. The structurally-high-delivery stocks (the same large caps every quarter) failed the independent
  check: the effect is not steady across cut-offs and disappears without the best 10 trades.
- **Lag rule:** delivery does not separate its trades. The 75 trades whose delivery quantity also rose made +2.14%,
  the other 10 made +2.11%. Using delivery quantity instead of total volume picks almost the same trades (75 of 89
  shared) and earns less (+1.87%), so the rule's volume condition already reflects real buying.

**Trade B:**

- A winner's results-day delivery % is almost always below its normal level (median 17.7 points below; only 8 of 392
  are above): the jump comes with intraday and speculative volume, not delivery buying.
- Waiting a day for the delivery file costs about 0.25% a trade (plain winners +1.45% bought at the results-day close,
  +1.19% the next day).
- Heavy results-day delivery quantity (3x normal) looked better (+1.98% vs +1.19% at the next close) but is mostly the
  size of the jump, and it disappears without its best 5 trades.

## 3. Company news flow (27 tests)

Announcements cover all 22 quarters (Mar 2021 to Sep 2026). Board-meeting intimations (10,244) and SAST promoter and
large-holder disclosures (2,586) were fetched from NSE's public pages. Insider-trading (PIT) disclosures could not be
used: NSE's feed stops in about September 2024.

**Trade A:**

| Signal before the cutoff | Side | Trades | Net avg | Quarters positive | First 14 / last 8 quarters | Adjusted p |
|---|---|---:|---:|---:|---|---:|
| Results date 7+ days later than last year | Short | 236 | +0.28% | 10 of 19 | +0.50% / +0.11% | 1.00 |
| Results date 7+ days earlier than last year | Buy | 372 | -0.04% | 10 of 19 | -0.17% / +0.10% | 1.00 |
| Board meeting announced at the legal minimum notice | Short | 656 | +0.14% | 12 of 22 | -0.23% / +0.42% | 0.69 |
| News flow 1.5x the stock's norm | Buy | 606 | +0.08% | 12 of 21 | -0.28% / +0.71% | 1.00 |
| **Press release in the last 30 days** | Buy | 1,023 | **+0.25%** | **15 of 22** | **+0.29% / +0.20%** | **0.12** |
| Order win in the last 30 days | Buy | 171 | +0.26% | 13 of 22 | -0.47% / +0.82% | 1.00 |
| Acquisition announced | Short | 303 | -0.29% | 11 of 22 | -0.10% / -0.54% | 1.00 |
| Business update with a positive market reaction | Buy | 170 | +0.48% | 14 of 22 | +0.80% / +0.22% | 1.00 |
| Promoter buying (SAST) in the last 90 days | Buy | 112 | -0.06% | 11 of 22 | -0.15% / +0.09% | 1.00 |
| Promoter selling in the last 90 days | Short | 125 | -0.27% | 10 of 21 | -0.43% / -0.04% | 1.00 |

- **Press release in the last 30 days** is the closest: +0.25% after costs on 1,023 trades, positive in both halves,
  beats its ordinary-day placebo, and holds without its best 5 trades. It just misses the correction (0.12), and by
  more when trades on the same day are not treated as independent. Much of it is car makers (monthly sales releases),
  which rise into results with or without a release; without them and without business-update issuers it is +0.05%.
  It does not help the lag rule (31 lag trades with a release +1.58%, the other 54 +2.45%). Realistic: about +0.1%.
- Found after the fact: every stock that publishes monthly or quarterly business updates (car makers, banks, ports)
  rose into results by +0.87% over the average result (323 results), and not on ordinary days. The direction of the
  update's reaction did not matter. It is about 40 stocks and needs a fresh pre-registered test.
- Late reporters, short notice, promoter buying or selling, order wins and acquisitions show nothing.
- No condition splits the lag rule's 85 trades.

**Trade B:** all 10 tests fail. Other news on the results day, news flow before results, analyst calls announced in
advance and early reporting add nothing to the winners trade. Early reporters among winners with RSI above 50 (29
trades, +2.08% over other RSI > 50 winners) were too few to test and depend on 4 big winners.

## Conclusion

F&O positioning, delivery % and company news do not improve the results trades. Keep:

- the lag 10% + volume rule for the 3-day window, unchanged;
- the winners trade after results (plain winners, or winners with RSI above 50), unchanged.

Watch items to paper-trade from the Jul-Sep 2026 results, fixed now:

1. Winners whose put-call ratio at the results-day close is in the top fifth (cut-off from the previous quarter),
   bought at the next morning's open: about +0.3% over plain winners realistic.
2. Stocks with a press release, or a regular business update, in the 30 days before the cutoff, for the 3-day window:
   about +0.1% realistic; too small on its own.

As in every study here, the stock list is today's 213 F&O stocks; stocks that later left F&O are missing, which
flatters absolute returns.

Files: scripts in `pattern_tests/more_signals/` (oi, delivery, news: fetch, features and pre-registered tests with
`prereg.txt`; verify_oi, verify_delivery, verify_news: the independent re-downloads, rebuilds and stress tests), outputs
in [results/more_signals/](../results/more_signals/). The scripts take their data paths as arguments; the downloaded
NSE data (about 400 MB) is not stored in the repo.
