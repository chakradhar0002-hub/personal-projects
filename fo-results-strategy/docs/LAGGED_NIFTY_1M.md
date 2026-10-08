# Stock lagged Nifty by more than 15% (or 10%) over the month: every quarter

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

"Up" counts 3-day trades above zero. (Same for the table below.) "All F&O stocks" is the average 3-day window of every F&O result that quarter.

## Lag of more than 10%: a trade in every quarter

| | Trades | Up | Average | After 0.17% cost | Quarters positive | At +2% or more |
|---|---:|---:|---:|---:|---:|---:|
| 3-day exit | 194 | 54.1% | +0.73% | +0.56% | 16 of 22 | 7 |
| Take-profit exit | 194 | 59.3% | +0.84% | +0.67% | 17 of 22 | 6 |

- Every quarter has trades (1 to 24, about 9 on average), but the average per trade is a third of the 15% rule's.
- The stocks added by loosening to 10% (lag between 10% and 15%, 143 trades) average only +0.24% (3-day) / +0.34%
  (take-profit); almost all of the profit is still the more-than-15% names.
- Losing quarters with take-profit: Apr-Jun 2021 (-2.56%), Jul-Sep 2022 (-1.11%), Apr-Jun 2023 (-0.64%), Jul-Sep 2024
  (-1.13%), Oct-Dec 2024 (-1.05%). First 14 quarters +0.65% a trade (11 of 14 positive), last 8 +1.11% (6 of 8).
- It beat the average F&O stock in 15 of 22 quarters, by +1.08% a quarter on average.
- **Most of it is not about results.** The same filter on dates with no results nearby makes +0.48% (3-day) / +0.38%
  (take-profit) and is positive in 19 of 22 quarters. So results add only about +0.25-0.45% a trade at 10%, versus
  about +1.5% at 15%.

