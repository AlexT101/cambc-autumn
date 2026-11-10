#!/bin/bash
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
export CAMBC_SLOT_WEIGHT=15 CAMBC_SLOT_GROUP=fgb-flcut CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
export FASTRUNNER_BOT_FUEL=fgb-flcut:10000000
python tools/ab.py variants/fgb-flcut variants/oc-ceil-ref --no-test-draft --suites maps/suites/merged/fceil-2020 --name fgb-flcut-rel
