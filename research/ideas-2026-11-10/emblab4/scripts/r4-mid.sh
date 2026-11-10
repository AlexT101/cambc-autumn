#!/bin/bash
# A fit on everything merged so far, while the lab plays: bash replays/emblab/r4-mid.sh TAG [slots]
set -e
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
export CAMBC_SLOTS=86 CAMBC_SLOT_WEIGHT=35 NODE_OPTIONS=--max-old-space-size=120000
TAG=$1; N=${2:-40}
# Not while a batch's decisions are being compressed.
while ls replays/emblab/r4b/decisions/*.jsonl >/dev/null 2>&1 || [ -n "$(find replays/emblab/r4b/decisions -name '*.zst' -newermt '-20 seconds' 2>/dev/null)" ]; do sleep 5; done
ls replays/emblab/r4/decisions replays/emblab/r4b/decisions | grep -c zst
SPLITS=gold_side,contested_share,spawn_dist,area,gems_side,big_share,cluster_share,altar_centre,altars
cp replays/emblab/r3/dmodel-dr-static.json replays/emblab/r4/dmodel-$TAG.json
python3 tools/emblab/with_slots.py $N node tools/emblab/dfit.mjs --labs r4,r4b --variant static --mapdr --mapsplits $SPLITS --mapcuts 2,4,6 --threads '{slots}' --out replays/emblab/r4/dmodel-$TAG.json > replays/emblab/r4/dfit-$TAG.log 2>&1
echo MID-DONE $TAG $(date -u +%T)
