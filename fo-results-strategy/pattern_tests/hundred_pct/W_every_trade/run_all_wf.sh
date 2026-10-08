#!/bin/bash
cd "$(dirname "$0")"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
python3 run_wf.py fo tp gross 0 0 > log_wf_fo_tp_gross_realonly.txt 2>&1
python3 run_wf.py fo 3day net 0 0 > log_wf_fo_3day_net.txt 2>&1
python3 run_wf.py fo tp net 0 0 > log_wf_fo_tp_net.txt 2>&1
python3 run_wf.py all 3day gross 0 0 > log_wf_all_3day_gross.txt 2>&1
python3 run_wf.py fo 3day gross 20 20 --seed 31 > log_wf_fo_3day_gross.txt 2>&1
python3 run_wf.py fo tp gross 20 20 --seed 32 > log_wf_fo_tp_gross.txt 2>&1
echo WFDONE > wf_done.flag
