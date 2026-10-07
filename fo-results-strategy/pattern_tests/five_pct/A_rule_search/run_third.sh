#!/bin/bash
cd "$(dirname "$0")"
while pgrep -f "run_secondary.sh" > /dev/null; do sleep 10; done
python3 02_fixed_split.py fo 50 --null signflip > log_fixed_fo_nullsignflip.txt 2>&1
python3 02_fixed_split.py fo 50 --full --null signflip > log_fixed_fo_full22_nullsignflip.txt 2>&1
