# Can a pre-results screen average 2% in the 3-day window every quarter?

Question: find stocks, picked before the numbers, whose three-day window (Day-1 + Result day + Day+1; buy at the close
2 sessions before the result session, sell at the Day+1 close) averages **2% or more in every one of the last 22
quarters** (Jan-Mar 2021 to Apr-Jun 2026 results). Open search; fewer than 10 picks a quarter is fine. Also tested with
the take-profit rule: stop after Day-1 if it is up more than 3%, after the Result day if the two days add to more than 3%,
otherwise hold to Day+1.

## Answer

**No rule found does this on quarters it was not fitted to.** Every rule that hit 2% in most quarters of the search
period failed in the quarters kept aside, and shuffled data produced rules that looked about as good. The closest
candidates are listed below with what they really earn.

| | Picks | Average 3-day | Quarters at 2% or more |
|---|---:|---:|---:|
| All F&O stocks | 4,460 | +0.28% | **0 of 22** (best quarter +1.08%) |
| Only stocks in F&O at the time (see note below) | 3,278 | +0.04% | **0 of 22** (best quarter +0.96%) |
| Best open-search rules, on the 8 quarters kept aside | 54 - 173 | +0.3% to +1.4% | 0 - 2 of 8 |
| Score model fitted on earlier quarters only | 60 - 630 | -3.8% to +0.7% a quarter | 1 - 3 of 16 |
| Early reporters with a strong week (below) | 42 | +3.4% (+2.8% with the take-profit) | 13 of 22 |
| Your Condition A (below) | 32 | +3.1% | see below |
| Sector valuation, P/B financials / P/E consumer-IT-pharma (below) | 27 - 518 | -1.2% to +1.6% | at most 10 of 22 |
| Sector performance before results (below) | 299 - 730 | -0.2% to +0.9% | at most 4 of 22 |
| Fresh sector strategies, 619 variants ([SECTOR_STRATEGIES.md](SECTOR_STRATEGIES.md)) | - | none beats chance | at most 5 of 21 |
| Rules aiming at a +5% average over all quarters ([TARGET_5PCT.md](TARGET_5PCT.md)) | 11 - 125 | +0.5% to +1.9% on unseen quarters | - |

Note: "All F&O stocks" uses today's F&O list over the whole period, so it includes results from before a stock joined
F&O (1,182 results, +0.94% on average); stocks that later joined were mostly the ones that grew. On stocks that were
in F&O at the time, the window averaged +0.04% (-0.05% vs Nifty), i.e. a loss after costs.

## Data

22 quarters, 4,462 results, 212 F&O stocks, all from NSE: results dates and times (35 of 35 dates in your
matched_stocks file match), equity and F&O bhavcopies, index closes, results XBRL, corporate actions and dividends.
Fixes made for this work:

- Renamed stocks keep their history (ZOMATO -> ETERNAL, TATAMOTORS -> TMPV, LTIM -> LTM and 19 more), and days in the BE
  series are kept (JSWENERGY, CGPOWER, PATANJALI had gaps). 74 results had no prices before.
- Results announced as "Board Meeting held on <date> to consider financial statements" were being discarded (common in
  2021-22).
- Price history back to Nov 2015 for 3-year and 5-year returns; two splits missing from NSE's data added (SOLARINDS
  Jul-2016, JSWSTEEL Jan-2017).

## How it was tested

- 49 features known at the cutoff (2 sessions before the result session): returns from 1 week to 5 years, versus Nifty
  and sector, distance from the 52-week high and low, moving averages, volatility, volume, past results reactions,
  previous quarter's sales and profit growth, profit and sales trends, P/E, P/B, ROE, debt, size, days since the last
  dividend, option IV, India VIX, days after the quarter end, and how stocks that reported earlier this season moved.
- Every rule of 1 or 2 conditions (feature above or below a decile): 842 conditions, about 350,000 rules. A quarter passes if the rule
  picks at least 3 (or at least 1) stocks and they average 2% or more. Also a version where a quarter with no picks is
  "no trade" rather than a fail.
- Rules were chosen on the first 14 quarters (Q4 FY21 - Q1 FY25) and checked on the last 8 (Q2 FY25 - Q1 FY27).
- Luck check: the whole search repeated 100 times on three-day returns shuffled within each quarter.

