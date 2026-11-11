#!/bin/bash
# Phase 1: 200k screens of the three allypos arms against chy18-cm2k3, pool batches 0-7.
source $HOME/venv/bin/activate
cd /home/ubuntu/cambc-autumn
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
L=~/tmp-offload/allypos/logs
mkdir $L/p1.started 2>/dev/null || exit 0
pids=""
for v in apgc apg apc; do
  python3 tools/fgate.py variants/chy18-$v variants/chy18-cm2k3 --fuel 200000 --screen --max-batches 8 --ci 0 --jobs 2 > $L/p1-$v.log 2>&1 &
  pids="$pids $!"; sleep 30
done
wait $pids
for v in apgc apg apc; do python3 ~/tmp-offload/allypos/report.py variants/chy18-$v variants/chy18-cm2k3 0-7 --fuel 200000 > $L/p1-$v.report 2>&1; done
touch $L/p1.done
