# Lagged Nifty by more than 10% and above-average volume: every quarter

Rule, at the cutoff close (2 sessions before the result session), stocks in F&O at the time:

- the stock's 21-session return is more than 10 points below Nifty 50's, and
- its average volume over the last 5 sessions is at least its 60-session average.

Buy at the cutoff close; sell at the Day+1 close (3-day) or with the take-profit rule (Day-1 close if Day-1 > +3%,
else Result-day close if Day-1 + Result day > +3%, else Day+1 close). Rebuilt from the raw daily returns and NSE volume;
it matches the earlier feature file exactly. Only 1 of the 85 trades had a bonus or split inside the 60 sessions.

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
- The same filter on dates with no results nearby makes about +0.67% over 3 days (positive in 20 of 22 quarters), so
  about +1.5% a trade is linked to results.
- Caution: the 10% and 1.0x cut points were picked after looking at the data (see [LAG5_PATTERNS.md](LAG5_PATTERNS.md)),
  so this is not an out-of-sample result. Encouragingly, nearby cut points give similar numbers rather than falling
  off a cliff:

| Rule | Trades | Up | 3-day avg | Take-profit avg | Quarters with trades | Positive (3-day) | Without best 5 |
|---|---:|---:|---:|---:|---:|---:|---:|
| lag > 8%, volume ≥ 1.0x | 125 | 58% | +1.56% | +1.68% | 21 | 17 | +1.01% |
| lag > 10%, volume ≥ 0.8x | 133 | 59% | +1.52% | +1.57% | 20 | 18 | +0.98% |
| lag > 10%, volume ≥ 1.0x (this rule) | 85 | 64% | +2.13% | +2.14% | 19 | 18 | +1.36% |
| lag > 10%, volume ≥ 1.2x | 54 | 70% | +2.51% | +2.75% | 18 | 16 | +1.40% |
| lag > 10%, volume ≥ 1.5x | 33 | 79% | +3.03% | +2.45% | 13 | 11 | +1.36% |
| lag > 12%, volume ≥ 1.0x | 56 | 66% | +2.26% | +1.91% | 17 | 15 | +1.11% |
| lag > 15%, volume ≥ 1.0x | 32 | 69% | +2.71% | +2.82% | 11 | 10 | +0.68% |
| lag > 10%, volume < 1.0x (quiet) | 109 | 47% | -0.37% | -0.18% | 21 | 11 | -0.98% |

## Quarter by quarter

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

Files: [results/lag10_volume/](../results/lag10_volume/) (summary.csv with the nearby variants, per_quarter.csv,
trades.csv). Script: `pattern_tests/lag10_volume.py PACK_DIR nse_prices.db features22.csv OUT_DIR` (PACK_DIR from
`sector_lab_data.py`).
