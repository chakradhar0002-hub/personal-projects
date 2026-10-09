# Results winners with RSI above 50, all quarters

Question: does the results-winner trade work better if you only buy winners that were already strong before the
results (RSI(14) above 50), and does it hold in every quarter?

The rule, fixed in advance in the earlier TA+FA study ([TA_FA_COMBINED.md](TA_FA_COMBINED.md)) and not changed here:

1. **Winner**: on the reaction day (the first session that trades on the numbers), the stock beats Nifty 50 by more
   than 4%.
2. **RSI**: the stock's RSI(14) at the cutoff close (2 sessions before the result session) is above 50.
3. Buy at the reaction-day close, hold 20 sessions, short Nifty 50 for the same value. Costs 0.19% (0.17% stock, 0.02%
   hedge). Only stocks in F&O at the time.

All three computations agree trade for trade (to 0.0001%): the main study, an independent rebuild with its own RSI
code, and a reconcile run. Every trade was also checked against raw exchange prices.

## Answer

- **It traded in all 22 quarters and made money in 17 of them**: 232 trades in 123 stocks, **+2.42% a trade over Nifty
  after costs** (median +2.21%, 62% of trades up). Plain winners make +1.45%; winners with RSI 50 or below make +0.04%.
- **It is not every quarter, and it is not proven.** It lost in 2021 and 2022, 2023 alone gives 46% of the profit, and
  it was the best of 117 post-results tests, so after allowing for that search it is not significant.
- **Realistic expectation: about +1% a trade over Nifty** after realistic entry and costs (range roughly 0 to +2%).
  Skipping winners with RSI 50 or below still looks sensible: they earn nothing, and lose money with a realistic entry.

## Quarter by quarter

20-session return over Nifty after costs. "Next open, 0.40% cost" is the same trade entered at the next session's open
with a fuller cost (see "Can it be traded?").

