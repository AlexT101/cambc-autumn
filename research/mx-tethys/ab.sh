#!/bin/bash
# ab.sh TAG CAND SUITE [extra ab.py args...]: CAND (a variants/ dir) against variants/chy-ref at 2x fuel, own drafts,
# in tmux session mx-tethys-TAG; log in research/mx-tethys/logs/TAG.log, results in replays/ab/mx-tethys-TAG/.
set -e
tag=$1; cand=$2; suite=$3; shift 3
cd /home/ubuntu/wt/mx-tethys
tmux new -d -s "mx-tethys-$tag" "source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-tethys && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=\$HOME/.cargo/bin:\$PATH py tools/ab.py variants/$cand variants/chy-ref --no-test-draft --fuel 200000 --suites $suite --name mx-tethys-$tag $* 2>&1 | tee research/mx-tethys/logs/$tag.log"
echo "started mx-tethys-$tag"
