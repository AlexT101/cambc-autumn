#!/bin/bash
# mechmv.sh: c520-mvf (Mite Vesper's hits counted twice in safety, forced on) from v116 live forks and against
# mf-c2 members 1-4 at 200k (base c520-ps's games already in ~/tmp-offload/vg/ext/c520-ps); extract.
R=/home/ubuntu/cambc-autumn; M=/home/ubuntu/tmp-offload/mitefit; cd $R; source /home/ubuntu/venv/bin/activate
export CAMBC_SLOTS=86 CAMBC_BIN=$R/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native FGATE_RUNNER_LIB=$R/tools/fastengine/runner/target-rt/release/libfastrunner.so
export FASTRUNNER_LIB=$FGATE_RUNNER_LIB
python3 research/ideas-2026-11-12/mitere/fork_arms.py ~/tmp-offload/vg/fork/mvf variants/c520-ps variants/c520-mvf > ~/tmp-offload/vg/logs/fork-mvf.log 2>&1
run() { python3 tools/ab.py variants/$1 variants/mf-c2 --no-test-draft --fuel 200000 --name vgmech-$1-k$2 --keep-replays 0 --experiment-config $M/cfg/ladder-k$2.json --game-timeout 600 > ~/tmp-offload/vg/logs/mech-$1-k$2.log 2>&1; }
for k in 1 2 3 4; do run c520-mvf $k; done
python3 tools/pooled.py 12 -- node tools/replay/extract.mjs $(ls -d replays/batch-*-ab-vgmech-c520-mvf-k*) --out ~/tmp-offload/vg/ext/c520-mvf --threads 12 > ~/tmp-offload/vg/logs/ext-c520-mvf.log 2>&1
touch ~/tmp-offload/vg/mechmv.done
