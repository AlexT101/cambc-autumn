#!/bin/bash
# gatemv.sh: c520-mvf (Mite Vesper's hits counted twice in safety, forced on) against c520-ps, fgate pool v4 at 200k
# with the mf-c2 Mite body, one batch.
R=/home/ubuntu/cambc-autumn; cd $R; source /home/ubuntu/venv/bin/activate
export CAMBC_SLOTS=86 CAMBC_BIN=$R/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
python3 tools/fgate.py variants/c520-mvf variants/c520-ps --pool v4 --fuel 200000 --mite-body mf-c2 --max-batches 1 --ci 0 > ~/tmp-offload/vg/logs/gate-mvf.log 2>&1
echo "exit $?" >> ~/tmp-offload/vg/logs/gate-mvf.log
touch ~/tmp-offload/vg/gatemv.done
