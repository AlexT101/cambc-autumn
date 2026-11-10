#!/bin/bash
# pipe.sh NAME: decode replays/ab/NAME's batch and join BX with truth -> ~/tmp-offload/burst/j-NAME.pkl
set -e
cd /home/ubuntu/cambc-autumn; source /home/ubuntu/venv/bin/activate
B=$(python3 -c "import json;print(json.load(open('replays/ab/$1/summary.json'))['suites'][0]['batch'])" 2>/dev/null || ls -d replays/batch-*-ab-$1-* | tail -n 1)
rm -rf ~/tmp-offload/burst/ana-$1
node tools/replay/extract.mjs $B --out ~/tmp-offload/burst/ana-$1 > ~/tmp-offload/burst/ex-$1.log 2>&1
BATCH=$B python3 ~/tmp-offload/burst/tools/bxjoin.py $B ~/tmp-offload/burst/ana-$1 ~/tmp-offload/burst/j-$1.pkl
