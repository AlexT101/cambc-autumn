#!/bin/bash
# Phase 2: the real budget (100k) on maps no gate had played (pool batches 51-62; 53-62 grown from mapgen seeds
# 2425000-2425099): comms alone (the best single at 200k) and the full combination.
source $HOME/venv/bin/activate
cd /home/ubuntu/cambc-autumn
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
O=~/tmp-offload/combo; L=$O/logs
mkdir $L/p2.started 2>/dev/null || exit 0
F="--first-batch 51 --max-batches 12 --ci 0 --jobs 3"
python3 tools/fgate.py variants/cbx-cm variants/charybdis-cb9f86d $F > $L/p2-cbx-cm.log 2>&1 & a=$!; sleep 30
python3 tools/fgate.py variants/cbx-cmgpck variants/charybdis-cb9f86d $F > $L/p2-cbx-cmgpck.log 2>&1 & b=$!
wait $a $b
for v in cbx-cm cbx-cmgpck; do
  python3 research/ideas-2026-11-11/chyport/report.py variants/$v variants/charybdis-cb9f86d 51-62 > $L/report-100k-$v.txt 2>&1
done
python3 research/ideas-2026-11-11/combo/additive.py variants/charybdis-cb9f86d 51-62 --arms cbx-cm,cbx-cmgpck > $L/additive-100k.txt 2>&1
touch $L/p2.done
