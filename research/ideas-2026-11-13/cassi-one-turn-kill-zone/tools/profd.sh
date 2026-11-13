#!/bin/bash
# prof.sh BOT OPP FUEL PART... : release runs of variants/BOT vs variants/OPP on pool-v4 batch 0 parts, all replays kept
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
export FASTRUNNER_LIB=/home/ubuntu/cambc-autumn/tools/fastengine/runner/target-rt/release/libfastrunner.so CAMBC_SLOTS=86 CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
B=$1; O=$2; F=$3; shift 3
S=~/tmp-offload/gatebatch/suites-v4/m2560
for P in "$@"; do
  python tools/ab.py variants/$B variants/$O --no-test-draft --suites $S/b000.parts/$P --name czkdbg-$B-$O-$P-$F --keep-replays 0 --debug --experiment-config $S/b000.json --fuel $F > ~/tmp-offload/cassizone/logs/dbg-$B-$O-$P-$F.log 2>&1 &
done
wait
touch ~/tmp-offload/cassizone/logs/dbg-$B-$O-$F.done
