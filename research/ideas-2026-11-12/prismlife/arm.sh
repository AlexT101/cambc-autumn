#!/bin/bash
# Mechanism read of one arm: variants/NAME against both rt bodies on fgate b000 parts PARTS (default p0,p1), release,
# real fuel, replays kept; then each game's outcome and champion statistics (tools/draftlab/outcome.mjs) to
# ~/tmp-offload/prismlife/out/NAME-{Flp4,Mt3q}.jsonl. Compare arms with quick.py.
NAME=$1; OUT=${2:-$1}; PARTS=${PARTS:-p0,p1}  # OUT: the output's name, for a second set of parts
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
export PATH=$HOME/.cargo/bin:$PATH
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native CAMBC_SLOTS=86 FASTRUNNER_LIB=$PWD/tools/fastengine/runner/target-rt/release/libfastrunner.so
S=/home/ubuntu/tmp-offload/gatebatch/suites/m2560
O=/home/ubuntu/tmp-offload/prismlife; L=$O/logs; mkdir -p $O/out
SUITES=$(echo $PARTS | tr ',' '\n' | sed "s|^|$S/b000.parts/|" | paste -sd,)
for B in Flp4 Mt3q; do
  N=pl-arm-$OUT-$B
  python3 tools/ab.py variants/$NAME variants/rt-$B --no-test-draft --suites $SUITES --name $N ${FUEL:+--fuel $FUEL} \
    --keep-replays 0 --experiment-config $S/b000.json --game-timeout 900 > $L/$N.log 2>&1 &
done
wait
for B in Flp4 Mt3q; do node tools/draftlab/outcome.mjs replays/batch-*-ab-pl-arm-$OUT-$B-* --out $O/out/$OUT-$B.jsonl --threads 24 > $L/out-$OUT-$B.log 2>&1; done
grep -h "Out-of-fuel" $L/pl-arm-$OUT-Flp4.log $L/pl-arm-$OUT-Mt3q.log > $O/out/$OUT.oof
touch $L/arm-$OUT.done
