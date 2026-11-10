#!/bin/bash
# A wave of A/Bs under one slot group with a kept weight: abwave.sh TAG REF WEIGHT SUITES CAND...
# (bot dirs under bots/; results in replays/emblab/r4/greedy/TAG-<cand>.log). The keeper lives as long as this script.
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
TAG=$1; REF=$2; W=$3; SUITES=$4; shift 4
mkdir -p replays/emblab/r4/greedy
export CAMBC_SLOTS=86 CAMBC_SLOT_WEIGHT=$W CAMBC_SLOT_GROUP=emb-greedy CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
python3 tools/emblab/slot_keeper.py emb-greedy $W $$ > /dev/null &
for c in "$@"; do
  n=$(basename $c)
  python3 tools/ab.py $c $REF --no-test-draft --suites $SUITES --name $TAG-$n > replays/emblab/r4/greedy/$TAG-$n.log 2>&1 &
done
wait $(jobs -p | tail -n +2)
for c in "$@"; do n=$(basename $c); echo "$n: $(grep '^CAND' replays/emblab/r4/greedy/$TAG-$n.log | cut -c1-80)"; done
echo WAVE-DONE $TAG $(date -u +%T)
