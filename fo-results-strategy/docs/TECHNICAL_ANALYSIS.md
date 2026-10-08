# Technical analysis around results

Question: do classic technical-analysis (TA) signals help in the 3-day results window (buy at the close 2 sessions
before the result session, sell at the Day+1 close), either on their own or on top of the "lag 10% + volume" rule?

Indicators were computed with textbook settings from split-adjusted daily OHLCV up to the cutoff close, for every
result and for ordinary non-results days (the placebo): RSI(14) and RSI(2), Stochastic(14,3), Williams %R(14),
CCI(20), MFI(14), Bollinger Bands(20,2), MACD(12,26,9), 20/50/200-day moving averages and golden/death crosses,
ADX(14), ATR(14), NR7, candles (hammer, engulfing, doji, shooting star), gaps, 52-week and 20-day highs/lows, and OBV.
Every signal and threshold was written down before looking at outcomes. Only stocks in F&O at the time.

## Answer

**No.** No TA signal gives a trustworthy edge on its own, none improves the lag 10% + volume rule, and none can replace
it. Oversold signals look mildly positive, but they earn the same on ordinary days and most of what they earn comes
from trades the lag rule already takes. The lag 10% + volume rule stays as it is.

## TA signals on their own (44 signals)

Baselines: an F&O result averages +0.04% in the window; the same stocks on ordinary days +0.21% over 3 days.

| Signal | Trades | 3-day avg | Quarters positive | Same signal, days without results | Without the lag-rule trades |
|---|---:|---:|---:|---:|---:|
| RSI(14) < 30, buy | 103 | +0.55% | 9 of 16 | +0.62% | -0.41% |
| RSI(2) < 10, buy | 409 | +0.23% | 14 of 22 | +0.27% | +0.12% |
| Stochastic %K < 20, buy | 656 | +0.07% | 13 of 22 | +0.26% | -0.10% |
| CCI(20) < -100, buy | 644 | +0.26% | 15 of 22 | +0.30% | +0.08% |
| Close below the lower Bollinger band, buy | 193 | +0.48% | 14 of 21 | +0.51% | +0.31% |
| Oversold count >= 3 (of RSI, Stochastic, BB, CCI, MFI, %R), buy | 492 | +0.22% | 13 of 21 | +0.30% | -0.04% |
| MACD bullish crossover, buy | 405 | +0.27% | 12 of 22 | +0.20% | +0.25% |
| Golden cross state (50 > 200-day), buy | 2,070 | +0.05% | 11 of 22 | +0.24% | +0.01% |
| Dip in an uptrend (above 200-day, below 50-day), buy | 594 | -0.05% | 12 of 22 | +0.24% | -0.09% |
| Hammer candle, buy | 41 | +0.39% | 8 of 17 | +0.40% | +0.13% |
| Bullish engulfing, buy | 59 | -0.06% | 10 of 22 | +0.21% | +0.01% |
| 20-day high breakout, buy | 239 | +0.66% | 13 of 21 | +0.10% | +0.66% |
| Close below the 20-day low, buy | 181 | +0.85% | 14 of 20 | +0.62% | +0.72% |
| RSI(14) > 70, short | 216 | -0.49% (loss) | 11 of 20 | -0.16% | |
| Near the 52-week high, short | 694 | -0.33% (loss) | 8 of 22 | -0.24% | |
| OBV bearish divergence, short | 206 | +0.56% | 15 of 22 | -0.22% | |

