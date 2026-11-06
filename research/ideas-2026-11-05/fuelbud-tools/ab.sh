#!/bin/bash
# ab.sh CAND REF NAME SUITE [extra ab.py args]: A/B on the fast runner, own drafts, one fair-share group (fuelbud)
# for all of this round's runs; shortcut counts per bot, then the replays are deleted (results and summaries kept).
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
export PATH=$HOME/.cargo/bin:$PATH CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
export CAMBC_SLOT_GROUP=${CAMBC_SLOT_GROUP:-fuelbud}
O=replays/fuel/fuelbud/ab; mkdir -p $O
C=$1 R=$2 N=$3 SU=$4; shift 4
python3 tools/ab.py bots/$C bots/$R --no-test-draft --name $N --suites maps/suites/merged/$SU "$@" > $O/$N.log 2>&1
for d in replays/batch-*-ab-$N-*; do [ -f "$d/results.json" ] && python3 replays/fuel/fc5/shortcuts.py "$d" > $O/$N.shortcuts 2>&1; done
find replays -maxdepth 1 -type d -name "batch-*-ab-$N-*" -exec sh -c 'find "$1" -name "*.repl26a" -delete' _ {} \; 2>/dev/null
find replays/ab/$N -name "*.repl26a" -delete 2>/dev/null
tail -4 $O/$N.log
