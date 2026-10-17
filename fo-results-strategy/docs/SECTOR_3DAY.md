# Results three-day sum by sector, every quarter

Question: for each of the last 22 results seasons, what did the **three-day sum** (Day-1 + Result day + Day+1 daily
returns) look like, sector by sector?

- **Three-day sum**: the return on the session before the result session (Day-1), the result session itself, and the
  session after (Day+1), added up. It is the move from the cutoff close (2 sessions before the result session) to the
  Day+1 close, the same window as all the pre-results trades in this project. The compounded version differs by under
  0.1% on average.
- **Universe**: every result of a stock that was in F&O at the time, 3,278 results in 22 seasons (Jan-Mar 2021 to
  Apr-Jun 2026 results). The number of stocks grows from 98 in the first season to 206 in the latest.
- **Sectors**: NSE's 49 industries grouped into 15 sectors (table at the end). Hospitals, KEI and TRENT, which NSE files
  under "Miscellaneous", were placed by hand.
- Figures are averages per result, in percent, before costs. Cells with only 1-3 results (see the counts table) are
  noisy.

## Answer

- **The average F&O result moves +0.04% over the three days**: up in 13 of 22 quarters, between -1.12% (Jul-Sep 2024
  results) and +0.96% (Jan-Mar 2025 results).
- **Auto and auto parts is the one sector that stands out**: +1.20% a result (264 results, 16 stocks), above the
  average result of the same quarter in 18 of 22 quarters, in both halves of the data, and in every calendar year.
  Random picks of the same size do this well about 3 times in 10,000, and it stays clearly significant after allowing
  for the 15 sectors compared (adjusted p 0.004). Details below.
- **Power is the weakest** (-1.29% a result, positive in 6 of 22 quarters), but it is only 94 results and is not
  significant once the 15-sector comparison is allowed for (adjusted p 0.18).
- **Every other sector is within about ±0.5%** of the average and indistinguishable from chance (adjusted p 1.00):
  banks -0.04%, NBFCs and financials -0.11%, IT +0.41%, pharma +0.16%, FMCG +0.06%.

## By sector, all 22 quarters