(Short rows show the short's profit.)

- After allowing for 44 signals tested, none is significant (best corrected p 0.07-0.11); 6 reached p < 0.05 on their
  own, against about 2 expected by chance.
- Oversold buys fire in quarters when everything was weak, earn the same on ordinary days, and lean on trades the lag
  rule already makes: without those, RSI(14) < 30 falls from +0.55% to -0.41%.
- Overbought shorts lose: those stocks drift up through results.
- Candles, crosses, ADX, NR7 and trend filters show nothing.
- Leads, not proven: buying a close below the 20-day low (+0.85% on 181 trades, but +0.62% on ordinary days, so not a
  results effect; it is the same "beaten-down stock bounces" idea as the lag rule) and shorting OBV bearish divergence
  (+0.56% on 206 trades, corrected p 0.64).

## TA filters on the lag 10% + volume rule

The rule's 85 trades (volume 1.0x+) were rebuilt from the TA panel and matched exactly, then split on 19 pre-registered
conditions:

| Condition | Yes: trades, avg | No: trades, avg | Note |
|---|---|---|---|
| RSI(14) < 30 | 31, +2.80% | 54, +1.75% | p 0.29; all of the gap in the first 14 quarters |
| RSI(2) < 10 | 23, +2.15% | 62, +2.13% | no difference |
| Stochastic < 20 | 50, +2.14% | 35, +2.12% | no difference |
| Below the lower Bollinger band | 19, +2.01% | 66, +2.17% | no difference |
| CCI < -100 | 52, +2.30% | 33, +1.86% | p 0.74 |
| Oversold count >= 3 | 40, +2.56% | 45, +1.75% | p 0.51 |
| MACD bullish crossover | 8, +1.04% | 77, +2.25% | |
| Above the 200-day average (dip in an uptrend) | 20, +1.24% | 65, +2.41% | opposite of the textbook idea |
| Golden cross state | 49, +1.58% | 36, +2.89% | opposite of the textbook idea |
| Strong downtrend (ADX > 25, -DI > +DI) | 66, +2.45% | 19, +1.03% | opposite of the textbook idea, p 0.29 |
| Near the 52-week low | 16, +1.47% | 69, +2.29% | |
| NR7 | 10, +0.69% | 75, +2.33% | |
| OBV bullish divergence | 7, +0.25% | 78, +2.30% | |
| MFI(14) < 20 | 9, +6.24% | 76, +1.65% | p 0.008 alone, 0.25 after the 19 tests; 5 trades in one quarter; reverses on ordinary days |

No condition passed the pre-set test (better in both halves, significant, beats its placebo).

On the stricter 44-trade version (volume 1.3x+), "oversold count >= 3" looked strong: 25 trades at +4.28% against
+0.78% for the other 19. An independent check rebuilt it exactly and rejected it:

- after allowing for the 19 splits tried, the chance of a result this good by luck is about 46%;
- on the 41 trades with volume 1.0-1.3x the same filter reverses (oversold -0.3% vs +2.5% for the rest), and on
  ordinary days oversold stocks also do worse;
- a stricter oversold test (4 indicators, or tighter levels) shrinks the gain instead of growing it.

## Can TA replace the lag rule?

| Rule (F&O stocks, no lag filter) | Trades | 3-day avg | Quarters positive | Lag-rule trades inside | Average of the rest |
|---|---:|---:|---:|---:|---:|
| RSI(14) < 30 + volume 1.0x+ | 53 | +1.64% | 8 of 11 | 31 | +0.01% |
| Oversold count >= 3 + volume 1.0x+ | 111 | +1.09% | 10 of 18 | 40 | +0.26% |
| Below the lower Bollinger band + volume 1.0x+ | 64 | +1.23% | 9 of 14 | 19 | +0.90% |
| Close below the 20-day low | 181 | +0.85% | 14 of 20 | 20 | +0.72% |
| **Lag 10% + volume 1.0x+ (the rule)** | **85** | **+2.13%** | **18 of 19** | | |

All earn less than the lag rule, and what they earn mostly comes from the lag rule's own trades. Oversold readings on
quiet volume lose (RSI(14) < 30 on quiet volume inside the lag group: -1.74%), so heavy volume remains the key
ingredient.

## Conclusion

Keep the lag 10% + volume rule as it is; do not add TA filters. Its independent re-check gave the same result again
(44 trades at +2.77% for the 1.3x version; about +0.8% of that also appears on ordinary days; realistic +1% to +1.5% a
trade after costs).

Files: scripts in `pattern_tests/ta/` (build: the indicator panel and its checks; A_standalone; B_on_lag_rule with the
pre-registration; verify_0 and verify_1: the independent checks), outputs in [results/ta/](../results/ta/). The
scripts read `LAB_ROOT` (the scratch data folder with `sector_lab/data` and `report/nse_prices.db`) and `REPO_ROOT`.
