# Real-data results

The playbook in [STRATEGY.md](STRATEGY.md) was backtested on real NSE data, with every option
leg replayed at the actual closing prices from the NSE F&O bhavcopy.

> **Verdict: no tradable edge after costs.** Over 71 F&O stocks and about five results seasons
> (Apr 2024 – May 2025), every part of the strategy as written lost money after realistic costs.
> - The event trade (iron condor / long straddle) is roughly break-even *before* costs.
>   Options priced the results move about fairly.
> - The follow-through futures trade lost money even before costs.
>
> Treat the playbook as a risk-control framework (what to skip, how to size, defined risk only),
> not as a source of profit. Don't trade it with real money on the strength of these rules.

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

## 7. What to do with this

1. **Don't trade the event structures for profit as written.** Over this sample their expected value is about zero before costs and negative after.
2. If you still trade results:
   - Use the playbook's **filters and risk rules**: skip FAIR events, defined risk only, 1% max loss, no direction across the numbers.
   - Measure your **actual fills against mid**. The only gross edge found (condors when IM/HM ≥ 1.2, about +0.03R) disappears above 0.5% slippage per leg.
3. **Keep the data growing.** Yahoo's calendar ends in May 2025. Add later seasons from the exchange's financial-results filings with
   `fo-results fetch --results-file my_results.csv` (columns `symbol,announce_date,announce_time` or `timing`), then re-run the backtest.
   A real edge should still be there as the sample grows.
