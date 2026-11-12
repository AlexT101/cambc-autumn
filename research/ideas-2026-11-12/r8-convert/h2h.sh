#!/bin/bash
# h2h.sh ARM SET [SPRT_SEED]: variants/ARM against variants/rc-524 (charybdis 524), own drafts, release, on this programme's
# fresh ladder-v4 maps: SET dev (seeds 8261000-8261019, 6,800 maps) or held (8260000-8260039, 13,600 maps), both sides.
source ~/tmp-offload/r8-convert/env.sh
ARM=$1; SET=$2; S=$HOME/tmp-offload/r8-convert/suites
SUITES=$(ls -d $S/$SET-p* | tr '\n' ',' | sed 's/,$//')
python tools/ab.py variants/$ARM variants/rc-524 --no-test-draft --suites $SUITES --name rc-h2h-$ARM-$SET --keep-replays 1 > $L/h2h-$ARM-$SET.log 2>&1
rm -rf replays/batch-*-ab-rc-h2h-$ARM-$SET-*
touch $L/h2h-$ARM-$SET.done
