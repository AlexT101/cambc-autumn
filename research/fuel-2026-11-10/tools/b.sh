#!/bin/bash
# b.sh BOT TAG MODE: MODE id (100M, own drafts), td (100M, test drafts), real (real budget, maps-trc), realid (real budget, maps-id)
cd /home/ubuntu/cambc-autumn; source /home/ubuntu/venv/bin/activate
export CAMBC_SLOTS=86 CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH
N=/home/ubuntu/tmp-offload/fuelC; b=$1; t=$2; mode=$3
case $mode in
  id) ml=$N/maps-id.txt; extra="";;
  td) ml=$N/maps-id.txt; extra="--test-draft";;
  real) ml=$N/maps-trc.txt; extra="--fuel 0";;
  chk) ml=$N/maps-chk.txt; extra="--fuel 0";;
  wt) ml=$N/maps-wt.txt; extra="";;
  div) ml=$N/maps-div.txt; extra="";;
  p1) ml=$N/maps-p1.txt; extra="--fuel 0";;
  realid) ml=$N/maps-id.txt; extra="--fuel 0";;
esac
rm -rf $N/g-$t-$mode $N/$t-$mode.done
python3 tools/fuel/bench.py run $b --opp ${OPP:-variants/ocf-base} --maps $(cat $ml) --jobs ${JOBS:-86} $extra --games $N/g-$t-$mode --out $N/$t-$mode.json > $N/$t-$mode.log 2>&1
echo $? > $N/$t-$mode.done
