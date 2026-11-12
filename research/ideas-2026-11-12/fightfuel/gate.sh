#!/bin/bash
# gate.sh CAND [FIRST [N]]: tools/fgate.py variants/CAND against variants/chy-life (= charybdis 520) on pool batches
# FIRST.. (default 1, N 6: the batches whose reference half earlier gates cached), a fixed read (--ci 0).
# Batches 75-86 are cached under --fuel 100000 (the same budget): FUELARG="--fuel 100000" gate.sh CAND 75 12.
CAND=$1; FIRST=${2:-1}; N=${3:-6}
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
export PATH=$HOME/.cargo/bin:$HOME/.local/bin:$PATH
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
L=/home/ubuntu/tmp-offload/fightfuel/logs
python3 tools/fgate.py variants/$CAND variants/${REF:-chy-life} $FUELARG --first-batch $FIRST --max-batches $N --ci 0 --jobs ${JOBS:-2} > $L/gate-$CAND-b$FIRST.log 2>&1
touch $L/gate-$CAND-b$FIRST.done
