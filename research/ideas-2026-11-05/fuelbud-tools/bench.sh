#!/bin/bash
# bench.sh BOT TAG [MODES]: bench.py vs oc-retest-clean (OPP) at 100M (def wide pool) or the real budget (real = wide, poolreal).
# Games kept in replays/fuel/fuelbud/bench/g-TAG-*; KEEP=0 deletes them after (the JSONs keep the replay hashes).
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
export PATH=$HOME/.cargo/bin:$PATH CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native CAMBC_SLOT_GROUP=fuelbud
D=/home/ubuntu/cambc-autumn/replays/fuel/fuelbud/bench; mkdir -p $D
b=$1 t=$2; shift 2; modes=${*:-def wide pool}
OPP=${OPP:-variants/oc-retest-clean}
# build both first: parallel bench.py runs race on a fresh build dir
for x in $b $OPP; do (cd bots/$x && cambc build . > /dev/null 2>&1) || { echo build failed: $x; exit 1; }; done
POOL=$(ls -d maps/suites/fresh/fresh-519039/*.map26a | head -64)
for m in $modes; do case $m in
 def) python3 tools/fuel/bench.py run $b --opp $OPP --jobs 16 --out $D/$t-def-100M.json --games $D/g-$t-def-100M > $D/$t-def-100M.log 2>&1 & ;;
 wide) python3 tools/fuel/bench.py run $b --opp $OPP --set wide --per-map --jobs 52 --out $D/$t-wide-100M.json --games $D/g-$t-wide-100M > $D/$t-wide-100M.log 2>&1 & ;;
 pool) python3 tools/fuel/bench.py run $b --opp $OPP --maps $POOL --per-map --jobs 64 --out $D/$t-pool-100M.json --games $D/g-$t-pool-100M > $D/$t-pool-100M.log 2>&1 & ;;
 poolreal) python3 tools/fuel/bench.py run $b --opp $OPP --fuel 0 --maps $POOL --per-map --jobs 64 --out $D/$t-pool-real.json --games $D/g-$t-pool-real > $D/$t-pool-real.log 2>&1 & ;;
 real) python3 tools/fuel/bench.py run $b --opp $OPP --fuel 0 --set wide --per-map --jobs 52 --out $D/$t-wide-real.json --games $D/g-$t-wide-real > $D/$t-wide-real.log 2>&1 & ;;
esac; done
wait
if [ "${KEEP:-1}" = 0 ]; then rm -rf $D/g-$t-*; fi
