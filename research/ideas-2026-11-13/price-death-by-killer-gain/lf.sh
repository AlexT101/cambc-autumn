#!/bin/bash
# lf.sh CAND  -> livefork from live r8 positions, chy-525 vs CAND against fr8-g25 members 1-4; ~/tmp-offload/pdkg/lf-CAND{.log,.done}
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
export CAMBC_SLOTS=86 CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
O=~/tmp-offload/pdkg/lf-$1
python research/ideas-2026-11-12/fishr8/fr_forkarms.py $O variants/chy-525 variants/$1 --members 1,2,3,4 --forks 100,200,300,450,600 > $O.log 2>&1
echo $? > $O.done
python research/ideas-2026-11-12/mitere/fork_read.py $O > $O.read 2>&1
