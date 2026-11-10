#!/bin/bash
# A wave of A/Bs under one slot group with a kept weight: abwave.sh TAG REF WEIGHT SUITES CAND...
# (bot dirs under bots/; logs in replays/emblab/r5/ab/TAG-<cand>.log). The keeper lives as long as this script.
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
TAG=$1; REF=$2; W=$3; SUITES=$4; shift 4
mkdir -p replays/emblab/r5/ab
export CAMBC_SLOTS=86 CAMBC_SLOT_WEIGHT=$W CAMBC_SLOT_GROUP=emb5-ab-$TAG CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH
python3 tools/emblab/slot_keeper.py emb5-ab-$TAG $W $$ > /dev/null &
for c in "$@"; do
  n=$(basename $c)
  python3 tools/ab.py $c $REF --no-test-draft --suites $SUITES --name e5$TAG-$n > replays/emblab/r5/ab/$TAG-$n.log 2>&1 &
done
wait $(jobs -p | tail -n +2)
for c in "$@"; do n=$(basename $c); echo "$n: $(grep '^CAND' replays/emblab/r5/ab/$TAG-$n.log | cut -c1-100)"; done
echo WAVE-DONE $TAG $(date -u +%T)
