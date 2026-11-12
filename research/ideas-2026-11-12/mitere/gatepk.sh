#!/bin/bash
# gatepk.sh: rule 2 arm c520-pk against c520-ps, fgate pool v3 at 200k from batch 8 (REF's runs cached there):
# Flp4 + Mt3q screen to a decision (at most 7 batches), then one mf-c2 batch.
R=/home/ubuntu/cambc-autumn; cd $R; source /home/ubuntu/venv/bin/activate
export CAMBC_SLOTS=86 CAMBC_BIN=$R/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
python3 tools/fgate.py variants/c520-pk variants/c520-ps --pool v3 --fuel 200000 --first-batch 8 --max-batches 7 --screen > ~/tmp-offload/vg/logs/gate-pk.log 2>&1
echo "exit $?" >> ~/tmp-offload/vg/logs/gate-pk.log
python3 tools/fgate.py variants/c520-pk variants/c520-ps --pool v3 --fuel 200000 --mite-body mf-c2 --first-batch 8 --max-batches 1 --ci 0 > ~/tmp-offload/vg/logs/gate-pk-mfc2.log 2>&1
echo "exit $?" >> ~/tmp-offload/vg/logs/gate-pk-mfc2.log
touch ~/tmp-offload/vg/gatepk.done
