# Technical and fundamental analysis together

Question: separately, technical analysis (TA) and fundamental analysis (FA) gave nothing (see
[TECHNICAL_ANALYSIS.md](TECHNICAL_ANALYSIS.md) and [FUNDAMENTAL_ANALYSIS.md](FUNDAMENTAL_ANALYSIS.md)). Do they work
when combined: "good company + good chart" screens before results, TA+FA filters on the lag 10% + volume rule, a model
using both, and TA+FA signals after the results?

The same point-in-time panels were joined: the TA indicators at the cutoff close and the fundamentals from filings
published before the decision. All cut-offs and tests were written down before any outcome was computed. Only stocks in
F&O at the time are traded; costs are 0.17% a round trip.

## Answer

**No.** Combining TA and FA does not create an edge:

- No combined screen makes money in the 3-day window once the number of screens tried is allowed for (40 screens; best
  adjusted p 0.08-0.11).
- No TA+FA pair improves the lag 10% + volume rule (12 pairs; best adjusted p 0.66-0.81), and a model trained on both
  ranks results about as well as a coin flip (AUC 0.52).
- After results, adding TA, FA or both to the results-winner trade does not beat what the winners already earn (117
  tests; best family-wise p 0.54).

The lag 10% + volume rule stays as it is, unfiltered.

## 1. Combined screens before results (3-day window)

40 screens pairing a fundamental condition with a technical one, longs and shorts. All F&O results average +0.04%.

| Screen | Trades | 3-day avg | Quarters positive | First 14 q / last 8 q | Without best 5 |
|---|---:|---:|---:|---|---:|
| **Quality on a dip**: no loss in 4 quarters, last profit up YoY, RSI(14) < 30 | 62 | +1.67% | 8 of 12 | +1.54% / +1.78% | +0.65% |
| Same, close below the lower Bollinger band | 108 | +0.80% | 10 of 16 | +1.24% / +0.46% | +0.12% |
| Same, oversold count >= 3 | 272 | +0.55% | 14 of 20 | +0.89% / +0.26% | +0.24% |
| Quality (ROE > 15%, D/E < 0.5) & RSI(14) < 30 | 24 | -1.45% | 3 of 8 | -2.30% / -1.17% | -2.99% |
| Cheap (P/E below own 3-year median or peers) & a bullish trigger | 453 | +0.11% | 12 of 22 | +0.47% / -0.14% | -0.09% |
| Growth (profit +20%, sales +10%) & uptrend near the 52-week high (CANSLIM-like) | 361 | +0.06% | 10 of 22 | -0.11% / +0.37% | -0.16% |
| Same, with volume 1.0x+ | 122 | +0.39% | 11 of 22 | +0.04% / +1.05% | -0.21% |
| GARP (PEG < 1) & strong uptrend (golden cross, ADX > 25) | 83 | +0.74% | 10 of 16 | +0.09% / +1.71% | +0.11% |
| Piotroski 6+ of 7 & above the 200-day average | 403 | +0.17% | 7 of 11 | +1.17% / -0.17% | -0.01% |
| Turnaround (loss a year ago, profit now) & 20-day breakout | 6 | -4.99% | 0 of 3 | | |
| Combined score: 8+ of 10 good flags | 690 | +0.37% | 14 of 22 | +0.40% / +0.32% | +0.24% |
| FA good >= 4 of 5 and TA good >= 4 of 5 | 430 | +0.47% | 11 of 22 | +0.36% / +0.61% | +0.30% |
| Short: expensive (P/E > 50 or 25%+ above peers) & RSI(14) > 70 | 80 | -1.05% (loss) | 5 of 15 | | |
| Short: falling profit & below the 200-day average & death cross | 148 | -0.29% (loss) | 11 of 21 | | |

- After allowing for 40 screens, none is significant (best Holm-adjusted p 0.11, family-wise 0.08).
- The textbook quality definition (high ROE, low debt) on a dip **lost** money; the looser "profitable and growing" one
  was the only screen that looked good.
- Expensive, overbought stocks kept rising through results, so the short lost, as in the TA-only tests.

**Quality on a dip** is the closest thing to a result, but it is not confirmed:

- It earned the same in both halves and beats random picks of the same size (p 0.003 on its own), but not after the 40
  screens (Holm 0.11).
- The same screen on ordinary days without results makes +0.70% over 3 days, so only about +1% is linked to results.
- 20 of its 62 trades are the lag rule's own trades (+3.19%); the other 42 make +0.95%, and **-0.40% without their best
  5**.
- Treat it as a watch item, not a rule.

## 2. TA+FA filters on the lag 10% + volume rule

The rule's 85 trades (volume 1.0x+) split by 12 pre-registered TA+FA pairs:

| Pair | Yes: trades, avg | No: trades, avg |
|---|---|---|
| Good fundamentals & oversold count >= 3 | 21, +3.83% | 57, +1.41% |
| Good fundamentals & strong downtrend (ADX > 25, -DI > +DI) | 34, +3.18% | 44, +1.21% |
| Large cap & RSI(14) < 30 | 12, +3.28% | 73, +1.94% |
| Piotroski high & oversold count >= 3 | 16, +3.10% | 43, +2.56% |
| Cheap vs own P/E & below the lower Bollinger band | 6, +2.88% | 34, +2.49% |
| Profit growing & MACD turning up | 29, +1.72% | 50, +2.48% |
| Profitable 4 quarters & above the 200-day average | 18, +0.69% | 60, +2.63% |
| Quality (ROE > 15%, D/E < 0.5) & RSI(14) < 30 | 10, -0.23% | 40, +3.31% |

