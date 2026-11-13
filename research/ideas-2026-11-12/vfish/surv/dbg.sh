#!/bin/bash
# dbg.sh VARIANT: debug-build batch of VARIANT against 525 on the surv-dbg maps, replays kept, extracted to ~/tmp-offload/vfish/ext/survdbg-VARIANT
R=/home/ubuntu/cambc-autumn; cd $R; source /home/ubuntu/venv/bin/activate
export CAMBC_SLOTS=86 CAMBC_BIN=$R/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH
V=$1; T=$HOME/tmp-offload/vfish; N=sdbg-$V
python3 -u tools/ab.py variants/$V variants/chy-bagfocus-525 --no-test-draft --debug --suites $T/suites/surv-dbg --name $N --keep-replays 0 > $T/logs/$N.log 2>&1
B=$(ls -d replays/batch-*-ab-$N-surv-dbg | sort | tail -n 1); X=$T/ext/survdbg-$V
rm -rf $X
node tools/replay/extract.mjs $B --threads 12 --out $X > $T/logs/$N-ext.log 2>&1
echo $B > $X/BATCH
tail -n 5 $T/logs/$N.log
