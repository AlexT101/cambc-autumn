#!/bin/bash
# gate2.sh: the two halves of vps-524 apart (vps-524c carrier by side only, vps-524w routing only), as gate.sh.
R=/home/ubuntu/cambc-autumn; O=/home/ubuntu/tmp-offload/vpsplit; cd $R; source /home/ubuntu/venv/bin/activate
export CAMBC_SLOTS=86 CAMBC_BIN=$R/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
for C in vps-524c vps-524w; do
  python3 tools/fgate.py variants/$C variants/chy-emb6-524 --pool v4 --fuel 200000 --fish-body fr8-g25 --mite-body mf-c2 --max-batches 4 --screen > $O/logs/gate-$C.log 2>&1
  echo "exit $?" >> $O/logs/gate-$C.log
done
touch $O/gate2.done
