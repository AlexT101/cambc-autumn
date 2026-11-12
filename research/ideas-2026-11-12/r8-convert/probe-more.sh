#!/bin/bash
# probe-more.sh ARM: probe.sh's games on three more parts of pool v3 batch 17 (p1-p3: 960 maps, 1,920 games against
# fr8-g25), extracted into one dir, then convstats over them.
source ~/tmp-offload/r8-convert/env.sh
ARM=$1; BODY=fr8-g25; S=$HOME/tmp-offload/gatebatch/suites-v3/m2560
E=$HOME/tmp-offload/r8-convert/ext/$ARM-$BODY-more; rm -rf $E
for P in p1 p2 p3; do
  N=rc-probe-$ARM-$BODY-$P
  rm -rf replays/ab/$N replays/batch-*-ab-$N-$P
  FASTRUNNER_LIB=$FGATE_RUNNER_LIB python tools/ab.py variants/$ARM variants/$BODY --no-test-draft --suites $S/b017.parts/$P --name $N --keep-replays 0 \
    --experiment-config $S/b017.json --game-timeout 600 > $L/probe-$ARM-$BODY-$P.log 2>&1
  B=$(ls -d replays/batch-*-ab-$N-$P)
  node tools/replay/extract.mjs $B --out $E --threads 24 > $L/extract-$ARM-$BODY-$P.log 2>&1
  rm -rf $B
done
python research/ideas-2026-11-12/r8-convert/convstats.py $E > $L/conv-$ARM-$BODY-more.txt 2>&1
touch $L/probe-$ARM-$BODY-more.done