| Results for | Quarter | Trades | Up | 3-day avg | Take-profit avg | All F&O stocks | Stocks (3-day %) |
|---|---|---:|---:|---:|---:|---:|---|
| Jan-Mar 2021 | Q4 FY21 | 5 | 1 | +0.44% | +2.35% | +0.82% | BAJFINANCE +12.7, AUBANK -7.0, LTF -1.4, RBLBANK -0.8, BANDHANBNK -1.3 |
| Apr-Jun 2021 | Q1 FY22 | 7 | 3 | -1.88% | -2.56% | +0.06% | TMPV -3.7, BANDHANBNK +1.2, ZYDUSLIFE -7.3, AUROPHARMA -14.0, BHARATFORG +9.0, GLENMARK -1.6, GMRAIRPORT +3.2 |
| Jul-Sep 2021 | Q2 FY22 | 14 | 7 | -0.18% | +0.08% | -0.84% | ULTRACEMCO -2.4, BIOCON -6.0, CONCOR +1.9, CROMPTON -0.7, POLYCAB +2.0, COLPAL -2.9, HDFCAMC -3.8, AMBUJACEM +1.5, CIPLA +2.9, CUMMINSIND +3.0, ZYDUSLIFE -1.4, EICHERMOT +4.0, COALINDIA -4.2, PIIND +3.4 |
| Oct-Dec 2021 | Q3 FY22 | 9 | 5 | +1.34% | +0.86% | -0.64% | PERSISTENT -1.1, IDEA -8.4, COFORGE -1.8, RBLBANK +7.2, DIXON -3.2, NAUKRI +8.7, TECHM +5.1, PIIND +4.7, ZYDUSLIFE +0.7 |
| Jan-Mar 2022 | Q4 FY22 | 16 | 7 | +0.87% | +1.19% | -0.83% | HCLTECH +2.9, MPHASIS +2.7, WIPRO -4.6, RBLBANK -1.3, DLF +2.0, SAIL -7.0, APOLLOHOSP -1.3, NATIONALUM -3.0, NMDC -1.0, OBEROIRLTY -4.0, HINDALCO +4.9, JSWSTEEL +2.1, NAUKRI +12.2, AUROPHARMA -0.9, DIXON +14.3, JINDALSTEL -4.2 |
| Apr-Jun 2022 | Q1 FY23 | 7 | 5 | +2.09% | +1.56% | +0.75% | WIPRO -2.4, AUBANK +5.2, IEX -5.8, NMDC +6.6, GLENMARK +2.9, ZYDUSLIFE +6.6, HEROMOTOCO +1.5 |
| Jul-Sep 2022 | Q2 FY23 | 9 | 2 | -1.01% | -1.11% | +0.03% | IEX -3.7, GODREJCP -1.1, ASHOKLEY -0.3, HINDPETRO -1.0, MOTHERSON +6.6, PAGEIND -4.9, ABB -2.5, ASTRAL -5.3, AUROPHARMA +3.0 |
| Oct-Dec 2022 | Q3 FY23 | 7 | 5 | +3.52% | +1.72% | -0.16% | INDUSTOWER -7.9, BAJAJFINSV +2.1, BANKBARODA +8.5, SBIN +3.4, ADANIPORTS +19.1, AMBUJACEM +2.9, ADANIENT -3.5 |
| Jan-Mar 2023 | Q4 FY23 | 7 | 5 | +2.07% | +1.46% | +0.61% | PERSISTENT +3.9, INDUSTOWER +4.3, LTM +5.5, TECHM +2.7, MANAPPURAM -3.7, CROMPTON +2.2, NMDC -0.5 |
| Apr-Jun 2023 | Q1 FY24 | 6 | 2 | -0.92% | -0.64% | -0.30% | BANDHANBNK -2.8, SRF -3.5, DIXON -2.1, JUBLFOOD +0.3, SHREECEM +2.7, UPL -0.2 |
| Jul-Sep 2023 | Q2 FY24 | 1 | 1 | +3.50% | +3.50% | +0.41% | BIOCON +3.5 |
| Oct-Dec 2023 | Q3 FY24 | 4 | 3 | +1.76% | +1.76% | +0.48% | POLYCAB +1.9, IEX +3.0, AUROPHARMA +2.4, CROMPTON -0.2 |
| Jan-Mar 2024 | Q4 FY24 | 5 | 3 | +0.51% | +0.27% | +0.88% | INFY +1.3, WIPRO +3.0, LTM -0.9, OFSS -5.3, KOTAKBANK +4.4 |
| Apr-Jun 2024 | Q1 FY25 | 18 | 9 | +0.66% | +1.21% | +0.53% | POLYCAB -4.8, OBEROIRLTY +1.1, RBLBANK -2.8, JINDALSTEL -1.5, BANDHANBNK +16.1, INDUSINDBK +1.1, IDFCFIRSTB +1.8, BANKBARODA -1.8, ABCAPITAL -5.1, CUMMINSIND +6.8, ABB +6.7, ASTRAL -2.8, SAIL -4.3, SIEMENS +1.4, NATIONALUM -1.5, NMDC +1.0, HINDALCO -0.2, HAL +0.9 |
| Jul-Sep 2024 | Q2 FY25 | 7 | 4 | -1.13% | -1.13% | -1.12% | IEX +0.9, BHEL +3.6, GAIL +4.5, MANAPPURAM -1.5, MOTHERSON -9.4, IDEA -6.4, HEROMOTOCO +0.3 |
| Oct-Dec 2024 | Q3 FY25 | 24 | 11 | -1.61% | -1.05% | -0.79% | ANGELONE -10.1, HDFCAMC +5.2, JIOFIN +1.2, ETERNAL -11.3, OBEROIRLTY -5.3, DLF -1.3, CDSL -17.4, LODHA +4.4, BHEL +0.1, CGPOWER +1.3, JSWENERGY -13.3, CAMS -4.1, VOLTAS -10.0, KALYANKJIL +14.8, POLICYBZR +5.1, PRESTIGE +6.8, GODREJPROP -2.4, CUMMINSIND +9.5, NAUKRI +4.3, RECLTD +3.3, TRENT -4.9, OIL -6.2, MOTHERSON -3.0, ABB -5.6 |
| Jan-Mar 2025 | Q4 FY25 | 15 | 10 | +3.39% | +2.59% | +0.96% | WIPRO -1.1, INFY +1.8, TATAELXSI +11.0, HCLTECH +10.6, PERSISTENT +6.2, SONACOMS +7.3, VEDL -0.2, COFORGE +1.7, VOLTAS -1.4, BHARATFORG +7.2, UNIONBANK +4.1, MUTHOOTFIN -6.7, JSWENERGY +6.1, SHREECEM +4.8, POWERGRID -0.6 |
| Apr-Jun 2025 | Q1 FY26 | 6 | 4 | +1.13% | +1.13% | -0.56% | IREDA -3.8, HINDZINC +2.2, COFORGE +2.6, BDL +6.2, IDEA +0.0, INOXWIND -0.5 |
| Jul-Sep 2025 | Q2 FY26 | 5 | 3 | +5.17% | +5.17% | +0.67% | DMART -2.3, ADANIGREEN +8.2, GODREJCP +6.4, POWERINDIA +14.1, RVNL -0.5 |
| Oct-Dec 2025 | Q3 FY26 | 13 | 8 | +0.87% | +1.01% | +0.18% | WAAREEENER +3.6, PREMIERENE -6.6, ADANIGREEN -8.2, CGPOWER +1.9, IDEA -2.2, LODHA +5.6, DIXON +2.6, ITC +1.1, PRESTIGE +4.9, SWIGGY -0.6, GODREJPROP +0.0, KALYANKJIL +13.3, NAUKRI -4.0 |
| Jan-Mar 2026 | Q4 FY26 | 1 | 1 | +2.40% | +2.40% | -0.31% | PGEL +2.4 |
| Apr-Jun 2026 | Q1 FY27 | 8 | 6 | +1.73% | +4.16% | +0.17% | INDIANB +9.2, TATAELXSI -4.5, BANKBARODA -0.7, KPITTECH +1.3, DELHIVERY +2.1, IDEA +2.1, AMBER +3.9, PATANJALI +0.4 |

Patterns inside the wider lag-over-5% group: [LAG5_PATTERNS.md](LAG5_PATTERNS.md).

Files: [results/lagged_nifty/](../results/lagged_nifty/) (summary.csv with all thresholds and the all-results version;
per_quarter_lag10/12/15/20.csv and trades_lag10/12/15/20.csv for each threshold). Script: `pattern_tests/lagged_nifty_1m.py PACK_DIR features22.csv OUT_DIR` (PACK_DIR
from `sector_lab_data.py`).
