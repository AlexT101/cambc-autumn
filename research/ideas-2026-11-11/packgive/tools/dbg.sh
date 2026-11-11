#!/bin/bash
# dbg.sh BOT TAG: BOT (under bots/variants) against the static Fish and Mite bodies on the 128 ladder maps, both
# sides, debug builds; replays decoded into ~/tmp-offload/packgive/ext-TAG, decision lines into dlines-TAG.jsonl.gz.
source /home/ubuntu/venv/bin/activate; cd /home/ubuntu/cambc-autumn
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
P=/home/ubuntu/tmp-offload/packgive; L=$P/logs; B=$1; T=$2
for O in F:spar-dvn1-Flp4 M:spar-dvn1-Mt3q; do
  K=${O%%:*}; OB=${O#*:}
  python tools/ab.py variants/$B variants/$OB --no-test-draft --suites ladder --debug --keep-replays 0 --name pgd-$T-$K > $L/pgd-$T-$K.log 2>&1
  echo "exit $?" >> $L/pgd-$T-$K.log
done
DIRS=$(ls -d replays/batch-*-ab-pgd-$T-[FM]-* 2>/dev/null)
node tools/replay/extract.mjs $DIRS --out $P/ext-$T --threads 6 > $L/extract-$T.log 2>&1
python3 $P/bin/dlines.py $P/dlines-$T.jsonl.gz $DIRS >> $L/extract-$T.log 2>&1
for d in $DIRS; do find $d -name "*.repl26a" -delete; done
touch $L/dbg-$T.done
