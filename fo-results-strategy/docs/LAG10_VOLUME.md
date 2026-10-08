# Lagged Nifty by more than 10% (or 15%, 20%) and above-average volume: every quarter

Rule, at the cutoff close (2 sessions before the result session), stocks in F&O at the time:

- the stock's 21-session return is more than 10 points below Nifty 50's, and
- its average volume over the last 5 sessions is at least its 60-session average (volume adjusted for bonuses and
  splits inside the window).

Buy at the cutoff close; sell at the Day+1 close (3-day) or with the take-profit rule (Day-1 close if Day-1 > +3%,
else Result-day close if Day-1 + Result day > +3%, else Day+1 close). Rebuilt from the raw daily returns and NSE volume;
it matches the earlier feature file exactly wherever no split or bonus falls inside the volume window.

## Summary

| Exit | Trades | Up | Average | After 0.17% cost | Quarters with trades | Positive | At +2% or more | Without best 5 trades |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 3-day | 85 | 63.5% | +2.13% | +1.96% | 19 of 22 | 18 of 19 | 8 | +1.36% |
| Take-profit | 85 | 71.8% | +2.14% | +1.97% | 19 of 22 | 17 of 19 | 9 | +1.54% |

- No trade in 3 quarters (Apr-Jun 2021, Jul-Sep 2023, Jan-Mar 2026). About 4 trades a quarter, 0-12.
- The only losing quarter with the 3-day exit was Apr-Jun 2023 (BANDHANBNK -2.8%, SRF -3.5%); with take-profit Jan-Mar
  2022 was also slightly negative (-0.26%).
- First 14 quarters +1.65% a trade, last 8 +2.86%. Worst trade -11.3% (ETERNAL), best +19.1% (ADANIPORTS). No stock
  appears more than 3 times.
- Deep laggards on quiet volume did the opposite: -0.37% (109 trades), positive in 11 of 21 quarters.
- The same filter on dates with no results nearby makes about +0.65% over 3 days (positive in 19-20 of 22 quarters), so
  about +1.5% a trade is linked to results.
- Caution: the 10% and 1.0x cut points were picked after looking at the data (see [LAG5_PATTERNS.md](LAG5_PATTERNS.md)),
  so this is not an out-of-sample result. Nearby cut points give similar numbers rather than falling off a cliff:

| Rule | Trades | Up | 3-day avg | Take-profit avg | Quarters with trades | Positive (3-day) | Without best 5 |
|---|---:|---:|---:|---:|---:|---:|---:|
| lag > 8%, volume ≥ 1.0x | 124 | 59% | +1.59% | +1.71% | 21 | 17 | +1.03% |
| lag > 10%, volume ≥ 0.8x | 131 | 58% | +1.45% | +1.52% | 20 | 17 | +0.90% |
| lag > 10%, volume ≥ 1.0x (this rule) | 85 | 64% | +2.13% | +2.14% | 19 | 18 | +1.36% |
| lag > 10%, volume ≥ 1.2x | 54 | 70% | +2.51% | +2.75% | 18 | 16 | +1.40% |
| lag > 10%, volume ≥ 1.5x | 32 | 78% | +3.05% | +2.44% | 12 | 10 | +1.31% |
| lag > 12%, volume ≥ 1.0x | 56 | 66% | +2.26% | +1.91% | 17 | 15 | +1.11% |
| lag > 15%, volume ≥ 1.0x | 32 | 69% | +2.71% | +2.82% | 11 | 10 | +0.68% |
| lag > 10%, volume < 1.0x (quiet) | 109 | 47% | -0.37% | -0.18% | 21 | 11 | -0.98% |

## Quarter by quarter (volume 1.0x or more)

