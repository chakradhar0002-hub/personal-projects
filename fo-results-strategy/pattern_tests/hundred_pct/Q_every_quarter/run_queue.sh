#!/bin/bash
# runs the jobs in queue.txt, 3 at a time, 1 BLAS thread each; log per job in logs/
cd "$(dirname "$0")"
cat queue.txt | xargs -P 4 -I{} bash -c 'j="{}"; log="logs/$(echo $j | tr " " "_" | sed "s/.py//;s/--//").log"; OPENBLAS_NUM_THREADS=1 python3 $j > "$log" 2>&1'
