#!/bin/bash
# The edit lab under one slot group with a kept weight: run-lab.sh LAB WEIGHT GAMES BATCHES   (in tmux)
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
LAB=$1; W=$2; GAMES=$3; BATCHES=$4
export CAMBC_SLOTS=86 CAMBC_SLOT_WEIGHT=$W CAMBC_SLOT_GROUP=emb5-lab CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH
python3 tools/emblab/slot_keeper.py emb5-lab $W $$ > /dev/null &
python3 tools/emblab/elab.py run --lab $LAB --games $GAMES --batches $BATCHES 2>&1 | tee -a replays/emblab/$LAB/run.out
echo RUN-DONE $(date -u +%T) | tee -a replays/emblab/$LAB/run.out
