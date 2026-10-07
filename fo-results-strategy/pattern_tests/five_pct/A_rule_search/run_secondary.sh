#!/bin/bash
# secondary fixed-split runs, run one after another once the main run has finished
cd "$(dirname "$0")"
while pgrep -f "02_fixed_split.py fo 100" > /dev/null; do sleep 10; done
python3 02_fixed_split.py fo 50 --full > log_fixed_fo_full22.txt 2>&1
python3 02_fixed_split.py fo 50 --null week > log_fixed_fo_nullweek.txt 2>&1
python3 02_fixed_split.py all 50 > log_fixed_all.txt 2>&1
python3 02_fixed_split.py fo 50 --n0 20 > log_fixed_fo_n020.txt 2>&1
