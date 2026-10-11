# Looking for a negative average (shorts)

Question: is there a rule whose stocks fall on average around results, so that shorting them (selling the stock future)
makes money?

Two windows were searched:

- **Before results**: short at the cutoff close (2 sessions before the result session), cover at the Day+1 close.
  Cost 0.17%. The average F&O result rises +0.04% here, so shorting every result loses about 0.2% a trade.
- **After results**: short at the reaction-day close (or a day later), hold 5 to 40 sessions, buy Nifty against it.
  Cost 0.19%. Results stocks beat Nifty by +0.42% over 20 sessions in this period, a headwind for shorts.

How it was tested:

- 131 rules in four families (40 "fall into results", 42 "losers keep falling", 35 "fade the over-reaction", 14
  walk-forward ranking models), using everything collected so far: lag and volume, technical, fundamental, past
  performance, F&O open interest and implied volatility, delivery and company news.
- Every rule was written down before its result was computed and searched **only on the first 14 quarters** (Jan-Mar
  2021 to Apr-Jun 2024 results). A rule became a finalist only if the short made money in both halves of that period,
  beat shorting every result by 0.5 points, and had at least 40 trades.
- A separate agent rebuilt the 3 finalists from scratch and tested them once on the **last 8 quarters** (Jul-Sep 2024
  to Apr-Jun 2026 results), which the search never saw. A third agent then tried to knock down what was left.

The stock list is today's F&O list, so stocks that fell and left F&O are missing. That biases every result here
**against** shorts, but not by enough to change any verdict.

## Answer

**No rule has a negative average that survives costs.** Only one group kept falling on the unseen quarters, results
losers already in a downtrend, and shorting it made +0.30% a trade there. Without the IT sell-off of February 2026 and
one quarter (Jul-Sep 2024 results, out in Oct-Nov 2024) it makes about -0.3%, and entered a day later it makes about
zero. The realistic expectation for the best short is **about 0% a trade**.

| Finalist | First 14 quarters (search) | Last 8 quarters (test) | Shorting every result, last 8 quarters | Verdict |
|---|---|---|---|---|
| **Results losers in a downtrend**: down 4%+ vs Nifty on the results day and below both the 50- and 200-day averages; short 20 sessions against Nifty | 88 trades, short +1.24% | 119 trades, short **+0.30%** (stocks -0.49% vs Nifty); -0.38% without the 5 biggest falls | -0.57% | Reject |
| **Weak reported numbers + a breakdown to a 20-day low on 1.5x volume**; short 20 sessions against Nifty | 74 trades, +0.65% | 71 trades, **-0.04%** | -0.57% | Reject |
| **Model ranking predicted falls** (gradient boosting, trained only on past quarters), short the bottom tenth for the 3-day pre-results window | 132 trades, +0.42% | 137 trades, **-0.54%** (the stocks rose +0.37%) | -0.11% | Reject |

None reached even an unadjusted p of 0.10 on the unseen quarters.

## Why shorting results stocks does not work here

- **The stocks drifted up.** Over the 20 sessions after results, the average F&O result beat Nifty by +0.79% in the
  first 14 quarters and +0.38% in the last 8. Shorting every result lost about 1% and 0.6% a trade.
- **Big moves keep going rather than reverse.** In the first 14 quarters, winners with RSI above 75 on the results day
  beat Nifty by a further +5.4% over 20 sessions; winners more than 15% above their 50-day average +4.6%; winners up
  8%+ on the day +1.8%. Failed gaps (opened up 3%+, closed below the open) went nowhere, so a fade only loses its costs.
- **Losers do not keep falling.** Plain results losers (down 4%+ vs Nifty) shorted for 20 sessions lost -0.31% in the
  first 14 quarters and made only +0.09% in the last 8. Shorting them a day later is worse: they tend to fall again on
  the next day and then drift back up.
