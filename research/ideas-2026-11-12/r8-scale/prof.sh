#!/bin/bash
# prof.sh ARM [BATCH] [PARTS] [BODY]: bots/variants/ARM against the fr8-g25 body on parts of a v4 pool batch
# (default b000 p0-p1, 1,280 games) with every replay kept, extracted into ~/tmp-offload/r8-scale/prof/ARM-BODY,
# then prismprof.py's table. A profile, not a gate.
R=/home/ubuntu/wt/r8-scale; cd $R; source /home/ubuntu/venv/bin/activate
export FASTRUNNER_LIB=/home/ubuntu/cambc-autumn/tools/fastengine/runner/target-rt/release/libfastrunner.so
export CAMBC_SLOTS=86 CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH
ARM=$1; B=${2:-b000}; PARTS=${3:-p0,p1}; BODY=${4:-fr8-g25}
S=/home/ubuntu/tmp-offload/gatebatch/suites-v4/m2560; OUT=/home/ubuntu/tmp-offload/r8-scale/prof/$ARM-$BODY; mkdir -p $OUT
SU=$(echo $PARTS | tr ',' '\n' | sed "s|^|$S/$B.parts/|" | paste -sd,)
N=prof-$ARM-$BODY-$B
rm -rf replays/ab/$N
python3 tools/ab.py variants/$ARM variants/$BODY --no-test-draft --suites $SU --name $N --keep-replays 0 --experiment-config $S/$B.json --game-timeout 600 > $OUT/ab.log 2>&1
DIRS=$(grep -o 'replays/batch-[^` ]*' replays/ab/$N/summary.md | sort -u)
python3 tools/pooled.py 40 -- node tools/replay/extract.mjs $DIRS --out $OUT/extract --threads 40 > $OUT/extract.log 2>&1
python3 research/ideas-2026-11-12/r8-scale/prismprof.py $OUT/extract --team $ARM > $OUT/prof.txt 2>&1
rm -rf $DIRS
cat $OUT/prof.txt
