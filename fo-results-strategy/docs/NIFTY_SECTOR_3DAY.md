# Results three-day sum by Nifty index sector, every quarter

Question: the earlier sector table ([SECTOR_3DAY.md](SECTOR_3DAY.md)) used 15 hand-made sectors. What does it look like
with **NSE's own Nifty sectors**?

Two views:

- **NSE index sector**: the sector NSE gives each stock for its Nifty indices (the Industry column of the Nifty 500
  list). Every one of the 206 F&O stocks has one, 18 sectors in all, and each stock is in exactly one.
- **Nifty sectoral index members**: the stocks in Nifty Auto, Nifty Bank, Nifty IT and the other sectoral and thematic
  indices, using NSE's current member lists. A stock can be in several, 84 of the 206 F&O stocks are in no sectoral
  index, and Nifty Media has no F&O stock. This view also compares each stock with **its own index over the same three
  days**.

Same window and universe as before: the three-day sum (Day-1 + Result day + Day+1 daily returns, the move from the
cutoff close to the Day+1 close) for every result of a stock in F&O at the time, 3,278 results in 22 seasons (Jan-Mar
2021 to Apr-Jun 2026 results). Figures are averages per result in percent, before costs. "Excess" is the result minus
the average of all F&O results of the same quarter.

## Answer

- **Auto is still the only sector that stands out.**
  - NSE's "Automobile and Auto Components" (15 stocks, 242 results) averages **+1.10%**. It is positive in 18 of 22
    quarters, and it is the only one of 17 sectors that stays significant after allowing for the number of sectors
    (adjusted p 0.018).
  - Nifty Auto members (262 results) average **+1.20%** while the Nifty Auto index moved +0.39% on the same days, so they
    beat their own index by **+0.81%** a result, in 18 of 22 quarters. On ordinary days they are level with the index
    (-0.04%), so the gap is specific to results.
- **But the auto lead is weaker than the earlier p 0.004 suggested.**
  - It comes from 2021-23 and 2026; 2024 and 2025 were about zero.
  - Without its three best stocks (M&M, Bharat Forge, TVS Motor) it falls to +0.64 excess, which is not significant.
  - Tests that allow for sector-wide quarters or for stock effects put the adjusted p at 0.06 to 0.23 for NSE Auto
    (0.02 to 0.05 for Nifty Auto members).
  - This is the same data on which auto was first noticed, so it is a re-check, not new evidence. Treat it as a watch
    item, not a trade.
- **No other sector or index survives the adjustment for the number of sectors tested.**
  - Power (-1.29%), Telecommunication (-1.42%) and Consumer Durables (-0.90%) are the weakest. Power and Telecom rest
    mostly on thin quarters and one stock (Tata Power, Vodafone Idea); Consumer Durables is broader (7 of 10 stocks
    negative) but not significant either.
  - Consumer Services (+1.02%) and Capital Goods (+0.60%) made their gains only in the first 14 quarters.
  - Financial Services, the biggest sector (53 stocks, 837 results), is -0.07%.
- **Stocks do not beat their own sector index around results, apart from autos.**
  - Bank +0.07%, Financial Services -0.06%, FMCG +0.04%, Pharma +0.06%, Healthcare +0.11%, IT +0.27%, Metal -0.25%,
    Oil & Gas -0.38%. None of these is significant.
  - Pooled over all index members the gap is +0.02%, against +0.05% on ordinary days.
- **One thematic index result looks real but is not new.** Nifty Commodities members trail their index by -0.54% a
  result (4 of 22 quarters positive; ordinary days +0.05%). Its members are the already-weak commodity sectors (Power,
  Chemicals, Oil & Gas, Cement), so it is not separate evidence.

## By NSE index sector, all 22 quarters

| Sector | Stocks | Results | Avg 3-day sum | Median | Up | Quarters positive | First 14 q / last 8 q | Best quarter | Worst quarter |
|---|---:|---:|---:|---:|---:|---:|---|---|---|
| Financial Services | 53 | 837 | -0.07% | -0.38% | 47% | 10 of 22 | -0.19% / +0.08% | Apr-Jun 2022 (+1.85%) | Jan-Mar 2022 (-2.62%) |
| Healthcare | 16 | 294 | +0.16% | -0.24% | 49% | 11 of 22 | +0.21% / +0.10% | Jul-Sep 2023 (+2.05%) | Apr-Jun 2021 (-2.49%) |
| Capital Goods | 23 | 247 | +0.60% | +0.93% | 57% | 17 of 22 | +1.35% / +0.01% | Jan-Mar 2024 (+4.99%) | Jan-Mar 2026 (-2.94%) |
| Automobile and Auto Components | 15 | 242 | +1.10% | +1.00% | 58% | 18 of 22 | +1.52% / +0.54% | Jan-Mar 2021 (+4.19%) | Jul-Sep 2024 (-4.51%) |
| Information Technology | 12 | 227 | +0.25% | +0.13% | 51% | 11 of 22 | +0.18% / +0.33% | Apr-Jun 2021 (+4.54%) | Jan-Mar 2026 (-3.36%) |
| Fast Moving Consumer Goods | 14 | 226 | +0.04% | -0.31% | 46% | 10 of 22 | +0.34% / -0.36% | Jan-Mar 2021 (+2.46%) | Jul-Sep 2024 (-4.46%) |
| Metals & Mining | 10 | 200 | -0.17% | +0.15% | 53% | 8 of 22 | -0.49% / +0.35% | Apr-Jun 2022 (+2.41%) | Jul-Sep 2023 (-1.70%) |
| Oil Gas & Consumable Fuels | 9 | 179 | -0.37% | -0.63% | 44% | 10 of 22 | -0.21% / -0.61% | Jul-Sep 2023 (+1.96%) | Jan-Mar 2022 (-3.17%) |
| Consumer Durables | 10 | 149 | -0.90% | -0.78% | 42% | 8 of 22 | -0.74% / -1.07% | Oct-Dec 2025 (+3.91%) | Jul-Sep 2024 (-5.71%) |
| Consumer Services | 9 | 110 | +1.02% | -0.00% | 50% | 15 of 21 | +2.50% / -0.31% | Apr-Jun 2024 (+7.79%) | Oct-Dec 2024 (-4.22%) |
| Chemicals | 5 | 94 | -0.28% | -0.09% | 49% | 6 of 22 | -0.40% / -0.12% | Jan-Mar 2026 (+3.83%) | Jul-Sep 2024 (-4.63%) |
| Power | 8 | 94 | -1.29% | -0.80% | 36% | 6 of 22 | -0.45% / -1.91% | Apr-Jun 2023 (+4.54%) | Jan-Mar 2021 (-7.84%) |
| Services | 5 | 94 | +0.76% | +1.14% | 55% | 13 of 22 | +0.52% / +1.11% | Oct-Dec 2025 (+5.66%) | Jan-Mar 2023 (-2.66%) |
| Construction Materials | 4 | 86 | -0.25% | -0.26% | 43% | 11 of 22 | -0.44% / +0.07% | Oct-Dec 2023 (+2.29%) | Apr-Jun 2024 (-3.55%) |
| Realty | 6 | 82 | -0.32% | -0.46% | 44% | 10 of 22 | -0.26% / -0.36% | Jul-Sep 2023 (+6.21%) | Jan-Mar 2021 (-7.09%) |
| Telecommunication | 3 | 64 | -1.42% | -0.94% | 38% | 7 of 22 | -1.71% / -0.91% | Jul-Sep 2025 (+4.84%) | Jan-Mar 2021 (-6.23%) |
| Construction | 3 | 35 | -0.07% | -0.52% | 43% | 8 of 22 | -1.42% / +0.95% | Jul-Sep 2024 (+8.29%) | Jan-Mar 2024 (-5.37%) |
| Textiles | 1 | 18 | +0.07% | +0.42% | 50% | 9 of 18 | -0.49% / +0.77% | Jul-Sep 2024 (+10.38%) | Jan-Mar 2023 (-10.41%) |
| All F&O results | 206 | 3,278 | +0.04% | -0.15% | 49% | 13 of 22 | +0.12% / -0.06% | Jan-Mar 2025 (+0.96%) | Jul-Sep 2024 (-1.12%) |

