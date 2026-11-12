#!/bin/bash
# Phase 1: five arms on charybdis-cb9f86d at 200k on pool batches 16-31 (no component was screened there),
# and fresh maps (mapgen seeds 2425000-2425099) grown into the pool for the 100k read.
source $HOME/venv/bin/activate
export PATH=$HOME/.local/bin:$HOME/venv/bin:$PATH
cd /home/ubuntu/cambc-autumn
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
O=~/tmp-offload/combo; L=$O/logs
mkdir -p $L/mapgen $O/gen
mkdir $L/p1.started 2>/dev/null || exit 0
(
  seq 2425000 2425099 | xargs -P 8 -I{} sh -c "python3 tools/pooled.py 1 -- node tools/mapgen/mapgen.mjs suite --out $O/gen/{} --seed {} --mix ladder-v2 --jobs 1 > $L/mapgen/{}.log 2>&1"
  n=$(ls -d $O/gen/2425??? | wc -l); echo "gen dirs: $n" > $L/grow.log
  python3 tools/pooled.py 1 -- py tools/fgate_batch.py grow 2425000-2425099 $(seq 2425000 2425099 | sed "s|^|$O/gen/|") >> $L/grow.log 2>&1
  touch $L/grow.done
) & g=$!
F="--fuel 200000 --first-batch 16 --max-batches 16 --ci 0 --jobs 2"
pids=""
for v in cbx-cm cbx-cmgpck cbx-cmgp cbx-gp cbx-cmck; do
  python3 tools/fgate.py variants/$v variants/charybdis-cb9f86d $F > $L/p1-$v.log 2>&1 & pids="$pids $!"; sleep 30
done
wait $pids
touch $L/p1-gates.done
wait $g
touch $L/p1.done