- **Before results, nothing falls reliably.** All 40 pre-results rules lose money unhedged once their 5 biggest falls
  are removed. Rules that looked negative (quiet-volume laggards, late reporters, stocks that habitually fall into
  results, overbought stocks) made their money in 2021-22 and lost it in 2023-24.

## The closest: results losers in a downtrend

Losers that were already below both their 50- and 200-day averages did keep falling on the unseen quarters: -1.11%
raw, -0.49% vs Nifty over 20 sessions, 119 trades from 89 stocks, both halves of the test positive, 5 of 8 quarters
short-profitable. The fall is specific to results: the same setup on ordinary days is followed by a rebound of about 3%
against Nifty. But:

- **One sector shock carries it.** 12 IT trades give +31.6 of the +35.9 total profit; in the February 2026 IT
  sell-off every IT stock that reported fell about 14% vs Nifty, signal or not. Without IT the short makes +0.04%;
  without IT and the Jul-Sep 2024 results quarter, -0.28%. By entry year: 2024 +3.18%, 2025 +0.30%, 2026 -0.18%.
- **A few big falls.** Without its 5 biggest falls it is -0.38%, without 10 it is -0.79%.
- **No dose-response.** Bigger losers fell less: down 5%+ makes -0.01%, down 6%+ -0.66%. Most of the margin over
  shorting every result comes from the downtrend, not from the bad reaction.
- **Not distinguishable from luck**: against random picks among other downtrend stocks of the same quarter, p 0.21.
- **Realistic entry kills it.** Shorting at the next day's close with 0.27% costs makes +0.01% (-0.66% without the 5
  biggest falls), before rolling the future at expiry.
- **Squeeze risk.** The worst trade lost 24%, the biggest one-day jump against a short was +10.4%, and 20% of trades
  lost more than 5%.

A 40-session version of the same idea, looked at only after the test, made +0.89% on the unseen quarters but +0.10%
without its 5 biggest falls; it contains the same trades and is not independent evidence.

## Groups already known to be negative, on the unseen quarters

These were seen on the full sample earlier, so they are references, not discoveries:

| Group | Last 8 quarters: trades | Stock return (raw / vs Nifty) | Short profit after costs | Without the 5 biggest falls |
|---|---:|---|---:|---:|
| Lagged Nifty by 10%+ on quiet volume, 3-day pre-results short | 45 | -0.72% / -0.40% | +0.55% | -0.86% |
| Good reported numbers but still below the 50-day average, 20 sessions | 216 | -1.10% / -0.46% | +0.27% | -0.09% |
| Winners with a futures short build-up before results, 20 sessions | 24 | -1.11% / -0.80% | +0.61% | -1.53% |
| Plain results losers, 20 sessions | 200 | -0.74% / -0.28% | +0.09% | -0.39% |

All four fell a little in 2024-26, but each loses money once its 5 biggest falls are removed, and none is
distinguishable from chance.

## Conclusion

There is no reliable negative average around results in this data: the stocks that fall are not predictable well
enough to pay for shorting costs, squeeze risk and the general upward drift. Keep the project long-only:

- before results: the lag 10% + volume rule (realistic +1% to +1.5% a trade);
- after results: the results-winner trade (realistic about +1% a trade over Nifty).

Use the negative groups only as **"avoid" lists** for long trades. Losers in a downtrend, and good numbers still below
the 50-day average, did not do well. If you want to keep the short idea alive, log "results losers below both
averages, short 20 sessions against Nifty" on the coming seasons with no money on it.

Files: scripts in `pattern_tests/negative_avg/` (search_pre, search_post, search_fade, search_model: the four searches
with their `candidates.txt` written before any result; holdout: the independent rebuild and the last-8-quarter test with
its `plan.txt`; skeptic: the adversarial checks), outputs in [results/negative_avg/](../results/negative_avg/). The
scripts read `LAB_ROOT` (the scratch data folder) and `REPO_ROOT`.
