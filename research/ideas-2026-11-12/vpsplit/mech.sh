#!/bin/bash
# mech.sh BOT...: each BOT against the mf-c2 body on the ladder maps, noise members 1-4, 200k fuel, then extracted.
R=/home/ubuntu/cambc-autumn; M=/home/ubuntu/tmp-offload/mitefit; O=/home/ubuntu/tmp-offload/vpsplit; cd $R; source /home/ubuntu/venv/bin/activate
export CAMBC_SLOTS=86 CAMBC_BIN=$R/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native FGATE_RUNNER_LIB=$R/tools/fastengine/runner/target-rt/release/libfastrunner.so
export FASTRUNNER_LIB=$FGATE_RUNNER_LIB
for C in "$@"; do
  for k in 1 2 3 4; do
    python3 tools/ab.py variants/$C variants/mf-c2 --no-test-draft --fuel 200000 --name vpmech-$C-k$k --keep-replays 0 --experiment-config $M/cfg/ladder-k$k.json --game-timeout 600 > $O/logs/mech-$C-k$k.log 2>&1 &
  done
  wait
  python3 tools/pooled.py 12 -- node tools/replay/extract.mjs $(ls -d replays/batch-*-ab-vpmech-$C-k*) --out $O/ext/$C --threads 12 > $O/logs/ext-$C.log 2>&1
  touch $O/mech-$C.done
done
