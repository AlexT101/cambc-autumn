#!/bin/bash
# full.sh CAND NAME SUITE [EXTRA...]: a full A/B of bots/variants/CAND against oc-retest-clean on maps/suites/merged/SUITE.
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
c=$1 n=$2 s=$3; shift 3
REF=${REF:-variants/oc-retest-clean}
[ -f replays/ab/$n/summary.md ] && exit 0
python3 tools/ab.py variants/$c $REF --no-test-draft --suites maps/suites/merged/$s --name $n "$@" > research/ideas-2026-11-05/astport-tools/logs/$n.log 2>&1
python3 research/ideas-2026-11-05/astport-tools/clean.py $n
