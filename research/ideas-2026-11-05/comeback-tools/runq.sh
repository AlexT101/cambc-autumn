#!/bin/bash
# runq.sh QUEUE [PAR]: each line "name suite fuel extra-ab-args..." runs ab.py variants/oc-cb-<name> against
# variants/oc-retest-clean (variants must exist; fuel "real" = the real budget), PAR at a time; done lines go to QUEUE.done. Skips names in .done.
source /home/ubuntu/venv/bin/activate
cd /home/ubuntu/cambc-autumn
Q=$1; PAR=${2:-2}
T=research/ideas-2026-11-05/comeback-tools
mkdir -p $T/logs
touch $Q.done
run() {
  set -- $1
  name=$1; suite=$2; fuel=$3; shift 3
  tag=$name-$(basename $suite)-$fuel
  grep -qx "$tag" $Q.done && return
  fa="--fuel $fuel"; [ "$fuel" = real ] && fa=""
  CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native python3 tools/ab.py variants/oc-cb-$name variants/oc-retest-clean \
    --no-test-draft --suites maps/suites/merged/$suite $fa --name cb-$tag "$@" > $T/logs/$tag.log 2>&1
  python3 $T/cbrate.py cb-$tag >> $T/logs/$tag.log 2>&1
  echo "$tag" >> $Q.done
}
export -f run; export Q T
grep -v '^#' $Q | grep -v '^\s*$' | xargs -P $PAR -I{} bash -c 'run "{}"'
