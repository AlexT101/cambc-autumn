#!/bin/bash
# body.sh X...: oc-dfuel-506 against each static body variants/spar-dvn1-X, release builds, on the 128 ladder maps and
# on maps/gen + maps/gen-s1 (both sides); replays decoded into ~/tmp-offload/fishfight/ext-X-{lad,gen}, engagement rows
# into rows-X-{lad,gen}.pkl.
source /home/ubuntu/venv/bin/activate; cd /home/ubuntu/cambc-autumn
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
P=/home/ubuntu/tmp-offload/fishfight; L=$P/logs; T=research/ideas-2026-11-11/fishfight/tools; O=research/ideas-2026-11-11/overruns/tools
for X in "$@"; do
  for S in lad:ladder gen:gen,maps/gen-s1; do
    K=${S%%:*}; SU=${S#*:}
    [ -f $P/rows-$X-$K.pkl ] && continue
    python tools/ab.py variants/oc-dfuel-506 variants/spar-dvn1-$X --no-test-draft --suites $SU --keep-replays 0 --name ff-$X-$K > $L/ab-$X-$K.log 2>&1
    echo "exit $?" >> $L/ab-$X-$K.log
    DIRS=$(ls -d replays/batch-*-ab-ff-$X-$K-* 2>/dev/null)
    node tools/replay/extract.mjs $DIRS --out $P/ext-$X-$K --threads 12 > $L/extract-$X-$K.log 2>&1
    for d in $DIRS; do find $d -name "*.repl26a" -delete; done
    (cd $P && python3 /home/ubuntu/cambc-autumn/$O/deaths_local.py $P/ext-$X-$K $P/games-$X-$K.pkl oc-dfuel-506 && python3 /home/ubuntu/cambc-autumn/$T/eng.py $P/games-$X-$K.pkl $P/rows-$X-$K.pkl) >> $L/extract-$X-$K.log 2>&1
  done
done
