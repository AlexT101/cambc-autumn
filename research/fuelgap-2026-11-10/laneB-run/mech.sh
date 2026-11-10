#!/bin/bash
# mech.sh BOT NAME: debug games at the real budget against oc-ceil-ref on the 640-map subset, all replays kept.
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
export CAMBC_SLOT_WEIGHT=15 CAMBC_SLOT_GROUP=fgb-mech CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native CAMBC_LOG_LIMIT=16000000
python tools/ab.py variants/$1 variants/oc-ceil-ref --no-test-draft --debug --keep-replays 0 --suites /tmp/claude-1000/-home-ubuntu-cambc-autumn/f02f8021-9589-4295-a15c-bf87a168ba28/scratchpad/m640 --name $2
