#!/bin/bash
# mechvc.sh: vc-c520 (mitefit's rule 1) against mf-c2, as mech.sh; after mech.sh.
R=/home/ubuntu/cambc-autumn; M=/home/ubuntu/tmp-offload/mitefit; cd $R; source /home/ubuntu/venv/bin/activate
export CAMBC_SLOTS=86 CAMBC_BIN=$R/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native FGATE_RUNNER_LIB=$R/tools/fastengine/runner/target-rt/release/libfastrunner.so
export FASTRUNNER_LIB=$FGATE_RUNNER_LIB
until [ -f ~/tmp-offload/vg/mech2.done ]; do sleep 10; done
for k in 1 2; do
  python3 tools/ab.py variants/vc-c520 variants/mf-c2 --no-test-draft --fuel 200000 --name vgmech-vc-c520-k$k --keep-replays 0 --experiment-config $M/cfg/ladder-k$k.json --game-timeout 600 > ~/tmp-offload/vg/logs/mech-vc-c520-k$k.log 2>&1
done
python3 tools/pooled.py 12 -- node tools/replay/extract.mjs $(ls -d replays/batch-*-ab-vgmech-vc-c520-k*) --out ~/tmp-offload/vg/ext/vc-c520 --threads 12 > ~/tmp-offload/vg/logs/ext-vc-c520.log 2>&1
touch ~/tmp-offload/vg/mechvc.done
