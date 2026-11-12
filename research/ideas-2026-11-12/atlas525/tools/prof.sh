#!/bin/bash
# prof.sh BOT [PART] : debug 100k runs of variants/BOT vs fr8-g25 and mf-f9 on pool-v4 batch 0 part PART (default p6), all replays kept
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
export FASTRUNNER_LIB=/home/ubuntu/cambc-autumn/tools/fastengine/runner/target-rt/release/libfastrunner.so CAMBC_SLOTS=86 CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
B=$1; P=${2:-p6}
S=~/tmp-offload/gatebatch/suites-v4/m2560
for O in fr8-g25 mf-f9; do
  python tools/ab.py variants/$B variants/$O --no-test-draft --suites $S/b000.parts/$P --name atlprof-$B-$O-$P --debug --keep-replays 0 --experiment-config $S/b000.json --fuel 100000 > ~/tmp-offload/atl/prof-$B-$O-$P.log 2>&1 &
done
wait
touch ~/tmp-offload/atl/prof-$B-$P.done
