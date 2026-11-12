#!/bin/bash
# gatemx.sh: exploit test copies (forced on) against c520-ps, fgate pool v4 at 200k with the mf-c2 Mite body. Read the
# "fresh, Mite" row; the Fish row prices a misfire. mxf (Vesper focus) to a decision within 4 batches, msf (chase
# standing bodies) one batch.
R=/home/ubuntu/cambc-autumn; cd $R; source /home/ubuntu/venv/bin/activate
export CAMBC_SLOTS=86 CAMBC_BIN=$R/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
python3 tools/fgate.py variants/c520-mxf variants/c520-ps --pool v4 --fuel 200000 --mite-body mf-c2 --max-batches 4 > ~/tmp-offload/vg/logs/gate-mxf.log 2>&1
echo "exit $?" >> ~/tmp-offload/vg/logs/gate-mxf.log
python3 tools/fgate.py variants/c520-msf variants/c520-ps --pool v4 --fuel 200000 --mite-body mf-c2 --max-batches 1 --ci 0 > ~/tmp-offload/vg/logs/gate-msf.log 2>&1
echo "exit $?" >> ~/tmp-offload/vg/logs/gate-msf.log
touch ~/tmp-offload/vg/gatemx.done
