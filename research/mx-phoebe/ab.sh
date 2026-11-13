#!/bin/bash
# ab.sh TAG CAND SUITE [extra ab.py args...] : CAND vs variants/chy-ref, 2x fuel, own drafts
cd /home/ubuntu/wt/mx-phoebe
source ~/venv/bin/activate
TAG=$1; CAND=$2; SUITE=$3; shift 3
export CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH
py tools/ab.py variants/$CAND variants/chy-ref --no-test-draft --fuel 200000 --suites $SUITE --name mx-phoebe-$TAG "$@" 2>&1 | tee research/mx-phoebe/logs/ab-$TAG.log
