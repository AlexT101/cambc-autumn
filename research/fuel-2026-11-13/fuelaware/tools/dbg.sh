#!/bin/bash
# dbg.sh NAME [TAG]: debug 100k games of variants/NAME against fr8-g25 and mf-f9 on pool-v4 batch 0 PARTS (default p6:
# 320 maps, 1,280 games), replays kept. Logs and done-file in ~/tmp-offload/fuelaware/logs.
NAME=$1; TAG=${2:-$1}; PARTS=${PARTS:-p6}
cd /home/ubuntu/cambc-autumn; source /home/ubuntu/venv/bin/activate
export PATH=$HOME/.cargo/bin:$PATH CAMBC_LOG_LIMIT=16000000
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native CAMBC_SLOTS=86 FASTRUNNER_LIB=$PWD/tools/fastengine/runner/target-rt/release/libfastrunner.so
S=/home/ubuntu/tmp-offload/gatebatch/suites-v4/m2560
L=/home/ubuntu/tmp-offload/fuelaware/logs; mkdir -p $L; rm -f $L/dbg-$TAG.done
SUITES=$(echo $PARTS | tr ',' '\n' | sed "s|^|$S/b000.parts/|" | paste -sd,)
for B in fr8-g25 mf-f9; do
  python3 tools/ab.py variants/$NAME variants/$B --no-test-draft --suites $SUITES --name fa-dbg-$TAG-$B --debug ${FUEL:+--fuel $FUEL} \
    --keep-replays 0 --experiment-config $S/b000.json --game-timeout 900 > $L/dbg-$TAG-$B.log 2>&1 &
done
wait
touch $L/dbg-$TAG.done
