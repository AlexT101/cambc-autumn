#!/bin/bash
# id.sh BOT TAG: bench at 100M vs oc-ceil-ref over research/fuel-2026-11-10/tools/maps-id.txt (both sides).
cd /home/ubuntu/cambc-autumn; source /home/ubuntu/venv/bin/activate
export CAMBC_SLOT_WEIGHT=15 CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
N=/home/ubuntu/cambc-autumn/research/fuelgap-2026-11-10/laneB-run/bench; b=$1; t=$2
G=/tmp/claude-1000/-home-ubuntu-cambc-autumn/f02f8021-9589-4295-a15c-bf87a168ba28/scratchpad/bench-g-$t
rm -rf $G
python3 tools/fuel/bench.py run $b --opp variants/oc-ceil-ref --maps $(cat research/fuel-2026-11-10/tools/maps-id.txt) --games $G --out $N/$t.json > $N/$t.log 2>&1
