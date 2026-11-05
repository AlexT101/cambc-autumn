#!/bin/bash
# ab.sh CAND NAME FIRST LAST: A/B CAND against variants/astraeus-5b66bde on maps/fresh-FIRST..LAST, own drafts, real budget.
cd "$(dirname "$0")/../.."
export PATH=/home/ubuntu/venv/bin:$HOME/.cargo/bin:$PATH CAMBC_SLOTS=86
export CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
suites=$(seq -f "maps/fresh-%g" "$3" "$4" | paste -sd,)
/home/ubuntu/venv/bin/python tools/ab.py "$1" variants/astraeus-5b66bde --no-test-draft --suites "$suites" --name "$2" > "replays/ab-$2.log" 2>&1
