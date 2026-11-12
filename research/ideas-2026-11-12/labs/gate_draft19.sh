#!/bin/bash
# gate_draft19.sh PHASE: the coordinator's gate of lab-draft19-lab-emb6-c520-ps against lab-emb6-c520-ps (2026-11-12),
# on the ladder-v4 pool (v4 batches 0-3 played by earlier gates).
#   s200: 200k screen from v4 batch 4, --screen, at most 8 batches (4-11); then a fixed 2-batch mf-c2 read on 4-5.
#   growv4: 130 --mix ladder-v4 suites (seeds 2500128-2500257, in the block reserved for the v4 pool) appended to it.
#   g100 N: 100k gate from v4 batch N (maps the screen did not play) and a fixed 2-batch mf-c2 read there.
# The draft is new, so gate_draft19_watch.py stops the gate on any draft failure (see there).
# Logs in ~/tmp-offload/labs/gate-draft19/; each phase ends with a done-file.
R=/home/ubuntu/cambc-autumn; G=/home/ubuntu/tmp-offload/labs/gate-draft19; mkdir -p $G; cd $R; source /home/ubuntu/venv/bin/activate
export CAMBC_SLOTS=86 CAMBC_BIN=$R/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
C=variants/lab-draft19-lab-emb6-c520-ps; REF=variants/lab-emb6-c520-ps
case $1 in
s200)
  python3 tools/fgate.py $C $REF --pool v4 --fuel 200000 --first-batch 4 --max-batches 8 --screen --jobs 4 > $G/s200.log 2>&1
  python3 tools/fgate.py $C $REF --pool v4 --fuel 200000 --first-batch 4 --max-batches 2 --ci 0 --mite-body mf-c2 --jobs 4 > $G/s200-mfc2.log 2>&1
  touch $G/s200.done ;;
growv4)
  GEN=/home/ubuntu/tmp-offload/gatebatch/generated-v4
  seq 2500128 2500257 | xargs -P 6 -I{} sh -c "[ -f $GEN/{}/.done ] || { python3 tools/pooled.py 1 -- node tools/mapgen/mapgen.mjs suite --mix ladder-v4 --seed {} --jobs 1 --out $GEN/{} > /dev/null 2>&1 && touch $GEN/{}/.done; }"
  DIRS=$(for s in $(seq 2500128 2500257); do echo $GEN/$s; done)
  [ $(for d in $DIRS; do [ -f $d/.done ] && echo; done | wc -l) -eq 130 ] || { echo "mapgen incomplete" > $G/growv4.fail; exit 1; }
  python3 tools/pooled.py 4 -- python3 tools/fgate_batch.py grow 2500128-2500257 $DIRS --pool v4 > $G/growv4.log 2>&1 || { echo grow > $G/growv4.fail; exit 1; }
  touch $G/growv4.done ;;
g100)
  F=$2
  python3 tools/fgate.py $C $REF --pool v4 --first-batch $F --jobs 4 > $G/g100.log 2>&1
  python3 tools/fgate.py $C $REF --pool v4 --first-batch $F --max-batches 2 --ci 0 --mite-body mf-c2 --jobs 4 > $G/g100-mfc2.log 2>&1
  touch $G/g100.done ;;
esac
