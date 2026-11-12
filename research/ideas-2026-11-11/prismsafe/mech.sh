#!/bin/bash
# Mechanism run with replays: BOT (dir under bots/) against both rt bodies on fgate b000 parts p0,p1 (640 maps), 200k fuel; then extract.
BOT=$1; TAG=$2
cd /home/ubuntu/cambc-autumn
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native CAMBC_SLOTS=86 FASTRUNNER_LIB=$PWD/tools/fastengine/runner/target-rt/release/libfastrunner.so
S=/home/ubuntu/tmp-offload/gatebatch/suites/m2560
O=/home/ubuntu/tmp-offload/prismsafe; L=$O/logs
for B in Flp4 Mt3q; do
  N=ps-mech-$TAG-$B
  python3 tools/ab.py $BOT variants/rt-$B --no-test-draft --suites $S/b000.parts/p0,$S/b000.parts/p1 --name $N --fuel 200000 \
    --keep-replays 0 --experiment-config $S/b000.json --game-timeout 900 > $L/$N.log 2>&1 &
done
wait
node tools/replay/extract.mjs replays/batch-*-ab-ps-mech-$TAG-Flp4-* replays/batch-*-ab-ps-mech-$TAG-Mt3q-* --threads 12 --out $O/ext/$TAG > $L/ext-$TAG.log 2>&1
touch $L/mech-$TAG.done
