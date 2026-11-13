#!/bin/bash
# queue.sh SUITE VARIANT... : read each variant vs chy-ref on SUITE in turn (waits for its smoke to finish first)
source ~/venv/bin/activate
cd /home/ubuntu/wt/mac13-nyx
suite=$1; shift
for v in "$@"; do
  while tmux ls 2>/dev/null | grep -q "mac13-nyx-smoke-$v:"; do sleep 10; done
  [ -f /tmp/mac13-nyx-$v-$suite.log ] && grep -q Results: /tmp/mac13-nyx-$v-$suite.log && continue
  CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH \
    py tools/ab.py variants/$v variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mac13/$suite --name mac13-nyx-$v-$suite > /tmp/mac13-nyx-$v-$suite.log 2>&1
  rm -rf replays/batch-*-ab-mac13-nyx-$v-$suite-$suite
done
