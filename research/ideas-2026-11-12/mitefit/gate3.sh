#!/bin/bash
# gate3.sh CAND [REF=variants/c520-ps] [BATCHES=2]: CAND against REF on a fresh pool (fgate --pool $POOL, default v4, from
# batch 0) against the Fish body with the Mite bodies mf-c2 (current Mite) and Mt3q (old); plus a head-to-head ab.py
# on a fresh ladder-v3 suite (seed 7933000) no tune has seen.
R=/home/ubuntu/cambc-autumn; M=/home/ubuntu/tmp-offload/mitefit; cd $R; source /home/ubuntu/venv/bin/activate
C=$1; REF=${2:-variants/c520-ps}; NB=${3:-2}; T=$(basename $C)
export CAMBC_BIN=$R/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
for MB in mf-c2 Mt3q; do
  python3 tools/fgate.py $C $REF --pool ${POOL:-v4} --mite-body $MB --max-batches $NB --ci 0 --jobs 4 > $M/logs/gate3-$T-$MB.log 2>&1
done
[ -d $M/h2h-v3 ] || python3 tools/pooled.py 1 -- node tools/mapgen/mapgen.mjs suite --mix ladder-v3 --seed 7933000 --jobs 1 --out $M/h2h-v3 > /dev/null 2>&1
python3 tools/ab.py $C $REF --no-test-draft --suites $M/h2h-v3 --name mf-h2h3-$T --keep-replays 1 > $M/logs/h2h3-$T.log 2>&1
touch $M/logs/gate3-$T.done
