#!/bin/bash
source /home/ubuntu/venv/bin/activate; cd /home/ubuntu/cambc-autumn
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
P=/home/ubuntu/tmp-offload/packgive
for v in "$@"; do
  b=variants/pg-$v; [ $v = base ] && b=variants/oc-dfuel-506
  for o in Flp4 Mt3q; do
    python tools/fuel/bench.py run $b --opp variants/spar-dvn1-$o --set wide --fuel 0 --out replays/fuel/pg-$v-$o.json > $P/logs/bench-$v-$o.log 2>&1
  done
done
for o in Flp4 Mt3q; do python tools/fuel/stats.py $(for v in "$@"; do echo replays/fuel/pg-$v-$o.json; done); done > $P/bench.txt 2>&1
find replays/fuel/games -maxdepth 1 -name "pg-*" -exec rm -rf {} + 2>/dev/null
touch $P/logs/bench.done
