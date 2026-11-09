#!/bin/bash
# runs.sh NAME CAND MEMBER... : CAND (bots dir) against each member (variants/<member>) on the 128 ladder maps, release,
# own drafts, all replays kept; done-files in ~/tmp-offload/oppfidelity/logs.
source /home/ubuntu/venv/bin/activate
cd /home/ubuntu/cambc-autumn
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
L=~/tmp-offload/oppfidelity/logs; tag=$1; cand=$2; shift 2
for m in "$@"; do
  n=of-$tag-$m
  [ -f replays/ab/$n/summary.json ] && { echo 0 > $L/$n.done; continue; }
  ( python tools/ab.py $cand variants/$m --no-test-draft --suites ladder --name $n --keep-replays 1000 > $L/$n.log 2>&1; echo $? > $L/$n.done ) &
done
wait
