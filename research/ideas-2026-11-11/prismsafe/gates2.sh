#!/bin/bash
# Fixed reads: ARM FIRST N FUEL(empty = 100k) TAG
cd /home/ubuntu/cambc-autumn
L=/home/ubuntu/tmp-offload/prismsafe/logs
arm=$1; first=$2; n=$3; fuel=$4; tag=$5
F=""; [ -n "$fuel" ] && F="--fuel $fuel"
python3 tools/fgate.py variants/psafe-$arm variants/charybdis-cb9f86d $F --first-batch $first --max-batches $n --ci 0 > $L/gate-$tag.log 2>&1
touch $L/gate-$tag.done
