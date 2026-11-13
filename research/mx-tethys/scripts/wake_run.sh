#!/bin/bash
# run.sh N: subset then full train for mx-wake-vN, logs in research/mx-tethys/logs/
n=$1
source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-tethys
export CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH
py tools/ab.py variants/mx-wake-v$n variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mx/train-mono --name mx-tethys-wake-v$n 2>&1 | tee research/mx-tethys/logs/wake-v$n-mono.log
py tools/ab.py variants/mx-wake-v$n variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mx/train --name mx-tethys-wake-v$n-train 2>&1 | tee research/mx-tethys/logs/wake-v$n-train.log
echo DONE > research/mx-tethys/logs/wake-v$n.done
