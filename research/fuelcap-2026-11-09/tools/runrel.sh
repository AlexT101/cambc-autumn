#!/bin/bash
# runrel.sh BOT TAG MAPLIST: release-build bench vs oc-base25 (both sides) at the real budget.
cd /home/ubuntu/cambc-autumn; source /home/ubuntu/venv/bin/activate
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
N=/home/ubuntu/tmp-offload/nooof; b=$1; t=$2; ml=$3
rm -rf $N/g-$t $N/$t.done
python3 $N/tools/benchrel.py run $b --fuel 0 --opp variants/oc-base25 --maps $(cat $ml) --jobs ${JOBS:-60} --games $N/g-$t --out $N/$t.json > $N/$t.log 2>&1
echo $? > $N/$t.done
