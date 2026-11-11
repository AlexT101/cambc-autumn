#!/bin/bash
# usage: research/macro-delphi/ab.sh CAND NAME SUITES [extra ab.py args]   (runs in tmux session mo4-NAME)
C=$1; N=$2; S=$3; shift 3
mkdir -p /home/ubuntu/wt/macro-o4/replays/logs
tmux new -d -s "mo4-$N" "source /home/ubuntu/venv/bin/activate && cd /home/ubuntu/wt/macro-o4 && TMPDIR=/home/ubuntu/wt/macro-o4/replays/tmp CAMBC_SLOTS=86 PATH=\$HOME/.cargo/bin:\$PATH CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native py tools/ab.py variants/$C variants/charybdis-ref --no-test-draft --fuel 200000 --suites $S --name $N $* 2>&1 | tee /home/ubuntu/wt/macro-o4/replays/logs/$N.log"