| Results for | Quarter | Trades | Up | Avg vs Nifty | Unhedged | All winners (n) | Winners RSI ≤ 50 (n) | Next open, 0.40% cost | Stocks (% vs Nifty) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Jan-Mar 2021 | Q4 FY21 | 8 | 6 | +1.08% | +4.39% | +0.40% (11) | -1.41% (3) | -0.09% | WIPRO +4.7, ICICIPRULI +8.9, UPL +4.5, BOSCHLTD -8.3, CONCOR +4.0, MOTHERSON -11.2, MUTHOOTFIN +3.6, BHARATFORG +2.3 |
| Apr-Jun 2021 | Q1 FY22 | 6 | 3 | +0.17% | +6.40% | -0.32% (9) | -1.30% (3) | +0.84% | ASIANPAINT -11.2, MPHASIS +9.1, SUNPHARMA -5.9, TECHM +9.7, SIEMENS -5.1, APOLLOHOSP +4.3 |
| Jul-Sep 2021 | Q2 FY22 | 11 | 4 | -2.47% | -5.88% | -1.81% (17) | -0.60% (6) | -2.63% | WIPRO -5.9, LTM +10.5, FEDERALBNK -7.5, TVSMOTOR +18.2, ICICIBANK -6.0, INDUSINDBK -19.5, BEL +2.2, INDIGO -8.7, PIDILITIND -4.2, APOLLOHOSP +6.7, ASHOKLEY -13.1 |
| Oct-Dec 2021 | Q3 FY22 | 4 | 3 | -0.08% | -2.51% | -4.09% (10) | -6.76% (6) | -0.97% | BANDHANBNK +0.1, AXISBANK +4.4, MARUTI +2.2, BANKBARODA -6.9 |
| Jan-Mar 2022 | Q4 FY22 | 3 | 1 | -0.13% | -2.23% | -0.51% (17) | -0.59% (14) | -0.07% | SHRIRAMFIN -0.1, INDUSINDBK -5.9, BRITANNIA +5.6 |
| Apr-Jun 2022 | Q1 FY23 | 9 | 3 | +0.31% | +3.17% | +0.61% (11) | +1.95% (2) | +0.33% | INDUSINDBK +6.0, ULTRACEMCO -4.8, BAJAJFINSV +7.4, SBILIFE -1.0, SUNPHARMA -9.0, IDFCFIRSTB +15.8, LUPIN -2.9, MANAPPURAM -3.6, HINDALCO -5.1 |
| Jul-Sep 2022 | Q2 FY23 | 9 | 2 | -2.47% | +0.14% | -2.71% (12) | -3.43% (3) | -2.15% | AXISBANK -7.4, MARUTI -9.9, ADANIENT -0.9, BANKBARODA +7.5, BOSCHLTD -3.2, PIIND -6.7, LUPIN +1.5, GLENMARK -2.4, MANAPPURAM -0.8 |
| Oct-Dec 2022 | Q3 FY23 | 9 | 5 | +2.13% | +0.33% | +2.33% (17) | +2.55% (8) | +1.85% | PERSISTENT +16.0, DRREDDY +4.7, TMPV -3.4, RECLTD -4.3, CHOLAFIN +3.0, JINDALSTEL -5.1, BRITANNIA -2.5, CUMMINSIND +9.0, APOLLOHOSP +1.8 |
| Jan-Mar 2023 | Q4 FY23 | 13 | 12 | +5.89% | +7.63% | +5.98% (14) | +7.20% (1) | +5.11% | ABB +6.7, CHOLAFIN +8.4, TVSMOTOR +4.7, MARICO +1.1, EICHERMOT -2.8, POLYCAB +3.1, DLF +3.5, ASTRAL +16.5, MUTHOOTFIN +2.4, DIXON +27.2, NAUKRI +1.5, BHEL +0.3, TORNTPHARM +3.9 |
| Apr-Jun 2023 | Q1 FY24 | 9 | 8 | +9.15% | +8.35% | +9.66% (11) | +11.95% (2) | +9.20% | POLYCAB +18.8, ASHOKLEY +4.3, MPHASIS +1.0, UNITDSPR -1.9, COLPAL +0.3, RECLTD +29.0, LICHSGFIN +4.7, BHARATFORG +14.2, NMDC +11.9 |
| Jul-Sep 2023 | Q2 FY24 | 5 | 5 | +16.34% | +22.82% | +12.36% (7) | +2.41% (2) | +16.65% | BAJAJ-AUTO +2.0, ALKEM +9.3, HINDPETRO +29.8, TRENT +10.2, PFC +30.4 |
| Oct-Dec 2023 | Q3 FY24 | 13 | 7 | +0.06% | +2.05% | +1.78% (18) | +6.24% (5) | -0.11% | INFY +5.3, WIPRO +4.9, OFSS +18.1, CIPLA -1.3, PERSISTENT -0.8, INDUSTOWER -5.8, BAJAJ-AUTO +6.8, VOLTAS +0.4, GODREJCP -1.3, TMPV +3.7, CUMMINSIND +4.0, NATIONALUM -13.6, NMDC -19.5 |
| Jan-Mar 2024 | Q4 FY24 | 14 | 12 | +5.81% | +9.17% | +3.31% (21) | -1.68% (7) | +4.58% | RECLTD +11.5, COALINDIA +3.1, GODREJCP +3.7, BHARATFORG +5.2, TVSMOTOR +12.1, POLYCAB +5.4, ABB -4.4, HAL +6.1, CONCOR +0.2, CROMPTON +4.2, ZYDUSLIFE -7.1, BEL +8.3, GLENMARK +4.8, MOTHERSON +28.3 |
| Apr-Jun 2024 | Q1 FY25 | 9 | 6 | +2.16% | +3.96% | +0.78% (17) | -0.78% (8) | +1.60% | TCS +0.7, ICICIPRULI +3.8, PETRONET +6.9, UNITDSPR +3.2, MPHASIS -1.2, COLPAL +5.8, MARICO -10.1, TRENT +11.2, JUBLFOOD -0.8 |
| Jul-Sep 2024 | Q2 FY25 | 3 | 2 | +3.05% | +0.91% | +0.38% (20) | -0.09% (17) | +4.09% | COFORGE +12.2, MFSL -6.3, PERSISTENT +3.3 |
| Oct-Dec 2024 | Q3 FY25 | 6 | 5 | +3.47% | -0.12% | -0.97% (22) | -2.64% (16) | +2.37% | KOTAKBANK +3.3, SRF +3.6, TATACONSUM -0.3, UPL +10.5, SAIL +2.8, MUTHOOTFIN +0.9 |
| Jan-Mar 2025 | Q4 FY25 | 19 | 13 | +3.53% | +5.38% | +3.42% (23) | +2.93% (4) | +3.25% | HDFCAMC +4.3, AUBANK +2.2, SBILIFE +2.1, RBLBANK -0.4, RELIANCE +1.7, PNBHOUSING -0.4, ADANIPORTS +11.2, BSE +25.1, PAYTM +6.5, LT +1.8, TITAN -2.9, ABCAPITAL +10.7, TIINDIA -2.5, DELHIVERY +3.8, DIVISLAB +1.4, ASTRAL +4.4, LICI -1.2, CUMMINSIND +3.1, NBCC -3.9 |
| Apr-Jun 2025 | Q1 FY26 | 5 | 4 | +5.03% | +5.33% | +3.23% (19) | +2.58% (14) | +4.30% | ETERNAL +8.8, AMBER -6.0, DELHIVERY +3.4, HEROMOTOCO +15.9, CUMMINSIND +3.1 |
| Jul-Sep 2025 | Q2 FY26 | 22 | 12 | +0.41% | +1.35% | -0.85% (31) | -3.95% (9) | -0.10% | PERSISTENT +4.1, AUBANK +6.0, BANKINDIA +13.5, FEDERALBNK +7.3, IDFCFIRSTB +2.5, RBLBANK -6.2, INDUSTOWER +3.9, VBL -6.5, ABCAPITAL +8.1, BHEL +9.9, POLICYBZR -2.8, BANKBARODA +0.7, POWERINDIA +5.1, ASTRAL -10.3, PAYTM -1.6, NATIONALUM +2.6, BHARATFORG -2.1, BIOCON -6.3, BSE -6.7, MFSL -0.9, BDL -13.4, MUTHOOTFIN +2.3 |
| Oct-Dec 2025 | Q3 FY26 | 15 | 9 | +2.97% | -0.82% | +1.91% (32) | +0.98% (17) | +2.57% | UNIONBANK +0.2, APLAPOLLO +10.6, BANKINDIA +0.8, INDIANB +2.6, AXISBANK +3.1, BEL -4.5, DELHIVERY -2.4, LICI -4.4, POWERINDIA +21.3, CROMPTON -0.7, SBIN +3.1, AMBER +5.1, BSE -2.8, MFSL -0.1, ABB +12.7 |
| Jan-Mar 2026 | Q4 FY26 | 23 | 10 | -0.15% | -2.08% | +1.04% (29) | +5.60% (6) | -0.36% | ANGELONE -3.0, HDFCAMC -3.3, NESTLEIND +6.5, PNBHOUSING +11.9, OFSS +10.0, ADANIENSOL -1.3, INDUSINDBK +4.1, VBL +3.0, BANDHANBNK +7.5, BHEL +11.4, CAMS -3.2, SRF +3.8, BHARATFORG +0.6, PAYTM -7.3, DABUR -9.8, TITAN -2.9, TATACONSUM -10.7, UPL -3.8, HINDPETRO -5.4, SOLARINDS -1.3, CUMMINSIND -7.2, GMRAIRPORT +7.1, NMDC -10.1 |
| Apr-Jun 2026 | Q1 FY27 | 17 | 11 | +3.82% | +2.94% | +2.07% (24) | -2.19% (7) | +3.23% | ICICIPRULI -5.2, BHEL -5.1, FEDERALBNK +0.3, TVSMOTOR +14.8, CONCOR +0.0, IDFCFIRSTB +0.1, KFINTECH +1.1, COFORGE +10.6, BAJAJFINSV -0.7, GAIL -5.0, TORNTPHARM -0.8, APLAPOLLO +17.1, DIVISLAB +12.9, NAUKRI +4.7, BOSCHLTD +11.2, ASTRAL -4.8, SOLARINDS +13.6 |
| **All 22** |  | **232** | **143** | **+2.42%** | +2.82% | +1.45% (392) | +0.04% (160) | +2.04% | 17 of 22 quarters positive |

