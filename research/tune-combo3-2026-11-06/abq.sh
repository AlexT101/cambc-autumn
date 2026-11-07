#!/bin/bash
# A queue of A/Bs: each line of the file "NAME CAND REF SUITE", run in turn with the fast runner, own drafts.
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
export CAMBC_SLOTS=86 CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH
while read -r name cand ref suite; do
  [ -z "$name" ] && continue
  [ -f replays/ab/$name/summary.md ] && continue
  py tools/ab.py $cand $ref --no-test-draft --suites maps/suites/merged/$suite --name $name > replays/ab-$name.log 2>&1
  rm -rf replays/batch-*-ab-$name-*  # replays: the results are in replays/ab/$name
done < "$1"