| Sector | Stocks | Results | Avg 3-day sum | Median | Up | Quarters positive | First 14 q / last 8 q | Best quarter | Worst quarter |
|---|---:|---:|---:|---:|---:|---:|---|---|---|
| Banks | 18 | 336 | -0.04% | -0.42% | 48% | 11 of 22 | +0.02% / -0.11% | Oct-Dec 2021 (+4.12%) | Jan-Mar 2022 (-2.87%) |
| NBFC & financials | 33 | 487 | -0.11% | -0.39% | 47% | 13 of 22 | -0.35% / +0.16% | Jan-Mar 2021 (+4.06%) | Jul-Sep 2021 (-4.17%) |
| IT | 13 | 248 | +0.41% | +0.18% | 52% | 12 of 22 | +0.44% / +0.36% | Apr-Jun 2021 (+4.09%) | Jan-Mar 2026 (-3.13%) |
| Pharma & healthcare | 16 | 294 | +0.16% | -0.24% | 49% | 11 of 22 | +0.21% / +0.10% | Jul-Sep 2023 (+2.05%) | Apr-Jun 2021 (-2.49%) |
| Auto & auto parts | 16 | 264 | +1.20% | +1.20% | 59% | 18 of 22 | +1.59% / +0.66% | Jan-Mar 2021 (+4.19%) | Jul-Sep 2024 (-3.74%) |
| Capital goods & defence | 21 | 253 | +0.33% | +0.27% | 52% | 12 of 22 | +0.48% / +0.18% | Jan-Mar 2025 (+3.57%) | Jan-Mar 2026 (-1.32%) |
| Real estate & construction | 8 | 95 | -0.53% | -0.68% | 41% | 9 of 22 | -0.40% / -0.61% | Jul-Sep 2023 (+6.21%) | Jan-Mar 2021 (-7.09%) |
| Cement & building materials | 6 | 112 | -0.35% | -0.26% | 44% | 9 of 22 | -0.47% / -0.19% | Jan-Mar 2023 (+2.31%) | Oct-Dec 2021 (-3.43%) |
| Metals & mining | 11 | 206 | -0.26% | +0.01% | 50% | 6 of 22 | -0.34% / -0.14% | Apr-Jun 2022 (+2.88%) | Oct-Dec 2023 (-1.70%) |
| Oil & gas | 8 | 158 | -0.36% | -0.59% | 45% | 10 of 22 | -0.37% / -0.34% | Jan-Mar 2025 (+2.11%) | Jan-Mar 2022 (-3.55%) |
| Power | 8 | 94 | -1.29% | -0.80% | 36% | 6 of 22 | -0.45% / -1.91% | Apr-Jun 2023 (+4.54%) | Jan-Mar 2021 (-7.84%) |
| FMCG | 15 | 247 | +0.06% | -0.31% | 46% | 11 of 22 | +0.28% / -0.25% | Jul-Sep 2025 (+2.69%) | Jul-Sep 2024 (-3.44%) |
| Consumer durables & retail | 13 | 158 | -0.28% | -0.42% | 46% | 11 of 22 | +0.86% / -1.28% | Oct-Dec 2025 (+5.58%) | Oct-Dec 2022 (-4.61%) |
| Chemicals & agro | 5 | 94 | -0.28% | -0.09% | 49% | 6 of 22 | -0.40% / -0.12% | Jan-Mar 2026 (+3.83%) | Jul-Sep 2024 (-4.63%) |
| Services, telecom & internet | 15 | 232 | +0.14% | -0.09% | 50% | 10 of 22 | -0.28% / +0.61% | Oct-Dec 2025 (+2.56%) | Jul-Sep 2021 (-2.18%) |
| All F&O results | 206 | 3,278 | +0.04% | -0.15% | 49% | 13 of 22 | +0.12% / -0.06% | Jan-Mar 2025 (+0.96%) | Jul-Sep 2024 (-1.12%) |

## Each quarter: best and worst sector

Best and worst count only sectors with at least 4 results that quarter (number of results in brackets). "Results up" is the share of results with a positive three-day sum; "Sectors up" counts sectors with a positive average. "Auto rank" is where auto and auto parts finished among the ranked sectors.