- Losing quarters: Jul-Sep 2021 (-2.47%), Oct-Dec 2021 (-0.08%), Jan-Mar 2022 (-0.13%), Jul-Sep 2022 (-2.47%) and
  Jan-Mar 2026 (-0.15%). Three of the five are within 0.15% of zero. The longest losing run is 3 quarters (Jul-Sep 2021
  to Jan-Mar 2022); the longest winning run is 13 quarters.
- First 14 quarters: +2.65% on 122 trades, 10 of 14 positive. Last 8 quarters: +2.16% on 110 trades, 7 of 8 positive.
- It beat all winners of the same quarter in 15 of 22 quarters. The fair same-quarter gain over all winners is +0.63% a
  trade (90% range +0.10% to +1.18%); the pooled gap (+2.42% vs +1.45%) is larger because RSI > 50 winners bunch in
  strong quarters.
- Trades per quarter: 3 to 23 (median 9), rising in recent seasons.

## Overall

| | Trades | Avg vs Nifty | Median | Up | Without best 5 | Without best 10 | Unhedged |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Winners with RSI > 50** | **232** | **+2.42%** | +2.21% | 62% | +1.83% | +1.42% | +2.82% |
| All winners | 392 | +1.45% | +0.65% | 54% | +1.09% | +0.83% | +1.55% |
| Winners with RSI <= 50 | 160 | +0.04% | -0.58% | 43% | -0.54% | | -0.29% |
| All F&O results | 3,280 | +0.42% | -0.12% | 49% | +0.36% | | +0.89% |

