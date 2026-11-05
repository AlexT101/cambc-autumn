#!/bin/bash
# screen.sh SUITE NAMEPREFIX var1 var2 ...: one ab.py at a time, each var vs oc-base1, own drafts.
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
suite=$1; pre=$2; shift 2
for v in "$@"; do
  python3 tools/ab.py variants/oc-altar-$v variants/oc-base1 --no-test-draft --suites $suite --name altar-$pre-$v $EXTRA > replays/altar/ab-$pre-$v.log 2>&1
  grep -E "CAND|overall|win|SPRT|out-of-fuel" replays/altar/ab-$pre-$v.log | head -6 | sed "s/^/[$v] /"
done
