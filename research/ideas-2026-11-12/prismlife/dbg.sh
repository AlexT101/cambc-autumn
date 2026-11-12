#!/bin/bash
# Debug games of variants/NAME against rt-Flp4 on one part (default p6), for stdout traces; no extraction.
NAME=$1; PART=${PART:-p6}
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
export PATH=$HOME/.cargo/bin:$PATH
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native CAMBC_SLOTS=86 FASTRUNNER_LIB=$PWD/tools/fastengine/runner/target-rt/release/libfastrunner.so
S=/home/ubuntu/tmp-offload/gatebatch/suites/m2560
python3 tools/ab.py variants/$NAME variants/rt-Flp4 --no-test-draft --suites $S/b000.parts/$PART --name pl-dbg-$NAME --debug ${FUEL:+--fuel $FUEL} \
  --keep-replays 0 --experiment-config $S/b000.json --game-timeout 900 > /home/ubuntu/tmp-offload/prismlife/logs/pl-dbg-$NAME.log 2>&1
touch /home/ubuntu/tmp-offload/prismlife/logs/dbg-$NAME.done
