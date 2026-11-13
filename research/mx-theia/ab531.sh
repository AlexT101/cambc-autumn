#!/bin/bash
# usage: ab.sh TAG CAND SUITE [extra ab.py args...]
TAG=$1; CAND=$2; SUITE=$3; shift 3
source ~/venv/bin/activate
cd /home/ubuntu/wt/mx-theia
mkdir -p research/mx-theia/logs
CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH \
  py tools/ab.py variants/$CAND variants/chy-531 --no-test-draft --fuel 200000 --suites $SUITE --name mx-theia-$TAG "$@" 2>&1 | tee research/mx-theia/logs/$TAG.log
