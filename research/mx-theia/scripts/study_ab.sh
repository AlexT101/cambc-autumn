#!/bin/bash
# usage: study_ab.sh TAG CANDNAME  -> extracts the A/B's kept replays and prints CAND vs REF profiles
TAG=$1; CAND=$2
cd /home/ubuntu/wt/mx-theia; source ~/venv/bin/activate
B=$(ls -d replays/batch-*-ab-mx-theia-$TAG-* | head -1)
OUT=replays/mx-theia-an/$TAG
node tools/replay/extract.mjs $B --threads 32 --out $OUT > /dev/null 2>&1
echo "== $TAG ($B)"
py research/mx-theia/scripts/terr.py $OUT "" $CAND
py research/mx-theia/scripts/orbit.py $OUT $CAND
py research/mx-theia/scripts/steals.py $OUT $CAND
