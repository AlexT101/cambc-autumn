#!/bin/bash
# gen.sh NAME A B : fresh ladder-v4 suite of seeds A-B into maps/suites/mx-phoebe/NAME (flat)
set -e
cd /home/ubuntu/wt/mx-phoebe
N=$1; A=$2; B=$3
T=/tmp/mx-phoebe-gen-$N
rm -rf $T; mkdir -p $T
node tools/mapgen/mapgen.mjs suite --out "$T/{seed}" --seed $A-$B --mix ladder-v4 --jobs 16
mkdir -p maps/suites/mx-phoebe/$N
for d in $T/*/; do s=$(basename $d); for f in $d*.map26a; do mv "$f" maps/suites/mx-phoebe/$N/; done; [ -f $d/index.json ] && cp $d/index.json maps/suites/mx-phoebe/$N/index-$s.json || true; done
rm -rf $T
ls maps/suites/mx-phoebe/$N/*.map26a | wc -l