| Results for | Quarter | Trades | Up | 3-day avg | Take-profit avg | Lag 10%+ on quiet volume | All F&O stocks | Stocks (3-day %) |
|---|---|---:|---:|---:|---:|---:|---:|---|
| Jan-Mar 2021 | Q4 FY21 | 4 | 1 | +0.75% | +3.14% | -0.80% (1) | +0.82% | BAJFINANCE +12.7, AUBANK -7.0, LTF -1.4, BANDHANBNK -1.3 |
| Apr-Jun 2021 | Q1 FY22 | 0 | 0 | - | - | -1.88% (7) | +0.06% |  |
| Jul-Sep 2021 | Q2 FY22 | 7 | 4 | +0.27% | +0.80% | -0.64% (7) | -0.84% | ULTRACEMCO -2.4, BIOCON -6.0, CROMPTON -0.7, POLYCAB +2.0, AMBUJACEM +1.5, EICHERMOT +4.0, PIIND +3.4 |
| Oct-Dec 2021 | Q3 FY22 | 5 | 4 | +3.21% | +2.89% | -1.00% (4) | -0.64% | DIXON -3.2, NAUKRI +8.7, TECHM +5.1, PIIND +4.7, ZYDUSLIFE +0.7 |
| Jan-Mar 2022 | Q4 FY22 | 7 | 2 | +0.42% | -0.26% | +1.21% (9) | -0.83% | RBLBANK -1.3, NMDC -1.0, OBEROIRLTY -4.0, JSWSTEEL +2.1, NAUKRI +12.2, AUROPHARMA -0.9, JINDALSTEL -4.2 |
| Apr-Jun 2022 | Q1 FY23 | 3 | 3 | +5.36% | +4.70% | -0.37% (4) | +0.75% | NMDC +6.6, GLENMARK +2.9, ZYDUSLIFE +6.6 |
| Jul-Sep 2022 | Q2 FY23 | 2 | 1 | +1.00% | +1.00% | -1.59% (7) | +0.03% | HINDPETRO -1.0, AUROPHARMA +3.0 |
| Oct-Dec 2022 | Q3 FY23 | 6 | 4 | +3.75% | +1.65% | +2.14% (1) | -0.16% | INDUSTOWER -7.9, BANKBARODA +8.5, SBIN +3.4, ADANIPORTS +19.1, AMBUJACEM +2.9, ADANIENT -3.5 |
| Jan-Mar 2023 | Q4 FY23 | 4 | 3 | +2.52% | +1.45% | +1.46% (3) | +0.61% | PERSISTENT +3.9, INDUSTOWER +4.3, LTM +5.5, MANAPPURAM -3.7 |
| Apr-Jun 2023 | Q1 FY24 | 2 | 0 | -3.15% | -3.15% | +0.20% (4) | -0.30% | BANDHANBNK -2.8, SRF -3.5 |
| Jul-Sep 2023 | Q2 FY24 | 0 | 0 | - | - | +3.50% (1) | +0.41% |  |
| Oct-Dec 2023 | Q3 FY24 | 4 | 3 | +1.76% | +1.76% | - | +0.48% | POLYCAB +1.9, IEX +3.0, AUROPHARMA +2.4, CROMPTON -0.2 |
| Jan-Mar 2024 | Q4 FY24 | 4 | 3 | +1.96% | +1.66% | -5.31% (1) | +0.88% | INFY +1.3, WIPRO +3.0, LTM -0.9, KOTAKBANK +4.4 |
| Apr-Jun 2024 | Q1 FY25 | 3 | 1 | +0.33% | +3.28% | +0.73% (15) | +0.53% | JINDALSTEL -1.5, CUMMINSIND +6.8, SAIL -4.3 |
| Jul-Sep 2024 | Q2 FY25 | 2 | 1 | +1.07% | +1.07% | -2.01% (5) | -1.12% | BHEL +3.6, MANAPPURAM -1.5 |
| Oct-Dec 2024 | Q3 FY25 | 12 | 8 | +1.99% | +1.95% | -5.21% (12) | -0.79% | JIOFIN +1.2, ETERNAL -11.3, LODHA +4.4, CGPOWER +1.3, CAMS -4.1, KALYANKJIL +14.8, POLICYBZR +5.1, PRESTIGE +6.8, GODREJPROP -2.4, CUMMINSIND +9.5, RECLTD +3.3, TRENT -4.9 |
| Jan-Mar 2025 | Q4 FY25 | 5 | 4 | +5.92% | +4.54% | +2.13% (10) | +0.96% | WIPRO -1.1, INFY +1.8, TATAELXSI +11.0, HCLTECH +10.6, SONACOMS +7.3 |
| Apr-Jun 2025 | Q1 FY26 | 1 | 1 | +2.65% | +2.65% | +0.83% (5) | -0.56% | COFORGE +2.6 |
| Jul-Sep 2025 | Q2 FY26 | 1 | 1 | +6.43% | +6.43% | +4.86% (4) | +0.67% | GODREJCP +6.4 |
| Oct-Dec 2025 | Q3 FY26 | 11 | 8 | +1.98% | +2.15% | -5.23% (2) | +0.18% | WAAREEENER +3.6, PREMIERENE -6.6, CGPOWER +1.9, LODHA +5.6, DIXON +2.6, ITC +1.1, PRESTIGE +4.9, SWIGGY -0.6, GODREJPROP +0.0, KALYANKJIL +13.3, NAUKRI -4.0 |
| Jan-Mar 2026 | Q4 FY26 | 0 | 0 | - | - | +2.40% (1) | -0.31% |  |
| Apr-Jun 2026 | Q1 FY27 | 2 | 2 | +5.27% | +10.72% | +0.55% (6) | +0.17% | INDIANB +9.2, KPITTECH +1.3 |