| Results for | Quarter | Results | All F&O avg | Results up | Sectors up | Best sector | Worst sector | Auto rank |
|---|---|---:|---:|---:|---:|---|---|---:|
| Jan-Mar 2021 | Q4 FY21 | 98 | +0.82% | 48% | 7 of 15 | Auto +4.19% (11) | IT -1.83% (6) | 1 of 11 |
| Apr-Jun 2021 | Q1 FY22 | 117 | +0.06% | 55% | 9 of 15 | IT +4.09% (9) | Pharma -2.49% (11) | 10 of 11 |
| Jul-Sep 2021 | Q2 FY22 | 125 | -0.84% | 41% | 4 of 15 | IT +1.59% (11) | NBFC/Fin -4.17% (17) | 2 of 13 |
| Oct-Dec 2021 | Q3 FY22 | 132 | -0.64% | 46% | 4 of 15 | Banks +4.12% (14) | Cement -3.43% (5) | 4 of 14 |
| Jan-Mar 2022 | Q4 FY22 | 131 | -0.83% | 40% | 3 of 15 | Auto +3.68% (11) | Oil & gas -3.55% (7) | 1 of 13 |
| Apr-Jun 2022 | Q1 FY23 | 134 | +0.75% | 52% | 10 of 15 | Metals +2.88% (9) | Oil & gas -1.82% (7) | 5 of 13 |
| Jul-Sep 2022 | Q2 FY23 | 133 | +0.03% | 50% | 9 of 15 | Metals +1.12% (9) | Cons dur -3.59% (6) | 9 of 13 |
| Oct-Dec 2022 | Q3 FY23 | 133 | -0.16% | 44% | 6 of 15 | Auto +2.87% (11) | Cons dur -4.61% (5) | 1 of 13 |
| Jan-Mar 2023 | Q4 FY23 | 134 | +0.61% | 56% | 9 of 15 | Cement +2.31% (5) | Chem/agro -1.39% (4) | 3 of 13 |
| Apr-Jun 2023 | Q1 FY24 | 133 | -0.30% | 42% | 4 of 15 | Auto +1.30% (11) | IT -1.89% (11) | 1 of 13 |
| Jul-Sep 2023 | Q2 FY24 | 132 | +0.41% | 53% | 9 of 15 | Cons dur +2.51% (6) | Banks -1.07% (14) | 4 of 13 |
| Oct-Dec 2023 | Q3 FY24 | 135 | +0.48% | 53% | 9 of 15 | Cons dur +3.81% (6) | Chem/agro -2.62% (4) | 7 of 13 |
| Jan-Mar 2024 | Q4 FY24 | 135 | +0.88% | 53% | 11 of 15 | Auto +3.69% (11) | IT -1.60% (11) | 1 of 13 |
| Apr-Jun 2024 | Q1 FY25 | 135 | +0.53% | 53% | 9 of 15 | Cons dur +3.80% (6) | Cement -3.40% (5) | 5 of 13 |
| Jul-Sep 2024 | Q2 FY25 | 134 | -1.12% | 42% | 4 of 15 | IT +1.29% (11) | Chem/agro -4.63% (4) | 11 of 13 |
| Oct-Dec 2024 | Q3 FY25 | 172 | -0.79% | 45% | 4 of 15 | Chem/agro +3.70% (5) | Power -4.45% (7) | 11 of 15 |
| Jan-Mar 2025 | Q4 FY25 | 178 | +0.96% | 53% | 10 of 15 | IT +3.70% (13) | FMCG -0.93% (13) | 6 of 15 |
| Apr-Jun 2025 | Q1 FY26 | 191 | -0.56% | 46% | 3 of 15 | Services +2.34% (14) | Banks -1.83% (18) | 2 of 15 |
| Jul-Sep 2025 | Q2 FY26 | 191 | +0.67% | 54% | 9 of 15 | FMCG +2.69% (13) | Cons dur -2.12% (12) | 6 of 15 |
| Oct-Dec 2025 | Q3 FY26 | 196 | +0.18% | 46% | 6 of 15 | Cons dur +5.58% (12) | Power -3.35% (7) | 3 of 15 |
| Jan-Mar 2026 | Q4 FY26 | 203 | -0.31% | 46% | 7 of 15 | Chem/agro +3.83% (5) | Cons dur -3.81% (13) | 6 of 15 |
| Apr-Jun 2026 | Q1 FY27 | 206 | +0.17% | 50% | 9 of 15 | Auto +2.70% (16) | Power -2.79% (8) | 1 of 15 |

- Auto and auto parts was the best sector in 6 of 22 quarters and in the top three in 10; its average was negative in 4 quarters (Apr-Jun 2021, Jul-Sep 2022, Jul-Sep 2024 and Oct-Dec 2024 results).
- No other sector led more than 4 times. Consumer durables & retail led 4 times and was also the worst 4 times, the most swing of any sector.
- Power was the worst in 3 of the last 7 quarters.

## Average three-day sum, by sector and quarter (%)

