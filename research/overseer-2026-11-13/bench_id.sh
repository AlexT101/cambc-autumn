#!/bin/bash
# Identity benches (100M) of a candidate against nyx-vl's: own drafts and test drafts, --set wide.
# usage: bench_id.sh variants/NAME TAG
set -e
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH
W=replays/fuel/wardfuel
py tools/fuel/bench.py run $1 --set wide --jobs 86 --out $W/$2-own.json > $W/$2-own.log 2>&1
py tools/fuel/bench.py run $1 --set wide --test-draft --jobs 86 --out $W/$2-td.json > $W/$2-td.log 2>&1
py tools/fuel/bench.py compare $W/base-own.json $W/$2-own.json > $W/$2-own.cmp 2>&1 || true
py tools/fuel/bench.py compare $W/base-td.json $W/$2-td.json > $W/$2-td.cmp 2>&1 || true
