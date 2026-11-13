#!/bin/bash
# ab.sh CAND SUITE TAG [extra ab.py args]: CAND vs variants/chy-ref at 2x fuel, own drafts, in tmux mac13-argo-TAG.
CAND=$1; SUITE=$2; TAG=$3; shift 3
cd /home/ubuntu/wt/mac13-argo
tmux new -d -s mac13-argo-$TAG "source ~/venv/bin/activate && cd /home/ubuntu/wt/mac13-argo && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=\$HOME/.cargo/bin:\$PATH py tools/ab.py variants/$CAND variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mac13/$SUITE --name mac13-argo-$TAG $* 2>&1 | tee research/mac13-argo/logs/$TAG.log"