Short names used in the wide tables below: Fin services = Financial Services, Cap goods = Capital Goods, Auto =
Automobile and Auto Components, IT = Information Technology, FMCG = Fast Moving Consumer Goods, Metals = Metals &
Mining, Oil & gas = Oil Gas & Consumable Fuels, Cons dur = Consumer Durables, Cons services = Consumer Services, Constr
mat = Construction Materials, Telecom = Telecommunication.

## Is any NSE sector better than chance?

| Sector | Stocks | Results | Avg 3-day sum | Excess over same-quarter avg | Quarters above | Excess first 14 q / last 8 q | Luck p | Holm p |
|---|---:|---:|---:|---:|---:|---|---:|---:|
| Automobile and Auto Components | 15 | 242 | +1.10% | +1.06 | 16 of 22 | +1.39 / +0.61 | 0.001 | 0.018 |
| Power | 8 | 94 | -1.29% | -1.32 | 7 of 22 | -0.55 / -1.89 | 0.012 | 0.187 |
| Telecommunication | 3 | 64 | -1.42% | -1.46 | 4 of 22 | -1.84 / -0.78 | 0.022 | 0.336 |
| Consumer Durables | 10 | 149 | -0.90% | -0.94 | 6 of 22 | -0.87 / -1.02 | 0.023 | 0.336 |
| Consumer Services | 9 | 110 | +1.02% | +1.00 | 16 of 21 | +2.42 / -0.27 | 0.040 | 0.515 |
| Capital Goods | 23 | 247 | +0.60% | +0.55 | 17 of 22 | +1.21 / +0.03 | 0.077 | 0.923 |
| Services | 5 | 94 | +0.76% | +0.73 | 14 of 22 | +0.40 / +1.19 | 0.167 | 1.000 |
| Oil Gas & Consumable Fuels | 9 | 179 | -0.37% | -0.40 | 9 of 22 | -0.32 / -0.52 | 0.273 | 1.000 |
| Financial Services | 53 | 837 | -0.07% | -0.11 | 8 of 22 | -0.32 / +0.13 | 0.479 | 1.000 |
| Information Technology | 12 | 227 | +0.25% | +0.22 | 11 of 22 | +0.08 / +0.41 | 0.519 | 1.000 |
| Realty | 6 | 82 | -0.32% | -0.36 | 8 of 22 | -0.38 / -0.35 | 0.522 | 1.000 |
| Chemicals | 5 | 94 | -0.28% | -0.32 | 6 of 22 | -0.52 / -0.04 | 0.534 | 1.000 |
| Metals & Mining | 10 | 200 | -0.17% | -0.21 | 8 of 22 | -0.60 / +0.43 | 0.556 | 1.000 |
| Construction Materials | 4 | 86 | -0.25% | -0.30 | 10 of 22 | -0.57 / +0.17 | 0.586 | 1.000 |
| Healthcare | 16 | 294 | +0.16% | +0.11 | 14 of 22 | +0.07 / +0.18 | 0.695 | 1.000 |
| Construction | 3 | 35 | -0.07% | -0.09 | 7 of 22 | -1.49 / +0.96 | 0.917 | 1.000 |
| Fast Moving Consumer Goods | 14 | 226 | +0.04% | -0.01 | 11 of 22 | +0.20 / -0.29 | 0.980 | 1.000 |
| Textiles | 1 | 18 | +0.07% | -0.08 | 9 of 18 | -0.83 / +0.87 | 0.950 | not tested (fewer than 30 results) |

Luck p: how often 20,000 random picks of the same number of results in each quarter do as well or as badly (two-sided).
Adjusted (Holm) p allows for the 17 sectors tested. Textiles (only Page Industries) is too small to test.

## Each quarter: best and worst NSE sector

