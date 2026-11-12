#!/bin/bash
# subset.sh BOT...: each BOT against fr8-g25 and mf-c2 on parts p0-p1 of fgate pool-v4 batch 0 (640 maps, both sides), 200k, replays kept and extracted.
R=/home/ubuntu/cambc-autumn; O=/home/ubuntu/tmp-offload/vpsplit; G=/home/ubuntu/tmp-offload/gatebatch/suites-v4/m2560; cd $R; source /home/ubuntu/venv/bin/activate
export CAMBC_SLOTS=86 CAMBC_BIN=$R/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native FASTRUNNER_LIB=$R/tools/fastengine/runner/target-rt/release/libfastrunner.so
for C in "$@"; do
  for B in fr8-g25 mf-c2; do
    python3 tools/ab.py variants/$C variants/$B --no-test-draft --fuel 200000 --suites $G/b000.parts/p0,$G/b000.parts/p1 --name vpsub-$C-$B --keep-replays 0 --experiment-config $G/b000.json --game-timeout 600 > $O/logs/sub-$C-$B.log 2>&1
  done
  python3 tools/pooled.py 16 -- node tools/replay/extract.mjs $(ls -d replays/batch-*-ab-vpsub-$C-*) --out $O/sub/$C --threads 16 > $O/logs/subext-$C.log 2>&1
  touch $O/sub-$C.done
done
