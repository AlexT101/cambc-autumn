#!/bin/bash
# usage: runs.sh DONEFILE "cand ref name [extra]" ...   (ladder suite, own drafts, all replays kept)
cd /home/ubuntu/cambc-autumn; source /home/ubuntu/venv/bin/activate
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
done=$1; shift
for spec in "$@"; do
  set -- $spec; c=$1; r=$2; n=$3; shift 3
  [ -f replays/ab/$n/summary.json ] && continue
  python3 tools/ab.py $c $r --no-test-draft --suites ${SUITES:-ladder} --name $n --keep-replays ${KEEP:-0} "$@" > ~/tmp-offload/spar/$n.log 2>&1
done
touch $done
