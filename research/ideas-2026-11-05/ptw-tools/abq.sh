#!/bin/bash
# abq.sh FUEL SUITES NAME_SUFFIX VARIANT... : sequential A/Bs vs oc-retest-clean; logs in tmp-offload/ptw
cd /home/ubuntu/cambc-autumn; source /home/ubuntu/venv/bin/activate
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
fuel=$1; suites=$2; suf=$3; shift 3
for v in "$@"; do
  n=ptw-${v#oc-ptwd-}-$suf
  if [ "$fuel" = real ]; then fa=""; else fa="--fuel $fuel"; fi
  py tools/ab.py variants/$v variants/oc-retest-clean --no-test-draft $fa --suites $suites --name $n > /home/ubuntu/tmp-offload/ptw/ab-$n.log 2>&1
  echo "$n: $(grep '\*\*total' replays/ab/$n/summary.md)"
done