"Up" counts 3-day trades above zero. "All F&O stocks" is the average 3-day window of every F&O result that quarter.

## Stricter volume: 1.5x or more

| Exit | Trades | Up | Average | After 0.17% cost | Quarters with trades | Positive | Without best 5 trades |
|---|---:|---:|---:|---:|---:|---:|---:|
| 3-day | 32 | 78% | +3.05% | +2.88% | 12 of 22 | 10 | +1.31% |
| Take-profit | 32 | 81% | +2.44% | +2.27% | 12 of 22 | 10 | +1.15% |

An independent check rebuilt it from the raw data and agreed after one fix: COFORGE (Apr-Jun 2025 results) only passed
1.5x because of its 1:5 split inside the volume window (adjusted ratio 1.42x), so it is dropped here (it stays in the
1.0x rule). What the check found:

- **Higher average, fewer trades.** About 1.5 trades a quarter, no trade in 10 of 22 quarters, including the last two.
  The two losing quarters had a single trade each (JINDALSTEL -4.2%, MANAPPURAM -3.7%). First 14 quarters +2.81% (18
  trades), last 8 +3.35% (14).
- **Results matter.** The same filter on dates without results makes about +0.9% over 3 days, so roughly +2% a trade is
  linked to results; it beat random oversold stocks reporting in the same quarters (p about 0.005).
- **But 1.5x is not proven better than 1.0x.** Random picks of the same size from the 1.0x trades do as well about 1
  time in 5 (p 0.18). Without its best 5 trades it averages +1.3%, the same as the 1.0x rule. Higher volume cuts look
  better (1.6x +3.7% on 27, 2.0x +4.4% on 16) but all sit at +1.2-1.8% without their best 5 trades.
- **Lumpy.** Many trades come from crash rebounds: Feb 2023 (Adani fall: ADANIPORTS +19%, AMBUJACEM, SBIN, BANKBARODA),
  Jan 2025 and Jan 2026 (LODHA, PRESTIGE, GODREJPROP).
- **Take-profit hurts here** (+2.44% vs +3.05% held to Day+1).
- **About 100 cut-point combinations were looked at** in this family, and the stock list is today's F&O list (stocks
  that crashed and were dropped from F&O are missing), so +3% is an optimistic estimate. Realistic: about +1% a trade
  after costs and slippage.