| Results for | Quarter | Results | All F&O avg | Results up | Sectors up | Best sector | Worst sector | Auto rank |
|---|---|---:|---:|---:|---:|---|---|---:|
| Jan-Mar 2021 | Q4 FY21 | 98 | +0.82% | 48% | 10 of 17 | Auto +4.19% (10) | IT -1.83% (6) | 1 of 9 |
| Apr-Jun 2021 | Q1 FY22 | 117 | +0.06% | 55% | 9 of 17 | IT +4.54% (8) | Healthcare -2.49% (11) | 11 of 12 |
| Jul-Sep 2021 | Q2 FY22 | 125 | -0.84% | 41% | 5 of 17 | Auto +1.32% (10) | Fin services -2.42% (31) | 1 of 12 |
| Oct-Dec 2021 | Q3 FY22 | 132 | -0.64% | 46% | 4 of 17 | Cons services +2.50% (4) | Constr mat -3.04% (4) | 3 of 13 |
| Jan-Mar 2022 | Q4 FY22 | 131 | -0.83% | 40% | 6 of 18 | Cons services +7.43% (4) | Oil & gas -3.17% (8) | 2 of 13 |
| Apr-Jun 2022 | Q1 FY23 | 134 | +0.75% | 52% | 12 of 18 | Cap goods +2.54% (9) | Cons dur -1.45% (6) | 5 of 13 |
| Jul-Sep 2022 | Q2 FY23 | 133 | +0.03% | 50% | 9 of 18 | Metals +1.49% (9) | Cons services -2.73% (4) | 8 of 13 |
| Oct-Dec 2022 | Q3 FY23 | 133 | -0.16% | 44% | 6 of 17 | Services +3.29% (4) | Cons dur -4.98% (6) | 2 of 13 |
| Jan-Mar 2023 | Q4 FY23 | 134 | +0.61% | 56% | 10 of 18 | Cap goods +3.30% (9) | Services -2.66% (4) | 3 of 13 |
| Apr-Jun 2023 | Q1 FY24 | 133 | -0.30% | 42% | 8 of 18 | FMCG +1.26% (9) | Cons dur -3.61% (6) | 2 of 13 |
| Jul-Sep 2023 | Q2 FY24 | 132 | +0.41% | 53% | 12 of 18 | Services +3.24% (4) | IT -1.75% (9) | 6 of 13 |
| Oct-Dec 2023 | Q3 FY24 | 135 | +0.48% | 53% | 11 of 18 | Cons services +4.45% (4) | Chemicals -2.62% (4) | 7 of 13 |
| Jan-Mar 2024 | Q4 FY24 | 135 | +0.88% | 53% | 12 of 18 | Cap goods +4.99% (9) | IT -2.11% (10) | 2 of 13 |
| Apr-Jun 2024 | Q1 FY25 | 135 | +0.53% | 53% | 9 of 18 | Cons services +7.79% (4) | Constr mat -3.55% (4) | 8 of 13 |
| Jul-Sep 2024 | Q2 FY25 | 134 | -1.12% | 42% | 7 of 18 | Cons services +1.51% (4) | Cons dur -5.71% (6) | 11 of 13 |
| Oct-Dec 2024 | Q3 FY25 | 172 | -0.79% | 45% | 6 of 18 | Chemicals +3.70% (5) | Power -4.45% (7) | 12 of 15 |
| Jan-Mar 2025 | Q4 FY25 | 178 | +0.96% | 53% | 11 of 18 | IT +4.33% (12) | Cons services -1.87% (7) | 6 of 15 |
| Apr-Jun 2025 | Q1 FY26 | 191 | -0.56% | 46% | 4 of 18 | Cons services +3.03% (7) | Cons dur -2.81% (10) | 4 of 15 |
| Jul-Sep 2025 | Q2 FY26 | 191 | +0.67% | 54% | 10 of 18 | FMCG +2.40% (12) | Services -1.39% (5) | 6 of 15 |
| Oct-Dec 2025 | Q3 FY26 | 196 | +0.18% | 46% | 8 of 18 | Services +5.66% (5) | Power -3.35% (7) | 4 of 15 |
| Jan-Mar 2026 | Q4 FY26 | 203 | -0.31% | 46% | 10 of 18 | Chemicals +3.83% (5) | IT -3.36% (12) | 4 of 15 |
| Apr-Jun 2026 | Q1 FY27 | 206 | +0.17% | 50% | 9 of 18 | Auto +2.85% (15) | Power -2.79% (8) | 1 of 15 |

Best and worst count only sectors with at least 4 results that quarter (number of results in brackets). Auto rank is
where Automobile and Auto Components finished among them.

- Consumer Services was best most often (6 quarters), then Auto, Capital Goods and Services (3 each). Auto was top three
  in 9 quarters. With the hand-made sectors it was best 6 times: Ashok Leyland now sits in Capital Goods, and the new
  small sectors (Consumer Services, Services) top some quarters.
- Consumer Durables was worst most often (5), then IT (4) and Power (3).
- Small sectors with 4-5 results win and lose these rankings more often just because their averages swing more; a
  shuffle test expects about 2.2 "best" quarters for Consumer Services against about 1.1 for Auto.

## Average three-day sum, by NSE sector and quarter (%)

