#!/bin/bash
# Interim fit on the batches merged so far: bash replays/emblab/r4-interim.sh TAG [threads]
set -e
cd /home/ubuntu/cambc-autumn
TAG=$1; TH=${2:-24}
mkdir -p replays/emblab/r4i
for f in config.json maps.jsonl; do ln -sfn ../r4/$f replays/emblab/r4i/$f; done
# A snapshot of games.jsonl up to its last complete line (the lab appends to it).
python3 - <<'P'
data = open('replays/emblab/r4/games.jsonl', 'rb').read()
open('replays/emblab/r4i/games.jsonl', 'wb').write(data[:data.rfind(b'\n') + 1])
P
ls replays/emblab/r4/decisions/b*.jsonl.zst | tee replays/emblab/r4i/batches-$TAG.txt | wc -l
zstd -dc $(cat replays/emblab/r4i/batches-$TAG.txt) > replays/emblab/r4i/decisions.jsonl
NODE_OPTIONS=--max-old-space-size=65536 node tools/emblab/dfit.mjs --labs r4i --variant static --dr --threads $TH --out replays/emblab/r4/dmodel-$TAG.json > replays/emblab/r4/dfit-$TAG.log 2>&1
rm replays/emblab/r4i/decisions.jsonl
echo INTERIM-DONE $TAG