| Results for | Quarter | Trades | Up | 3-day avg | Take-profit avg | All F&O stocks | Stocks (3-day %) |
|---|---|---:|---:|---:|---:|---:|---|
| Jan-Mar 2021 | Q4 FY21 | 0 | 0 | - | - | +0.82% |  |
| Apr-Jun 2021 | Q1 FY22 | 0 | 0 | - | - | +0.06% |  |
| Jul-Sep 2021 | Q2 FY22 | 1 | 1 | +1.53% | +1.53% | -0.84% | AMBUJACEM +1.5 |
| Oct-Dec 2021 | Q3 FY22 | 3 | 3 | +6.19% | +5.65% | -0.64% | NAUKRI +8.7, TECHM +5.1, PIIND +4.7 |
| Jan-Mar 2022 | Q4 FY22 | 1 | 0 | -4.19% | -4.19% | -0.83% | JINDALSTEL -4.2 |
| Apr-Jun 2022 | Q1 FY23 | 0 | 0 | - | - | +0.75% |  |
| Jul-Sep 2022 | Q2 FY23 | 1 | 1 | +3.01% | +3.01% | +0.03% | AUROPHARMA +3.0 |
| Oct-Dec 2022 | Q3 FY23 | 6 | 4 | +3.75% | +1.65% | -0.16% | INDUSTOWER -7.9, BANKBARODA +8.5, SBIN +3.4, ADANIPORTS +19.1, AMBUJACEM +2.9, ADANIENT -3.5 |
| Jan-Mar 2023 | Q4 FY23 | 1 | 0 | -3.71% | -3.71% | +0.61% | MANAPPURAM -3.7 |
| Apr-Jun 2023 | Q1 FY24 | 0 | 0 | - | - | -0.30% |  |
| Jul-Sep 2023 | Q2 FY24 | 0 | 0 | - | - | +0.41% |  |
| Oct-Dec 2023 | Q3 FY24 | 3 | 3 | +2.40% | +2.40% | +0.48% | POLYCAB +1.9, IEX +3.0, AUROPHARMA +2.4 |
| Jan-Mar 2024 | Q4 FY24 | 2 | 2 | +2.84% | +2.24% | +0.88% | INFY +1.3, KOTAKBANK +4.4 |
| Apr-Jun 2024 | Q1 FY25 | 0 | 0 | - | - | +0.53% |  |
| Jul-Sep 2024 | Q2 FY25 | 1 | 1 | +3.64% | +3.64% | -1.12% | BHEL +3.6 |
| Oct-Dec 2024 | Q3 FY25 | 5 | 4 | +4.51% | +3.89% | -0.79% | LODHA +4.4, CGPOWER +1.3, KALYANKJIL +14.8, PRESTIGE +6.8, TRENT -4.9 |
| Jan-Mar 2025 | Q4 FY25 | 2 | 2 | +6.39% | +5.10% | +0.96% | INFY +1.8, TATAELXSI +11.0 |
| Apr-Jun 2025 | Q1 FY26 | 0 | 0 | - | - | -0.56% |  |
| Jul-Sep 2025 | Q2 FY26 | 0 | 0 | - | - | +0.67% |  |
| Oct-Dec 2025 | Q3 FY26 | 6 | 4 | +1.31% | +1.61% | +0.18% | CGPOWER +1.9, LODHA +5.6, PRESTIGE +4.9, SWIGGY -0.6, GODREJPROP +0.0, NAUKRI -4.0 |
| Jan-Mar 2026 | Q4 FY26 | 0 | 0 | - | - | -0.31% |  |
| Apr-Jun 2026 | Q1 FY27 | 0 | 0 | - | - | +0.17% |  |

## Deeper lag and stricter volume: lag over 15% and 1.5x or more

| Exit | Trades | Up | Average | After 0.17% cost | Quarters with trades | Positive | Without best 3 | Without best 5 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 3-day | 16 | 75% | +3.77% | +3.60% | 8 of 22 | 6 | +1.36% | +0.52% |
| Take-profit | 16 | 81% | +3.13% | +2.96% | 8 of 22 | 7 | +1.32% | +0.71% |

An independent check rebuilt it and got the same 16 trades (split adjustment changes nothing here). Its findings:

- **Too few trades.** 16 trades in 8 of 22 quarters; 14 quarters had none, including the last two. 13 of the 16 come
  from the Oct-Dec results seasons (cutoffs in late January / early February), and 10 sit in three sell-off windows
  (late Jan 2022, the Feb 2023 Adani fall, late Jan 2025), so it is really about 8 independent bets.
