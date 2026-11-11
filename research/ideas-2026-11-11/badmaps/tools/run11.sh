#!/bin/bash
# usage: run11.sh TAG SUITE_DIR FUELARG CAND...   (plays each CAND against both bodies on SUITE_DIR)
cd /home/ubuntu/cambc-autumn
TAG=$1; SUITE=$2; FUEL=$3; shift 3
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
L=/home/ubuntu/tmp-offload/badmaps/logs11; mkdir -p $L
for C in "$@"; do
  for B in Mt3q Flp4; do
    N=bm11-$TAG-$C-$B
    python3 tools/ab.py variants/$C variants/spar-dvn1-$B --no-test-draft --suites $SUITE --name $N $FUEL --keep-replays 1 > $L/$N.log 2>&1
  done
done
touch $L/$TAG.done