## Open search

| Outcome | Minimum picks | Best rule | Search quarters at 2% | Kept-aside quarters at 2% | Kept-aside average |
|---|---:|---|---:|---:|---:|
| 3-day | 3 | 3-month vs sector > +8.6% and never paid a dividend | 11 / 14 | 1 / 8 | +0.53% |
| 3-day | 1 | 1-week < -1.5% and never paid a dividend | 12 / 14 | 2 / 8 | +0.77% |
| 3-day | 1, no-trade allowed | 1-week < -2.8% and never paid a dividend | 12 / 14 | 1 / 8 | +0.47% |
| Take-profit | 3 | 3-month vs Nifty > +10.5% and never paid a dividend | 10 / 14 | 0 / 8 | +0.29% |
| Take-profit | 1 | 1-week vs Nifty < -1.5% and never paid a dividend | 11 / 14 | 2 / 8 | +0.97% |
| Take-profit | 1, no-trade allowed | 76% above the 52-week low and 3-month vs Nifty < -13% | 9 / 14 | 2 / 8 | +1.35% |

The best rule found on shuffled data passes 1 kept-aside quarter (median), about what the real rules managed.

**What the search kept finding: stocks that have never paid a dividend.** 44 such stocks (growth and new-age
companies) did well around results while growth stocks rallied, then stopped:

| Average 3-day window | Never paid a dividend | Pay dividends |
|---|---:|---:|
| First 14 quarters (Jan 2021 - Jun 2024 results) | +1.82% | +0.19% |
| Last 8 quarters (Jul 2024 - Jun 2026 results) | -0.05% | +0.12% |

**Score model.** A ridge regression on the same 49 features, refitted each quarter on earlier quarters only, buying stocks
whose score is in the top 2.5-20% of earlier scores: averages -3.8% to +0.7% a quarter, 1-3 of 16 quarters at 2%, no
better than the same model on shuffled data.

## Early reporters with a strong week

Rule: the stock rose 5.9% or more in the week up to the cutoff, and its results come within 19 days of the quarter end
(IT, banks, AMCs, brokers). It was found on 8 quarters, then checked on 7 later quarters and on the 7 earlier quarters
(2021-22) that were not used at all.

- 42 trades, about 2 a quarter (none in 4 quarters): three-day +3.35%, take-profit +2.81%, 13 of 22 quarters at 2%.
  The 7 unused earlier quarters: 10 trades, take-profit +2.14%, 3 of 7 quarters at 2%.
- Three independent checks (recompute from the raw prices, a skeptic, a threshold map) agree the numbers are right but
  the rule is not a dependable 2% edge:
  - Above Nifty it earns about +1.3% to +1.6% a trade; above other stocks reporting on the same day about +0.5%,
    not statistically significant.
  - Either condition alone earns nothing (+0.3% and +0.1%). A limit of 21 days instead of 19 turns the unused
    quarters from +2.1% to -1.7%. Measuring the week one session earlier halves the result.
  - ANANDRATHI and ANGELONE make 13 of 42 trades; 20 of 42 trades were in stocks not yet in F&O; without the top 3
    trades the take-profit average is +1.6%.
  - After searching this many rules, a rule passing the unused quarters by luck was likely (about 94%).
- Realistic expectation: about +1% above the market after costs, with zero not ruled out. Worth paper-trading with the
  thresholds fixed (not changed after seeing new results), not trading with size.

## Your Condition A / B

Measured as in your file (cutoff 2 sessions before the result session, total returns, sector = the NSE sector index
because BSE is not reachable from here):

| Screen | Picks | Stocks | Average 3-day | Up | vs other stocks that quarter |
|---|---:|---:|---:|---:|---:|
| Condition A | 32 | 14 | +3.12% | 66% | +2.72% (t 2.4) |
| Condition B | 76 | 45 | +0.96% | 61% | +0.55% (t 0.7) |
| A or B | 88 | 46 | +1.71% | 63% | +1.36% |
| A or B, P/B above peers | 30 | 20 | +2.37% | 73% | +2.02% |

