# Results report builder (all NSE data)

Builds `reports/results_report_last_15_quarters.xlsx`: one row per F&O stock per quarter, no filters.

```bash
DATA=report_data                      # any empty folder; ~1.5 GB while building
mkdir -p $DATA/report
curl -sS -A "Mozilla/5.0" -o $DATA/fo_mktlots.csv https://nsearchives.nseindia.com/content/fo/fo_mktlots.csv
python3 nse_events.py   $DATA          # NSE results filings + announcements (results date/time, industry)
python3 nse_prices.py   $DATA 2021-12-01 2026-09-30   # NSE equity bhavcopy + index closes
python3 nse_ca.py       $DATA          # NSE corporate actions (bonus, split, demerger)
python3 build_store.py  $DATA          # NSE F&O bhavcopy around each results season (edit SEASONS)
python3 nse_fin.py      $DATA          # results XBRL up to Dec-2024 quarters
python3 nse_fin_if.py   $DATA          # Integrated Filing XBRL from 2025 (if_lister_rev.py speeds up the listing)
python3 nse_fin_banks.py $DATA         # standalone filings for banks (NPA ratios)
python3 analyze_events.py $DATA        # -> $DATA/report/events.json
python3 fill_exit_legs.py $DATA && python3 analyze_events.py $DATA   # exact run-up exit strikes
python3 build_xlsx.py $DATA/report/events.json ../reports/results_report_last_15_quarters.xlsx
```

To add a quarter: extend `QUARTERS` in `analyze_events.py`, `SEASONS` in `build_store.py`, the quarter-end
sets in `nse_fin.py` / `nse_fin_if.py`, and the date ranges passed to the price and announcement downloads.
The workbook's Summary / By industry / By stock sheets are formulas; recalculate in Excel or LibreOffice.
