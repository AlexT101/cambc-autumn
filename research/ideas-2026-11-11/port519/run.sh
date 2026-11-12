#!/bin/bash
# port519: comms + psafe-a (and psafe-a alone) on charybdis-p3 (= charybdis 519), read at 100k on pool batches
# 63-74, maps grown here from mapgen seeds 2448000-2448129 (--mix ladder-v2), which no gate had played.
source $HOME/venv/bin/activate
export PATH=$HOME/.local/bin:$HOME/venv/bin:$PATH
cd /home/ubuntu/cambc-autumn
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
O=~/tmp-offload/port519; L=$O/logs; P=research/ideas-2026-11-11/port519
mkdir -p $L/mapgen $O/gen
mkdir $L/run.started 2>/dev/null || exit 0
[ "$(ls -d $O/gen/2448??? 2>/dev/null | wc -l)" = 130 ] || seq 2448000 2448129 | xargs -P 8 -I{} sh -c "python3 tools/pooled.py 1 -- node tools/mapgen/mapgen.mjs suite --out $O/gen/{} --seed {} --mix ladder-v2 --jobs 1 > $L/mapgen/{}.log 2>&1"
echo "gen dirs: $(ls -d $O/gen/2448??? | wc -l)" > $L/grow.log
python3 tools/pooled.py 1 -- python3 tools/fgate_batch.py grow 2448000-2448129 $(seq 2448000 2448129 | sed "s|^|$O/gen/|") >> $L/grow.log 2>&1
echo "grow-rc=$?" >> $L/grow.log
# batches 63.. that the pool now holds whole, at most 12
n=$(python3 -c "import json,os;print(min(12,len(json.load(open(os.path.expanduser('~/tmp-offload/gatebatch/pool/index.json')))['maps'])//2560-63))")
echo "batches: 63 + $n" >> $L/grow.log
[ "$n" -ge 1 ] || { touch $L/run.done; exit 1; }
last=$((62 + n))
F="--fuel 100000 --first-batch 63 --max-batches $n --ci 0 --jobs 2"
pids=""
for v in c519-cmps c519-ps; do
  python3 tools/fgate.py variants/$v variants/charybdis-p3 $F > $L/gate-$v.log 2>&1 & pids="$pids $!"; sleep 30
done
wait $pids
for v in c519-cmps c519-ps; do
  python3 research/ideas-2026-11-11/chyport/report.py variants/$v variants/charybdis-p3 63-$last --fuel 100000 > $L/report-$v.txt 2>&1
done
python3 $P/contrast.py variants/charybdis-p3 63-$last --fuel 100000 > $L/contrast.txt 2>&1
touch $L/run.done
