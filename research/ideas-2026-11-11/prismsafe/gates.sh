#!/bin/bash
# fgate screens at 200k fuel against charybdis-cb9f86d, one arm after another; a done-file each.
cd /home/ubuntu/cambc-autumn
L=/home/ubuntu/tmp-offload/prismsafe/logs
for arm in "$@"; do
  python3 tools/fgate.py variants/psafe-$arm variants/charybdis-cb9f86d --fuel 200000 --screen --max-batches ${MAXB:-8} > $L/gate-$arm.log 2>&1
  touch $L/gate-$arm.done
done