| Results for | Quarter | Fin services | Healthcare | Cap goods | Auto | IT | FMCG | Metals | Oil & gas | Cons dur | Cons services | Chemicals | Power | Services | Constr mat | Realty | Telecom | Construction | Textiles | All |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Jan-Mar 2021 | Q4 FY21 | +1.52 | -1.09 | +1.09 | +4.19 | -1.83 | +2.46 | -0.66 | +0.63 | +1.92 | - | +3.17 | -7.84 | +2.77 | +0.40 | -7.09 | -6.23 | +0.27 | -0.47 | +0.82 |
| Apr-Jun 2021 | Q1 FY22 | -0.54 | -2.49 | +1.12 | -1.23 | +4.54 | -0.61 | -0.19 | +0.16 | +2.47 | +3.14 | -0.69 | +0.65 | +0.88 | -0.98 | +2.09 | +1.07 | -2.06 | - | +0.06 |
| Jul-Sep 2021 | Q2 FY22 | -2.42 | -0.24 | +0.05 | +1.32 | +1.12 | -1.00 | -1.39 | -0.55 | -1.71 | -0.39 | -0.66 | -3.29 | -0.48 | -0.63 | +2.21 | -1.49 | +1.69 | - | -0.84 |
| Oct-Dec 2021 | Q3 FY22 | -0.23 | +0.67 | -2.04 | +1.07 | -3.01 | -0.34 | -0.20 | -1.35 | -2.90 | +2.50 | -1.92 | -0.07 | +1.98 | -3.04 | -0.99 | -2.22 | -3.33 | - | -0.64 |
| Jan-Mar 2022 | Q4 FY22 | -2.62 | -0.83 | +1.77 | +3.80 | -1.71 | +0.31 | -1.24 | -3.17 | +0.27 | +7.43 | -1.51 | -1.84 | -0.97 | -2.94 | -3.07 | -2.04 | -4.61 | +3.70 | -0.83 |
| Apr-Jun 2022 | Q1 FY23 | +1.85 | +0.76 | +2.54 | +1.20 | -0.61 | -1.35 | +2.41 | -0.99 | -1.45 | +2.02 | +0.49 | +0.03 | -0.24 | +0.66 | +0.24 | -2.66 | +1.67 | +1.05 | +0.75 |
| Jul-Sep 2022 | Q2 FY23 | +0.80 | -1.20 | -0.90 | -0.23 | -0.27 | +1.00 | +1.49 | +0.65 | -1.34 | -2.73 | +0.29 | +1.61 | +0.35 | +0.65 | -2.52 | -1.35 | +3.06 | -4.92 | +0.03 |
| Oct-Dec 2022 | Q3 FY23 | -0.24 | -0.22 | +0.83 | +2.62 | +2.01 | -0.75 | -1.55 | -0.95 | -4.98 | +0.92 | -0.43 | +1.10 | +3.29 | -1.76 | -1.15 | -3.82 | -2.31 | - | -0.16 |
| Jan-Mar 2023 | Q4 FY23 | -0.15 | +1.34 | +3.30 | +2.20 | +1.23 | +1.76 | -1.15 | -0.92 | +3.18 | +2.19 | -1.39 | -1.24 | -2.66 | +0.68 | +2.03 | +1.93 | -5.21 | -10.41 | +0.61 |
| Apr-Jun 2023 | Q1 FY24 | -0.51 | -0.33 | +0.55 | +0.90 | -1.23 | +1.26 | -0.49 | -0.70 | -3.61 | +0.87 | -1.02 | +4.54 | -2.29 | +0.75 | -3.95 | -0.62 | +2.37 | +4.34 | -0.30 |
| Jul-Sep 2023 | Q2 FY24 | -0.21 | +2.05 | +0.12 | +0.91 | -1.75 | +0.21 | -1.70 | +1.96 | -1.63 | +2.88 | +0.96 | +0.84 | +3.24 | +0.71 | +6.21 | -2.77 | -0.22 | +2.98 | +0.41 |
| Oct-Dec 2023 | Q3 FY24 | -0.51 | +1.30 | +2.41 | +0.96 | +4.33 | +0.07 | -1.32 | +0.81 | +0.09 | +4.45 | -2.62 | -2.82 | +2.29 | +2.29 | -6.80 | +0.11 | -3.05 | -0.12 | +0.48 |
| Jan-Mar 2024 | Q4 FY24 | +0.71 | +0.71 | +4.99 | +3.18 | -2.11 | +2.00 | +0.22 | +0.81 | -1.09 | +1.39 | -0.19 | -2.53 | -0.87 | +0.82 | +5.00 | +0.20 | -5.37 | +0.96 | +0.88 |
| Apr-Jun 2024 | Q1 FY25 | -0.05 | +1.79 | +1.81 | +0.09 | +1.73 | -0.27 | -1.17 | +0.96 | +1.98 | +7.79 | -0.07 | -0.42 | +0.48 | -3.55 | +1.19 | -3.07 | -0.80 | -2.02 | +0.53 |
| Jul-Sep 2024 | Q2 FY25 | +0.25 | -0.97 | +0.16 | -4.51 | +1.47 | -4.46 | +0.37 | -2.94 | -5.71 | +1.51 | -4.63 | -0.49 | -0.61 | -0.16 | -0.89 | -5.38 | +8.29 | +10.38 | -1.12 |
| Oct-Dec 2024 | Q3 FY25 | -0.72 | -0.40 | +0.22 | -2.18 | +1.51 | -0.15 | -1.09 | -2.35 | -1.27 | -4.22 | +3.70 | -4.45 | +0.27 | +1.87 | +0.44 | -3.03 | -1.37 | -7.10 | -0.79 |
| Jan-Mar 2025 | Q4 FY25 | +0.63 | -0.62 | +3.07 | +1.58 | +4.33 | -0.86 | +1.88 | +1.87 | +0.24 | -1.87 | -0.22 | -0.62 | +3.14 | -0.37 | +0.63 | -2.99 | +7.54 | +2.89 | +0.96 |
| Apr-Jun 2025 | Q1 FY26 | -1.20 | +1.34 | -0.37 | +0.95 | -1.89 | -0.36 | -1.51 | -1.74 | -2.81 | +3.03 | -0.77 | -0.99 | +2.64 | -0.68 | -0.70 | -1.06 | -0.30 | -1.88 | -0.56 |
| Jul-Sep 2025 | Q2 FY26 | +1.50 | -0.65 | +1.34 | +0.52 | +0.89 | +2.40 | +0.18 | +1.43 | -0.37 | -1.03 | -0.75 | -1.36 | -1.39 | -1.11 | +0.30 | +4.84 | +0.58 | -1.09 | +0.67 |
| Oct-Dec 2025 | Q3 FY26 | +0.04 | +0.25 | -0.54 | +2.14 | -0.83 | -2.12 | +1.13 | -2.39 | +3.91 | +2.24 | -0.45 | -3.35 | +5.66 | -0.27 | -0.54 | -0.44 | -0.03 | +5.34 | +0.18 |
| Jan-Mar 2026 | Q4 FY26 | +0.02 | +0.86 | -2.94 | +1.19 | -3.36 | +1.75 | -0.12 | +1.67 | -2.79 | -2.21 | +3.83 | -0.49 | +0.26 | +0.71 | -1.16 | +2.63 | -0.49 | +1.98 | -0.31 |
| Apr-Jun 2026 | Q1 FY27 | +0.16 | +0.63 | +0.52 | +2.85 | +0.75 | -0.01 | +1.78 | -0.69 | -1.30 | +0.76 | -2.53 | -2.79 | -1.43 | +0.54 | -1.12 | +0.05 | -0.33 | -4.38 | +0.17 |

Cells with 1-3 results are noisy (Power, Telecom, Realty, Construction and Textiles have 1-3 results in most quarters).
The counts are in [count_by_sector_quarter.csv](../results/nifty_sector_3day/count_by_sector_quarter.csv) and
[table_count.md](../results/nifty_sector_3day/table_count.md), and the sums in
[table_sum.md](../results/nifty_sector_3day/table_sum.md).

## By Nifty sectoral index, against the index itself

