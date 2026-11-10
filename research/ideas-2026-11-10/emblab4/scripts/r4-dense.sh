#!/bin/bash
# The final fit of round 4's dense phases (r4, r4b, r4c), once r4c's last batch is merged.
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
until grep -q "batch 4: merged" replays/emblab/r4c-run.log; do sleep 10; done
sleep 25   # the batch's decisions are compressed after the merge line's games.jsonl write
SPLITS=gold_side,contested_share,spawn_dist,area,gems_side,big_share,cluster_share,altar_centre,altars
cp replays/emblab/r3/dmodel-dr-static.json replays/emblab/r4/dmodel-dense.json
NODE_OPTIONS=--max-old-space-size=120000 node tools/emblab/dfit.mjs --labs r4,r4b,r4c --variant static --mapdr --mapsplits $SPLITS --mapcuts 2,4,6 --threads 30 --out replays/emblab/r4/dmodel-dense.json > replays/emblab/r4/dfit-dense.log 2>&1
echo DENSE-DONE $(date -u +%T)
