#!/bin/bash
# b.sh KIND BOT NAME [extra]: KIND id (100M, maps-id) | screen (real, maps-screen) | dev | final | cov (100M coverage)
set -e
cd /home/ubuntu/wt/ocean-fuel6
source ~/venv/bin/activate
export CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native CAMBC_SLOTS=86 PATH=$HOME/.cargo/bin:$PATH
K=$1; BOT=$2; N=$3; shift 3
T=research/fuel-2026-11-10-sixth/tools
OUT=/home/ubuntu/tmp-offload/f6
mkdir -p $OUT
OPP=${OPP:-variants/oc-f6-base}
case $K in
  id) py tools/fuel/bench.py run $BOT --opp $OPP --maps $(cat $T/maps-id.txt) --jobs 86 --games $OUT/games/$N --out $OUT/$N.json "$@" ;;
  cov) py tools/fuel/bench.py run $BOT --opp $OPP --maps $(cat $T/maps-coverage.txt) --jobs 86 --games $OUT/games/$N --out $OUT/$N.json "$@" ;;
  screen|dev|final) py tools/fuel/bench.py run $BOT --opp $OPP --maps $(cat $T/maps-$K.txt) --fuel 0 --jobs 86 --games $OUT/games/$N --out $OUT/$N.json "$@" ;;
esac
