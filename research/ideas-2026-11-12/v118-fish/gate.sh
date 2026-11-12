#!/bin/bash
# gate.sh ARM [WAIT_FOR_DONE_FILE]: ARM (bots/variants/ARM, a copy of variants/lab-emb6-c520-ps = v118 without the live
# mask) against variants/lab-emb6-c520-ps at the real budget (100k), two fixed reads of two fgate batches each
# (2,560 fresh ladder-v3 maps + the 128 ladder maps a batch, both sides):
#   std: the standard bodies (rt-Flp4, rt-Mt3q) on pool v3 batches 16-17, where REF's half is cached from emb6's gate;
#   fr8: the Fish r8 body (fr8-g25) in Flp4's place, same maps.
# Logs and done-files in ~/tmp-offload/v118-fish/gates/.
R=/home/ubuntu/cambc-autumn; G=/home/ubuntu/tmp-offload/v118-fish/gates; mkdir -p $G; cd $R; source /home/ubuntu/venv/bin/activate
export CAMBC_SLOTS=86 CAMBC_BIN=$R/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH
ARM=$1; REF=variants/lab-emb6-c520-ps
python3 tools/fgate.py variants/$ARM $REF --pool v3 --first-batch 16 --max-batches 2 --ci 0 --jobs 4 > $G/$ARM-std.log 2>&1
touch $G/$ARM-std.done
if [ -n "$2" ]; then until [ -f "$2" ]; do sleep 20; done; fi
python3 tools/fgate.py variants/$ARM $REF --pool v3 --first-batch 16 --max-batches 2 --ci 0 --fish-body fr8-g25 --jobs 4 > $G/$ARM-fr8.log 2>&1
touch $G/$ARM-fr8.done
