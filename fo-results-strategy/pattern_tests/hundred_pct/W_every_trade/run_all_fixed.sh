#!/bin/bash
# two queues of fixed-split / hindsight jobs (each: real + nulls)
cd "$(dirname "$0")"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
(
python3 run_fixed.py fo split 3day gross 50 50 --seed 11 > log_fo_split_3day_gross.txt 2>&1
python3 run_fixed.py fo split tp gross 50 50 --seed 12 > log_fo_split_tp_gross.txt 2>&1
python3 run_fixed.py fo split 3day net 50 50 --seed 13 > log_fo_split_3day_net.txt 2>&1
python3 run_fixed.py fo split tp net 50 50 --seed 14 > log_fo_split_tp_net.txt 2>&1
python3 run_fixed.py all split 3day gross 20 20 --seed 15 > log_all_split_3day_gross.txt 2>&1
) &
(
python3 run_fixed.py fo full22 3day gross 50 50 --seed 21 > log_fo_full22_3day_gross.txt 2>&1
python3 run_fixed.py fo full22 tp gross 50 50 --seed 22 > log_fo_full22_tp_gross.txt 2>&1
python3 run_fixed.py fo full22 3day net 50 50 --seed 23 > log_fo_full22_3day_net.txt 2>&1
python3 run_fixed.py fo full22 tp net 50 50 --seed 24 > log_fo_full22_tp_net.txt 2>&1
python3 run_fixed.py all full22 3day gross 20 20 --seed 25 > log_all_full22_3day_gross.txt 2>&1
) &
wait
echo ALLDONE > fixed_done.flag
