#!/bin/bash
# q2x.sh SUITE TAG V...: each oc-lock-V against oc-retest-clean at 2x fuel, in turn; logs in replays/fuel/plock/ab-pl-V-TAG.log
source /home/ubuntu/venv/bin/activate
cd /home/ubuntu/cambc-autumn
suite=$1; tag=$2; shift 2
for v in "$@"; do
  CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native python3 tools/ab.py variants/oc-lock-$v ${REF:-variants/oc-retest-clean} \
    --no-test-draft --suites $suite --fuel 200000 --name pl-$v-$tag > replays/fuel/plock/ab-pl-$v-$tag.log 2>&1
done