- **Three trades carry it.** ADANIPORTS +19.1%, KALYANKJIL +14.8%, NAUKRI +8.7%. Without the best 3 trades the average
  is +1.4%, without the best 5 only +0.5%.
- **The stricter cuts add nothing measurable.** Picking 16 trades at random from the wider "lag over 15%" results does
  as well about 1 time in 6 (p 0.17); from "lag over 10% & 1.5x", about 1 time in 2 (p 0.44). Tighter cut points look
  better only because they keep the same few big winners: every nearby version (lag 12-20%, volume 1.3-2.0x) sits at
  +0.35% to +1.5% without its best 5 trades.
- **Results-specific part.** The same filter on dates without results makes about +1.1% over 3 days, so about +2.7%
  is linked to results, borderline significant (p about 0.03) on 16 trades and before allowing for the ~100 cut
  combinations looked at.
- Realistic expectation: about +1.5% a trade after costs at best, with long gaps between trades. The looser
  "lag over 10% & volume 1.0x" rule gives about the same edge per trade with five times as many trades.

| Results for | Quarter | Trades | Up | 3-day avg | Take-profit avg | All F&O stocks | Stocks (3-day %) |
|---|---|---:|---:|---:|---:|---:|---|
| Jan-Mar 2021 | Q4 FY21 | 0 | 0 | - | - | +0.82% |  |
| Apr-Jun 2021 | Q1 FY22 | 0 | 0 | - | - | +0.06% |  |
| Jul-Sep 2021 | Q2 FY22 | 0 | 0 | - | - | -0.84% |  |
| Oct-Dec 2021 | Q3 FY22 | 3 | 3 | +6.19% | +5.65% | -0.64% | NAUKRI +8.7, TECHM +5.1, PIIND +4.7 |
| Jan-Mar 2022 | Q4 FY22 | 1 | 0 | -4.19% | -4.19% | -0.83% | JINDALSTEL -4.2 |
| Apr-Jun 2022 | Q1 FY23 | 0 | 0 | - | - | +0.75% |  |
| Jul-Sep 2022 | Q2 FY23 | 1 | 1 | +3.01% | +3.01% | +0.03% | AUROPHARMA +3.0 |
| Oct-Dec 2022 | Q3 FY23 | 3 | 2 | +6.19% | +2.94% | -0.16% | ADANIPORTS +19.1, AMBUJACEM +2.9, ADANIENT -3.5 |
| Jan-Mar 2023 | Q4 FY23 | 0 | 0 | - | - | +0.61% |  |
| Apr-Jun 2023 | Q1 FY24 | 0 | 0 | - | - | -0.30% |  |
| Jul-Sep 2023 | Q2 FY24 | 0 | 0 | - | - | +0.41% |  |
| Oct-Dec 2023 | Q3 FY24 | 1 | 1 | +1.90% | +1.90% | +0.48% | POLYCAB +1.9 |
| Jan-Mar 2024 | Q4 FY24 | 0 | 0 | - | - | +0.88% |  |
| Apr-Jun 2024 | Q1 FY25 | 0 | 0 | - | - | +0.53% |  |
| Jul-Sep 2024 | Q2 FY25 | 0 | 0 | - | - | -1.12% |  |
| Oct-Dec 2024 | Q3 FY25 | 4 | 3 | +5.30% | +4.53% | -0.79% | LODHA +4.4, KALYANKJIL +14.8, PRESTIGE +6.8, TRENT -4.9 |
| Jan-Mar 2025 | Q4 FY25 | 1 | 1 | +1.77% | +1.77% | +0.96% | INFY +1.8 |
| Apr-Jun 2025 | Q1 FY26 | 0 | 0 | - | - | -0.56% |  |
| Jul-Sep 2025 | Q2 FY26 | 0 | 0 | - | - | +0.67% |  |
| Oct-Dec 2025 | Q3 FY26 | 2 | 1 | -0.27% | +1.82% | +0.18% | SWIGGY -0.6, GODREJPROP +0.0 |
| Jan-Mar 2026 | Q4 FY26 | 0 | 0 | - | - | -0.31% |  |
| Apr-Jun 2026 | Q1 FY27 | 0 | 0 | - | - | +0.17% |  |

