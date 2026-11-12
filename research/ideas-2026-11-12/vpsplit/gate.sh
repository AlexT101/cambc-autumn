#!/bin/bash
# gate.sh: vps-524 (vp split: carrier + routing 0.5) against chy-emb6-524, fgate pool v4 at 200k, Fish r8 body fr8-g25 and Mite body mf-c2.
R=/home/ubuntu/cambc-autumn; O=/home/ubuntu/tmp-offload/vpsplit; cd $R; source /home/ubuntu/venv/bin/activate
export CAMBC_SLOTS=86 CAMBC_BIN=$R/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
python3 tools/fgate.py variants/vps-524 variants/chy-emb6-524 --pool v4 --fuel 200000 --fish-body fr8-g25 --mite-body mf-c2 --max-batches 4 --screen > $O/logs/gate-vps-524.log 2>&1
echo "exit $?" >> $O/logs/gate-vps-524.log
touch $O/gate.done
