#!/bin/bash
# Debug-build runs (D traces) of BOT on the heavy suite vs both bodies, 200k.
source $HOME/venv/bin/activate
cd /home/ubuntu/cambc-autumn
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
export FASTRUNNER_LIB=$PWD/tools/fastengine/runner/target-rt/release/libfastrunner.so
B=$1; T=$(basename $B); C=~/tmp-offload/campkill; L=$C/logs
for O in Mt3q Flp4; do
  N=ck-hvd-$T-$O
  python3 tools/ab.py variants/$T variants/rt-$O --no-test-draft --suites replays/campkill/hv/maps --name $N --fuel 200000 --debug \
    --keep-replays 0 --experiment-config replays/campkill/hv/cfg.json --game-timeout 900 > $L/$N.log 2>&1 &
done
wait
node tools/replay/extract.mjs replays/batch-*-ab-ck-hvd-$T-Mt3q-* replays/batch-*-ab-ck-hvd-$T-Flp4-* --threads 16 --out $C/ext/hvd-$T > $L/ext-hvd-$T.log 2>&1
touch $L/dbg-$T.done
