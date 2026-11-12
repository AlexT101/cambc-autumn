#!/bin/bash
# Phase 4: the rest of the factorial at 100k on batches 51-62 (gp alone, cm+gp, cm+ck), to place the full stack's
# extra out-of-fuel turns at 100k and read additivity at the real budget.
source $HOME/venv/bin/activate
cd /home/ubuntu/cambc-autumn
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
O=~/tmp-offload/combo; L=$O/logs
mkdir $L/p4.started 2>/dev/null || exit 0
F="--first-batch 51 --max-batches 12 --ci 0 --jobs 2"
pids=""
for v in cbx-gp cbx-cmgp cbx-cmck; do
  python3 tools/fgate.py variants/$v variants/charybdis-cb9f86d $F > $L/p4-$v.log 2>&1 & pids="$pids $!"; sleep 30
done
wait $pids
for v in cbx-gp cbx-cmgp cbx-cmck; do
  python3 research/ideas-2026-11-11/chyport/report.py variants/$v variants/charybdis-cb9f86d 51-62 > $L/report-100k-$v.txt 2>&1
done
until [ -e $L/p3.done ] || ! kill -0 $(cat $L/p3.pid) 2>/dev/null; do sleep 60; done
python3 research/ideas-2026-11-11/combo/additive.py variants/charybdis-cb9f86d 51-62 \
  --arms cbx-cm,cbx-gp,cbx-cmgp,cbx-cmck,cbx-cmgpck,cbx-ps,cbx-cmps,cbx-allps > $L/additive-100k-full.txt 2>&1
touch $L/p4.done