- A or B reaches 2% in 8 of 22 quarters (quarters range from -6.2% to +8.4%).
- Condition A is the strongest screen in this work, but it lost to the average stock in results up to May 2023 (-0.9%)
  and beat it by +3.8% after that, it rests on 14 stocks, and it was designed while looking at the same years, so this is not an
  independent test.
- Of the individual parts, only "profits rising 4 quarters" (+0.36% vs the quarter) and "no dividend in 365 days"
  (+0.47%) add anything alone.

## Valuation by sector: P/B for financials, P/E for consumer, IT and pharma

Banks and NBFCs (and as a variant metals and real estate) valued on P/B; FMCG, IT services, pharma and consumer brands
on P/E. Each stock is compared with its sector peers valued on the same date (using only fundamentals already
published), and with its own last 2 years. Insurers could not be tested (their filings use a format the report cannot
read), and P/B exists only from the Oct-Dec 2022 results (earlier results filings have no balance sheet). Two
independent checks rebuilt the valuations from the raw data (1,810 of 1,821 match; the rest are mis-scaled share counts
in filings, handled correctly) and reproduced every figure.

| Test | Picks | Avg 3-day | vs all stocks that quarter | Quarters at 2% |
|---|---:|---:|---:|---:|
| All your sectors | 1,949 | +0.22% | -0.06% | 0 / 22 |
| Cheapest third vs peers (P/B or P/E) | 518 | +0.49% | +0.37% (t 1.5) | 3 / 22 |
| Dearest third vs peers | 518 | +0.25% | -0.02% | 4 / 22 |
| Banks + NBFCs, cheaper on P/B vs peers | 246 | +0.27% | +0.10% | 1 / 15 |
| Banks + NBFCs, dearer on P/B vs peers | 256 | -0.17% | -0.60% | 1 / 15 |
| FMCG + IT + pharma + consumer, cheapest third on P/E | 351 | +0.77% | +0.51% (t 2.0) | 4 / 22 |
| Consumer brands, P/E above peers | 111 | -1.24% | -1.50% (t -3.0) | 2 / 22 |
| IT services, P/E above peers | 134 | +1.06% | +0.86% (t 1.6) | 10 / 22 |
| Your Condition A or B in these sectors, valuation above peers | 27 | +1.56% | +0.10% | 6 / 16 |

- No valuation scheme comes close to 2% a quarter (best subset average about +1.2-1.6% on a few dozen picks).
- Cheap vs expensive on P/B makes little difference for banks and NBFCs; on P/E the cheapest third did a little better
  in 2021-24 (+0.66% vs the quarter) but not in the last 8 quarters (-0.12%).
- Expensive consumer brands doing worse is the only result with a consistent link to valuation, but it is fragile: it
  rests on a few always-expensive names (DMART, TITAN, DIXON, AMBER) and a few crashes (KAYNES twice, AMBER); without the
  3 biggest crashes t falls to -1.85, it does not show against the stock's own history, and among the 8 groups tested
  it is consistent with chance (p about 0.11). Shorting them for the three days netted about +1% a trade, +0.5% without
  those crashes. At most, a reason to be careful buying richly priced consumer names into results.
- "Expensive IT and FMCG did better" is not a valuation effect: it is a few always-expensive midcap winners (COFORGE,
  KPIT, PERSISTENT, VBL) and reverses when each stock is compared with itself.

**The single cheapest stock in each peer group** (ranked on its cutoff date; groups with 4+ valued stocks): 111 picks
over 22 quarters, about 5 a quarter. Average 3-day +0.84% (+0.67% after costs), 57% up, 8 of 22 quarters at 2% or more,
15 of 22 positive. But +1.62% a quarter in the first 14 quarters and +0.00% in the last 8 (only 1 at 2%; the last two
quarters -2.4% and -3.0%). It is the same names again and again (GODFRYPHLP 14 times, CROMPTON 12, WIPRO 12, DRREDDY 9,
BANKINDIA 8), the median pick is +0.52%, and without the 3 best events the average is +0.44%. One-off gains can make a
P/E look cheap (NAUKRI in 2021-22, after its investment gains). The 2nd + 3rd cheapest averaged +0.51% (4 of 22
quarters at 2%), and the 2nd + 3rd most expensive +0.43% (5 of 22). Per-quarter list:
[results/target_2pct/cheapest_in_peer_group.csv](../results/target_2pct/cheapest_in_peer_group.csv).

