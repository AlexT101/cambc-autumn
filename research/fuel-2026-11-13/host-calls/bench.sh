#!/bin/bash
# bench.sh BOT TAG MODE: id (100M, wide, own drafts), idv (100M, 48 v4 maps), td (100M, wide, test drafts), real (100k, 48 v4 maps)
# -> ~/tmp-offload/fuhost/b/TAG-MODE.{json,log,done}, games in g-TAG-MODE. OPP defaults to variants/chy-525 (as research/fuel-2026-11-13/tools/bench.sh).
cd /home/ubuntu/cambc-autumn; source /home/ubuntu/venv/bin/activate
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
N=/home/ubuntu/tmp-offload/fuhost; M=research/fuel-2026-11-13/tools/maps-id48.txt; b=$1; t=$2; mode=$3
case $mode in
  id) maps="--set wide"; extra="";;
  idv) maps="--maps $(cat $M)"; extra="";;
  td) maps="--set wide"; extra="--test-draft";;
  real) maps="--maps $(cat $M)"; extra="--fuel 0";;
esac
rm -rf $N/b/g-$t-$mode $N/b/$t-$mode.done; mkdir -p $N/b
python3 tools/fuel/bench.py run variants/$b --opp ${OPP:-variants/chy-525} $maps --per-map --jobs ${JOBS:-24} $extra --games $N/b/g-$t-$mode --out $N/b/$t-$mode.json > $N/b/$t-$mode.log 2>&1
echo $? > $N/b/$t-$mode.done
