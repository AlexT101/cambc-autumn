#!/bin/bash
# ab.sh CAND SUITE TAG [extra ab.py args]: candidate vs chy-ref at 2x fuel in tmux session mac13-eos-TAG
CAND=$1; SUITE=$2; TAG=$3; shift 3
tmux new -d -s mac13-eos-$TAG "source ~/venv/bin/activate && cd /home/ubuntu/wt/mac13-eos && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=\$HOME/.cargo/bin:\$PATH py tools/ab.py variants/$CAND variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mac13/$SUITE --name mac13-eos-$TAG $* 2>&1 | tee /tmp/eos-$TAG.log"