**The middle of the peer group** (place = half the group size, so 6 stocks -> 3rd, 14 -> 7th): 107 picks, average
3-day -0.50%, 49% up, positive in only 9 of 22 quarters (7 at 2% or more), -0.85% against all stocks that quarter;
+0.04% a quarter in the first 14 quarters, -1.62% in the last 8. Two-thirds of the way from the cheapest (6 -> 4th):
-0.52%, 3 of 22 quarters at 2%. List: [results/target_2pct/middle_place_in_peer_group.csv](../results/target_2pct/middle_place_in_peer_group.csv).

**At or below the middle place (6 stocks: 1st-3rd cheapest) with sales up in each of the last 4 reported quarters:**
235 picks, about 11 a quarter, average 3-day +0.32%, 53% up, 5 of 22 quarters at 2% or more, 14 of 22 positive,
+0.28% against all stocks that quarter (t 0.6); +1.00% a quarter in the first 14 quarters, -0.19% in the last 8. Rising
sales add little on their own (+0.23%, any place). List:
[results/target_2pct/cheaper_half_sales_rising.csv](../results/target_2pct/cheaper_half_sales_rising.csv).

**Cheapest two-thirds of the peer group (the dearest third dropped; 6 stocks: places 1-4) with sales rising 4
quarters:** 326 picks, about 15 a quarter, average 3-day +0.18% (+0.01% after costs), 51% up, 4 of 22 quarters at 2% or
more, 11 of 22 positive, +0.07% against all stocks that quarter; +0.55% a quarter in the first 14 quarters, +0.01% in
the last 8. The dropped dearest third with rising sales did about the same (+0.30%). List:
[results/target_2pct/cheapest_two_thirds_sales_rising.csv](../results/target_2pct/cheapest_two_thirds_sales_rising.csv).

## The take-profit rule and 1-week vs Nifty

| Group (1-week vs Nifty, before results) | Picks | 3-day hold | Quarters at 2% | Take-profit | Up | Quarters at 2% |
|---|---:|---:|---:|---:|---:|---:|
| All stocks | 4,460 | +0.28% | 0 / 22 | +0.22% | 53% | 0 / 22 |
| Beat Nifty by > 10% | 115 | +0.23% | 7 / 22 | -0.18% | 50% | 6 / 22 |
| Beat Nifty by > 5% | 490 | +0.28% | 3 / 22 | +0.15% | 54% | 5 / 22 |
| Beat Nifty by > 2% | 1,292 | +0.32% | 2 / 22 | +0.21% | 52% | 1 / 22 |
| Lagged Nifty by > 5% | 346 | +0.56% | 4 / 22 | +0.29% | 56% | 4 / 22 |
| Lagged Nifty by > 10% | 47 | +3.26% | 9 / 22 | +2.41% | 68% | 7 / 22 |

- The take-profit raises the share of winning trades a little but lowers the average: stocks sold after Day-1 was up
  more than 3% (362 trades) still had +0.44% to come on average, and those sold after the Result day had +0.22% more on
  Day+1.
- Last week's move does not predict the window (rank correlation -0.01). The "lagged by more than 10%" row (about 2
  picks a quarter) was noticed after looking at this table, so treat it as an idea to test, not a finding.

## Sector performance before results

Each stock's sector index (the Nifty sector index matched to its industry; 4,075 results, the rest only had the Nifty
500) measured at the cutoff: its 1-week, 1-month and 3-month return, the same against Nifty, its rank among 20 sector
indices, its distance from its 50-day and 200-day averages and its 52-week high, how the sector's stocks that already
reported this season did, and the stock against its own sector.

**First look.** Comparing the top and bottom third of stocks each quarter, a hot sector seemed to mean a worse window:

| Sector measure at the cutoff | Hot third | Cold third | Difference | t |
|---|---:|---:|---:|---:|
| Sector 1-month return | -0.18% | +0.70% | -0.88% | -3.8 |
| Sector 3-month return | -0.17% | +0.51% | -0.68% | -3.4 |
| Sector vs its 50-day average | -0.16% | +0.76% | -0.92% | -3.3 |
| Sector distance from its 52-week high (near the high = hot) | -0.33% | +0.77% | -1.10% | -4.8 |
| Same-sector stocks already reported this season | -0.23% | +0.65% | -0.88% | -3.4 |
| Sector vs Nifty, 1 month | +0.22% | +0.26% | -0.05% | -0.2 |
| Sector rank among 20 sector indices, 1 month | +0.39% | +0.21% | +0.18% | 0.8 |
| Stock vs its sector, 1 month | +0.37% | +0.31% | +0.06% | 0.3 |

