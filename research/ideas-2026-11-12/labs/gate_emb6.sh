#!/bin/bash
# gate_emb6.sh PHASE: the coordinator's gate of lab-emb6-c520-ps against c520-ps (2026-11-12), on the ladder-v3 pool
# (user decision 2026-11-12: new gates use --pool v3).
#   s200: 200k screen from v3 batch 8 (batches 0-3 played by earlier gates; 8-15 left to this screen), --screen, at
#         most 8 batches; then a fixed 2-batch read against the mf-c2 Mite body on batches 8-9.
#   growv3: 130 --mix ladder-v3 suites (seeds 2490500-2490629, in the block reserved for the v3 pool) appended to it.
#   g100 N: 100k gate from v3 batch N (maps the screen did not play) and a fixed 2-batch mf-c2 read there.
# (Its first version grew the v2 pool by seeds 2520000-2520259, batches 89+, before the switch; nothing played there.)
# Logs in ~/tmp-offload/labs/gate-emb6/; each phase ends with a done-file.
R=/home/ubuntu/cambc-autumn; G=/home/ubuntu/tmp-offload/labs/gate-emb6; mkdir -p $G; cd $R; source /home/ubuntu/venv/bin/activate
export CAMBC_SLOTS=86 CAMBC_BIN=$R/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
C=variants/lab-emb6-c520-ps; REF=variants/c520-ps
case $1 in
s200)
  python3 tools/fgate.py $C $REF --pool v3 --fuel 200000 --first-batch 8 --max-batches 8 --screen --jobs 4 > $G/s200.log 2>&1
  python3 tools/fgate.py $C $REF --pool v3 --fuel 200000 --first-batch 8 --max-batches 2 --ci 0 --mite-body mf-c2 --jobs 4 > $G/s200-mfc2.log 2>&1
  touch $G/s200.done ;;
growv3)
  GEN=/home/ubuntu/tmp-offload/gatebatch/generated-v3
  seq 2490500 2490629 | xargs -P 6 -I{} sh -c "[ -f $GEN/{}/.done ] || { python3 tools/pooled.py 1 -- node tools/mapgen/mapgen.mjs suite --mix ladder-v3 --seed {} --jobs 1 --out $GEN/{} > /dev/null 2>&1 && touch $GEN/{}/.done; }"
  DIRS=$(for s in $(seq 2490500 2490629); do echo $GEN/$s; done)
  [ $(for d in $DIRS; do [ -f $d/.done ] && echo; done | wc -l) -eq 130 ] || { echo "mapgen incomplete" > $G/growv3.fail; exit 1; }
  python3 tools/pooled.py 4 -- python3 tools/fgate_batch.py grow 2490500-2490629 $DIRS --pool v3 > $G/growv3.log 2>&1 || { echo grow > $G/growv3.fail; exit 1; }
  touch $G/growv3.done ;;
g100)
  F=$2
  python3 tools/fgate.py $C $REF --pool v3 --first-batch $F --jobs 4 > $G/g100.log 2>&1
  python3 tools/fgate.py $C $REF --pool v3 --first-batch $F --max-batches 2 --ci 0 --mite-body mf-c2 --jobs 4 > $G/g100-mfc2.log 2>&1
  touch $G/g100.done ;;
esac
