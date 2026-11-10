#!/bin/bash
# id.sh BOT TAG [MAPLIST]: bench at 100M vs ocean-16d6f78 (both sides), done-file at the end.
cd /home/ubuntu/cambc-autumn; source /home/ubuntu/venv/bin/activate
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
N=/home/ubuntu/tmp-offload/fuelB; b=$1; t=$2; ml=${3:-/home/ubuntu/tmp-offload/nooof/maps-id.txt}
rm -rf $N/g-$t $N/$t.done
python3 tools/fuel/bench.py run $b --opp variants/ocean-16d6f78 --maps $(cat $ml) --jobs ${JOBS:-64} --games $N/g-$t --out $N/$t.json > $N/$t.log 2>&1
echo $? > $N/$t.done
