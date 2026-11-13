#!/bin/bash
# research/mx-rhea/ab.sh TAG CAND SUITE [extra ab.py args]: CAND vs chy-ref at 2x fuel in tmux session mx-rhea-TAG.
TAG=$1; CAND=$2; SUITE=$3; shift 3
cd /home/ubuntu/wt/mx-rhea
mkdir -p research/mx-rhea/logs
tmux new -d -s mx-rhea-$TAG "source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-rhea && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=\$HOME/.cargo/bin:\$PATH py tools/ab.py variants/$CAND variants/chy-ref --no-test-draft --fuel ${FUEL:-200000} --suites $SUITE --name mx-rhea-$TAG $* 2>&1 | tee research/mx-rhea/logs/$TAG.log"
echo "started mx-rhea-$TAG"