- After allowing for the pairs tried, none is significant (smallest Holm p 0.81, family-wise 0.66).
- The best pair, **good fundamentals & oversold**, was rebuilt independently and rejected:
  - after allowing for the pairs tried, a gap this large appears by chance about 80% of the time (family-wise p 0.80);
  - one trade (ADANIPORTS, Jan 2023) is about a quarter of its gain;
  - it reverses on the trades with volume 1.0-1.3x, and the 2x2 table (good fundamentals only, oversold only, both) does
    not line up as a real effect would;
  - in the last 8 quarters the gap fails at 8 of 16 nearby lag and volume settings;
  - the same pair on ordinary days earns nothing extra.
  Realistic value: about +1.3% a trade, the same as the plain rule.
- Quality & oversold, the textbook "quality on a dip" inside the lag group, did worst (10 trades, -0.23%).

## 3. A model using TA and FA together

Logistic regression, random forest and gradient boosting were trained walk-forward (only past quarters, tested on
seasons 8-21) on TA only, FA only, and both:

| Features | AUC (0.50 = coin flip) | Top 10% of results: trades, avg |
|---|---:|---|
| TA only | 0.52-0.53 | 129-246, +0.10% to +0.83% |
| FA only | 0.49-0.50 | 125-187, +0.12% to +0.63% |
| TA + FA | 0.52 | 151-250, +0.40% to +1.35% |
| **Gradient boosting, TA + FA, top 10%** | 0.52 | **182, +1.35% (net +1.18%)** |
| Reference: lag 10% + volume rule, same seasons | | 51, +2.29% |

- FA adds nothing to TA: the AUC does not rise when fundamentals are added.
- The best version, gradient boosting on TA + FA, picks 182 trades at +1.35% (11 of 14 quarters up; last 8 quarters
  +0.95%; +0.98% without the best 5). Models trained on shuffled outcomes rank as well 19% of the time and reach that
  top-10% return 3% of the time; after all the models tried the family-wise p is 0.10. It is the nearest miss, not a
  result.
- Inside the lag group, the model's top half (52 trades, +2.04%) did not beat the plain volume filter (51 trades,
  +2.29%).

## 4. After results: TA and FA on the reported numbers

Buy at the reaction-day close, hold 5, 10 or 20 sessions, short Nifty against it, after costs (117 pre-set tests).
20-session results:

| Signal | Trades | Over Nifty, after costs | Quarters positive |
|---|---:|---:|---:|
| Plain results-winner drift (reference: beat Nifty by > 4% on the day) | 392 | +1.45% | 15 of 22 |
| Good numbers + breakout on volume | 286 | +1.74% | 15 of 22 |
| Breakout on volume alone, any numbers (found after the fact) | 580 | +1.47% | 15 of 22 |
| Good numbers but below the 50-day average | 482 | -0.73% | 8 of 22 |
| Bad numbers + breakdown on volume, short | 145 | +0.31% (-0.28% without best 5) | 11 of 21 |
| Winners with RSI(14) > 50 at the cutoff | 232 | +2.42% | 17 of 22 |
| Winners with RSI(14) <= 50 at the cutoff | 160 | +0.04% | 10 of 22 |
| Winners & good numbers & RSI(14) > 50 | 121 | +2.92% | 15 of 21 |
| Winners & quality (ROE, D/E) | 103 | +2.63% | 13 of 15 |
| Winners & every bullish flag | 105 | +3.05% | 13 of 20 |

- After allowing for 117 tests, none is significant (all Holm p 1.00; best family-wise p 0.54).
- Good numbers with a breakout earn the same as any breakout on volume (p 0.49): the fundamentals add nothing.
- Good numbers on a weak chart lose; bad numbers on a breakdown do not give a short.
- A +3% take-profit cuts the winners' drift to less than half (+0.64%): the drift needs the full 20 sessions.

**Winners with RSI > 50** is the only watch item:

- +2.42% against +0.04% for winners with a weaker RSI, in both halves (+2.65% / +2.16%); luck p 0.01 on its own, but
  family-wise 0.54 after 117 tests.
- It is not special to winners: around results, strength before the numbers helps every stock, while on ordinary days
  the same split goes the other way (-0.29 points).
- Adding good numbers does not help: inside winners with RSI > 50, those with good numbers made 0.46 points less than
  the rest.
- An independent re-check of "winners & good numbers & RSI > 50" (+2.92%) rejected it: all of its profit comes from 2023
  on, and against plain winners the gap has p 0.07. Realistic value: about +1.5% a trade over Nifty, like the plain
  winner drift.
- Followed up quarter by quarter in [WINNERS_RSI50.md](WINNERS_RSI50.md): traded in all 22 quarters, 17 positive;
  realistic about +1% a trade over Nifty; skipping winners with RSI 50 or below looks sensible.

## Conclusion

Technical and fundamental analysis together do not improve the results trades. Keep:

- the lag 10% + volume rule for the 3-day window, unfiltered (realistic +1% to +1.5% a trade after costs);
- the plain results-winner drift after results (about +1% a trade over Nifty).

Watch items only, not to be traded: quality on a dip before results (62 trades, +1.67%), the TA+FA gradient-boosting top
10% (182 trades, +1.18% after costs), and results winners with RSI > 50 (232 trades, +2.42% over Nifty).

Files: scripts in `pattern_tests/tafa/` (A_combined_screens; B_lag_rule_and_model: the pairs, the pre-registration and
the walk-forward models; C_post_results with its PREREGISTRATION.txt; verify_0 and verify_1: the independent checks),
outputs in [results/tafa/](../results/tafa/). The scripts read `LAB_ROOT` (the scratch data folder with the TA panel
`ta/build`, the fundamentals panel `fa/build`, `sector_lab/data` and `report/`) and `REPO_ROOT`.
