#!/bin/bash
# The final fits of round 4 on both phases' games: bash replays/emblab/r4-final.sh
set -e
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
export CAMBC_SLOTS=86 CAMBC_SLOT_WEIGHT=35 NODE_OPTIONS=--max-old-space-size=120000
ls replays/emblab/r4/decisions replays/emblab/r4b/decisions | wc -l
SPLITS=gold_side,contested_share,spawn_dist,area,gems_side,big_share,cluster_share,altar_centre,altars
# Round 3's searched penalties (the out file's lam is the fit's start).
[ -s replays/emblab/r4/dmodel-static.json ] || cp replays/emblab/r3/dmodel-dr-static.json replays/emblab/r4/dmodel-static.json
python3 tools/emblab/with_slots.py 64 node tools/emblab/dfit.mjs --labs r4,r4b --variant static --mapdr --mapsplits $SPLITS --mapcuts 2,4,6 --threads '{slots}' --out replays/emblab/r4/dmodel-static.json > replays/emblab/r4/dfit-static.log 2>&1
echo STATIC-DONE $(date -u +%T)
[ -s replays/emblab/r4/dmodel-map.json ] || cp replays/emblab/r3/dmodel-dr-static.json replays/emblab/r4/dmodel-map.json
python3 tools/emblab/with_slots.py 64 node tools/emblab/dfit.mjs --labs r4,r4b --variant map --dr --threads '{slots}' --out replays/emblab/r4/dmodel-map.json > replays/emblab/r4/dfit-map.log 2>&1
echo MAP-DONE $(date -u +%T)
