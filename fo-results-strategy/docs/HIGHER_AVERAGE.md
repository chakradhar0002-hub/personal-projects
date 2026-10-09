# A higher average for the results-winner trade

Question: can the "winners with RSI above 50" trade ([WINNERS_RSI50.md](WINNERS_RSI50.md)) be made to earn more per
trade? The base trade: the stock beats Nifty 50 by more than 4% on its reaction day, its RSI(14) two sessions before
the results is above 50; buy at that close, hold 20 sessions, short Nifty against it. It made +2.42% a trade over Nifty
after costs over 22 quarters (realistic about +1%).

How it was tested:

- Five families of ideas, 136 versions in all, were searched **only on the first 14 quarters** (Jan-Mar 2021 to Apr-Jun
  2024 results). Every version was written down before its result was computed.
- Each family put forward at most 2 finalists by a rule fixed in advance (enough trades, and beating the base trade by
  at least 0.5% a trade even without its best 5 trades).
- The 8 finalists were rebuilt from scratch by a separate agent and tested once on the **last 8 quarters** (Jul-Sep
  2024 to Apr-Jun 2026 results), which the search never saw. A third agent then tried to knock down what survived.

## Answer

**Only one change kept a higher average on the unseen quarters: hold the same trades 60 sessions instead of 20.** It
roughly doubles the average per trade, but only because the money stays in the market three times as long; it earns
the same per day. Every attempt to raise the average by picking fewer, "better" trades fell back to the base trade on
the unseen quarters, and options only added leverage and large losses.

| Idea | First 14 quarters (search) | Last 8 quarters (test) | Base trade, last 8 quarters | Verdict |
|---|---|---|---|---|
| **Hold 60 sessions instead of 20** | 122 trades, +4.64% | **93 trades, +5.10%** | +1.85% (same trades) | Watch |
| Pullback entry, then hold 60 | 119, +4.25% | 92, +4.43% | +1.77% (same trades) | Reject: F3 with a worse entry |
| Bigger winners (beat Nifty by 5%+) | 89, +4.12% | 75, +2.26% | +2.16% | Reject |
| Close above the 20-day high on volume | 100, +3.86% | 94, +2.09% | +2.16% | Reject |
| Only when India VIX is low (13.35 or less) | 41, +6.91% | 52, +2.32% | +2.44% (same 4 quarters) | Reject |
| Ranking by RSI and size of the jump, top ~5 a quarter | 53, +5.56% | 46, +2.47% | +2.16% | Reject (+0.72% without best 5) |
| Buy the at-the-money call (return on premium) | 118, +49.5% | 110, **-10.3%** | | Reject |
| Buy the 5% out-of-the-money call (return on premium) | 115, +70.5% | 108, **-26.8%** | | Reject |
| *Base trade (winners, RSI > 50, 20 sessions)* | *122, +2.65%* | *110, +2.16%* | | |

All figures are per trade over Nifty after costs, except the two option rows (return on the premium paid, not hedged).
The search periods' averages were inflated by 2023, which gave 60-90% of the profit for every stricter filter.

## Hold 60 sessions: why only "watch"

On the last 8 quarters: 93 trades, +5.10% a trade (median +4.75%, +3.11% without the best 5, all 7 quarters with a
full 60 sessions positive) against +1.85% for the same trades held 20 sessions. With entry at the next open and a 0.40%
cost it still makes +4.72%. Over all 22 quarters: 215 trades, +4.84% (the 17 trades from Apr-Jun 2026 results cannot be
scored until about November 2026).

| Hold (sessions), same 93 trades, last 8 quarters | 20 | 30 | 40 | 50 | 55 | 60 |
|---|---:|---:|---:|---:|---:|---:|
| Average per trade | +1.85% | +2.66% | +3.68% | +5.01% | +5.34% | +5.10% |
| Average per 20 sessions held | +1.85% | +1.77% | +1.84% | +2.01% | +1.94% | +1.70% |

- **Same return per day.** The gain per 20 sessions held stays at about +1.8% whatever the hold. Run as daily
  portfolios, the 60-session version beats the 20-session one by +0.03% per 20 sessions over all 22 quarters (t 0.06).
  More per trade, not more per month.
