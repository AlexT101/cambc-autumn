#!/bin/bash
# dprof.sh ARM [BATCH] [PARTS]: prof.sh with debug builds (the bot's D lines: round, handle, branch, farm group, claim),
# replays kept in place for their stdout; extract in ~/tmp-offload/r8-scale/prof/ARM-dbg. Debug games differ from release ones.
R=/home/ubuntu/wt/r8-scale; cd $R; source /home/ubuntu/venv/bin/activate
export FASTRUNNER_LIB=/home/ubuntu/cambc-autumn/tools/fastengine/runner/target-rt/release/libfastrunner.so
export CAMBC_SLOTS=86 CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH
ARM=$1; B=${2:-b000}; PARTS=${3:-p0,p1}; BODY=fr8-g25
S=/home/ubuntu/tmp-offload/gatebatch/suites-v4/m2560; OUT=/home/ubuntu/tmp-offload/r8-scale/prof/$ARM-dbg; mkdir -p $OUT
SU=$(echo $PARTS | tr ',' '\n' | sed "s|^|$S/$B.parts/|" | paste -sd,)
N=dprof-$ARM-$BODY-$B
rm -rf replays/ab/$N
python3 tools/ab.py variants/$ARM variants/$BODY --no-test-draft --debug --suites $SU --name $N --keep-replays 0 --experiment-config $S/$B.json --game-timeout 600 > $OUT/ab.log 2>&1
DIRS=$(grep -o 'replays/batch-[^` ]*' replays/ab/$N/summary.md | sort -u)
echo $DIRS > $OUT/dirs.txt
python3 tools/pooled.py 40 -- node tools/replay/extract.mjs $DIRS --out $OUT/extract --threads 40 > $OUT/extract.log 2>&1
tail -n 12 $OUT/ab.log