## Deepest: lag over 20% and 1.5x or more

| Exit | Trades | Up | Average | After 0.17% cost | Quarters with trades | Positive | Without best 3 | Without best 5 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 3-day | 9 | 89% | +6.26% | +6.09% | 4 of 22 | 4 | +2.61% | +1.46% |
| Take-profit | 9 | 89% | +4.66% | +4.49% | 4 of 22 | 4 | | +1.19% |

| Results for | Stock | Lag vs Nifty | Volume vs 60-day | 3-day | Take-profit |
|---|---|---:|---:|---:|---:|
| Oct-Dec 2021 | TECHM | -20.4% | 1.7x | +5.1% | +4.8% |
| Oct-Dec 2021 | PIIND | -20.9% | 1.7x | +4.7% | +3.4% |
| Oct-Dec 2022 | ADANIPORTS | -37.4% | 6.1x | +19.1% | +9.3% |
| Oct-Dec 2022 | AMBUJACEM | -26.9% | 5.6x | +2.9% | +2.9% |
| Oct-Dec 2022 | ADANIENT | -49.0% | 3.3x | -3.5% | -3.5% |
| Oct-Dec 2023 | POLYCAB | -26.1% | 5.9x | +1.9% | +1.9% |
| Oct-Dec 2024 | LODHA | -20.7% | 1.6x | +4.4% | +4.4% |
| Oct-Dec 2024 | KALYANKJIL | -38.2% | 2.8x | +14.8% | +14.8% |
| Oct-Dec 2024 | PRESTIGE | -21.2% | 2.2x | +6.8% | +3.7% |

- **Only 9 trades in 4 of 22 quarters**, all in the Oct-Dec results seasons (cutoffs in late January / early February)
  of 2021, 2022, 2023 and 2024: market sell-offs, including the Feb 2023 Adani fall. 18 quarters had no trade, and
  there has been none since the Oct-Dec 2024 season (late January 2025).
- 8 of 9 rose, but two trades (ADANIPORTS +19.1%, KALYANKJIL +14.8%) make up over half of the total; without the best
  5 trades the average is +1.5%.
- The same filter on dates without results makes +0.8% over 3 days (+1.2% counting each episode once), and 9 random
  such episodes reach +6.26% about 2 times in 100, so the results window does add something.
- But going from 15% to 20% adds nothing measurable: picking 9 trades at random (same quarters) from the "lag over
  15% & 1.5x" trades does as well about 1 time in 4 (p 0.24); from "lag over 10% & 1.5x", about 1 time in 8 (p 0.13).
  Nearby volume cuts at a 20% lag: 1.0x +4.7% (14 trades), 1.3x +4.6% (12), 2.0x +7.0% (6); all under +1% once their
  best 5 trades are removed.
- Read it as a description of a handful of crash rebounds, not a rule you can size: it fires about once a year.

## Lag over 10% and volume 2x or more

| Exit | Trades | Up | Average | After 0.17% cost | Quarters with trades | Positive | Without best 3 | Without best 5 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 3-day | 16 | 88% | +4.38% | +4.21% | 8 of 22 | 7 | +2.12% | +1.43% |
| Take-profit | 16 | 88% | +3.49% | +3.32% | 8 of 22 | 7 | | +1.30% |

