#!/bin/bash
# Mechanism read: BOT against rt-Mt3q and rt-Flp4 on SUITE (dir with maps/ and cfg.json), all replays, then extract.
# usage: mech.sh BOT SUITE TAG [FUEL]
source $HOME/venv/bin/activate
cd /home/ubuntu/cambc-autumn
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
export FASTRUNNER_LIB=$PWD/tools/fastengine/runner/target-rt/release/libfastrunner.so
B=$1; S=$2; TAG=$3; F=${4:-200000}; T=$(basename $B)
C=~/tmp-offload/campkill; L=$C/logs; rm -f $L/mech-$T-$TAG-f$F.done
for O in Mt3q Flp4; do
  N=ck-$TAG-$T-$O-f$F
  python3 tools/ab.py variants/$T variants/rt-$O --no-test-draft --suites $S/maps --name $N --fuel $F \
    --keep-replays 0 --experiment-config $S/cfg.json --game-timeout 600 > $L/$N.log 2>&1
done
node tools/replay/extract.mjs replays/batch-*-ab-ck-$TAG-$T-Mt3q-f$F-* replays/batch-*-ab-ck-$TAG-$T-Flp4-f$F-* --threads 16 --out $C/ext/$TAG-$T-f$F > $L/ext-$T-$TAG-f$F.log 2>&1
touch $L/mech-$T-$TAG-f$F.done