| Results for | Quarter | Banks | NBFC/Fin | IT | Pharma | Auto | Cap goods | Realty | Cement | Metals | Oil & gas | Power | FMCG | Cons dur | Chem/agro | Services | All |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Jan-Mar 2021 | Q4 FY21 | -0.85 | +4.06 | -1.83 | -1.09 | +4.19 | -0.25 | -7.09 | +0.40 | -1.28 | +0.63 | -7.84 | +2.46 | +2.61 | +3.17 | -1.13 | +0.82 |
| Apr-Jun 2021 | Q1 FY22 | +0.12 | -1.08 | +4.09 | -2.49 | -1.18 | +1.21 | +2.09 | -0.98 | -0.43 | +0.40 | +0.65 | +0.99 | +1.25 | -0.69 | +0.61 | +0.06 |
| Jul-Sep 2021 | Q2 FY22 | -0.30 | -4.17 | +1.59 | -0.24 | +1.42 | -0.84 | +2.21 | -0.49 | -0.91 | -0.03 | -3.29 | -2.07 | +0.97 | -0.66 | -2.18 | -0.84 |
| Oct-Dec 2021 | Q3 FY22 | +4.12 | -3.28 | -1.94 | +0.67 | +0.04 | -1.32 | -2.20 | -3.43 | -0.26 | -1.17 | -0.07 | -0.89 | -0.71 | -1.92 | +0.51 | -0.64 |
| Jan-Mar 2022 | Q4 FY22 | -2.87 | -2.43 | -0.44 | -0.83 | +3.68 | -0.84 | -3.07 | -2.94 | -0.93 | -3.55 | -1.84 | +1.58 | +2.90 | -1.51 | -0.90 | -0.83 |
| Apr-Jun 2022 | Q1 FY23 | +2.34 | +1.51 | -0.16 | +0.76 | +1.48 | +1.58 | +0.24 | +0.88 | +2.88 | -1.82 | +0.03 | -1.25 | -0.04 | +0.49 | -1.02 | +0.75 |
| Jul-Sep 2022 | Q2 FY23 | +0.91 | +0.73 | +0.85 | -1.20 | -0.23 | +0.45 | -2.52 | -0.54 | +1.12 | +0.19 | +1.61 | +0.03 | -3.59 | +0.29 | -0.43 | +0.03 |
| Oct-Dec 2022 | Q3 FY23 | +0.27 | -0.62 | +1.06 | -0.22 | +2.87 | +0.30 | -1.15 | -1.59 | -1.26 | -0.98 | +1.10 | -1.72 | -4.61 | -0.43 | +1.31 | -0.16 |
| Jan-Mar 2023 | Q4 FY23 | -0.56 | +0.15 | +1.88 | +1.34 | +1.75 | +1.59 | +2.03 | +2.31 | -1.22 | -0.99 | -1.24 | +1.71 | +1.70 | -1.39 | -0.51 | +0.61 |
| Apr-Jun 2023 | Q1 FY24 | -0.68 | -0.39 | -1.89 | -0.33 | +1.30 | -0.37 | -3.95 | +0.72 | -0.72 | -0.89 | +4.54 | +1.16 | -0.07 | -1.02 | -0.96 | -0.30 |
| Jul-Sep 2023 | Q2 FY24 | -1.07 | +0.46 | -0.98 | +2.05 | +1.10 | -0.82 | +6.21 | -0.51 | -0.89 | +1.60 | +0.84 | -0.17 | +2.51 | +0.96 | +0.00 | +0.41 |
| Oct-Dec 2023 | Q3 FY24 | -2.20 | +0.74 | +3.30 | +1.30 | +1.15 | +1.70 | -6.80 | +2.19 | -1.70 | +1.10 | -2.82 | -0.13 | +3.81 | -2.62 | +1.45 | +0.48 |
| Jan-Mar 2024 | Q4 FY24 | +0.38 | +0.94 | -1.60 | +0.71 | +3.69 | +2.11 | +5.00 | +0.51 | +1.07 | +0.25 | -2.53 | +1.93 | +1.13 | -0.19 | -0.77 | +0.88 |
| Apr-Jun 2024 | Q1 FY25 | +0.64 | -0.56 | +1.75 | +1.79 | +0.74 | +1.42 | +1.19 | -3.40 | -0.68 | +0.32 | -0.42 | +0.43 | +3.80 | -0.07 | -0.04 | +0.53 |
| Jul-Sep 2024 | Q2 FY25 | -0.53 | +0.82 | +1.29 | -0.97 | -3.74 | -0.33 | -0.89 | +0.09 | -1.50 | -2.36 | -0.49 | -3.44 | -4.38 | -4.63 | +0.10 | -1.12 |
| Oct-Dec 2024 | Q3 FY25 | -0.32 | -1.07 | +1.72 | -0.40 | -1.70 | +0.03 | -0.84 | +0.23 | -1.16 | -2.15 | -4.45 | -0.32 | -2.89 | +3.70 | -1.76 | -0.79 |
| Jan-Mar 2025 | Q4 FY25 | +0.52 | +0.46 | +3.70 | -0.62 | +1.31 | +3.57 | +1.57 | -0.15 | +1.46 | +2.11 | -0.62 | -0.93 | +0.44 | -0.22 | +1.17 | +0.96 |
| Apr-Jun 2025 | Q1 FY26 | -1.83 | -1.11 | -1.75 | +1.34 | +1.62 | -0.77 | -1.43 | -1.31 | -1.55 | -1.59 | -0.99 | -0.31 | -1.61 | -0.77 | +2.34 | -0.56 |
| Jul-Sep 2025 | Q2 FY26 | +1.93 | +1.10 | +0.86 | -0.65 | +0.90 | +1.98 | +0.24 | -1.24 | +0.68 | +1.89 | -1.36 | +2.69 | -2.12 | -0.75 | -0.03 | +0.67 |
| Oct-Dec 2025 | Q3 FY26 | +0.09 | +0.41 | -1.08 | +0.25 | +2.17 | -1.23 | -1.04 | -0.41 | -0.29 | -2.04 | -3.35 | -1.91 | +5.58 | -0.45 | +2.56 | +0.18 |
| Jan-Mar 2026 | Q4 FY26 | -1.00 | +0.33 | -3.13 | +0.86 | +0.70 | -1.32 | -1.04 | -0.94 | -0.55 | +1.43 | -0.49 | +1.31 | -3.81 | +3.83 | +0.70 | -0.31 |
| Apr-Jun 2026 | Q1 FY27 | +0.15 | +0.40 | +1.43 | +0.63 | +2.70 | +0.33 | -1.44 | +2.25 | +1.38 | -0.28 | -2.79 | +0.21 | -2.64 | -2.53 | -0.50 | +0.17 |

