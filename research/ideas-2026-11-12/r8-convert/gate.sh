#!/bin/bash
# gate.sh ARM KIND FIRST N [POOL]: fgate variants/ARM against variants/rc-524 (= charybdis 524), fixed read of N batches from FIRST.
# KIND std (Flp4/Mt3q) or fr8 (fr8-g25/Mt3q). POOL v3 (default) or v4.
source ~/tmp-offload/r8-convert/env.sh
ARM=$1; KIND=$2; FIRST=$3; N=$4; POOL=${5:-v3}
EXTRA=""; [ "$KIND" = fr8 ] && EXTRA="--fish-body fr8-g25"
python3 tools/fgate.py variants/$ARM variants/rc-524 --pool $POOL --first-batch $FIRST --max-batches $N --ci 0 --jobs 4 $EXTRA > $L/$ARM-$KIND-$POOL-b$FIRST-n$N.log 2>&1
touch $L/$ARM-$KIND-$POOL-b$FIRST-n$N.done
