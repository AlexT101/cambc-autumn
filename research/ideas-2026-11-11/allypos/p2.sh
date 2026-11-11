#!/bin/bash
# Phase 2 (200k): apc on batches 8-15; apc2 and apk (told tile over recent sight in the crew count) on 0-15.
source $HOME/venv/bin/activate
cd /home/ubuntu/cambc-autumn
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
L=~/tmp-offload/allypos/logs
mkdir $L/p2.started 2>/dev/null || exit 0
F="--fuel 200000 --screen --ci 0 --jobs 2"
python3 tools/fgate.py variants/chy18-apc variants/chy18-cm2k3 $F --first-batch 8 --max-batches 8 > $L/p2-apc.log 2>&1 & p1=$!; sleep 30
python3 tools/fgate.py variants/chy18-apc2 variants/chy18-cm2k3 $F --max-batches 16 > $L/p2-apc2.log 2>&1 & p2=$!; sleep 30
python3 tools/fgate.py variants/chy18-apk variants/chy18-cm2k3 $F --max-batches 16 > $L/p2-apk.log 2>&1 & p3=$!
wait $p1 $p2 $p3
for v in apc apc2 apk apgc apg; do python3 ~/tmp-offload/allypos/report.py variants/chy18-$v variants/chy18-cm2k3 0-15 --fuel 200000 > $L/p2-$v.report 2>&1; done
touch $L/p2.done