## Number of results in each cell

| Results for | Quarter | Banks | NBFC/Fin | IT | Pharma | Auto | Cap goods | Realty | Cement | Metals | Oil & gas | Power | FMCG | Cons dur | Chem/agro | Services | All |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Jan-Mar 2021 | Q4 FY21 | 14 | 13 | 6 | 11 | 11 | 5 | 1 | 3 | 5 | 5 | 1 | 9 | 3 | 4 | 7 | 98 |
| Apr-Jun 2021 | Q1 FY22 | 14 | 17 | 9 | 11 | 10 | 7 | 2 | 4 | 9 | 7 | 3 | 10 | 3 | 3 | 8 | 117 |
| Jul-Sep 2021 | Q2 FY22 | 14 | 17 | 11 | 11 | 11 | 8 | 2 | 4 | 9 | 7 | 3 | 10 | 5 | 4 | 9 | 125 |
| Oct-Dec 2021 | Q3 FY22 | 14 | 20 | 11 | 12 | 11 | 9 | 4 | 5 | 9 | 7 | 3 | 10 | 4 | 4 | 9 | 132 |
| Jan-Mar 2022 | Q4 FY22 | 14 | 19 | 11 | 12 | 11 | 9 | 3 | 4 | 9 | 7 | 3 | 10 | 6 | 4 | 9 | 131 |
| Apr-Jun 2022 | Q1 FY23 | 14 | 20 | 11 | 12 | 11 | 10 | 3 | 5 | 9 | 7 | 3 | 10 | 6 | 4 | 9 | 134 |
| Jul-Sep 2022 | Q2 FY23 | 14 | 19 | 11 | 13 | 11 | 9 | 3 | 5 | 9 | 7 | 3 | 10 | 6 | 4 | 9 | 133 |
| Oct-Dec 2022 | Q3 FY23 | 14 | 19 | 11 | 13 | 11 | 10 | 3 | 5 | 9 | 7 | 3 | 10 | 5 | 4 | 9 | 133 |
| Jan-Mar 2023 | Q4 FY23 | 14 | 19 | 11 | 13 | 11 | 10 | 3 | 5 | 9 | 7 | 3 | 10 | 6 | 4 | 9 | 134 |
| Apr-Jun 2023 | Q1 FY24 | 14 | 19 | 11 | 13 | 11 | 10 | 3 | 5 | 9 | 6 | 3 | 10 | 6 | 4 | 9 | 133 |
| Jul-Sep 2023 | Q2 FY24 | 14 | 18 | 10 | 13 | 11 | 9 | 3 | 5 | 9 | 7 | 3 | 11 | 6 | 4 | 9 | 132 |
| Oct-Dec 2023 | Q3 FY24 | 14 | 19 | 11 | 13 | 11 | 10 | 3 | 5 | 9 | 7 | 3 | 11 | 6 | 4 | 9 | 135 |
| Jan-Mar 2024 | Q4 FY24 | 14 | 19 | 11 | 13 | 11 | 10 | 3 | 5 | 9 | 7 | 3 | 11 | 6 | 4 | 9 | 135 |
| Apr-Jun 2024 | Q1 FY25 | 14 | 19 | 11 | 13 | 11 | 10 | 3 | 5 | 9 | 7 | 3 | 11 | 6 | 4 | 9 | 135 |
| Jul-Sep 2024 | Q2 FY25 | 14 | 19 | 11 | 13 | 11 | 9 | 3 | 5 | 9 | 7 | 3 | 11 | 6 | 4 | 9 | 134 |
| Oct-Dec 2024 | Q3 FY25 | 18 | 26 | 13 | 14 | 13 | 12 | 6 | 6 | 10 | 8 | 7 | 12 | 8 | 5 | 14 | 172 |
| Jan-Mar 2025 | Q4 FY25 | 18 | 28 | 13 | 14 | 13 | 13 | 7 | 6 | 11 | 8 | 7 | 13 | 8 | 5 | 14 | 178 |
| Apr-Jun 2025 | Q1 FY26 | 18 | 30 | 13 | 16 | 14 | 16 | 8 | 6 | 11 | 8 | 7 | 13 | 12 | 5 | 14 | 191 |
| Jul-Sep 2025 | Q2 FY26 | 18 | 30 | 13 | 16 | 14 | 17 | 8 | 6 | 11 | 8 | 7 | 13 | 12 | 5 | 13 | 191 |
| Oct-Dec 2025 | Q3 FY26 | 18 | 31 | 13 | 16 | 14 | 19 | 8 | 6 | 11 | 8 | 7 | 13 | 12 | 5 | 15 | 196 |
| Jan-Mar 2026 | Q4 FY26 | 18 | 33 | 13 | 16 | 16 | 20 | 8 | 6 | 10 | 8 | 8 | 14 | 13 | 5 | 15 | 203 |
| Apr-Jun 2026 | Q1 FY27 | 18 | 33 | 13 | 16 | 16 | 21 | 8 | 6 | 11 | 8 | 8 | 15 | 13 | 5 | 15 | 206 |

