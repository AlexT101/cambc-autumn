#!/bin/bash
# The sparse phase's fits: its even and odd batches apart (r4d-a, r4d-b: two independent halves whose sums
# select.py adds or scores against each other).  bash replays/emblab/r4-sparse.sh [threads each]
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
TH=${1:-40}
for h in a b; do
  d=replays/emblab/r4d-$h; rm -rf $d; mkdir -p $d/decisions
  for f in config.json maps.jsonl; do ln -sfn ../r4d/$f $d/$f; done
  python3 - "$d" <<'P'
import sys
data = open('replays/emblab/r4d/games.jsonl', 'rb').read()
open(sys.argv[1] + '/games.jsonl', 'wb').write(data[:data.rfind(b'\n') + 1])
P
done
i=0
for f in $(ls replays/emblab/r4d/decisions/b*.jsonl.zst | sort); do
  if [ $((i % 2)) -eq 0 ]; then h=a; else h=b; fi
  ln -sfn ../../r4d/decisions/$(basename $f) replays/emblab/r4d-$h/decisions/$(basename $f); i=$((i + 1))
done
echo "$i batches: a $(ls replays/emblab/r4d-a/decisions | wc -l), b $(ls replays/emblab/r4d-b/decisions | wc -l)"
for h in a b; do
  cp replays/emblab/r3/dmodel-dr-static.json replays/emblab/r4d-$h/dmodel.json
  NODE_OPTIONS=--max-old-space-size=100000 node tools/emblab/dfit.mjs --labs r4d-$h --variant static --dr --fitall --threads $TH --out replays/emblab/r4d-$h/dmodel.json > replays/emblab/r4d-$h/dfit.log 2>&1 &
done
wait
echo SPARSE-DONE $(date -u +%T)
