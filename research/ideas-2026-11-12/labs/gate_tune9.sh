#!/bin/bash
# gate_tune9.sh PHASE: the coordinator's gate of lab-tune9-lab-emb6-c520-ps against lab-emb6-c520-ps (2026-11-12), on
# the ladder-v4 pool's unplayed batches 16-33 (grown by 2500128-2500257; draft19's gate played 4-7).
#   s200: 200k screen from v4 batch 16, --screen, at most 8 batches (16-23); then a fixed 2-batch mf-c2 read on 16-17.
#   g100 N: 100k gate from v4 batch N (maps the screen did not play) and a fixed 2-batch mf-c2 read there.
#   fbody BODY FUEL N: a fixed 2-batch read against Fish body BODY (the r8 body, when it exists) from batch N at FUEL.
# Logs in ~/tmp-offload/labs/gate-tune9/; each phase ends with a done-file.
R=/home/ubuntu/cambc-autumn; G=/home/ubuntu/tmp-offload/labs/gate-tune9; mkdir -p $G; cd $R; source /home/ubuntu/venv/bin/activate
export CAMBC_SLOTS=86 CAMBC_BIN=$R/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
C=variants/lab-tune9-lab-emb6-c520-ps; REF=variants/lab-emb6-c520-ps
case $1 in
s200)
  python3 tools/fgate.py $C $REF --pool v4 --fuel 200000 --first-batch 16 --max-batches 8 --screen --jobs 4 > $G/s200.log 2>&1
  python3 tools/fgate.py $C $REF --pool v4 --fuel 200000 --first-batch 16 --max-batches 2 --ci 0 --mite-body mf-c2 --jobs 4 > $G/s200-mfc2.log 2>&1
  touch $G/s200.done ;;
g100)
  F=$2
  python3 tools/fgate.py $C $REF --pool v4 --first-batch $F --jobs 4 > $G/g100.log 2>&1
  python3 tools/fgate.py $C $REF --pool v4 --first-batch $F --max-batches 2 --ci 0 --mite-body mf-c2 --jobs 4 > $G/g100-mfc2.log 2>&1
  touch $G/g100.done ;;
fbody)
  B=$2; FU=$3; F=$4
  python3 tools/fgate.py $C $REF --pool v4 --fuel $FU --first-batch $F --max-batches 2 --ci 0 --fish-body $B --jobs 4 > $G/fbody-$B-$FU.log 2>&1
  touch $G/fbody-$B-$FU.done ;;
esac
