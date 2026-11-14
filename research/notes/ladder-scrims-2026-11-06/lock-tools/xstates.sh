#!/bin/bash
# xstates.sh NAME [--both]: extract run pl-NAME-2x's replays to /home/ubuntu/tmp-offload/plock/x2 and write its states.
source /home/ubuntu/venv/bin/activate
cd /home/ubuntu/cambc-autumn
n=$1; shift
B=$(grep -oE "/home/ubuntu/cambc-autumn/replays/batch-[0-9]+-[0-9]+-ab-pl-$n-2x-[a-z0-9-]+" replays/ab/pl-$n-2x/*.log | head -1 | sed 's/.*:\///; s/^/\//')
O=/home/ubuntu/tmp-offload/plock/x2
mkdir -p $O/st
node tools/replay/extract.mjs $B --out $O --threads 24 2>&1 | tail -n 1
python3 research/notes/ladder-scrims-2026-11-06/lock-tools/states.py $O $O/st/$n.jsonl oc-lock-$n "$@"
