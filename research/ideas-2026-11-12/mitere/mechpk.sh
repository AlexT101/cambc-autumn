#!/bin/bash
# mechpk.sh: c520-pk (rule 2) against mf-c2 members 1-4 and c520-ps members 3-4 (1-2 already played), 200k, all replays; extract.
R=/home/ubuntu/cambc-autumn; M=/home/ubuntu/tmp-offload/mitefit; cd $R; source /home/ubuntu/venv/bin/activate
export CAMBC_SLOTS=86 CAMBC_BIN=$R/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native FGATE_RUNNER_LIB=$R/tools/fastengine/runner/target-rt/release/libfastrunner.so
export FASTRUNNER_LIB=$FGATE_RUNNER_LIB
run() { python3 tools/ab.py variants/$1 variants/mf-c2 --no-test-draft --fuel 200000 --name vgmech-$1-k$2 --keep-replays 0 --experiment-config $M/cfg/ladder-k$2.json --game-timeout 600 > ~/tmp-offload/vg/logs/mech-$1-k$2.log 2>&1; }
for k in 1 2 3 4; do run c520-pk $k; done
for k in 3 4; do run c520-ps $k; done
for C in c520-pk c520-ps; do
  python3 tools/pooled.py 12 -- node tools/replay/extract.mjs $(ls -d replays/batch-*-ab-vgmech-$C-k*) --out ~/tmp-offload/vg/ext/$C --threads 12 > ~/tmp-offload/vg/logs/ext-$C.log 2>&1
done
touch ~/tmp-offload/vg/mechpk.done
