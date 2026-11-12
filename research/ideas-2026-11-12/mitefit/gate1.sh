#!/bin/bash
# gate1.sh CAND [REF=variants/c520-ps] [BATCHES=2]: after tune1, CAND against REF on fresh maps (fgate, fixed read of
# BATCHES batches from pool batch 30, which early gates have not played) against the Fish body with each Mite body:
# mf-c2 (current Mite, retreat rule), mf-c1, and the old Mt3q; plus a head-to-head ab.py on a fresh tune-unseen suite.
R=/home/ubuntu/cambc-autumn; M=/home/ubuntu/tmp-offload/mitefit; cd $R; source /home/ubuntu/venv/bin/activate
C=$1; REF=${2:-variants/c520-ps}; NB=${3:-2}; T=$(basename $C)
export CAMBC_BIN=$R/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
for MB in mf-c2 mf-c1 Mt3q; do
  python3 tools/fgate.py $C $REF --mite-body $MB --first-batch 30 --max-batches $NB --ci 0 --jobs 4 > $M/logs/gate-$T-$MB.log 2>&1
done
[ -d $M/h2h ] || python3 tools/pooled.py 1 -- node tools/mapgen/mapgen.mjs suite --mix ladder-v2 --seed 7931000 --jobs 1 --out $M/h2h > /dev/null 2>&1
python3 tools/ab.py $C $REF --no-test-draft --suites $M/h2h --name mf-h2h-$T --keep-replays 1 > $M/logs/h2h-$T.log 2>&1
touch $M/logs/gate-$T.done
