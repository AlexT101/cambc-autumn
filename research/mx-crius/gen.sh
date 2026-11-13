#!/bin/bash
# usage: gen NAME A B
cd /home/ubuntu/wt/mx-crius
name=$1; a=$2; b=$3
out=maps/suites/mx/$name
tmp=/tmp/mxc-gen-$name
rm -rf $tmp; mkdir -p $tmp $out
node tools/mapgen/mapgen.mjs suite --out "$tmp/{seed}" --seed $a-$b --mix ladder-v4 --jobs 16
for d in $tmp/*/; do mv $d/*.map26a $out/ 2>/dev/null; done
rm -rf $tmp
echo done $name $(ls $out | wc -l)
