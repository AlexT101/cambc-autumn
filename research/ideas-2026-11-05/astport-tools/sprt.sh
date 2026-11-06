#!/bin/bash
# sprt.sh NAME...: SPRT 0.50/0.51 of each bots/variants/oc-ap-NAME against oc-retest-clean on ap-dev, one after another.
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
for n in "$@"; do
  [ -f replays/ab/ap-$n-dev/summary.md ] && continue
  python3 tools/ab.py variants/oc-ap-$n variants/oc-retest-clean --no-test-draft --sprt 0.50,0.51 \
    --suites maps/suites/merged/ap-dev --name ap-$n-dev > research/ideas-2026-11-05/astport-tools/logs/ap-$n-dev.log 2>&1
  python3 research/ideas-2026-11-05/astport-tools/clean.py ap-$n-dev
done
