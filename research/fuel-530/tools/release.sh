#!/bin/bash
set -euo pipefail
cd /home/ubuntu/wt/fuel-530
source /home/ubuntu/venv/bin/activate
export CAMBC_SLOTS=86 CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH
py tools/ab.py variants/f530-final variants/chy-530 --no-test-draft --suites maps/suites/f530-final --name f530-final > research/fuel-530/results/release.log 2>&1
