# Results report builder (all NSE data)

Builds `reports/results_report_last_15_quarters.xlsx` (one row per F&O stock per quarter, no filters), the HTML viewer
`reports/results_report_last_15_quarters.html`, and the cross-check `reports/results_cross_check.csv`.

```bash
DATA=report_data                      # any empty folder; ~1.5 GB while building
mkdir -p $DATA/report
curl -sS -A "Mozilla/5.0" -o $DATA/fo_mktlots.csv https://nsearchives.nseindia.com/content/fo/fo_mktlots.csv
python3 nse_events.py   $DATA          # NSE results filings + announcements (results date/time, industry)
python3 nse_prices.py   $DATA 2021-12-01 2026-09-30   # NSE equity bhavcopy + index closes, weekend sessions included
python3 nse_ca.py       $DATA          # NSE corporate actions (bonus, split, demerger)
python3 build_store.py  $DATA          # NSE F&O bhavcopy around each results season (edit SEASONS)
python3 nse_fin.py      $DATA          # results XBRL up to Dec-2024 quarters
python3 nse_fin_if.py   $DATA          # Integrated Filing XBRL from 2025, read by period dates (xbrl_periods.py);
                                       # if_lister_rev.py speeds up the listing
python3 nse_fin_banks.py $DATA         # standalone filings for banks (NPA ratios), up to Dec-2024 quarters
python3 analyze_events.py $DATA        # -> $DATA/report/events.json
python3 fill_exit_legs.py $DATA && python3 analyze_events.py $DATA   # exact run-up exit strikes
# second-source check (bseindia.com is blocked here: BSE closes via Yahoo .BO tickers, financials via Yahoo)
python3 -I bse_check_fetch.py $DATA/report/events.json $DATA/report/yahoo_bse.json
python3 -I bse_check_compare.py $DATA/report/events.json $DATA/report/yahoo_bse.json \
    ../reports/results_cross_check.csv $DATA/report/cross_check_summary.json $DATA/report/nse_prices.db
python3 build_xlsx.py $DATA/report/events.json ../reports/results_report_last_15_quarters.xlsx $DATA/report/cross_check_summary.json
# recalculate the formulas (Excel, or LibreOffice: the xlsx skill's recalc.py), then
python3 build_html.py ../reports/results_report_last_15_quarters.xlsx ../reports/results_report_last_15_quarters.html \
    $DATA/report/cross_check_summary.json
```

`industry_fill.csv` gives an industry to the 84 stocks whose NSE announcements carry none (NSE labels, checked
against NSE's Nifty 500 sector list).

To add a quarter: extend `QUARTERS` in `analyze_events.py`, `SEASONS` in `build_store.py`, the quarter-end
sets in `nse_fin.py` / `nse_fin_if.py`, and the date ranges passed to the price and announcement downloads.
The workbook's Summary / By industry / By stock sheets are formulas; recalculate in Excel or LibreOffice before
building the HTML viewer (it shows the recalculated values).
