#!/bin/bash
# One arm's games: variants/NAME against both rt bodies on fgate pool parts, then each game's outcome and champion
# statistics (tools/draftlab/outcome.mjs) to ~/tmp-offload/fightfuel/out/TAG-{Flp4,Mt3q}.jsonl. The arm's own replays
# (replays/batch-*-ab-ff-arm-TAG-*) are removed after that unless KEEP=1. arm.sh NAME [TAG]; DEBUG=1 (debug builds: the
# self-capping copies need them), FUEL=200000, PARTS=p0,..,p7 (default all eight: 2,560 maps, 10,240 games), BATCH=b000.
# Compare arms with quick.py.
NAME=$1; TAG=${2:-$1}; PARTS=${PARTS:-p0,p1,p2,p3,p4,p5,p6,p7}; BATCH=${BATCH:-b000}
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
export PATH=$HOME/.cargo/bin:$PATH
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native CAMBC_SLOTS=86 FASTRUNNER_LIB=$PWD/tools/fastengine/runner/target-rt/release/libfastrunner.so
S=/home/ubuntu/tmp-offload/gatebatch/suites/m2560
O=/home/ubuntu/tmp-offload/fightfuel; L=$O/logs; mkdir -p $O/out $L
SUITES=$(echo $PARTS | tr ',' '\n' | sed "s|^|$S/$BATCH.parts/|" | paste -sd,)
for B in Flp4 Mt3q; do
  N=ff-arm-$TAG-$B
  python3 tools/ab.py variants/$NAME variants/rt-$B --no-test-draft --suites $SUITES --name $N ${DEBUG:+--debug} ${FUEL:+--fuel $FUEL} \
    --keep-replays 0 --experiment-config $S/$BATCH.json --game-timeout 900 > $L/$N.log 2>&1 &
done
wait
for B in Flp4 Mt3q; do
  node tools/draftlab/outcome.mjs replays/batch-*-ab-ff-arm-$TAG-$B-* --out $O/out/$TAG-$B.jsonl --threads 16 > $L/out-$TAG-$B.log 2>&1
  if [ -z "$KEEP" ] && [ -s $O/out/$TAG-$B.jsonl ]; then
    for d in replays/batch-*-ab-ff-arm-$TAG-$B-*; do mv "$d" $O/trash-$(basename "$d") 2>/dev/null; done
  fi
done
grep -h "Out-of-fuel" $L/ff-arm-$TAG-Flp4.log $L/ff-arm-$TAG-Mt3q.log > $O/out/$TAG.oof
touch $L/arm-$TAG.done
