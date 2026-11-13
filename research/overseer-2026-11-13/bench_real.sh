#!/bin/bash
# Real-budget bench on the 205 sampled overseer-nyx maps against charybdis, games kept.
# usage: bench_real.sh BOTDIR NAME
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH
W=replays/fuel/wardfuel
py tools/fuel/bench.py run $1 --opp charybdis --maps $(cat $W/maps200.txt) --fuel 0 --jobs 86 --games $W/g-$2 --out $W/real-$2.json > $W/real-$2.log 2>&1
