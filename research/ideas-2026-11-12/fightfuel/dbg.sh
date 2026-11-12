#!/bin/bash
# Debug games of variants/NAME against both rt bodies on fgate batch-0 parts (default p6), replays kept, for stdout
# traces: dbg.sh NAME [TAG]; PARTS=p6,p7 FUEL=200000 BATCH=b000.
NAME=$1; TAG=${2:-$1}; PARTS=${PARTS:-p6}; BATCH=${BATCH:-b000}
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
export PATH=$HOME/.cargo/bin:$PATH
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native CAMBC_SLOTS=86 FASTRUNNER_LIB=$PWD/tools/fastengine/runner/target-rt/release/libfastrunner.so
S=/home/ubuntu/tmp-offload/gatebatch/suites/m2560
L=/home/ubuntu/tmp-offload/fightfuel/logs
SUITES=$(echo $PARTS | tr ',' '\n' | sed "s|^|$S/$BATCH.parts/|" | paste -sd,)
for B in Flp4 Mt3q; do
  python3 tools/ab.py variants/$NAME variants/rt-$B --no-test-draft --suites $SUITES --name ff-dbg-$TAG-$B --debug ${FUEL:+--fuel $FUEL} \
    --keep-replays 0 --experiment-config $S/$BATCH.json --game-timeout 900 > $L/ff-dbg-$TAG-$B.log 2>&1 &
done
wait
touch $L/dbg-$TAG.done
