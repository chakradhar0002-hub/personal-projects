# Stock lagged Nifty by more than 15% over the month: every quarter

Rule: at the cutoff close (2 sessions before the result session), if the stock's 21-session return is more than 15
points below Nifty 50's 21-session return, buy it at that close. Exit at the Day+1 close (3-day), or with the
take-profit rule (Day-1 close if Day-1 > +3%, else Result-day close if Day-1 + Result day > +3%, else Day+1 close).
Only stocks that were in F&O at the time. Built from the raw daily returns and checked against the earlier feature
file (4,446 results, largest difference 0.0001%).

## Summary

| | Trades | Up | Average | After 0.17% cost | Quarters with trades | Positive | At +2% or more |
|---|---:|---:|---:|---:|---:|---:|---:|
| 3-day exit | 51 | 64.7% | +2.09% | +1.92% | 16 of 22 | 14 of 16 | 7 |
| Take-profit exit | 51 | 72.5% | +2.24% | +2.07% | 16 of 22 | 15 of 16 | 10 |
| Every F&O result (for comparison) | 3,278 | 48.6% | +0.04% | -0.13% | 22 | 13 of 22 | 0 |

- **6 of 22 quarters had no trade** (Jan-Mar 2021, Jul-Sep 2023, Jan-Mar 2024, Apr-Jun 2024, Jul-Sep 2025, Jan-Mar
  2026): in rising markets few F&O stocks lag Nifty by 15% in a month. Most quarters have 1-3 trades; three have 8.
- The only losing quarter with take-profit was Apr-Jun 2023 (one trade, BANDHANBNK -2.8%). With the 3-day exit Jan-Mar
  2025 also lost (-0.23%).
- First 14 quarters +2.54% a trade (3-day), last 8 +1.50%. Worst trade -10.1% (ANGELONE), best +19.1% (ADANIPORTS).
  Without the 5 best trades the average is +0.72% (3-day) or +1.19% (take-profit).
- The same stocks bounce about +0.5% over 3 days without results, so roughly +1.5% of the average is results-related.
- The -15% level was picked after looking at the data. Looser levels trade in more quarters but earn less:

| Lag vs Nifty | Trades | Quarters with trades | 3-day avg | Take-profit avg | Quarters positive (take-profit) |
|---|---:|---:|---:|---:|---:|
| more than 10% | 194 | 22 of 22 | +0.73% | +0.84% | 17 of 22 |
| more than 12% | 116 | 21 of 22 | +1.02% | +1.05% | 15 of 21 |
| more than 15% | 51 | 16 of 22 | +2.09% | +2.24% | 15 of 16 |
| more than 20% | 16 | 7 of 22 | +4.03% | +4.08% | 7 of 7 |

## Quarter by quarter (more than 15%, F&O at the time)

| Results for | Quarter | Trades | Up | 3-day avg | Take-profit avg | All F&O stocks | Stocks (3-day %) |
|---|---|---:|---:|---:|---:|---:|---|
| Jan-Mar 2021 | Q4 FY21 | 0 |  | - | - | +0.82% |  |
| Apr-Jun 2021 | Q1 FY22 | 2 | 1 | +0.83% | +0.83% | +0.06% | GLENMARK -1.6, GMRAIRPORT +3.2 |
| Jul-Sep 2021 | Q2 FY22 | 2 | 2 | +3.21% | +3.21% | -0.84% | CUMMINSIND +3.0, PIIND +3.4 |
| Oct-Dec 2021 | Q3 FY22 | 8 | 5 | +1.64% | +1.10% | -0.64% | IDEA -8.4, COFORGE -1.8, RBLBANK +7.2, DIXON -3.2, NAUKRI +8.7, TECHM +5.1, PIIND +4.7, ZYDUSLIFE +0.7 |
| Jan-Mar 2022 | Q4 FY22 | 8 | 4 | +2.23% | +2.77% | -0.83% | MPHASIS +2.7, SAIL -7.0, APOLLOHOSP -1.3, NMDC -1.0, JSWSTEEL +2.1, NAUKRI +12.2, DIXON +14.3, JINDALSTEL -4.2 |
| Apr-Jun 2022 | Q1 FY23 | 1 | 1 | +5.20% | +3.50% | +0.75% | AUBANK +5.2 |
| Jul-Sep 2022 | Q2 FY23 | 2 | 2 | +4.82% | +4.40% | +0.03% | MOTHERSON +6.6, AUROPHARMA +3.0 |
| Oct-Dec 2022 | Q3 FY23 | 3 | 2 | +6.19% | +2.94% | -0.16% | ADANIPORTS +19.1, AMBUJACEM +2.9, ADANIENT -3.5 |
| Jan-Mar 2023 | Q4 FY23 | 1 | 1 | +2.24% | +2.24% | +0.61% | CROMPTON +2.2 |
| Apr-Jun 2023 | Q1 FY24 | 1 | 0 | -2.79% | -2.79% | -0.30% | BANDHANBNK -2.8 |
| Jul-Sep 2023 | Q2 FY24 | 0 |  | - | - | +0.41% |  |
| Oct-Dec 2023 | Q3 FY24 | 1 | 1 | +1.90% | +1.90% | +0.48% | POLYCAB +1.9 |
| Jan-Mar 2024 | Q4 FY24 | 0 |  | - | - | +0.88% |  |
| Apr-Jun 2024 | Q1 FY25 | 0 |  | - | - | +0.53% |  |
| Jul-Sep 2024 | Q2 FY25 | 1 | 1 | +0.93% | +0.93% | -1.12% | IEX +0.9 |
| Oct-Dec 2024 | Q3 FY25 | 8 | 5 | +1.93% | +2.36% | -0.79% | ANGELONE -10.1, LODHA +4.4, CAMS -4.1, KALYANKJIL +14.8, POLICYBZR +5.1, PRESTIGE +6.8, RECLTD +3.3, TRENT -4.9 |
| Jan-Mar 2025 | Q4 FY25 | 3 | 1 | -0.23% | +1.22% | +0.96% | WIPRO -1.1, INFY +1.8, VOLTAS -1.4 |
| Apr-Jun 2025 | Q1 FY26 | 2 | 1 | +2.86% | +2.86% | -0.56% | BDL +6.2, INOXWIND -0.5 |
| Jul-Sep 2025 | Q2 FY26 | 0 |  | - | - | +0.67% |  |
| Oct-Dec 2025 | Q3 FY26 | 6 | 4 | +1.63% | +2.33% | +0.18% | PREMIERENE -6.6, DIXON +2.6, ITC +1.1, SWIGGY -0.6, GODREJPROP +0.0, KALYANKJIL +13.3 |
| Jan-Mar 2026 | Q4 FY26 | 0 |  | - | - | -0.31% |  |
| Apr-Jun 2026 | Q1 FY27 | 2 | 2 | +0.84% | +4.67% | +0.17% | KPITTECH +1.3, PATANJALI +0.4 |

"Up" counts 3-day trades above zero. "All F&O stocks" is the average 3-day window of every F&O result that quarter.

Files: [results/lagged_nifty/](../results/lagged_nifty/) (summary.csv with all thresholds and the all-results version,
per_quarter.csv, trades.csv). Script: `pattern_tests/lagged_nifty_1m.py PACK_DIR features22.csv OUT_DIR` (PACK_DIR
from `sector_lab_data.py`).