| Year | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|
| Trades | 25 | 25 | 36 | 39 | 52 | 55 |
| Avg vs Nifty | -0.70% | -0.81% | +7.22% | +2.84% | +2.35% | +1.93% |

- Best trade PFC (Jul-Sep 2023) +30.4%; worst INDUSINDBK (Jul-Sep 2021) -19.5%.
- Without 2023: +1.54% a trade, against +0.73% for all winners. The single best quarter (Jul-Sep 2023, 5 trades,
  +16.3%) adds about 0.3% to the average.
- The top 5 stocks (TVSMOTOR, RECLTD, PFC, OFSS, APLAPOLLO) give 31% of the profit; IT services and NBFCs made the
  most, FMCG lost.
- A +3% take-profit exit cuts it to +1.08%: the gain needs the full 20 sessions.

## Holding period and variants (after the fact, not for choosing a rule)

| Hold (sessions) | 5 | 10 | 20 | 30 | 40 | 60 |
|---|---:|---:|---:|---:|---:|---:|
| Winners with RSI > 50 | +0.45% | +0.69% | **+2.42%** | +2.84% | +3.35% | +4.84% |
| All winners | +0.07% | +0.22% | +1.45% | +1.59% | +2.19% | +3.90% |
| Winners with RSI <= 50 | -0.48% | -0.47% | +0.04% | -0.22% | +0.49% | +2.57% |
| All F&O results | -0.12% | -0.08% | +0.42% | +0.58% | +0.92% | +1.80% |

