# Do sector excesses carry over to the next quarter?

Sector excess = sector average three-day sum minus the all-F&O average of the quarter. Index members: the members' average excess over their own sectoral index. Spearman = rank correlation, over the sectors (indices) with at least 4 results in both quarters, of the excess in quarter t and in quarter t+1 (t+4 = the same results period a year later). Slope = pooled weighted regression of the later excess on the earlier one (weight n1*n2/(n1+n2)).

## Summary

Lag 1:

| | Mean Spearman | Null mean | p | Pairs positive | Slope | Null mean | p |
|---|---:|---:|---:|---:|---:|---:|---:|
| NSE sectors | +0.02 | -0.00 | 0.785 | 11 of 21 | +0.01 | +0.00 | 0.860 |
| Custom sectors | +0.05 | +0.00 | 0.431 | 12 of 21 | +0.00 | +0.00 | 0.996 |
| Sectoral index members (vs own index) | -0.11 | -0.00 | 0.127 | 8 of 21 | -0.08 | -0.00 | 0.229 |

Lag 4:

| | Mean Spearman | Null mean | p | Pairs positive | Slope | Null mean | p |
|---|---:|---:|---:|---:|---:|---:|---:|
| NSE sectors | +0.09 | -0.00 | 0.222 | 8 of 18 | +0.09 | -0.00 | 0.129 |
| Custom sectors | -0.06 | -0.00 | 0.393 | 8 of 18 | -0.03 | -0.00 | 0.605 |
| Sectoral index members (vs own index) | +0.06 | +0.00 | 0.517 | 10 of 18 | +0.02 | -0.01 | 0.683 |

Null: 2,000 within-quarter shuffles of the results across sector labels (every cell keeps its size); for the index members, within-quarter shuffles of the member results over the member slots (a result takes over all index memberships of the slot it lands in, so overlapping indices stay overlapping; its excess is recomputed against each of those indices on its own sessions). p two-sided, before Holm (Holm p in s_table_tests.md).

## Lag 1, per quarter pair

| Results for t -> t+1 | NSE sectors | Spearman | Custom sectors | Spearman | Sectoral indices | Spearman |
|---|---:|---:|---:|---:|---:|---:|
| Jan-Mar 2021 -> Apr-Jun 2021 | 8 | -0.33 | 10 | -0.33 | 11 | +0.01 |
| Apr-Jun 2021 -> Jul-Sep 2021 | 11 | +0.06 | 11 | -0.02 | 11 | +0.20 |
| Jul-Sep 2021 -> Oct-Dec 2021 | 12 | +0.12 | 13 | +0.10 | 12 | -0.04 |
| Oct-Dec 2021 -> Jan-Mar 2022 | 13 | +0.48 | 13 | +0.27 | 12 | -0.20 |
| Jan-Mar 2022 -> Apr-Jun 2022 | 13 | +0.27 | 13 | -0.14 | 12 | +0.32 |
| Apr-Jun 2022 -> Jul-Sep 2022 | 13 | -0.03 | 13 | +0.47 | 12 | +0.15 |
| Jul-Sep 2022 -> Oct-Dec 2022 | 13 | -0.33 | 13 | +0.20 | 12 | -0.24 |
| Oct-Dec 2022 -> Jan-Mar 2023 | 13 | +0.04 | 13 | +0.02 | 12 | -0.26 |
| Jan-Mar 2023 -> Apr-Jun 2023 | 13 | +0.42 | 13 | +0.57 | 12 | -0.36 |
| Apr-Jun 2023 -> Jul-Sep 2023 | 13 | +0.15 | 13 | +0.29 | 12 | -0.08 |
| Jul-Sep 2023 -> Oct-Dec 2023 | 13 | +0.23 | 13 | +0.16 | 12 | +0.17 |
| Oct-Dec 2023 -> Jan-Mar 2024 | 13 | +0.21 | 13 | +0.02 | 12 | +0.08 |
| Jan-Mar 2024 -> Apr-Jun 2024 | 13 | -0.03 | 13 | +0.20 | 12 | -0.15 |
| Apr-Jun 2024 -> Jul-Sep 2024 | 13 | +0.10 | 13 | -0.15 | 12 | -0.64 |
| Jul-Sep 2024 -> Oct-Dec 2024 | 13 | -0.04 | 13 | +0.22 | 12 | +0.44 |
| Oct-Dec 2024 -> Jan-Mar 2025 | 15 | +0.28 | 15 | +0.04 | 13 | -0.13 |
| Jan-Mar 2025 -> Apr-Jun 2025 | 15 | -0.32 | 15 | -0.34 | 13 | -0.42 |
| Apr-Jun 2025 -> Jul-Sep 2025 | 15 | -0.31 | 15 | +0.00 | 13 | +0.10 |
| Jul-Sep 2025 -> Oct-Dec 2025 | 15 | -0.39 | 15 | -0.27 | 13 | -0.58 |
| Oct-Dec 2025 -> Jan-Mar 2026 | 15 | -0.10 | 15 | -0.12 | 13 | -0.51 |
| Jan-Mar 2026 -> Apr-Jun 2026 | 15 | -0.14 | 15 | -0.06 | 13 | -0.16 |

