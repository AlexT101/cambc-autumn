#!/bin/bash
# ab.sh ARM SUITE [extra ab.py args]: CAND oc-kill-ARM vs oc-retest-clean on maps/suites/merged/kill-SUITE
source /home/ubuntu/venv/bin/activate
cd /home/ubuntu/cambc-autumn
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
arm=$1; suite=$2; shift 2
name=kill-$arm-$suite${TAG:+-$TAG}
python3 tools/ab.py variants/oc-kill-$arm variants/oc-retest-clean --no-test-draft --suites maps/suites/merged/kill-$suite --name $name "$@" > /tmp/claude-1000/-home-ubuntu-cambc-autumn/3650a530-f591-417e-a0c5-31524a1e3260/scratchpad/kill/ab-$name.log 2>&1
