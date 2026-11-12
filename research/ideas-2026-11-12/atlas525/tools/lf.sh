#!/bin/bash
# lf.sh CAND : livefork from live r8 positions, chy-525 vs CAND against fr8-g25 members 1-4
cd /home/ubuntu/cambc-autumn; source /home/ubuntu/venv/bin/activate
O=~/tmp-offload/atl/lf-$1
python research/ideas-2026-11-12/fishr8/fr_forkarms.py $O variants/chy-525 variants/$1 --members 1,2,3,4 --forks 100,200,300,450,600 > $O.log 2>&1
python research/ideas-2026-11-12/mitere/fork_read.py $O > $O.read 2>&1
touch $O.done
