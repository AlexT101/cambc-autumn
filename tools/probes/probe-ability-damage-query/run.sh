#!/usr/bin/env bash
# Usage: tools/probes/probe-ability-damage-query/run.sh [rounds] [outdir]
# Builds, runs the probe against itself on emblems.map26a (stock cambc), prints both teams' PROBE lines.
set -e
cd "$(dirname "$0")/../../.."
P=tools/probes/probe-ability-damage-query
R=${1:-150}
OUT=${2:-${TMPDIR:-/tmp}/probes/ability-damage-query}
cambc build $P 2>&1 | grep -iE " error|error:" || true
rm -rf "$OUT"; mkdir -p "$OUT"
cambc run $P $P --map $P/emblems.map26a --rounds "$R" --fuel 50000000 -o "$OUT" > "$OUT/run.log" 2>&1 || true
cd "$OUT" && unzip -o -q ./*.repl26a
for t in a b; do tr -cd '\11\12\15\40-\176' < team-$t.stdout | grep PROBE > probe-$t.txt || true; done
cat probe-a.txt probe-b.txt
