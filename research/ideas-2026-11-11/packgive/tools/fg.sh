#!/bin/bash
# fg.sh FIRST N VARIANT...: fresh-map reads at 200k fuel against oc-dfuel-506, pool batches FIRST..FIRST+N-1, one candidate after another.
source /home/ubuntu/venv/bin/activate; cd /home/ubuntu/cambc-autumn
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
P=/home/ubuntu/tmp-offload/packgive; F=$1; N=$2; shift 2
for v in "$@"; do
  python tools/fgate.py variants/pg-$v variants/oc-dfuel-506 --fuel 200000 --first-batch $F --max-batches $N --ci 0 > $P/logs/fgate-$v-b$F.log 2>&1
  echo "exit $?" >> $P/logs/fgate-$v-b$F.log
done
touch $P/logs/fg-b$F.done