## Lag 4, per quarter pair

| Results for t -> t+4 | NSE sectors | Spearman | Custom sectors | Spearman | Sectoral indices | Spearman |
|---|---:|---:|---:|---:|---:|---:|
| Jan-Mar 2021 -> Jan-Mar 2022 | 9 | +0.50 | 11 | -0.01 | 11 | +0.35 |
| Apr-Jun 2021 -> Apr-Jun 2022 | 12 | -0.07 | 11 | -0.28 | 11 | +0.16 |
| Jul-Sep 2021 -> Jul-Sep 2022 | 12 | -0.46 | 13 | -0.20 | 12 | +0.65 |
| Oct-Dec 2021 -> Oct-Dec 2022 | 13 | +0.53 | 13 | +0.29 | 12 | -0.06 |
| Jan-Mar 2022 -> Jan-Mar 2023 | 13 | +0.68 | 13 | +0.48 | 12 | +0.16 |
| Apr-Jun 2022 -> Apr-Jun 2023 | 13 | +0.41 | 13 | +0.16 | 12 | +0.34 |
| Jul-Sep 2022 -> Jul-Sep 2023 | 13 | -0.24 | 13 | -0.73 | 12 | -0.13 |
| Oct-Dec 2022 -> Oct-Dec 2023 | 13 | +0.50 | 13 | +0.05 | 12 | -0.03 |
| Jan-Mar 2023 -> Jan-Mar 2024 | 13 | +0.51 | 13 | +0.29 | 12 | +0.04 |
| Apr-Jun 2023 -> Apr-Jun 2024 | 13 | -0.23 | 13 | +0.16 | 12 | -0.45 |
| Jul-Sep 2023 -> Jul-Sep 2024 | 13 | -0.16 | 13 | -0.54 | 12 | +0.10 |
| Oct-Dec 2023 -> Oct-Dec 2024 | 13 | -0.01 | 13 | -0.14 | 12 | +0.30 |
| Jan-Mar 2024 -> Jan-Mar 2025 | 13 | -0.35 | 13 | -0.12 | 12 | -0.75 |
| Apr-Jun 2024 -> Apr-Jun 2025 | 13 | +0.10 | 13 | -0.05 | 12 | -0.14 |
| Jul-Sep 2024 -> Jul-Sep 2025 | 13 | -0.03 | 13 | +0.15 | 12 | +0.11 |
| Oct-Dec 2024 -> Oct-Dec 2025 | 15 | -0.07 | 15 | -0.20 | 13 | -0.02 |
| Jan-Mar 2025 -> Jan-Mar 2026 | 15 | -0.29 | 15 | -0.42 | 13 | -0.03 |
| Apr-Jun 2025 -> Apr-Jun 2026 | 15 | +0.21 | 15 | +0.10 | 13 | +0.37 |
