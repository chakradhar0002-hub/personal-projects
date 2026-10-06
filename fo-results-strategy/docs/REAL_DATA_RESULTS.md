# Real-data results

The playbook in [STRATEGY.md](STRATEGY.md) was backtested on real NSE data, with every option
leg replayed at the actual closing prices from the NSE F&O bhavcopy.

> **Verdict: one trade survived.**
> - **The pre-results IV run-up straddle made money:** buy the ATM straddle 5 sessions before the last
>   close before the numbers, sell at that close. After costs: +0.065R a trade over 280 trades, profit
>   factor 1.9, t = 3.5, all 9 results seasons positive (section 7).
> - **The original Day-1 / Result Day / Day+1 trades did not.** The event trade (iron condor / long
>   straddle across the numbers) is roughly break-even *before* costs and loses after them. The Day+1
>   follow-through futures trade lost money even before costs.
> - **Other ideas tried and rejected** (section 7): pre- and post-results stock drift (nothing beyond
>   the market), and calendar spreads across the results (the apparent profit came from stale prices).
>
> The playbook now leads with the run-up trade. It is a small edge (a few % of the premium a trade)
> that depends on getting filled near mid, found in two years of data. Paper-trade a season first.

---

## 1. Data

| Item | Source and handling |
|---|---|
| Universe | 74 liquid F&O stocks (`realdata.DEFAULT_UNIVERSE`); 72 had data |
| Results dates and release times | Yahoo Finance earnings calendar: 647 results, Apr 2023 – May 2025 (9 per stock; Yahoo has nothing later yet) |
| Before open / during market / after close | From the release time in IST. Checked against the options: front IV fell on the session the code treats as the reaction session (IV after ÷ before ≈ 0.81–0.84 on average; the front expiry still holds ~2 weeks of normal volatility) |
| Daily prices | Yahoo Finance. 98 events sat before a later split or bonus; the right factor was recovered from option put-call parity |
| Option prices | NSE F&O bhavcopy, 250 sessions, closing prices. ATM IV from the straddle, or from the nearest traded OTM call and put |
| Usable events | 513 of 647 had IVs. Dropped: 109 with no second liquid expiry, 18 with an unresolved price mismatch, 7 with no quotes |
| Traded window | The first 4 results of each stock only build the historical move, so trades run **Apr 2024 – May 2025** (71 stocks) |
| Execution | Entry at the pre-results close, exit at the reaction-session close, at real closing prices. Costs: 2% of premium per leg per side plus Rs 20 per order (options); 5 bps per side (futures). Rupee figures use today's lot sizes |

Reproduce with:

```bash
fo-results fetch --out-dir real_data
fo-results backtest --prices real_data/prices.csv --events real_data/events.csv --quotes real_data/quotes.csv
```

The events file and the full trade list from this run are in [`results/`](../results/).

---

## 2. Default rules

303 events had enough history to be assessed. Verdicts: RICH 122, FAIR 91, CHEAP 42, SKIP 48.
The rules called for 159 event trades; 150 were replayed. 8 were dropped because the real credit was
below the 20% rule, and 1 because a leg had no price. Another 5 RICH verdicts never became trades because
the estimated credit was already too thin.

| Setup | Trades | Win % | Avg R | Total R | Profit factor |
|---|---:|---:|---:|---:|---:|
| Short iron condor (IM/HM ≥ 1.2) | 109 | 41% | −0.09 | −10.2 | 0.36 |
| Long ATM straddle (IM/HM ≤ 0.85) | 41 | 22% | −0.08 | −3.3 | 0.42 |
| Follow-through long futures | 34 | 38% | −0.16 | −5.4 | 0.59 |
| Follow-through short futures | 34 | 38% | −0.12 | −4.0 | 0.65 |

R = P&L ÷ the trade's maximum loss (condor: width − credit; straddle: debit; futures: entry − stop).

---

## 3. Does the implied-vs-historical ratio mean anything?

Every assessed event, traded or not. *move/IM* is the actual reaction move divided by the implied move.
*Short ATM straddle* is the P&L of selling the front straddle at the pre-results close and buying it
back at the reaction close, as a % of spot, before costs.