| Index | F&O members | Results | Members avg | Index, same days | Members vs index | Quarters beating index | First 14 q / last 8 q vs index | Ordinary days vs index | Results minus ordinary days (p) |
|---|---:|---:|---:|---:|---:|---:|---|---:|---|
| Nifty Auto | 15 | 262 | +1.20% | +0.39% | +0.81% | 18 of 22 | +1.18% / +0.30% | -0.04% | +0.87% (0.002) |
| Nifty Bank | 14 | 278 | +0.11% | +0.04% | +0.07% | 10 of 22 | +0.23% / -0.17% | +0.06% | +0.02% (0.935) |
| Nifty Financial Services | 20 | 401 | +0.06% | +0.12% | -0.06% | 10 of 22 | +0.01% / -0.18% | +0.08% | -0.09% (0.729) |
| Nifty FMCG | 14 | 226 | +0.04% | 0.00% | +0.04% | 11 of 22 | +0.13% / -0.08% | +0.02% | 0.00% (0.999) |
| Nifty Healthcare | 16 | 294 | +0.16% | +0.06% | +0.11% | 9 of 22 | +0.02% / +0.25% | +0.04% | +0.03% (0.840) |
| Nifty IT | 10 | 213 | +0.26% | -0.01% | +0.27% | 12 of 22 | +0.14% / +0.48% | +0.08% | +0.20% (0.427) |
| Nifty Metal | 11 | 207 | -0.16% | +0.09% | -0.25% | 7 of 22 | -0.67% / +0.37% | +0.02% | -0.29% (0.247) |
| Nifty Pharma | 13 | 260 | +0.09% | +0.03% | +0.06% | 10 of 22 | -0.03% / +0.20% | +0.06% | -0.04% (0.850) |
| Nifty PSU Bank | 7 | 109 | +0.33% | +0.17% | +0.16% | 14 of 22 | -0.33% / +0.68% | -0.02% | +0.05% (0.891) |
| Nifty Private Bank | 10 | 205 | -0.11% | -0.10% | -0.01% | 9 of 22 | +0.16% / -0.28% | +0.01% | -0.04% (0.882) |
| Nifty Realty | 6 | 82 | -0.32% | -0.01% | -0.30% | 9 of 22 | -0.74% / +0.08% | +0.01% | -0.51% (0.272) |
| Nifty Consumer Durables | 9 | 127 | -0.81% | -0.30% | -0.51% | 8 of 22 | -0.40% / -0.63% | +0.01% | -0.48% (0.295) |
| Nifty Oil & Gas | 8 | 158 | -0.36% | +0.02% | -0.38% | 8 of 22 | -0.55% / -0.12% | +0.07% | -0.46% (0.118) |
| Nifty Energy (thematic) | 25 | 352 | -0.50% | -0.04% | -0.46% | 6 of 22 | -0.34% / -0.58% | +0.06% | -0.49% (0.014) |
| Nifty Infrastructure (thematic) | 30 | 534 | +0.33% | +0.27% | +0.06% | 13 of 22 | -0.13% / +0.33% | +0.06% | -0.02% (0.907) |
| Nifty Commodities (thematic) | 28 | 498 | -0.42% | +0.12% | -0.54% | 4 of 22 | -0.73% / -0.28% | +0.05% | -0.62% (<0.001) |
| Nifty India Consumption (thematic) | 30 | 565 | +0.51% | 0.00% | +0.51% | 16 of 22 | +0.75% / +0.17% | +0.05% | +0.46% (0.030) |
| Nifty MNC (thematic) | 17 | 298 | +0.61% | +0.13% | +0.48% | 13 of 22 | +0.80% / 0.00% | +0.03% | +0.44% (0.121) |
| Nifty PSE (thematic) | 20 | 384 | +0.03% | +0.17% | -0.14% | 10 of 22 | -0.30% / +0.08% | +0.04% | -0.09% (0.716) |
| Nifty CPSE (thematic) | 9 | 130 | -0.11% | +0.01% | -0.12% | 11 of 22 | +0.10% / -0.37% | +0.05% | -0.19% (0.394) |
| Nifty Services Sector (thematic) | 30 | 563 | +0.08% | +0.06% | +0.02% | 11 of 22 | +0.10% / -0.11% | +0.09% | -0.06% (0.736) |

Members: today's index members that are in F&O. Index, same days: the index's own three-day sum over each member
result's three sessions. Ordinary days: the same comparison for the same stocks on ordinary three-day windows at least
10 sessions from any result. Results minus ordinary days: quarter-by-quarter difference, with a two-sided p.

- Only Nifty Auto is significant among the 13 sectoral indices with F&O members (adjusted p 0.031 for results minus
  ordinary days; 0.003 for its members against all results).
- Bank vs Private Bank vs PSU Bank: PSU Bank members are +0.33% and Private Bank members -0.11%, but the gap is not
  significant (p 0.53), and PSU Bank swings by ±7 points in single quarters.
- Healthcare (+0.16%) is a little above Pharma (+0.09%); the gap is the three hospitals (Apollo Hospitals +1.21% on its
  own), and it is not significant.
- Nifty India Consumption (+0.51% vs its index) and Nifty MNC (+0.48%) mostly echo the auto stocks in them: without the
  auto names they are +0.22% (p 0.34) and +0.34% (p 0.30) over all results.
- Nifty Energy (-0.46% vs its index) is its power stocks; without them -0.21% (p 0.37).

## Nifty sectoral index members, average three-day sum by quarter (%)

