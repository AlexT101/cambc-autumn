#!/bin/bash
# port520: psafe-a (c520-ps) and comms + psafe-a (c520-cmps) on chy-life (= charybdis 520), read at 100k against it on
# pool batches 75-86: 75 unplayed, 76-86 grown here from mapgen seeds 2471000-2471129 (--mix ladder-v2), which no
# gate had played. Then the winning-bag mechanism games (pool batch 0 parts p0-p3, with replays, 100k).
source $HOME/venv/bin/activate
export PATH=$HOME/.local/bin:$HOME/venv/bin:$PATH
cd /home/ubuntu/cambc-autumn
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
O=~/tmp-offload/port520; L=$O/logs; P=research/ideas-2026-11-12/port520
REF=variants/chy-life; ARMS="c520-ps c520-cmps"
mkdir -p $L/mapgen $O/gen
mkdir $L/run.started 2>/dev/null || exit 0
[ "$(ls -d $O/gen/2471??? 2>/dev/null | wc -l)" = 130 ] || seq 2471000 2471129 | xargs -P 8 -I{} sh -c "python3 tools/pooled.py 1 -- node tools/mapgen/mapgen.mjs suite --out $O/gen/{} --seed {} --mix ladder-v2 --jobs 1 > $L/mapgen/{}.log 2>&1"
echo "gen dirs: $(ls -d $O/gen/2471??? | wc -l)" > $L/grow.log
python3 tools/pooled.py 1 -- python3 tools/fgate_batch.py grow 2471000-2471129 $(seq 2471000 2471129 | sed "s|^|$O/gen/|") >> $L/grow.log 2>&1
echo "grow-rc=$?" >> $L/grow.log
# batches 75.. that the pool now holds whole, at most 12
n=$(python3 -c "import json,os;print(min(12,len(json.load(open(os.path.expanduser('~/tmp-offload/gatebatch/pool/index.json')))['maps'])//2560-75))")
echo "batches: 75 + $n" >> $L/grow.log
[ "$n" -ge 1 ] || { touch $L/run.done; exit 1; }
last=$((74 + n))
F="--fuel 100000 --first-batch 75 --max-batches $n --ci 0 --jobs 2"
pids=""
for v in $ARMS; do
  python3 tools/fgate.py variants/$v $REF $F > $L/gate-$v.log 2>&1 & pids="$pids $!"; sleep 30
done
wait $pids
for v in $ARMS; do
  python3 research/ideas-2026-11-11/chyport/report.py variants/$v $REF 75-$last --fuel 100000 > $L/report-$v.txt 2>&1
done
python3 $P/contrast.py $REF 75-$last --fuel 100000 > $L/contrast.txt 2>&1
touch $L/gate.done
# Mechanism: each bot against both rt bodies on batch 0 parts p0-p3 (1,280 maps, both sides), replays kept, 100k.
export FASTRUNNER_LIB=$PWD/tools/fastengine/runner/target-rt/release/libfastrunner.so
S=~/tmp-offload/gatebatch/suites/m2560
for t in ref:chy-life ps:c520-ps cmps:c520-cmps; do
  tag=${t%%:*}; bot=variants/${t#*:}
  for B in Flp4 Mt3q; do
    N=p520-mech-$tag-$B
    python3 tools/ab.py $bot variants/rt-$B --no-test-draft --suites $S/b000.parts/p0,$S/b000.parts/p1,$S/b000.parts/p2,$S/b000.parts/p3 \
      --name $N --fuel 100000 --keep-replays 0 --experiment-config $S/b000.json --game-timeout 900 > $L/$N.log 2>&1 &
  done
  wait
  node tools/replay/extract.mjs replays/batch-*-ab-p520-mech-$tag-Flp4-* replays/batch-*-ab-p520-mech-$tag-Mt3q-* --threads 12 --out $O/ext/$tag > $L/ext-$tag.log 2>&1
done
python3 tools/pooled.py 16 -- python3 $P/mech.py $O/ext ref ps cmps > $L/mech.txt 2>&1
touch $L/run.done