| IM/HM | Events | move/IM | move < IM | Short ATM straddle |
|---|---:|---:|---:|---:|
| < 0.85 (CHEAP) | 42 | 1.47 | 50% | +0.17% |
| 0.85–1.00 | 23 | 0.95 | 70% | +0.26% |
| 1.00–1.20 | 51 | 1.18 | 49% | −0.32% |
| 1.20–1.50 (RICH) | 52 | 0.83 | 67% | +0.26% |
| ≥ 1.50 (RICH) | 87 | 0.82 | 76% | −0.01% |

- **The ratio does sort events.**
  - When options looked rich, the stock moved less than implied two-thirds to three-quarters of the time (0.82× IM on average).
  - When they looked cheap, it moved 1.47× IM on average.
- **It doesn't turn into money.** Selling the straddle made about 0% in every bucket.
  - Small moves win often, but the minority of big moves cost about as much.
  - Option P&L depends on the *squared* move, and results moves are fat-tailed.
- **The implied-move method itself checks out.** Post-results IV averaged 1.01× the normal-vol estimate from the term structure (median 0.98), so IM isn't biased.

---

## 4. Why the event trade doesn't work, and what was tried

These were tested one at a time on the same data. The halves of the sample agree in sign.
None of these results justifies changing the rules: each variant has about 100 trades, and the best
one was picked after looking.

| Variant (real prices, after costs) | Trades | Avg R |
|---|---:|---:|
| Condor on **every** event (no ratio, no tail check) | 232 | −0.24 |
| Condor, IM/HM ≥ 1.0 | 133 | −0.10 |
| **Condor, IM/HM ≥ 1.2 (default)** | 109 | −0.09 |
| Condor, IM/HM ≥ 1.5 | 73 | −0.11 |
| Condor, default without the tail check | 125 | −0.10 |
| Condor, short strikes at 1.0 × IM | 120 | −0.24 |
| Condor, short strikes at 1.5 × IM | 80 | −0.04 |
| Iron fly (short at the money, wings 1 × IM) | 122 | −0.22 |
| Condor, front expiry ≤ 7 sessions away | 27 | −0.08 |
| Straddle on every event | 253 | −0.05 |
| Straddle, IM/HM ≤ 0.70 | 26 | −0.02 |

**Costs decide it.** The condor's average R by slippage per leg per side:

| Slippage | 0% | 0.5% | 1% | 1.5% | 2% (default) | 3% |
|---|---:|---:|---:|---:|---:|---:|
| Condor avg R | +0.03 | 0.00 | −0.03 | −0.06 | −0.09 | −0.16 |
| Straddle avg R | −0.04 | −0.05 | −0.06 | −0.07 | −0.08 | −0.10 |

To break even, the condor needs fills within about 0.5% of mid on all four legs, in and out.
Bid-ask spreads on stock options, especially the cheap OTM wings, are usually wider than that.

The results premium is also a small part of what you pay. The median front expiry is 14 sessions
after entry, so most of each option's price is ordinary time value that survives the results.
Choosing expiries closer to the results didn't help in this sample.

**Model vs. reality:** the Black-Scholes model in the backtester (flat IV, exit at the open) shows the condor
at −0.01R with 59% winners. Real prices show −0.09R with 41% winners. The model is too kind: real skew
makes downside losses larger. Don't trust model-only backtests of this trade.

---

## 5. Follow-through (Day+1) trade

| Reaction type | Trades | Avg R |
|---|---:|---:|
| CONTINUATION_UP | 30 | −0.09 |
| CONTINUATION_DOWN | 28 | −0.13 |
| FAILED_GAP_UP | 6 | −0.03 |
| FAILED_GAP_DOWN | 4 | −0.64 |
| All, held 2 sessions | 68 | −0.19 |
| All, held 3 sessions | 68 | −0.12 |

The long and short futures trades averaged −0.12R and −0.08R even with zero costs. Over one to three
sessions, these large liquid stocks showed no usable post-results drift after a strong reaction candle.

---

## 6. Not tested

- **The reaction-session opening-range trade.** It needs historical intraday bars, and there is no free source.
- **Exits at 09:30–10:30.** The bhavcopy only has closing prices, so the backtest exits at the reaction-session close.
- **Earlier years, other market regimes, and smaller or less liquid F&O stocks.** Less liquid stocks will have even wider spreads.
- **Survivorship:** the universe is today's liquid F&O list.

