#!/bin/bash
source /home/ubuntu/venv/bin/activate
cd /home/ubuntu/cambc-autumn
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
for b in 27 28; do for o in F M; do
  n=lf-c$b-o29$o
  ( python tools/ab.py variants/oc-base$b variants/spar-oc29-$o --no-test-draft --suites ladder --name $n --keep-replays 1000 > ~/tmp-offload/liveforensic/logs/$n.log 2>&1; echo $? > ~/tmp-offload/liveforensic/logs/$n.done ) &
done; done
wait
touch ~/tmp-offload/liveforensic/run1.alldone
