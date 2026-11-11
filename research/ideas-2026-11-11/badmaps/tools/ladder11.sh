#!/bin/bash
cd /home/ubuntu/cambc-autumn
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
L=/home/ubuntu/tmp-offload/badmaps/logs11
for C in "$@"; do for B in Mt3q Flp4; do
  python3 tools/ab.py variants/$C variants/spar-dvn1-$B --no-test-draft --suites ladder --name bm11-lad-$C-$B --keep-replays 0 > $L/lad-$C-$B.log 2>&1
done; done
touch $L/lad-$1.done
