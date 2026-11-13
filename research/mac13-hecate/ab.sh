#!/bin/bash
# ab.sh CAND TAG [SUITE] : full A/B of variants/CAND against variants/chy-ref at 2x fuel, in tmux mac13-hecate-TAG
CAND=$1; TAG=$2; SUITE=${3:-maps/suites/mac13/dev}
tmux new -d -s mac13-hecate-$TAG "source ~/venv/bin/activate && cd /home/ubuntu/wt/mac13-hecate && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=\$HOME/.cargo/bin:\$PATH python tools/ab.py variants/$CAND variants/chy-ref --no-test-draft --fuel 200000 --suites $SUITE --name mac13-hecate-$TAG 2>&1 | tee /tmp/mac13-hecate-$TAG.log"
echo launched mac13-hecate-$TAG
