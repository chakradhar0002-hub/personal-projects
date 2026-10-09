| # | candidate | definition | n | avg | w/o best 5 | median | quarters +/with | 2023 share | eligible | clears bar |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | BASE | XN>4 & cut RSI14>50 | 122 | +2.65 | +1.53 | +2.71 | 10/14 | 80% | no | no |
| 1 | C01_RSI55 | XN>4 & cut RSI14>55 | 91 | +2.70 | +1.31 | +3.13 | 8/14 | 80% | yes | no |
| 2 | C02_RSI60 | XN>4 & cut RSI14>60 | 65 | +3.87 | +1.97 | +3.66 | 9/12 | 75% | yes | no |
| 3 | C03_RSI65 | XN>4 & cut RSI14>65 | 47 | +4.08 | +1.89 | +3.66 | 10/12 | 63% | yes | no |
| 4 | C04_RSI70 | XN>4 & cut RSI14>70 | 19 | +6.40 | +2.25 | +4.71 | 6/7 | 44% | no | no |
| 5 | C05_XN5 | XN>5 & cut RSI14>50 | 89 | +4.12 | +2.76 | +3.76 | 12/14 | 64% | yes | YES |
| 6 | C06_XN6 | XN>6 & cut RSI14>50 | 73 | +3.59 | +2.06 | +3.59 | 10/14 | 67% | yes | YES |
| 7 | C07_XN8 | XN>8 & cut RSI14>50 | 31 | +3.06 | +0.36 | +4.03 | 8/11 | 44% | no | no |
| 8 | C08_VOL1.5 | base & rx_vol_ratio_50>=1.5 | 119 | +2.93 | +1.78 | +3.06 | 10/14 | 76% | yes | no |
| 9 | C09_VOL2 | base & rx_vol_ratio_50>=2 | 117 | +3.03 | +1.87 | +3.13 | 10/14 | 75% | yes | no |
| 10 | C10_VOL3 | base & rx_vol_ratio_50>=3 | 107 | +2.88 | +1.82 | +3.17 | 11/14 | 76% | yes | no |
| 11 | C11_CLV75 | base & (C-L)/(H-L) on day k >= 0.75 | 75 | +3.22 | +1.39 | +1.98 | 8/14 | 90% | yes | no |
| 12 | C12_GAPHOLD | base & gap>2% & low(k)>close(k-1) | 51 | +1.93 | +0.42 | +3.17 | 10/14 | 37% | yes | no |
| 13 | C13_BRK20 | base & close(k) > highest high of prior 20 sessions | 101 | +3.75 | +2.44 | +3.59 | 11/14 | 67% | yes | YES |
| 14 | C14_BRK52 | base & close(k) > highest high of prior 250 sessions | 65 | +3.52 | +1.74 | +3.66 | 9/13 | 63% | yes | no |
| 15 | C15_LAG0 | base & 21-session stock-minus-Nifty return to cutoff > 0 | 95 | +2.97 | +1.62 | +3.06 | 9/14 | 76% | yes | no |
| 16 | C16_LAG10 | base & 21-session stock-minus-Nifty return to cutoff > 10 | 21 | +3.28 | -0.27 | +4.03 | 7/10 | 22% | no | no |
| 17 | C17_SECREL0 | base & 21-session stock-minus-own-sector-index return to cutoff > 0 | 82 | +2.94 | +1.36 | +3.32 | 9/14 | 78% | yes | no |
| 18 | C18_GOOD | base & GOOD (PAT YoY>25 & sales YoY>15, or margin chg YoY>+2pp) | 75 | +2.92 | +1.33 | +3.50 | 8/14 | 74% | yes | no |
| 19 | C19_STRONG | base & rq PAT YoY>25 & rq sales YoY>15 | 34 | +4.99 | +1.93 | +5.79 | 7/12 | 61% | no | no |
| 20 | C20_PAT50 | base & rq PAT YoY>50 | 36 | +2.08 | -1.13 | +3.36 | 6/13 | 123% | yes | no |
| 21 | C21_LARGE | base & mcap>=100,000 cr | 34 | +0.44 | -1.17 | +1.35 | 7/12 | -3% | no | no |
| 22 | C22_SMALL | base & mcap<50,000 cr | 34 | +4.47 | +1.40 | +2.34 | 9/14 | 83% | no | no |
| 23 | C23_RSI60_XN6 | XN>6 & cut RSI14>60 | 43 | +3.78 | +1.41 | +3.50 | 9/12 | 71% | yes | no |
| 24 | C24_RSI60_VOL2 | XN>4 & cut RSI14>60 & vol>=2 | 62 | +4.37 | +2.41 | +3.81 | 9/12 | 70% | yes | YES |
| 25 | C25_XN6_VOL2 | XN>6 & cut RSI14>50 & vol>=2 | 72 | +3.65 | +2.10 | +3.63 | 10/14 | 67% | yes | YES |
| 26 | C26_VOL2_CLV75 | base & vol>=2 & CLV>=0.75 | 71 | +3.73 | +1.82 | +2.28 | 9/14 | 84% | yes | no |
| 27 | C27_BRK20_VOL1.5 | base & BRK20 & vol>=1.5 | 100 | +3.86 | +2.54 | +3.63 | 11/14 | 65% | yes | YES |
| 28 | C28_BRK52_VOL1.5 | base & BRK52 & vol>=1.5 | 64 | +3.69 | +1.89 | +3.71 | 9/13 | 61% | yes | no |
| 29 | C29_GOOD_VOL1.5 | base & GOOD & vol>=1.5 | 73 | +3.15 | +1.54 | +3.66 | 8/14 | 72% | yes | no |
| 30 | C30_GOOD_XN6 | XN>6 & cut RSI14>50 & GOOD | 50 | +3.38 | +1.57 | +3.95 | 10/14 | 60% | yes | no |
| 31 | C31_RSI60_GOOD | XN>4 & cut RSI14>60 & GOOD | 43 | +4.03 | +1.56 | +3.87 | 9/12 | 62% | yes | no |
| 32 | C32_XN6_CLV75 | XN>6 & cut RSI14>50 & CLV>=0.75 | 48 | +3.84 | +1.49 | +2.96 | 9/13 | 74% | yes | no |
| 33 | C33_LAG0_VOL2 | base & LAG0 & vol>=2 | 91 | +3.43 | +2.04 | +3.50 | 10/14 | 70% | yes | YES |
| 34 | C34_RSI60_CLV75 | XN>4 & cut RSI14>60 & CLV>=0.75 | 39 | +4.87 | +1.65 | +3.50 | 8/12 | 82% | yes | no |
| 35 | C35_RSI60_BRK52 | XN>4 & cut RSI14>60 & BRK52 | 44 | +5.04 | +2.49 | +4.12 | 8/11 | 60% | yes | YES |
| 36 | C36_GOOD_CLV75 | base & GOOD & CLV>=0.75 | 45 | +4.19 | +1.58 | +3.13 | 9/14 | 69% | yes | no |
| 37 | C37_SECREL0_VOL2 | base & SECREL0 & vol>=2 | 79 | +3.36 | +1.75 | +3.59 | 10/14 | 73% | yes | no |
| 38 | C38_LARGE_VOL2 | base & LARGE & vol>=2 | 32 | +0.72 | -0.96 | +2.08 | 7/12 | -2% | no | no |
