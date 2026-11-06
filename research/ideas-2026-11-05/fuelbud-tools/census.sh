#!/bin/bash
# census.sh CENBOT TAG [NMAPS]: census copy vs oc-tuned4 at the real budget on fresh-533400, both sides; then tables.
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
export PATH=$HOME/.cargo/bin:$PATH CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native CAMBC_SLOT_GROUP=fuelbud
D=/home/ubuntu/cambc-autumn/replays/fuel/fuelbud/cen; mkdir -p $D
b=$1 t=$2 n=${3:-128}
MAPS=$(ls -d /home/ubuntu/cambc-autumn/maps/suites/fresh/fresh-533400/*.map26a | head -$n)
python3 tools/fuel/bench.py run $b --opp ${OPP:-variants/oc-tuned4} --fuel 0 --maps $MAPS --per-map --jobs 64 --out $D/$t.json --games $D/g-$t > $D/$t.log 2>&1
python3 tools/fuel/census/census.py $D/g-$t > $D/$t-census.txt 2>&1
python3 tools/fuel/census/tail.py $D/g-$t > $D/$t-tail.txt 2>&1
python3 tools/fuel/census/gates.py $D/g-$t > $D/$t-gates.txt 2>&1
