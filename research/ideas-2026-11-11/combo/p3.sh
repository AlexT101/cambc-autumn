#!/bin/bash
# Phase 3: psafe-a (prismsafe) alone and stacked, at 100k on the same held-out batches 51-62 as phase 2
# (psafe used 0-9 at 100k and 0, 16-19 at 200k), for paired additivity with phase 2's arms.
source $HOME/venv/bin/activate
cd /home/ubuntu/cambc-autumn
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
O=~/tmp-offload/combo; L=$O/logs
mkdir $L/p3.started 2>/dev/null || exit 0
F="--first-batch 51 --max-batches 12 --ci 0 --jobs 2"
pids=""
for v in cbx-ps cbx-cmps cbx-allps; do
  python3 tools/fgate.py variants/$v variants/charybdis-cb9f86d $F > $L/p3-$v.log 2>&1 & pids="$pids $!"; sleep 30
done
wait $pids
for v in cbx-ps cbx-cmps cbx-allps; do
  python3 research/ideas-2026-11-11/chyport/report.py variants/$v variants/charybdis-cb9f86d 51-62 > $L/report-100k-$v.txt 2>&1
done
# phase 2's arms read in the same table once its gates are done
until [ -e $L/p2.done ] || ! kill -0 $(cat $L/p2.pid) 2>/dev/null; do sleep 60; done
python3 research/ideas-2026-11-11/combo/additive.py variants/charybdis-cb9f86d 51-62 --arms cbx-cm,cbx-cmgpck,cbx-ps,cbx-cmps,cbx-allps > $L/additive-100k-all.txt 2>&1
touch $L/p3.done