---

## 7. Second round: other ideas, and the one that worked

Each idea below was written down before testing, run once on the same data, and checked across the two
halves of the sample. Directional ideas are measured as excess return over the Nifty 50 (so a rising
market does not count), after 0.10% round-trip cost.

### 7.1 Rejected

| Idea | Best version | Result |
|---|---|---|
| **Pre-results drift**: buy the stock N sessions before results, sell before the numbers | 10 sessions | +0.41% raw (t = 2.0), but only +0.17% over the Nifty (t = 1.0), second half −0.16%: it was the market |
| **Post-results drift**: hold 5–20 sessions in the reaction's direction | Reaction agrees with a ≥ 5% EPS surprise (Yahoo), 20 sessions | +0.42% over the Nifty (t = 1.1), 254 events: too weak to trade. Big reactions alone (≥ 1 × HM): negative |
| **Calendar spread**: sell the front straddle, buy the next month's, across the results | – | +4.4% of the debit with all quotes, but **−20%** when every leg must have actually traded (146 events). The "profit" came from stale next-month settlement prices |

### 7.2 The IV run-up straddle

Buy the ATM straddle of the front expiry (the one that includes the results) at the close N sessions before
the last close before the numbers. Sell it at that close, so the trade never sits through the results.
Real closing prices, 2% slippage per leg per side plus brokerage, R = P&L ÷ debit.

**Planned test (5 sessions, every expiry): +3.5% of the debit a trade (t = 3.0), 485 trades.**

| Check | Result |
|---|---|
| Exit legs that actually traded (no settlement prices) | +2.7% (t = 2.4), 473 trades |
| Trimmed (drop the best and worst 2.5%) | +2.0% |
| Slippage 1% / 3% per leg per side | +5.6% / +1.5% |
| Results seasons positive | 7 of 9 |
| Without the Apr–Jun 2025 season (tariff shock) | +4.1% |
| Mechanism | ATM IV rose in 79% of events over the five sessions, by a median of 11% |

**Entry day: the effect builds smoothly, while costs are fixed per trade**

| Entry before the last close before the numbers | 1 session | 2 | 3 | 5 | 10 |
|---|---:|---:|---:|---:|---:|
| Avg return on debit, after costs | −2.6% | −0.8% | −0.1% | **+3.5%** | +3.0% |

A one-day version would fit inside the original three-day window (for after-close results, Day-1 close to
Result Day close), but it loses to costs.

**Expiry: it only works when the results premium is a big part of the option price**

| Front expiry, sessions after the exit | 1–7 | 8–14 | 15+ |
|---|---:|---:|---:|
| 5-session entry | +10.4% (126) | +3.8% (154) | −0.9% (205) |
| 10-session entry | +8.4% (126) | +4.5% (149) | −2.1% (175) |

**Default rules in the backtester** (5-session entry, expiry ≤ 14 sessions after the exit), as now written into
[STRATEGY.md](STRATEGY.md) section 5:

| | Trades | Win % | Avg R | Median R | Profit factor | t | 1st / 2nd half |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2% slippage (default) | 280 | 50% | +0.065 | −0.007 | 1.90 | 3.5 | +0.049 / +0.082 |
| 1% slippage | 280 | 52% | +0.086 | +0.013 | 2.36 | 4.6 | +0.070 / +0.103 |
| 3% slippage | 280 | 47% | +0.044 | −0.028 | 1.53 | 2.4 | +0.028 / +0.060 |

- **Seasons:** positive in all 9 (+0.015R to +0.162R).
- **Loss size:** worst trade −0.70R; 1 in 10 trades lost more than 0.23R.
- **Exposure:** up to 27 positions were open on one day, hence the 10-position cap in the playbook.

**Quarter by quarter** (default rules; *net* assumes ₹50,000 of premium spent on every trade, after costs).
Every trade is in [`results/runup_trades_by_quarter.csv`](../results/runup_trades_by_quarter.csv).

