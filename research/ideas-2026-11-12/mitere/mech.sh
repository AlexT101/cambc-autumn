#!/bin/bash
# mech.sh: c520-vg and c520-ps against the mf-c2 body on the ladder maps, noise members 1-2, 200k fuel, all replays kept.
R=/home/ubuntu/cambc-autumn; M=/home/ubuntu/tmp-offload/mitefit; cd $R; source /home/ubuntu/venv/bin/activate
export CAMBC_SLOTS=86 CAMBC_BIN=$R/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native FGATE_RUNNER_LIB=$R/tools/fastengine/runner/target-rt/release/libfastrunner.so
export FASTRUNNER_LIB=$FGATE_RUNNER_LIB
for k in 1 2; do for C in c520-vg c520-ps; do
  python3 tools/ab.py variants/$C variants/mf-c2 --no-test-draft --fuel 200000 --name vgmech-$C-k$k --keep-replays 0 --experiment-config $M/cfg/ladder-k$k.json --game-timeout 600 > ~/tmp-offload/vg/logs/mech-$C-k$k.log 2>&1
done; done
for C in c520-vg c520-ps; do
  python3 tools/pooled.py 12 -- node tools/replay/extract.mjs $(ls -d replays/batch-*-ab-vgmech-$C-k*) --out ~/tmp-offload/vg/ext/$C --threads 12 > ~/tmp-offload/vg/logs/ext-$C.log 2>&1
done
touch ~/tmp-offload/vg/mech2.done