The total of the three-day sums in each cell (the average times the count) is in
[results/sector_3day/sum_3day_by_sector_quarter.csv](../results/sector_3day/sum_3day_by_sector_quarter.csv), and every
result with its three daily returns is in [results/sector_3day/results_3day.csv](../results/sector_3day/results_3day.csv).

## The auto-sector lead

| Check | Result |
|---|---|
| Average three-day sum | +1.20% (264 results); +1.03% after 0.17% costs |
| Against Nifty 50 over the same 3 days | +1.06% (all F&O results: -0.05%) |
| Against the Nifty Auto index over the same 3 days | +0.80% |
| Above the same quarter's average result | +1.16 points; in 18 of 22 quarters; first 14 quarters +1.46, last 8 +0.74 |
| By results year | 2021 +1.56%, 2022 +1.24%, 2023 +1.76%, 2024 +0.46%, 2025 +0.56%, 2026 +1.84% |
| By day | Day-1 +0.24%, Result day +0.31%, Day+1 +0.65% (all results: +0.13%, -0.03%, -0.06%) |
| By stock | 14 of 16 stocks positive; best M&M +2.59%, ASHOKLEY +2.28%, BHARATFORG +2.11%, TVSMOTOR +1.97%; without the top 3 contributors +0.82% |
| By sub-industry | 4-wheelers +1.47%, 2/3-wheelers +1.09%, forgings +2.11%, ancillaries +0.49% |
| Without the best 5 results | +0.96% |
| Same stocks on ordinary 3-day windows without results | +0.20% (+0.08% vs Nifty), so about +1.0% is linked to the results |
| Overlap with the lag 10% + volume rule | 2 of its 85 trades are autos, so it is a separate effect |