| Results for | Quarter | Auto | Bank | Fin Serv | FMCG | Healthcare | IT | Media | Metal | Pharma | PSU Bank | Pvt Bank | Realty | Cons Dur | Oil & Gas | All |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Jan-Mar 2021 | Q4 FY21 | +4.19 | -0.81 | +4.48 | +2.46 | -1.09 | -1.83 | - | -0.66 | -1.09 | -1.46 | +0.11 | -7.09 | -0.28 | +0.63 | +0.82 |
| Apr-Jun 2021 | Q1 FY22 | -1.18 | +0.23 | -0.01 | -0.61 | -2.49 | +4.54 | - | -0.19 | -3.53 | +0.34 | -0.16 | +2.09 | +1.95 | +0.40 | +0.06 |
| Jul-Sep 2021 | Q2 FY22 | +1.42 | +1.12 | -0.81 | -1.00 | -0.24 | +1.12 | - | -1.39 | -1.40 | -1.88 | +0.76 | +2.21 | -0.77 | -0.03 | -0.84 |
| Oct-Dec 2021 | Q3 FY22 | +0.04 | +4.08 | -1.16 | -0.34 | +0.67 | -3.01 | - | -0.20 | +0.91 | +6.88 | +2.80 | -0.99 | -2.90 | -1.17 | -0.64 |
| Jan-Mar 2022 | Q4 FY22 | +3.68 | -3.94 | -2.84 | +0.31 | -0.83 | -1.71 | - | -1.24 | -0.78 | -7.54 | -1.06 | -3.07 | +0.06 | -3.55 | -0.83 |
| Apr-Jun 2022 | Q1 FY23 | +1.48 | +2.89 | +1.53 | -1.35 | +0.76 | -0.61 | - | +2.41 | +1.06 | -0.57 | +3.31 | +0.24 | -2.51 | -1.82 | +0.75 |
| Jul-Sep 2022 | Q2 FY23 | -0.23 | +2.29 | +0.55 | +1.00 | -1.20 | -0.27 | - | +1.49 | -1.41 | +3.84 | +0.12 | -2.52 | -0.77 | +0.19 | +0.03 |
| Oct-Dec 2022 | Q3 FY23 | +2.87 | +0.57 | -0.78 | -0.75 | -0.22 | +2.01 | - | -1.55 | -0.39 | +2.98 | -0.69 | -1.15 | -4.92 | -0.98 | -0.16 |
| Jan-Mar 2023 | Q4 FY23 | +1.75 | -0.39 | +0.55 | +1.76 | +1.34 | +1.23 | - | -1.15 | +1.43 | -0.49 | -0.28 | +2.03 | +3.18 | -0.99 | +0.61 |
| Apr-Jun 2023 | Q1 FY24 | +1.30 | -0.70 | -0.62 | +1.26 | -0.33 | -1.23 | - | -0.49 | -0.09 | -1.46 | +0.18 | -3.95 | -3.51 | -0.89 | -0.30 |
| Jul-Sep 2023 | Q2 FY24 | +1.10 | -0.03 | +0.21 | +0.21 | +2.05 | -1.75 | - | -1.70 | +1.98 | +2.28 | -2.40 | +6.21 | -1.19 | +1.60 | +0.41 |
| Oct-Dec 2023 | Q3 FY24 | +1.15 | -1.55 | +0.36 | +0.07 | +1.30 | +4.33 | - | -1.32 | +1.09 | +3.92 | -3.77 | -6.80 | +0.78 | +1.10 | +0.48 |
| Jan-Mar 2024 | Q4 FY24 | +3.69 | +0.82 | +1.92 | +2.00 | +0.71 | -2.11 | - | +0.22 | +0.85 | -1.51 | +1.24 | +5.00 | -0.35 | +0.25 | +0.88 |
| Apr-Jun 2024 | Q1 FY25 | +0.74 | -0.36 | -1.78 | -0.27 | +1.79 | +1.73 | - | -1.17 | +2.03 | -0.51 | +1.30 | +1.19 | +2.45 | +0.32 | +0.53 |
| Jul-Sep 2024 | Q2 FY25 | -3.74 | +0.70 | +1.04 | -4.46 | -0.97 | +1.47 | - | +0.37 | -1.60 | +4.11 | -2.34 | -0.89 | -4.17 | -2.36 | -1.12 |
| Oct-Dec 2024 | Q3 FY25 | -1.70 | -1.51 | +1.17 | -0.15 | -0.40 | +1.64 | - | -0.75 | -0.11 | +0.22 | -0.06 | +0.44 | -0.95 | -2.15 | -0.79 |
| Jan-Mar 2025 | Q4 FY25 | +1.31 | +0.16 | -1.04 | -0.86 | -0.62 | +3.68 | - | +1.96 | -0.50 | -1.41 | +0.61 | +0.63 | +1.11 | +2.11 | +0.96 |
| Apr-Jun 2025 | Q1 FY26 | +1.62 | -2.13 | -0.85 | -0.36 | +1.34 | -2.39 | - | -2.00 | +0.94 | +0.40 | -2.66 | -0.70 | -3.50 | -1.59 | -0.56 |
| Jul-Sep 2025 | Q2 FY26 | +0.90 | +2.51 | +1.05 | +2.40 | -0.65 | +0.57 | - | +0.26 | -0.36 | +3.03 | +0.56 | +0.30 | -1.34 | +1.89 | +0.67 |
| Oct-Dec 2025 | Q3 FY26 | +2.17 | -0.40 | +0.75 | -2.12 | +0.25 | -0.12 | - | +1.48 | -0.33 | +0.62 | +0.03 | -0.54 | +5.15 | -2.04 | +0.18 |
| Jan-Mar 2026 | Q4 FY26 | +0.78 | -2.02 | -1.58 | +1.75 | +0.86 | -2.94 | - | -0.60 | +1.13 | -4.27 | +1.51 | -1.16 | -3.04 | +1.43 | -0.31 |
| Apr-Jun 2026 | Q1 FY27 | +2.74 | +1.28 | +0.13 | -0.01 | +0.63 | +1.22 | - | +1.78 | +1.09 | +1.52 | -1.48 | -1.12 | -1.59 | -0.28 | +0.17 |

Media has no F&O member. The counts are in
[index_table_count.md](../results/nifty_sector_3day/index_table_count.md).

## Members against their own index, by quarter (percentage points)

