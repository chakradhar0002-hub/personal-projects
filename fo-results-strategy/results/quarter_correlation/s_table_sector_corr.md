# Which sectors are best and worst together

Pearson correlation, across quarters, of sector excess e(s,t) (sector average three-day sum minus the all-F&O average of that quarter), for sectors with at least 4 results in at least 18 of the 22 quarters. Each pair uses the quarters where both sectors have at least 4 results.

## NSE index sectors

| | Fin services | Healthcare | Cap goods | Auto | IT | FMCG | Metals | Oil & gas | Cons dur | Cons services | Chemicals | Services | Constr mat |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Fin services | - | -0.26 | -0.31 | -0.43 | -0.22 | -0.15 | +0.52 | -0.00 | -0.39 | -0.48 | +0.07 | -0.09 | +0.19 |
| Healthcare | -0.26 | - | -0.24 | +0.10 | -0.29 | -0.01 | -0.25 | -0.07 | -0.25 | +0.34 | -0.01 | +0.18 | +0.10 |
| Cap goods | -0.31 | -0.24 | - | +0.08 | +0.31 | -0.11 | -0.25 | -0.29 | +0.15 | +0.23 | -0.42 | -0.43 | -0.08 |
| Auto | -0.43 | +0.10 | +0.08 | - | -0.48 | +0.43 | -0.22 | -0.13 | +0.15 | +0.23 | +0.08 | +0.02 | -0.26 |
| IT | -0.22 | -0.29 | +0.31 | -0.48 | - | -0.45 | -0.00 | -0.03 | +0.12 | -0.02 | -0.35 | +0.07 | +0.04 |
| FMCG | -0.15 | -0.01 | -0.11 | +0.43 | -0.45 | - | -0.39 | +0.34 | +0.04 | -0.18 | +0.43 | -0.44 | +0.09 |
| Metals | +0.52 | -0.25 | -0.25 | -0.22 | -0.00 | -0.39 | - | -0.26 | -0.20 | -0.37 | -0.13 | -0.03 | +0.15 |
| Oil & gas | -0.00 | -0.07 | -0.29 | -0.13 | -0.03 | +0.34 | -0.26 | - | -0.18 | -0.33 | +0.24 | -0.06 | -0.03 |
| Cons dur | -0.39 | -0.25 | +0.15 | +0.15 | +0.12 | +0.04 | -0.20 | -0.18 | - | +0.26 | +0.05 | +0.01 | -0.24 |
| Cons services | -0.48 | +0.34 | +0.23 | +0.23 | -0.02 | -0.18 | -0.37 | -0.33 | +0.26 | - | -0.41 | +0.10 | -0.49 |
| Chemicals | +0.07 | -0.01 | -0.42 | +0.08 | -0.35 | +0.43 | -0.13 | +0.24 | +0.05 | -0.41 | - | +0.17 | +0.25 |
| Services | -0.09 | +0.18 | -0.43 | +0.02 | +0.07 | -0.44 | -0.03 | -0.06 | +0.01 | +0.10 | +0.17 | - | -0.07 |
| Constr mat | +0.19 | +0.10 | -0.08 | -0.26 | +0.04 | +0.09 | +0.15 | -0.03 | -0.24 | -0.49 | +0.25 | -0.07 | - |

Mean r over the 78 pairs -0.07 (shuffle null -0.07: the excesses of all sectors add up to zero each quarter, so chance alone gives slightly negative r); mean r^2 0.065 (null 0.057, p 0.283).

| | Pair | r | Null mean r | Quarters | Pair p | Familywise p |
|---|---|---:|---:|---:|---:|---:|
| Most negative | Cons services / Constr mat | -0.49 | -0.03 | 20 | 0.041 | 0.956 |
| Most negative | Auto / IT | -0.48 | -0.08 | 22 | 0.060 | 0.999 |
| Most negative | Fin services / Cons services | -0.48 | -0.11 | 21 | 0.117 | 1.000 |
| Most negative | IT / FMCG | -0.45 | -0.07 | 22 | 0.089 | 1.000 |
| Most negative | FMCG / Services | -0.44 | -0.05 | 21 | 0.074 | 0.999 |
| Most positive | Fin services / Metals | +0.52 | -0.15 | 22 | <0.001 | 0.082 |
| Most positive | FMCG / Chemicals | +0.43 | -0.04 | 21 | 0.029 | 0.932 |
| Most positive | Auto / FMCG | +0.43 | -0.08 | 22 | 0.017 | 0.798 |
| Most positive | FMCG / Oil & gas | +0.34 | -0.06 | 22 | 0.063 | 0.999 |
| Most positive | Healthcare / Cons services | +0.34 | -0.05 | 21 | 0.079 | 0.999 |

Null mean r: average r of that pair over 2,000 within-quarter shuffles of the results across sector labels (below 0 because the sector excesses add up to zero each quarter). Pair p (two-sided): share of shuffles in which the pair's r is at least as far from its null mean as the observed r. Familywise p: share of shuffles in which the largest such distance over all 78 pairs reaches the observed distance (single-step maxT; corrects for having looked at every pair). Under the null the largest distance has median 0.56 and 95th percentile 0.69.

