#!/bin/bash
# Base and the variants against v87's Fl / Mt3 bodies, every replay kept (dgate's block-0 games, deterministic).
source /home/ubuntu/venv/bin/activate; cd /home/ubuntu/cambc-autumn
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
L=~/tmp-offload/feint/logs; mkdir -p $L
for c in oc-base25 v87-ft-m3 v87-ft-k v87-ft-1; do for m in Fl Mt3; do
  n=fb-${c#v87-}-$m
  ( python tools/ab.py variants/$c variants/spar-o25-$m --no-test-draft --suites ladder --name $n --keep-replays 0 > $L/$n.log 2>&1; echo $? > $L/$n.done ) &
done; done; wait