(40 and 60 sessions lose the latest quarter's trades to the end of the data: 4 and 17 of the 232.) Most of the gain
comes between day 10 and day 20; longer holds earn more, but so does every F&O stock against Nifty in this period.

| Variant | Trades | Avg vs Nifty | Quarters positive |
|---|---:|---:|---:|
| RSI above 40 / 45 / **50** / 55 / 60 | 317 / 274 / **232** / 167 / 115 | +1.82% / +2.11% / **+2.42%** / +2.87% / +3.66% | 17 / 17 / **17** / 16 / 16 of 19 |
| RSI band 40-50 / 50-60 / 60-70 / above 70 | 85 / 117 / 86 / 29 | +0.18% / +1.20% / +2.93% / +5.82% | |
| Winner cut: beat Nifty by 3% / 5% / 6% / 8% (RSI > 50) | 343 / 164 / 127 / 58 | +2.29% / +3.27% / +3.10% / +2.63% | 18 / 20 / 18 / 15 of 19 |
| RSI measured at the reaction close instead | 350 | +1.54% | 15 |
| RSI > 50 and above the 200-day average | 182 | +2.60% | 17 of 21 |

- The higher the RSI before results, the better, in smooth steps; there is no cliff at 50. RSI 50-60 (+1.20%) earns
  less than all winners; most of the gain comes from RSI above 60.
- The winner cut hardly matters: at every cut, RSI > 50 earns +2.3% to +3.3% and RSI <= 50 earns about zero.
- RSI must be measured **before** the results. Measured after the jump, it adds nothing (+1.54%, the same as all
  winners).
- Picking a stricter cut from this table (for example RSI > 70: +5.82% on 29 trades) would be fitting the past.

## Is it real?

For it:

- Random picks of the same size from each quarter's winners do this well about 1% of the time (p 0.0105).
- The extra over all winners of the same quarter is positive in all 6 years (small in most), and RSI > 50 winners beat
  RSI <= 50 winners at every entry, cost, winner cut and holding period tested.
- It is not a market-regime effect: within weak, middling and strong Nifty phases the RSI gap is +2.9%, +2.8% and
  +1.7%.

Against it:

- **It was picked from many tests.** It was the best of 117 pre-registered post-results tests (Holm 1.00, family-wise p
  0.54), after 44 earlier TA screens that also tried RSI levels. Corrected for that selection, its extra over plain
  winners shrinks from +0.63% to about **+0.2% to +0.4%** a trade.
- **The trades overlap.** Treated as one daily portfolio, RSI > 50 winners minus RSI <= 50 winners is +1.70% per 20
  sessions with t 1.39: not significant. That long-short lost money in 2021, 2024 and 2026.
- **It is not special to winners.** Around results, strength before the numbers helps every stock: non-winners with
  RSI > 50 make +0.82% against -0.39%, and losers show the same pattern. On ordinary days without results the split
  goes the other way (quiet-day winners with RSI > 50: +0.36%, with RSI <= 50: +0.94%).
- **Part of it is sector and plain momentum.** RSI is 0.87 correlated with the 21-session return, so the two cannot be
  separated. RSI > 50 winners' sectors had risen +3.7% before results against -2.0%; measured against the stock's own
  sector, the extra over all winners falls to +0.35%.
- **One year carries it.** 2023 gives 46% of the profit; 2021 and 2022 lost money.

## Can it be traded?

| Version | Avg vs Nifty | Quarters positive |
|---|---:|---:|
| Study: buy at the reaction-day close, 0.19% cost | +2.42% | 17 of 22 |
| Buy at the next session's open, 0.19% cost | +2.25% | 18 of 22 |
| Buy at the next session's close, 0.19% cost | +2.15% | |
| Next open, 0.40% all-in cost (realistic for cash delivery) | +2.04% | 14 of 22 |
| Next open, 0.40% cost, only stocks already in F&O in 2021 | +1.41% | |
| Same, excluding 2023 | +0.62% (all winners +0.01%) | |

- **Entry**: you only know a stock beat Nifty by 4% near the close, so the next open is the safe entry. It costs about
  0.17%, and the gain over all winners stays the same (+1.24% for all winners, -0.22% for RSI <= 50 winners).
- **Costs**: 0.17% suits stock futures. Cash delivery pays 0.1% securities transaction tax on each side, so about 0.40%
  all-in is realistic. The edge survives costs up to about 2.4% a round trip.
- **Hedge**: shorting Nifty futures instead of spot is fine (about 0.02% roll and spread).
- **Book**: up to 21 positions open at once (mean 3.5; nothing open on 38% of days), 25-55 trades a year. The worst
  run was a -79% (in units of one position) drawdown from August 2021 to November 2022. On capital sized for the peak
  it returns about 4-5% a year before futures margin.
- **Survivorship is the biggest caveat**: the stock list is today's F&O list, so stocks that rose and stayed in F&O
  are over-represented. On stocks already in F&O in 2021 the rule earns +1.79% (172 trades); on later joiners +4.22%
  (60 trades). A momentum rule is exactly what this bias flatters.
- **Benchmark**: about 0.5% of the return is F&O stocks drifting above Nifty 50 in this period (+0.56% per 20 sessions
  on ordinary days). Against Nifty Midcap 150 the rule makes +1.22%.

## Conclusion

Winners with RSI above 50 traded in every quarter and made money in 17 of 22, at +2.42% a trade over Nifty in the
backtest. It is not +2% every quarter, and the honest forward estimate is about **+1% a trade over Nifty** after
realistic costs, with a range of roughly 0 to +2%.

What to do with it:

- Keep the results-winner drift as the post-results trade, and **skip winners whose RSI was 50 or below** before the
  results: across every check they earn nothing, and they lose money with a realistic entry.
- Treat the RSI > 50 version as a watch item to paper-trade, not a proven edge: enter at the next open, hold 20
  sessions, short Nifty futures against it, and expect about +1% a trade.
- Do not pick a stricter RSI cut (60 or 70) from this backtest.

Two data notes from the checks, neither affecting these 232 trades: 135 results filed between 15:00 and 15:29 are
dated to the results day although the market mostly reacted the next day, and in the first season (Jan-Mar 2021
results) only 98 of 189 results are flagged as F&O.

Files: scripts in `pattern_tests/winners_rsi/` (build: the main study; rebuild: the independent rebuild and raw-price
check; skeptic: selection, momentum, time, outliers, thresholds, sector and portfolio checks; tradability: entries,
costs, hedge, book and survivorship; reconcile: the trade-by-trade comparison), outputs in
[results/winners_rsi/](../results/winners_rsi/). The scripts read `LAB_ROOT` (the scratch data folder with
`tafa/C_post_results`, `ta/build`, `fa/build`, `sector_lab/data` and `report/nse_prices.db`).