| Results for | Quarter | Auto | Bank | Fin Serv | FMCG | Healthcare | IT | Media | Metal | Pharma | PSU Bank | Pvt Bank | Realty | Cons Dur | Oil & Gas | All vs Nifty 50 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Jan-Mar 2021 | Q4 FY21 | +2.54 | -1.81 | +3.33 | +2.09 | -0.32 | -0.16 | - | +0.52 | -0.47 | -3.17 | -0.19 | -5.17 | -0.30 | +1.17 | +0.04 |
| Apr-Jun 2021 | Q1 FY22 | -0.68 | -0.11 | +0.08 | -1.07 | -1.56 | +2.67 | - | -1.40 | -1.85 | +1.08 | -0.02 | +0.60 | +1.82 | -0.79 | -0.57 |
| Jul-Sep 2021 | Q2 FY22 | +1.21 | +1.24 | -0.63 | +0.07 | -0.58 | +0.73 | - | -0.37 | -1.17 | -2.27 | +0.83 | -0.96 | +0.96 | +0.20 | -0.42 |
| Oct-Dec 2021 | Q3 FY22 | +0.88 | +3.84 | +0.56 | -0.52 | +1.42 | -1.45 | - | -0.67 | +1.40 | +2.49 | +2.62 | -2.54 | -1.16 | -0.65 | +0.17 |
| Jan-Mar 2022 | Q4 FY22 | +2.90 | -1.85 | -1.84 | +0.12 | -0.97 | +0.34 | - | -1.28 | -1.14 | -3.75 | +1.16 | -2.11 | +0.85 | -3.51 | -0.55 |
| Apr-Jun 2022 | Q1 FY23 | +0.53 | +1.26 | -0.80 | -1.49 | -0.29 | +0.38 | - | -0.10 | -0.09 | -1.16 | +1.40 | -0.71 | -2.73 | -2.69 | -0.75 |
| Jul-Sep 2022 | Q2 FY23 | +0.54 | +0.76 | -0.75 | +0.37 | -0.96 | -0.68 | - | -0.75 | -1.03 | -1.46 | -1.36 | -1.69 | -0.64 | -1.25 | -0.90 |
| Oct-Dec 2022 | Q3 FY23 | +2.25 | -0.13 | -0.89 | -2.78 | +0.46 | +1.00 | - | +0.50 | +0.40 | +1.77 | -1.44 | +0.57 | -4.89 | +2.62 | -0.12 |
| Jan-Mar 2023 | Q4 FY23 | +0.41 | -1.00 | -0.01 | +1.08 | +0.74 | +0.63 | - | -1.87 | +1.36 | +1.04 | -1.03 | -0.51 | +2.53 | -0.84 | -0.02 |
| Apr-Jun 2023 | Q1 FY24 | +0.95 | -0.72 | -0.08 | +1.43 | -0.40 | -0.67 | - | +0.16 | -0.78 | -1.36 | -0.26 | -2.58 | -2.96 | -0.83 | +0.01 |
| Jul-Sep 2023 | Q2 FY24 | +0.61 | +0.40 | +0.67 | +0.27 | +1.09 | -0.08 | - | -1.67 | +1.11 | +0.62 | -1.04 | +1.26 | -0.83 | +0.25 | +0.44 |
| Oct-Dec 2023 | Q3 FY24 | +0.57 | -0.06 | +0.47 | +1.27 | -0.41 | +2.01 | - | -1.09 | -0.12 | +1.35 | -1.19 | -4.39 | +0.49 | -1.33 | +0.36 |
| Jan-Mar 2024 | Q4 FY24 | +2.97 | +0.95 | +1.35 | +1.13 | +0.94 | -1.80 | - | -0.76 | +0.86 | -0.33 | +0.57 | +2.84 | -0.74 | -0.50 | +0.65 |
| Apr-Jun 2024 | Q1 FY25 | +0.62 | +0.46 | -0.60 | -0.39 | +0.70 | -0.55 | - | -0.19 | +0.55 | +0.49 | +2.15 | +2.42 | +2.81 | +0.93 | +0.55 |
| Jul-Sep 2024 | Q2 FY25 | -1.20 | +0.20 | +0.71 | -2.62 | -0.14 | +1.88 | - | +1.61 | -0.55 | +0.73 | -2.33 | +2.56 | -2.81 | -0.63 | -0.36 |
| Oct-Dec 2024 | Q3 FY25 | -1.61 | -1.63 | +0.64 | -0.51 | -0.11 | +1.43 | - | -0.47 | +0.09 | +0.36 | +0.06 | +0.57 | -0.20 | -0.87 | -0.77 |
| Jan-Mar 2025 | Q4 FY25 | +0.55 | -0.30 | -1.82 | -0.39 | -0.51 | +0.79 | - | +1.77 | -0.50 | +0.78 | -0.23 | +0.32 | +0.70 | +1.32 | +0.49 |
| Apr-Jun 2025 | Q1 FY26 | +1.39 | -1.43 | -0.13 | -0.15 | +1.12 | -0.34 | - | -1.53 | +1.38 | +1.09 | -1.39 | +0.94 | -2.21 | -0.88 | -0.21 |
| Jul-Sep 2025 | Q2 FY26 | +0.26 | +1.90 | +0.53 | +2.38 | -0.24 | +0.69 | - | -0.43 | -0.19 | +1.43 | -0.11 | -0.37 | -0.98 | +0.95 | +0.43 |
| Oct-Dec 2025 | Q3 FY26 | +1.38 | -0.24 | +0.10 | -1.42 | -0.19 | -0.65 | - | +1.71 | -0.61 | +0.62 | +0.40 | -0.22 | +3.12 | -1.42 | +0.30 |
| Jan-Mar 2026 | Q4 FY26 | -0.17 | -1.07 | -1.15 | +1.88 | +1.05 | +0.60 | - | -0.68 | +1.03 | -0.12 | +1.92 | -0.26 | -1.07 | +1.09 | -0.14 |
| Apr-Jun 2026 | Q1 FY27 | +1.29 | +1.24 | -0.21 | -0.35 | +0.79 | -0.59 | - | +0.99 | +0.86 | +0.61 | -0.79 | -1.61 | -1.98 | -0.60 | -0.09 |

Each cell is the members' three-day sum minus their own index's three-day sum over the same sessions, averaged over
that quarter's results; the last column is all F&O results against Nifty 50. The index's own moves are in
[index_table_own.md](../results/nifty_sector_3day/index_table_own.md).

## The auto lead, checked again

| Check | NSE Auto (242 results) | Nifty Auto members (262 results) |
|---|---|---|
| Average three-day sum | +1.10% | +1.20% |
| Excess over the quarter's average result | +1.06 | +1.16 |
| Luck p / adjusted for the sectors tested | 0.001 / 0.018 | 0.0002 / 0.003 |
| Quarter-by-quarter test, adjusted | 0.23 | 0.051 |
| Random groups of 15 stocks instead of random results, adjusted | 0.064 | 0.021 |
| Against Nifty 50 over the same days | +0.97 | +1.07 |
| Against the Nifty Auto index over the same days | +0.72 | +0.81 |
| Same stocks, ordinary days, against Nifty Auto | -0.03 | -0.04 |
| First 14 quarters / last 8 quarters (excess) | +1.39 / +0.61 (last 8: p 0.22) | +1.18 / +0.30 vs index |
| Without the 3 biggest contributors | +0.64 excess, p 0.09 | +0.80 excess, p 0.03 |
| Only the 10 stocks in F&O since the first season | +1.11 excess, p 0.001 | - |

- By results year (NSE Auto excess): 2021 +1.51, 2022 +1.63, 2023 +1.52, **2024 -0.26, 2025 +0.17**, 2026 +2.05 (3
  quarters so far). Jul-Sep 2024 results alone were -3.39.
- The gain builds after the announcement: Day-1 +0.10, Result day +0.37, Day+1 +0.59. It is larger when results come
  out during market hours (+1.65, 117 results) than after the close (+0.45, 119).
- 13 of 15 auto stocks have a positive excess, so the lean is broad, but its significance needs M&M, Bharat Forge and TVS
  Motor. Without the top 5 stocks it is +0.45, p 0.30.
- The sector definition barely matters. NSE Auto is the hand-made auto group without Ashok Leyland (+2.28% over 22
  results, which NSE puts in Capital Goods). Nifty Auto is NSE Auto with Ashok Leyland and without Force Motors.
- The 25 other auto stocks in the Nifty 500 are not in this study, because only today's F&O stocks are. That includes
  MRF, Balkrishna Industries, Exide and Apollo Tyres, which were F&O stocks in 2021 but are not in the F&O list used
  here.

## The weak and strong sectors, checked

