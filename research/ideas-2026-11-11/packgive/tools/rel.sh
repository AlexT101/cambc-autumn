#!/bin/bash
# rel.sh TAG...: release builds against the static Fish and Mite bodies on maps/gen and maps/gen-s1 (514 maps, both sides);
# replays decoded into ext2-TAG. A second, larger sample for the mechanism rates.
source /home/ubuntu/venv/bin/activate; cd /home/ubuntu/cambc-autumn
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
P=/home/ubuntu/tmp-offload/packgive; L=$P/logs
for T in "$@"; do
  B=pg-$T; [ $T = base ] && B=oc-dfuel-506
  for O in F:spar-dvn1-Flp4 M:spar-dvn1-Mt3q; do
    K=${O%%:*}; OB=${O#*:}
    python tools/ab.py variants/$B variants/$OB --no-test-draft --suites gen,maps/gen-s1 --keep-replays 0 --name pgr-$T-$K > $L/pgr-$T-$K.log 2>&1
  done
  DIRS=$(ls -d replays/batch-*-ab-pgr-$T-[FM]-* 2>/dev/null)
  node tools/replay/extract.mjs $DIRS --out $P/ext2-$T --threads 12 > $L/extract2-$T.log 2>&1
  for d in $DIRS; do find $d -name "*.repl26a" -delete; done
  touch $L/rel-$T.done
done
touch $L/rel.done
