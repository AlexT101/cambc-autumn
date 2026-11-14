#!/bin/bash
# ab.sh ARM SUITE NAME [extra ab.py args]: CAND oc-obese-ARM vs oc-base10 on maps/suites/merged/SUITE
source /home/ubuntu/venv/bin/activate
cd /home/ubuntu/cambc-autumn
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
arm=$1; suite=$2; name=$3; shift 3
mkdir -p /home/ubuntu/tmp-offload/obese/logs
python3 tools/ab.py variants/oc-obese-$arm variants/oc-base10 --no-test-draft --suites maps/suites/merged/$suite --name $name "$@" > /home/ubuntu/tmp-offload/obese/logs/ab-$name.log 2>&1