**Checked, it does not hold.** Two independent checks rebuilt every number from raw index closes (all match) and found:

- **Most of it is made by the test itself.** Ranking stocks against others reporting later in the same season is
  biased: a later stock's 1-month return already contains an earlier stock's three-day window, so a good early window
  pushes later stocks into the "hot" third and leaves the early stock in the "cold" third. Random price paths with no
  real pattern give -0.5% to -0.9% from the same test. Tested without that bias (thirds set across all quarters) the
  difference is -0.3% (t -1.1) for the 1-month return and -0.4% (t -1.5) for the 52-week high.
- **The rest is the whole market, not the sector.** About 80% of the 1-month difference is the Nifty's own move over
  the same three days; against Nifty it is -0.16% (t -0.8). Comparing stocks that report on the same day, a hot sector
  does no worse than a cold one (+0.04%). That is why sector vs Nifty, sector rank and stock vs sector show nothing.
- **It is not about results.** Windows 10-20 sessions before results, with no results in them, show the same market
  part; over all days in 2021-26, Nifty's 1-month return does not predict its next 3 days.
- **Not tradeable.** The thirds above use the whole quarter's values, not known on the day. Real-time versions, after
  0.17% costs: buying stocks in the coldest third of sectors that day +0.01% a trade (48% up); using a fixed or rolling
  threshold +0.15% to +0.22% (against +0.07% for buying every result); hedged with Nifty, about 0. The best real-time
  version (buy when the sector's stocks that already reported did badly): +0.38% a trade, 4 of 21 quarters at 2%, +0.26%
  in the last 8 quarters, +0.22% hedged.

Simple rules (strong or weak sector, stock leading or lagging it, sector bounce from far below its 52-week high, sector
stocks already reported up or down) gave -0.18% to +0.86% a trade and 0-4 of 22 quarters at 2%. The open search on the
sector measures found rules that passed 9-10 of the first 14 quarters but only 3 and 1 of the last 8, and 9-11% of
searches on shuffled data did as well. **Sector performance gives no edge for the three-day window.** At most: after
the market and the sector have run up, the next three days have been slightly weaker, which goes away once hedged.

Files: [sector_bucket_tests.csv](../results/target_2pct/sector_bucket_tests.csv) (the first-look table, without the
corrections), [sector_rule_tests.csv](../results/target_2pct/sector_rule_tests.csv),
`sector_search_summary_min1.json` / `_min3.json`.

## What to do with this

- A 2%-every-quarter rule is not supported by 22 quarters of data. Individual quarters swing too much: even the best
  screens run from about -6% to +8% a quarter with a few picks.
- If you trade a screen, fix it now (Condition A, or the early-reporter rule), paper-trade 4-6 new quarters without
  changing it, and judge it against Nifty and against other stocks reporting the same week.
- The trades that held up best earlier are separate: the pre-results IV run-up straddle (STRATEGY.md section 5) and
  buying results winners for 20 sessions (PATTERNS.md).

Files: [results/target_2pct/](../results/target_2pct/) (search results, shuffled bests, walk-forward, the early-reporter
trades, Condition A/B matches). Scripts: `pattern_tests/features22.py`, `search22.py`, `walkforward22.py`, `screen.py`, `valuation.py`,
`sector.py`.

```bash
cd pattern_tests
python3 features22.py DATA features.csv
python3 search22.py features.csv OUT 100 3            # also: 100 1, 100 1 --no-trade-ok, and --tp3 for the take-profit
python3 walkforward22.py features.csv OUT 100 6       # add --tp3 for the take-profit
python3 screen.py DATA OUT                            # Condition A / B
python3 valuation.py DATA OUT                         # P/B / P/E by sector (reads OUT/screen_events.csv if present)
python3 sector.py DATA features.csv OUT               # sector performance; then search22.py on OUT/sector_features.csv
```
