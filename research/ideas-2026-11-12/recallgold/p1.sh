#!/bin/bash
# Phase 1: five recall-gold arms against charybdis-p3 at 200k on pool batches 0-15 (screen), and mechanism runs
# (each bot against both rt bodies on b000 parts p0,p1, 200k, replays extracted).
source $HOME/venv/bin/activate
export PATH=$HOME/.local/bin:$HOME/venv/bin:$PATH
cd /home/ubuntu/cambc-autumn
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
O=~/tmp-offload/recallgold; L=$O/logs
mkdir $L/p1.started 2>/dev/null || exit 0
F="--fuel 200000 --first-batch 0 --max-batches 16 --ci 0 --screen --jobs 2"
pids=""
for v in rg-s100 rg-s50 rg-score rg-own rg-own75; do
  python3 tools/fgate.py variants/$v variants/charybdis-p3 $F > $L/p1-$v.log 2>&1 & pids="$pids $!"; sleep 40
done
# mechanism runs
S=/home/ubuntu/tmp-offload/gatebatch/suites/m2560
mech() {
  BOT=$1; TAG=$2
  for B in Flp4 Mt3q; do
    N=rg-mech-$TAG-$B
    CAMBC_SLOTS=86 FASTRUNNER_LIB=$PWD/tools/fastengine/runner/target-rt/release/libfastrunner.so \
    python3 tools/ab.py variants/$BOT variants/rt-$B --no-test-draft --suites $S/b000.parts/p0,$S/b000.parts/p1 --name $N --fuel 200000 \
      --keep-replays 0 --experiment-config $S/b000.json --game-timeout 900 > $L/$N.log 2>&1
  done
  node tools/replay/extract.mjs replays/batch-*-ab-rg-mech-$TAG-Flp4-* replays/batch-*-ab-rg-mech-$TAG-Mt3q-* --threads 8 --out $O/ext/$TAG > $L/ext-$TAG.log 2>&1
  n=$(ls $O/ext/$TAG | wc -l)
  [ "$n" -ge 2500 ] && rm -rf replays/batch-*-ab-rg-mech-$TAG-Flp4-* replays/batch-*-ab-rg-mech-$TAG-Mt3q-*
  touch $L/mech-$TAG.done
}
mpids=""
for v in charybdis-p3:ref rg-s100:s100 rg-s50:s50 rg-score:score rg-own:own rg-own75:own75; do
  mech ${v%%:*} ${v##*:} & mpids="$mpids $!"; sleep 5
done
wait $mpids
touch $L/p1-mech.done
wait $pids
touch $L/p1.done
