#!/bin/bash
# Phase 2: gp-race (ZONE at 8 batches) run on to 16 batches at 200k; batches 0-7 are cached.
source $HOME/venv/bin/activate
cd /home/ubuntu/cambc-autumn
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
G=~/tmp-offload/gemprice; L=$G/logs
mkdir $L/p2.started 2>/dev/null || exit 0
python3 tools/fgate.py variants/gp-race variants/chy18-cm2k3 --fuel 200000 --screen --max-batches 16 --ci 0 --jobs 4 > $L/p2-gp-race.log 2>&1
python3 ~/tmp-offload/allypos/report.py variants/gp-race variants/chy18-cm2k3 0-15 --fuel 200000 > $L/p2-gp-race.report 2>&1
touch $L/p2.done
