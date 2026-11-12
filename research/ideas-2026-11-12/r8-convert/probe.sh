#!/bin/bash
# probe.sh ARM [BODY]: variants/ARM against the Fish r8 body (default fr8-g25) on the 320 maps of pool v3 batch 17's
# first part (640 games, the body's seeds as fgate sets them), every replay kept, extracted, then convstats.
source ~/tmp-offload/r8-convert/env.sh
ARM=$1; BODY=${2:-fr8-g25}; S=$HOME/tmp-offload/gatebatch/suites-v3/m2560
N=rc-probe-$ARM-$BODY
rm -rf replays/ab/$N replays/batch-*-ab-$N-p0
FASTRUNNER_LIB=$FGATE_RUNNER_LIB python tools/ab.py variants/$ARM variants/$BODY --no-test-draft --suites $S/b017.parts/p0 --name $N --keep-replays 0 \
  --experiment-config $S/b017.json --game-timeout 600 > $L/probe-$ARM-$BODY.log 2>&1
B=$(ls -d replays/batch-*-ab-$N-p0)
E=$HOME/tmp-offload/r8-convert/ext/$ARM-$BODY; rm -rf $E
node tools/replay/extract.mjs $B --out $E --threads 24 > $L/extract-$ARM-$BODY.log 2>&1
python research/ideas-2026-11-12/r8-convert/convstats.py $E > $L/conv-$ARM-$BODY.txt 2>&1
rm -rf $B
touch $L/probe-$ARM-$BODY.done
