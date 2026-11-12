#!/bin/bash
# arm.sh for debug builds (self-capping variants need them): armdbg.sh NAME OUT; FUEL and PARTS as arm.sh.
NAME=$1; OUT=${2:-$1}; PARTS=${PARTS:-p0,p1}
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
export PATH=$HOME/.cargo/bin:$PATH
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native CAMBC_SLOTS=86 FASTRUNNER_LIB=$PWD/tools/fastengine/runner/target-rt/release/libfastrunner.so
S=/home/ubuntu/tmp-offload/gatebatch/suites/m2560
O=/home/ubuntu/tmp-offload/prismlife; L=$O/logs; mkdir -p $O/out
SUITES=$(echo $PARTS | tr ',' '\n' | sed "s|^|$S/b000.parts/|" | paste -sd,)
for B in Flp4 Mt3q; do
  N=pl-arm-$OUT-$B
  python3 tools/ab.py variants/$NAME variants/rt-$B --no-test-draft --suites $SUITES --name $N --debug ${FUEL:+--fuel $FUEL} \
    --keep-replays 0 --experiment-config $S/b000.json --game-timeout 900 > $L/$N.log 2>&1 &
done
wait
for B in Flp4 Mt3q; do node tools/draftlab/outcome.mjs replays/batch-*-ab-pl-arm-$OUT-$B-* --out $O/out/$OUT-$B.jsonl --threads 24 > $L/out-$OUT-$B.log 2>&1; done
grep -h "Out-of-fuel" $L/pl-arm-$OUT-Flp4.log $L/pl-arm-$OUT-Mt3q.log > $O/out/$OUT.oof
touch $L/arm-$OUT.done
