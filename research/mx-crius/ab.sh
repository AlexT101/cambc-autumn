#!/bin/bash
# usage: ab.sh TAG CAND SUITE [extra ab.py args...]   (2x fuel unless FUEL=100000 set; FUEL=normal drops --fuel)
source ~/venv/bin/activate
cd /home/ubuntu/wt/mx-crius
tag=$1; cand=$2; suite=$3; shift 3
fuel="--fuel 200000"; [ "$FUEL" = normal ] && fuel=""
mkdir -p research/mx-crius/logs
CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH \
  py tools/ab.py variants/$cand variants/chy-ref --no-test-draft $fuel --suites maps/suites/mx/$suite --name mx-crius-$tag "$@" 2>&1 | tee research/mx-crius/logs/$tag.log