- **More capital tied up.** On average 12 positions are open at once (up to 24), against about 5.
- **Much of it is generic drift.** In the last 8 quarters any F&O stock beat Nifty by +1.48% over 60 sessions (+0.19%
  over 20), and winners with RSI 50 or below get a similar boost from holding longer. The RSI filter is not what makes
  the long hold work.
- **Survivorship.** The stock list is today's F&O list. 73% of the unseen-quarter gain came from stocks that joined F&O
  after 2021 (+7.46% against +2.32%); stocks already in F&O in 2021 made +3.07% against +1.46%.
- **A few trades carry it.** The best 10 trades give 66% of the last-8-quarter profit (POWERINDIA +58%, NATIONALUM
  +45%, DELHIVERY +35%, OFSS +32%, BSE +32%). 19% of trades were more than 10% down at some point while held.
- **Not a blind test.** The 60-session numbers had already been computed in the earlier study (on all 22 quarters,
  published as +4.84%), so this confirms a pattern that was already visible rather than discovering it. Allowing for
  trades in the same quarter moving together, it misses the significance bar (adjusted p 0.13).

Realistic expectation: about **+2% a trade over Nifty for a 60-session hold** (range roughly 0 to +4%), against about
+1% for the 20-session version. On stocks already in F&O in 2021, with next-open entry and 0.42% cost, it made +3.44%
a trade over 22 quarters, +2.08% after taking out the drift every F&O stock had, and it lost money in 2021 and 2026.

## What did not raise the average

- **Stricter entry filters** (38 tried): higher RSI (60, 65, 70), a bigger jump on the day, volume, breakouts to 20-day
  or 52-week highs, closing near the day's high, a gap that held, strong reported numbers, momentum before results,
  stock size. The best looked like +4% to +6% a trade on the search quarters, all from 2023, and fell back to the base
  trade on the unseen quarters.
- **Exits** (29 tried): trailing stops (10-day low, 20-day average, 10% off the high), stop-losses (-8%, -10%) and
  pullback entries all did worse than simply holding. A +10% take-profit with a 60-session cap was the most consistent
  (13 of 14 search quarters positive, median +6.2%) but did not raise the average.
- **Market and sector backdrop** (35 tried): Nifty trend, sector trend, breadth, early or late in the season, banks vs
  others. Only low India VIX stood out, and that was 2023 in disguise.
- **Ranking models** (23 tried): ridge, logistic and gradient-boosting models trained only on past quarters did no
  better than plain winners. A simple rank of RSI and the size of the jump looked best and still fell back on the unseen
  quarters.
- **Options** (11 tried): a bought call made +50% to +70% of premium in the search quarters, almost all from the 2023
  rally, then lost 10% to 27% of premium a trade on the unseen quarters. Half or more of the trades lost more than half
  the premium. Even in the good years, the return per unit of risk was worse than holding the stock. Stock futures
  raise the percentage on your money only by leverage: about 4x the gain on a 25% margin, and 4x the losses.

## Conclusion

The average can be raised only by holding longer, and that is a trade-off, not a better signal: about twice the return
per trade for three times the time in the market, with much of the extra coming from F&O stocks drifting above Nifty.
There is no honest version of this trade that averages much more than about +1% per 20 sessions.

What to do:

- Keep the base trade (winners with RSI above 50, 20 sessions, next-open entry) as a paper trade.
- Paper-trade a 60-session hold of the same trades alongside it, starting with the Jul-Sep 2026 results (out in
  October-November 2026). That is the first test neither version has seen.
- Do not add stricter filters, VIX timing, ranking models or options on this evidence.

Files: scripts in `pattern_tests/more_avg/` (search_signal, search_exit, search_context, search_ranking,
search_instrument: the five searches, each with its `candidates.txt` written before any result; holdout: the
independent rebuild and the last-8-quarter test with its `eval_plan.txt`; skeptic: the adversarial checks), outputs in
[results/more_avg/](../results/more_avg/). The scripts read `LAB_ROOT` (the scratch data folder) and, for one fetch
script, `REPO_ROOT`.
