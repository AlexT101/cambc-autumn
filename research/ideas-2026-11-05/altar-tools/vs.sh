#!/bin/bash
# vs.sh SUITE PRE OPP bot1 bot2 ...: each bot (a bots/ path) against OPP, own drafts.
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
suite=$1; pre=$2; opp=$3; shift 3
for v in "$@"; do
  n=$(basename $v)
  python3 tools/ab.py $v $opp --no-test-draft --suites $suite --name altar-$pre-$n > replays/altar/ab-$pre-$n.log 2>&1
  grep -E "CAND [0-9]|Out-of-fuel" replays/altar/ab-$pre-$n.log | head -3 | sed "s/^/[$n vs $(basename $opp)] /"
done