Short names: Fin services = Financial Services; Healthcare = Healthcare; Cap goods = Capital Goods; Auto = Automobile and Auto Components; IT = Information Technology; FMCG = Fast Moving Consumer Goods; Metals = Metals & Mining; Oil & gas = Oil Gas & Consumable Fuels; Cons dur = Consumer Durables; Cons services = Consumer Services; Chemicals = Chemicals; Services = Services; Constr mat = Construction Materials.

## Custom 15 sectors

| | NBFC/Fin | Banks | Pharma | Auto | Cap goods | IT | FMCG | Services | Metals | Cons dur | Oil & gas | Cement | Chem/agro |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| NBFC/Fin | - | -0.31 | -0.31 | -0.13 | -0.08 | -0.30 | +0.03 | -0.13 | -0.13 | -0.39 | -0.02 | +0.39 | +0.10 |
| Banks | -0.31 | - | -0.01 | -0.34 | +0.01 | -0.01 | -0.27 | +0.01 | +0.57 | -0.35 | -0.06 | -0.32 | -0.04 |
| Pharma | -0.31 | -0.01 | - | +0.11 | -0.38 | -0.25 | -0.15 | +0.29 | -0.17 | +0.28 | -0.11 | +0.04 | -0.01 |
| Auto | -0.13 | -0.34 | +0.11 | - | -0.37 | -0.47 | +0.30 | -0.10 | -0.10 | +0.31 | -0.24 | -0.10 | +0.07 |
| Cap goods | -0.08 | +0.01 | -0.38 | -0.37 | - | +0.64 | -0.11 | -0.22 | +0.18 | -0.20 | +0.09 | +0.09 | -0.39 |
| IT | -0.30 | -0.01 | -0.25 | -0.47 | +0.64 | - | -0.31 | +0.05 | -0.03 | -0.04 | +0.07 | +0.20 | -0.35 |
| FMCG | +0.03 | -0.27 | -0.15 | +0.30 | -0.11 | -0.31 | - | -0.31 | -0.21 | -0.03 | +0.12 | -0.12 | +0.30 |
| Services | -0.13 | +0.01 | +0.29 | -0.10 | -0.22 | +0.05 | -0.31 | - | -0.19 | +0.01 | -0.04 | -0.18 | -0.17 |
| Metals | -0.13 | +0.57 | -0.17 | -0.10 | +0.18 | -0.03 | -0.21 | -0.19 | - | -0.37 | -0.15 | -0.02 | -0.05 |
| Cons dur | -0.39 | -0.35 | +0.28 | +0.31 | -0.20 | -0.04 | -0.03 | +0.01 | -0.37 | - | -0.23 | -0.16 | -0.20 |
| Oil & gas | -0.02 | -0.06 | -0.11 | -0.24 | +0.09 | +0.07 | +0.12 | -0.04 | -0.15 | -0.23 | - | -0.11 | +0.16 |
| Cement | +0.39 | -0.32 | +0.04 | -0.10 | +0.09 | +0.20 | -0.12 | -0.18 | -0.02 | -0.16 | -0.11 | - | -0.15 |
| Chem/agro | +0.10 | -0.04 | -0.01 | +0.07 | -0.39 | -0.35 | +0.30 | -0.17 | -0.05 | -0.20 | +0.16 | -0.15 | - |

Mean r -0.07 (null -0.07); mean r^2 0.053 (null 0.057, p 0.645). Null max |r - null mean r|: median 0.56, 95th percentile 0.69.

| | Pair | r | Null mean r | Quarters | Pair p | Familywise p |
|---|---|---:|---:|---:|---:|---:|
| Most negative | Auto / IT | -0.47 | -0.08 | 22 | 0.076 | 1.000 |
| Most negative | NBFC/Fin / Cons dur | -0.39 | -0.09 | 20 | 0.219 | 1.000 |
| Most negative | Cap goods / Chem/agro | -0.39 | -0.05 | 21 | 0.147 | 1.000 |
| Most positive | Cap goods / IT | +0.64 | -0.07 | 22 | <0.001 | 0.030 |
| Most positive | Banks / Metals | +0.57 | -0.09 | 22 | 0.001 | 0.109 |
| Most positive | NBFC/Fin / Cement | +0.39 | -0.07 | 21 | 0.039 | 0.945 |

Short names: NBFC/Fin = NBFC & financials; Banks = Banks; Pharma = Pharma & healthcare; Auto = Auto & auto parts; Cap goods = Capital goods & defence; IT = IT; FMCG = FMCG; Services = Services, telecom & internet; Metals = Metals & mining; Cons dur = Consumer durables & retail; Oil & gas = Oil & gas; Cement = Cement & building materials; Chem/agro = Chemicals & agro.