| Results | Reported | Trades | Won | Avg per trade | Net (₹50k each) | Best / worst |
|---|---|---:|---:|---:|---:|---|
| Q4 FY23 | Apr–Jun 2023 | 31 | 58% | +2.2% | +₹33,915 | DIVISLAB +61% / PNB −46% |
| Q1 FY24 | Jul–Sep 2023 | 30 | 33% | +9.0% | +₹1,34,465 | MPHASIS +164% / RELIANCE −70% |
| Q2 FY24 | Oct–Dec 2023 | 29 | 41% | +2.5% | +₹36,690 | HAL +118% / JSWSTEEL −33% |
| Q3 FY24 | Jan–Mar 2024 | 19 | 63% | +7.2% | +₹67,995 | INDUSINDBK +44% / WIPRO −23% |
| Q4 FY24 | Apr–Jun 2024 | 27 | 63% | +5.3% | +₹71,960 | BEL +37% / PERSISTENT −18% |
| Q1 FY25 | Jul–Sep 2024 | 23 | 35% | +3.1% | +₹36,115 | GRASIM +61% / HINDALCO −22% |
| Q2 FY25 | Oct–Dec 2024 | 54 | 59% | +16.2% | +₹4,37,440 | DLF +191% / HINDALCO −28% |
| Q3 FY25 | Jan–Mar 2025 | 38 | 50% | +1.5% | +₹29,340 | DIXON +59% / ITC −32% |
| Q4 FY25 | Apr–Jun 2025 | 29 | 38% | +4.5% | +₹64,835 | BEL +97% / NTPC −37% |
| **Total** | | **280** | **50%** | **+6.5%** | **+₹9,12,755** | |

All 9 quarters were positive, but Q2 FY25 alone made almost half the profit. Without it, the average is
+4.2% a trade. In weak quarters (+1.5% to +2.5%) a little extra slippage would have turned the result negative.

**Caveats**
- The expiry filter was chosen after seeing the data. It repeats with the 10-session entry and has a clear
  reason, but the unfiltered version (+3.5%) is the conservative estimate.
- Closing option prices can be stale. Entry legs had to have traded; a few exits used settlement prices.
  Restricting to traded exits lowers the result (+2.7%) but keeps it positive.
- Two years, 72 large liquid stocks, one market regime. Option P&L also depends on how closely your fills
  match the closing prices.

---

### 7.3 Out-of-sample check: all F&O stocks, Jun 2025 - Aug 2026

The 15-quarter report ([`reports/results_report_last_15_quarters.xlsx`](../reports/results_report_last_15_quarters.xlsx),
built only from NSE data) re-runs the run-up trade on all 213 current F&O stocks, including 5 results seasons
that came after the strategy was designed. Rule pass, after the same costs:

| | Trades | Avg per trade | Median | Win rate |
|---|---:|---:|---:|---:|
| Jan 2023 - May 2025, the 72 stocks tested above | 325 | +5.8% | -2.5% | 46% |
| Jan 2023 - May 2025, the other 141 F&O stocks | 323 | +4.9% | -2.3% | 46% |
| **Jun 2025 - Aug 2026 (new seasons), all stocks** | **556** | **+2.2%** | -5.0% | 39% |

By new season: +0.9%, -1.5%, +7.2%, +6.1%, -0.6%. The edge carried over to the wider universe, but in the
newest 15 months it was about 40% of its earlier size, and two of five seasons were slightly negative. At that
size a little extra slippage removes it. Treat the trade as marginal until more seasons confirm it.

## 8. What to do with this

1. **The only options trade to consider is the IV run-up straddle, and its edge has shrunk** (section 7.3) ([STRATEGY.md](STRATEGY.md) section 5).
   A separate stock-futures trade, buying results winners for 20 sessions, is in [PATTERNS.md](PATTERNS.md).
   Paper-trade one results season and compare your fills with the closing prices before risking money.
2. **Don't trade the event structures or the follow-through for profit as written.** Over this sample their expected value is about zero or negative.
3. If you still trade around results:
   - Use the playbook's **filters and risk rules**: skip FAIR events, defined risk only, 1% max loss, no direction across the numbers.
   - Measure your **actual fills against mid**. The only gross edge found (condors when IM/HM ≥ 1.2, about +0.03R) disappears above 0.5% slippage per leg.
4. **Keep the data growing.** Yahoo's calendar ends in May 2025. Add later seasons from the exchange's financial-results filings with
   `fo-results fetch --results-file my_results.csv` (columns `symbol,announce_date,announce_time` or `timing`), then re-run the backtest.
   A real edge should still be there as the sample grows.
