#!/bin/bash
# usage: ab.sh CAND_DIR_NAME RUN_NAME FIRST_SEED LAST_SEED [extra ab.py args]
# runs in tmux session RUN_NAME; log in /home/ubuntu/wt/macro1-maps/logs/RUN_NAME.log
C=$1; N=$2; A=$3; B=$4; shift 4
S=$(seq -s, -f "/home/ubuntu/wt/macro1-maps/s-%g" $A $B)
mkdir -p /home/ubuntu/wt/macro1-maps/logs
tmux new -d -s "$N" "source /home/ubuntu/wt/macro1/research/macro-2026-11-11/env.sh && py tools/ab.py variants/$C variants/ocean-ref-b7c87cf --no-test-draft --fuel 200000 --suites $S --name $N $* 2>&1 | tee /home/ubuntu/wt/macro1-maps/logs/$N.log"
