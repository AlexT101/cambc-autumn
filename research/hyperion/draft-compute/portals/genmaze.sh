#!/bin/sh
# The maze suite's 195 candidates: sh genmaze.sh OUTDIR, from the repo root. fieldcost.mjs then
# ranks them; the suite is the 48 with the highest deepest field / (width + height).
out=$1
mkdir -p "$out"
for p in maze caves chambers labyrinth spiral cells tunnels serpentine dungeon city gem-centre dense-camps hourglass; do
  for s in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
    node tools/mapgen/mapgen.mjs gen $p --seed $((7700 + s)) --set size=$((80 + (s * 7) % 21)) --set aspect=square --out "$out/mz-$p-$s.map26a" > /dev/null 2>&1
  done
done
