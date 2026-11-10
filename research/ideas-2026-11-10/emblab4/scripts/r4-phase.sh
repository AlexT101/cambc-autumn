#!/bin/bash
# Hand the games over from lab OLD to lab NEW with no idle gap, once the fit log FITLOG says "wrote":
#   bash replays/emblab/r4-phase.sh OLD NEW FITLOG
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
export CAMBC_SLOTS=86 CAMBC_SLOT_WEIGHT=35 PATH=$HOME/.cargo/bin:$PATH
OLD=$1; NEW=$2; FIT=$3
until grep -q "^wrote" $FIT 2>/dev/null; do sleep 10; done
echo "$(date -u +%T) fit done"
# The next batch to start playing is OLD's last: its predecessor is still being merged, so none is prepared after it.
n=$(grep -c "batch [0-9]*: 80000 games" replays/emblab/$OLD-run.log)
until [ "$(grep -c 'batch [0-9]*: 80000 games' replays/emblab/$OLD-run.log)" -gt "$n" ]; do sleep 2; done
touch replays/emblab/$OLD/stop
last=$(grep "batch [0-9]*: 80000 games" replays/emblab/$OLD-run.log | tail -1 | sed 's/.*batch \([0-9]*\):.*/\1/')
echo "$(date -u +%T) stop: $OLD ends with batch $last"
until grep -q "batch $((last - 1)): merged" replays/emblab/$OLD-run.log; do sleep 2; done
echo "$(date -u +%T) starting $NEW"
python3 tools/emblab/lab.py run --lab $NEW --games 80000 --batches 60 2>&1 | tee -a replays/emblab/$NEW-run.log
