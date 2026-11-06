#!/bin/bash
# ab.sh CAND NAME SUITE [extra ab.py args]: CAND (a bots/ dir) against ${REF:-variants/oc-base7}, own drafts, fast runner.
cd /home/ubuntu/cambc-autumn; source /home/ubuntu/venv/bin/activate
cand=$1; name=$2; suite=$3; shift 3
CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native python3 tools/ab.py $cand ${REF:-variants/oc-base7} \
  --no-test-draft --suites $suite --name $name "$@" > /home/ubuntu/tmp-offload/draft6/ab-$name.out 2>&1
echo AB-DONE $name >> /home/ubuntu/tmp-offload/draft6/ab-$name.out
