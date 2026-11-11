#!/bin/bash
# Mechanism read: BOT against rt-Mt3q and rt-Flp4 on the badmaps suite (wheel x24 seeds, 13 maps x8), 200k, all replays, then extract.
# usage: mech.sh BOT [FUEL]
source $HOME/venv/bin/activate
cd /home/ubuntu/cambc-autumn
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
export FASTRUNNER_LIB=$PWD/tools/fastengine/runner/target-rt/release/libfastrunner.so
B=$1; F=${2:-200000}; T=$(basename $B)
G=~/tmp-offload/gemprice; L=$G/logs; rm -f $L/mech-$T-f$F.done
for O in Mt3q Flp4; do
  N=gp-mech-$T-$O-f$F
  python3 tools/ab.py variants/$T variants/rt-$O --no-test-draft --suites replays/gemprice/mech/maps --name $N --fuel $F \
    --keep-replays 0 --experiment-config replays/gemprice/mech/cfg.json --game-timeout 600 > $L/$N.log 2>&1
done
node tools/replay/extract.mjs replays/batch-*-ab-gp-mech-$T-Mt3q-f$F-* replays/batch-*-ab-gp-mech-$T-Flp4-f$F-* --threads 16 --out $G/ext/$T-f$F > $L/ext-$T-f$F.log 2>&1
touch $L/mech-$T-f$F.done