| Results for | Stock | Lag vs Nifty | Volume vs 60-day | 3-day | Take-profit |
|---|---|---:|---:|---:|---:|
| Oct-Dec 2021 | NAUKRI | -17.7% | 2.5x | +8.7% | +8.7% |
| Jul-Sep 2022 | AUROPHARMA | -15.3% | 2.5x | +3.0% | +3.0% |
| Oct-Dec 2022 | SBIN | -10.7% | 2.8x | +3.4% | +3.2% |
| Oct-Dec 2022 | ADANIPORTS | -37.4% | 6.1x | +19.1% | +9.3% |
| Oct-Dec 2022 | AMBUJACEM | -26.9% | 5.6x | +2.9% | +2.9% |
| Oct-Dec 2022 | ADANIENT | -49.0% | 3.3x | -3.5% | -3.5% |
| Jan-Mar 2023 | MANAPPURAM | -13.7% | 4.9x | -3.7% | -3.7% |
| Oct-Dec 2023 | POLYCAB | -26.1% | 5.9x | +1.9% | +1.9% |
| Oct-Dec 2023 | IEX | -10.0% | 2.3x | +3.0% | +3.0% |
| Oct-Dec 2023 | AUROPHARMA | -11.3% | 2.1x | +2.4% | +2.4% |
| Jan-Mar 2024 | KOTAKBANK | -13.2% | 4.1x | +4.4% | +3.2% |
| Oct-Dec 2024 | KALYANKJIL | -38.2% | 2.8x | +14.8% | +14.8% |
| Oct-Dec 2024 | PRESTIGE | -21.2% | 2.2x | +6.8% | +3.7% |
| Oct-Dec 2025 | CGPOWER | -11.1% | 2.1x | +1.9% | +1.9% |
| Oct-Dec 2025 | PRESTIGE | -10.3% | 2.2x | +4.9% | +4.9% |
| Oct-Dec 2025 | GODREJPROP | -15.6% | 2.0x | +0.0% | +0.0% |

- 14 of 16 trades rose; the two losers were small (ADANIENT -3.5%, MANAPPURAM -3.7%). 8 quarters had trades (7
  positive), 14 had none. First 14 quarters +3.78% (11 trades), last 8 +5.70% (5). 13 of the 16 come from the Oct-Dec
  results seasons (cutoffs in late January / early February).
- The same filter on dates without results makes +1.16% over 3 days (+1.49% counting each episode once, 60% up), so
  about +3% is linked to results; 16 random such episodes reach +4.38% about 2 times in 100.
- Compared with picking 16 trades at random from the same quarters: from all lag-over-10% results p = 0.006, from
  "lag over 10% & 1.0x" p = 0.03, from "lag over 10% & 1.5x" p = 0.03. So 2x volume picks somewhat better than the
  wider rules here; the 1.5-2x trades in between averaged only +1.7% (16 trades).
- But it is a local peak: nearby cuts fall away once their best 5 trades are removed (volume 1.75x +1.2%, 2.5x -0.6%;
  lag 8% & 2x +0.5%, lag 12% & 2x +0.1%), against +1.4% here. The p-values above also ignore the 100+ cut-point
  combinations looked at in this family. Realistic: about +1.5% a trade after costs, about once or twice a year.

## Lag over 15% and volume 2x or more

| Exit | Trades | Up | Average | After 0.17% cost | Quarters with trades | Positive | Without best 3 | Without best 5 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 3-day | 9 | 89% | +5.99% | +5.82% | 6 of 22 | 6 | +1.87% | +0.35% |
| Take-profit | 9 | 89% | +4.56% | +4.39% | 6 of 22 | 6 | | +0.35% |

| Results for | Stock | Lag vs Nifty | Volume vs 60-day | 3-day | Take-profit |
|---|---|---:|---:|---:|---:|
| Oct-Dec 2021 | NAUKRI | -17.7% | 2.5x | +8.7% | +8.7% |
| Jul-Sep 2022 | AUROPHARMA | -15.3% | 2.5x | +3.0% | +3.0% |
| Oct-Dec 2022 | ADANIPORTS | -37.4% | 6.1x | +19.1% | +9.3% |
| Oct-Dec 2022 | AMBUJACEM | -26.9% | 5.6x | +2.9% | +2.9% |
| Oct-Dec 2022 | ADANIENT | -49.0% | 3.3x | -3.5% | -3.5% |
| Oct-Dec 2023 | POLYCAB | -26.1% | 5.9x | +1.9% | +1.9% |
| Oct-Dec 2024 | KALYANKJIL | -38.2% | 2.8x | +14.8% | +14.8% |
| Oct-Dec 2024 | PRESTIGE | -21.2% | 2.2x | +6.8% | +3.7% |
| Oct-Dec 2025 | GODREJPROP | -15.6% | 2.0x | +0.0% | +0.0% |