A likely reason: car and two-wheeler makers publish monthly sales figures, so their quarterly numbers rarely surprise
on the downside, and the stocks tend to rise into and through the results.

Why to stay cautious:

- **It was found by looking.** The question was descriptive, and this sector grouping was made for this table. The
  15-sector correction allows for the comparison, not for every way the stocks could have been grouped.
- **It weakened in 2024 and 2025** (about +0.5% a result), and the last 8 quarters are about half the first 14.
- **Auto stocks did well in general in 2021-26.** The Nifty Auto comparison (+0.80%) and the ordinary-day placebo
  (+0.20%) take that out, but it is one sector in one strong period.
- **The stock list is today's F&O list.** It flatters every long result.

Treat it as a watch item: buy every auto and auto-parts F&O stock at its cutoff close and sell at the Day+1 close,
logged from the Jul-Sep 2026 results (out in October-November 2026) with no money on it. Expect well under the +1.03%
after costs measured here.

## Sector definitions

| Sector | NSE industries included |
|---|---|
| Banks | Banks |
| NBFC & financials | Finance, Finance - Housing, Financial Institution, Insurance, Capital Markets |
| IT | Computers - Software |
| Pharma & healthcare | Pharmaceuticals, APOLLOHOSP, FORTIS, MAXHEALTH |
| Auto & auto parts | Automobiles - 4 Wheelers, Automobiles - 2 And 3 Wheelers, Auto Ancillaries, Castings/Forgings |
| Capital goods & defence | Electrical Equipment, Engineering, Diesel Engines, Electronics - Industrial, Aerospace & Defence, KEI |
| Real estate & construction | Construction |
| Cement & building materials | Cement And Cement Products, Plastic And Plastic Products |
| Metals & mining | Steel And Steel Products, Aluminium, Metals, Mining |
| Oil & gas | Refineries, Oil Exploration/Production, Gas |
| Power | Power |
| FMCG | Food And Food Processing, Personal Care, Cigarettes, Brew/Distilleries, Diversified |
| Consumer durables & retail | Consumer Durables, Airconditioners, Gems Jewellery And Watches, Paints, Retail, Textile Products, TRENT |
| Chemicals & agro | Chemicals - Speciality, Pesticides And Agrochemicals, Textiles - Synthetic |
| Services, telecom & internet | Telecommunication - Services, Internet & E-commerce, Travel And Transport, Shipping, Hotels, Trading |

Files: scripts in `pattern_tests/sector_3day/` (sector_quarter_table.py: the tables; sector_significance.py: the
chance test for each sector; auto_checks.py: the auto checks; quarter_leaders.py: the best and worst sector each quarter), outputs in
[results/sector_3day/](../results/sector_3day/). The scripts read `LAB_ROOT` (the scratch data folder with
`sector_lab/data`) and write to `REPO_ROOT/results/sector_3day`.
