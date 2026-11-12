#!/bin/bash
# Mechanism run with replays: BOT (dir under bots/) against both rt bodies on fgate b000 parts PARTS (default p0,p1:
# 640 maps), at the real fuel budget; then extract to ~/tmp-offload/prismlife/ext/TAG. DEBUG=1 plays debug builds
# (decision lines in team stdout).
BOT=$1; TAG=$2; PARTS=${PARTS:-p0,p1}
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
export PATH=$HOME/.cargo/bin:$PATH
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native CAMBC_SLOTS=86 FASTRUNNER_LIB=$PWD/tools/fastengine/runner/target-rt/release/libfastrunner.so
S=/home/ubuntu/tmp-offload/gatebatch/suites/m2560
O=/home/ubuntu/tmp-offload/prismlife; L=$O/logs
SUITES=$(echo $PARTS | tr ',' '\n' | sed "s|^|$S/b000.parts/|" | paste -sd,)
for B in Flp4 Mt3q; do
  N=pl-mech-$TAG-$B
  python3 tools/ab.py $BOT variants/rt-$B --no-test-draft --suites $SUITES --name $N ${DEBUG:+--debug} ${FUEL:+--fuel $FUEL} \
    --keep-replays 0 --experiment-config $S/b000.json --game-timeout 900 > $L/$N.log 2>&1 &
done
wait
node tools/replay/extract.mjs replays/batch-*-ab-pl-mech-$TAG-Flp4-* replays/batch-*-ab-pl-mech-$TAG-Mt3q-* --threads 12 --out $O/ext/$TAG > $L/ext-$TAG.log 2>&1
touch $L/mech-$TAG.done