- 9 trades in 6 of 22 quarters, all 6 positive; 8 of 9 rose (only ADANIENT -3.5%). Eight of the 9 come from the
  Oct-Dec results seasons (late January / early February sell-offs).
- It is the 2x rule above minus its 7 milder laggards (lag 10-15%), which averaged +2.3%. Picking 9 at random from the
  lag-over-10% & 2x trades in the same quarters does as well 3 times in 4 (p 0.75), so the deeper 15% lag adds no
  measurable selection over 10% at 2x volume; it mostly drops trades.
- Three trades carry it (ADANIPORTS +19.1%, KALYANKJIL +14.8%, NAUKRI +8.7%): without the best 3 the average is +1.9%,
  without the best 5 only +0.35%. Nearby cuts behave the same (lag 12% & 2x +0.1%, lag 17% & 2x -0.8%, lag 15% & 2.5x
  -3.5% without their best 5). Volume 1.75x picks exactly the same 9 trades.
- The same filter on dates without results makes +1.5% over 3 days (+1.85% counting each episode once, positive in
  15 of 19 quarters), so roughly +4% is linked to results, but on 9 trades.
- Read it as a list of nine crash-rebound trades, not a rule: realistic expectation for anything this narrow is at most
  the +1.5% a trade of the wider family.

## Lag over 20% and volume 2x or more

| Exit | Trades | Up | Average | After 0.17% cost | Quarters with trades | Positive | Without best 2 | Without best 3 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 3-day | 6 | 83% | +7.01% | +6.84% | 3 of 22 | 3 | +2.05% | +0.46% |
| Take-profit | 6 | 83% | +4.87% | +4.70% | 3 of 22 | 3 | | |

| Results for | Stock | Lag vs Nifty | Volume vs 60-day | 3-day | Take-profit |
|---|---|---:|---:|---:|---:|
| Oct-Dec 2022 | ADANIPORTS | -37.4% | 6.1x | +19.1% | +9.3% |
| Oct-Dec 2022 | AMBUJACEM | -26.9% | 5.6x | +2.9% | +2.9% |
| Oct-Dec 2022 | ADANIENT | -49.0% | 3.3x | -3.5% | -3.5% |
| Oct-Dec 2023 | POLYCAB | -26.1% | 5.9x | +1.9% | +1.9% |
| Oct-Dec 2024 | KALYANKJIL | -38.2% | 2.8x | +14.8% | +14.8% |
| Oct-Dec 2024 | PRESTIGE | -21.2% | 2.2x | +6.8% | +3.7% |

- 6 trades in 3 of 22 quarters, all from the Oct-Dec results seasons; half of them in the same week of the Feb 2023
  Adani fall. Nothing since the January 2025 trades.
- Two trades (ADANIPORTS +19.1%, KALYANKJIL +14.8%) are the result: without them the average is +2.05%, without the
  best 3 +0.46%.
- Not distinguishable from chance: the same filter on dates without results makes +1.0% (+2.0% counting each episode
  once), and 6 random such episodes reach +7.0% about 8 times in 100; within the same quarters, the lag-over-10% & 2x
  trades do as well 3 times in 4.
- This is the end of the ladder: each tighter version keeps the same few crash-rebound winners and drops everything
  else, so it says nothing new about the edge.

Files: [results/lag10_volume/](../results/lag10_volume/) (summary.csv with the nearby variants; per_quarter.csv and
trades.csv for 1.0x; per_quarter_vol15.csv and trades_vol15.csv for 1.5x; *_lag15_vol15.csv and *_lag20_vol15.csv for lag over 15% / 20% & 1.5x; *_vol20.csv, *_lag15_vol20.csv and *_lag20_vol20.csv for lag over 10% / 15% / 20% & 2x). Script:
`pattern_tests/lag10_volume.py PACK_DIR nse_prices.db features22.csv OUT_DIR` (PACK_DIR from `sector_lab_data.py`).