| Sector | Average | Adjusted p | What carries it |
|---|---:|---:|---|
| Power | -1.29% | 0.19 | Tata Power is 44% of the shortfall; without it -0.96% (p 0.11). 1-3 results in 15 of 22 quarters; the worst quarter (Jan-Mar 2021, -7.84%) is one result. |
| Telecommunication | -1.42% | 0.34 | 3 stocks, 1-3 results in every quarter. Vodafone Idea is 64% of the shortfall; without it -0.77% (p 0.31). |
| Consumer Durables | -0.90% | 0.34 | Broad: 7 of 10 stocks negative. Without Havells -0.75% (p 0.10). |
| Consumer Services | +1.02% | 0.52 | All in the first 14 quarters (+2.50%; last 8 -0.31%). Trent is 61% of the excess; without it +0.48% (p 0.37). |
| Capital Goods | +0.60% | 0.92 | First 14 quarters +1.35%, last 8 +0.01%. Without Cummins +0.33%, without Ashok Leyland +0.39%. |

## How NSE's sectors differ from the hand-made ones

| NSE sector | Banks | NBFC/Fin | IT | Pharma | Auto | Cap goods | Realty | Cement | Metals | Oil & gas | Power | FMCG | Cons dur | Chem/agro | Services | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Financial Services | 18 | 33 | - | - | - | - | - | - | - | - | - | - | - | - | 2 | 53 |
| Healthcare | - | - | - | 16 | - | - | - | - | - | - | - | - | - | - | - | 16 |
| Capital Goods | - | - | - | - | 1 | 18 | - | 2 | 1 | - | - | - | 1 | - | - | 23 |
| Automobile and Auto Components | - | - | - | - | 15 | - | - | - | - | - | - | - | - | - | - | 15 |
| Information Technology | - | - | 12 | - | - | - | - | - | - | - | - | - | - | - | - | 12 |
| Fast Moving Consumer Goods | - | - | - | - | - | - | - | - | - | - | - | 14 | - | - | - | 14 |
| Metals & Mining | - | - | - | - | - | - | - | - | 9 | - | - | - | - | - | 1 | 10 |
| Oil Gas & Consumable Fuels | - | - | - | - | - | - | - | - | 1 | 8 | - | - | - | - | - | 9 |
| Consumer Durables | - | - | - | - | - | 2 | - | - | - | - | - | - | 8 | - | - | 10 |
| Consumer Services | - | - | 1 | - | - | - | - | - | - | - | - | 1 | 3 | - | 4 | 9 |
| Chemicals | - | - | - | - | - | - | - | - | - | - | - | - | - | 5 | - | 5 |
| Power | - | - | - | - | - | - | - | - | - | - | 8 | - | - | - | - | 8 |
| Services | - | - | - | - | - | - | - | - | - | - | - | - | - | - | 5 | 5 |
| Construction Materials | - | - | - | - | - | - | - | 4 | - | - | - | - | - | - | - | 4 |
| Realty | - | - | - | - | - | - | 6 | - | - | - | - | - | - | - | - | 6 |
| Telecommunication | - | - | - | - | - | - | - | - | - | - | - | - | - | - | 3 | 3 |
| Construction | - | - | - | - | - | 1 | 2 | - | - | - | - | - | - | - | - | 3 |
| Textiles | - | - | - | - | - | - | - | - | - | - | - | - | 1 | - | - | 1 |
| Total | 18 | 33 | 13 | 16 | 16 | 21 | 8 | 6 | 11 | 8 | 8 | 15 | 13 | 5 | 15 | 206 |

Rows are NSE index sectors and columns the hand-made sectors of [SECTOR_3DAY.md](SECTOR_3DAY.md). The main moves:

- Banks and NBFCs merge into Financial Services, which also takes Paytm and PB Fintech.
- Consumer Services is new: Trent, DMart, Info Edge, Jubilant FoodWorks, Indian Hotels, Eternal, Nykaa, Swiggy and Vishal
  Mega Mart.
- Bharti Airtel, Indus Towers and Vodafone Idea become Telecommunication.
- L&T, NBCC and RVNL become Construction.
- Ashok Leyland goes to Capital Goods, Coal India to Oil Gas & Consumable Fuels, and Adani Enterprises to Metals &
  Mining.
- The full list of the 27 moved stocks is in [table_crosswalk.md](../results/nifty_sector_3day/table_crosswalk.md).

## Caveats

- **Today's lists.** Sector labels, index members and the F&O stock list are all today's. Stocks that left F&O are
  missing, and when each stock joined its index is not known. Today's F&O stocks did well before they entered F&O
  (+0.75 points over the quarter's average), so grouping by today's status can pick up past winners. Auto passes this
  check (the 10 stocks in F&O since 2021 give +1.11). Consumer Services, Capital Goods, Power and Energy rest mostly on
  stocks that joined later.
- **The luck test treats results in a quarter as independent.** Stocks in one sector tend to move together in a season,
  and tests that allow for this give larger p values (the auto table above).
- **Own index includes the stock.** A big stock is part of its own index (for example HDFC Bank and ICICI Bank in Nifty
  Bank, M&M and Maruti in Nifty Auto), which shrinks its gap to the index. Against the other members only, Nifty Auto
  members are +0.93, so this does not create the auto gap.
- **Method change.** The random picks here are drawn without replacement; the earlier sector_significance.py drew with
  replacement. Auto's p is about the same either way (0.0003 for the hand-made group), but small sectors can differ.
- **Results days in general.** All F&O results trailed Nifty 50 by -0.05 over the three days, against +0.11 on ordinary
  days of the same stocks (p 0.07).

## Conclusion

Grouping by NSE's own sectors gives the same picture as the hand-made sectors: only auto stands out. It is a little
smaller (+1.10% for NSE Auto, +1.20% for Nifty Auto members) and clearly fragile. It rests on three stocks and on
2021-23, and the last 8 quarters alone (+0.61 excess, p 0.22) would not show it. Costs (about 0.17%) take about a third
of the recent edge. Keep "buy the auto F&O stocks two sessions before results, sell after Day+1" as a watch item. Log it
each season with no money on it, and stop watching if it stays flat for another 4-6 seasons. No other sector or index
gives a reason to buy or short.

Files: scripts in `pattern_tests/nifty_sector_3day/` and outputs in
[results/nifty_sector_3day/](../results/nifty_sector_3day/):

- nifty_sector_table.py: the NSE-sector tables, quarter leaders and crosswalk.
- nifty_sector_significance.py: the luck test.
- nifty_index_members.py: the Nifty index member view, with index_validation.log.
- skeptic/: the checks of the auto lead, the other sectors, the own-index comparison with ordinary days, and today's
  lists. Its outputs are in results/nifty_sector_3day/skeptic/.

The sector lists are NSE's index files (ind_nifty500list.csv and the ind_nifty...list.csv sector files from
nsearchives.nseindia.com/content/indices/). The scripts read `LAB_ROOT` (the scratch data folder), `LISTS_DIR` (the
downloaded lists) and `REPO_ROOT`. The numbers were rebuilt independently from the raw data and matched cell by cell.
