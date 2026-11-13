#!/bin/bash
# usage: mac13-castor-ab.sh TAG CAND SUITE [extra args...]
TAG=$1; CAND=$2; SUITE=$3; shift 3
source ~/venv/bin/activate
cd /home/ubuntu/wt/mac13-castor
CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH \
  py tools/ab.py variants/$CAND variants/chy-ref --no-test-draft --fuel 200000 --suites $SUITE --name mac13-castor-$TAG "$@" 2>&1 | tee research/mac13-castor/logs/$TAG.log
