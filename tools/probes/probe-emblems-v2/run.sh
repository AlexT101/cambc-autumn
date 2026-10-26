#!/usr/bin/env bash
# Usage: tools/probes/probe-emblems-v2/run.sh <join_delay> [rounds] [outdir]
# Writes src/scenario.h, builds, runs the probe against itself on emblems.map26a, prints both teams' PROBE lines.
set -e
cd "$(dirname "$0")/../../.."
JD=$1; R=${2:-130}
OUT=${3:-${TMPDIR:-/tmp}/probes/emblems/j$JD}
printf '#pragma once\n#define JOIN_DELAY %s\n' "$JD" > tools/probes/probe-emblems-v2/src/scenario.h
[ -f tools/probes/probe-emblems-v2/emblems.map26a ] || node tools/probes/probe-emblems-v2/makemap.mjs > /dev/null
cambc build tools/probes/probe-emblems-v2 2>&1 | grep -iE " error|error:" || true
rm -rf "$OUT"; mkdir -p "$OUT"
cambc run tools/probes/probe-emblems-v2 tools/probes/probe-emblems-v2 --map tools/probes/probe-emblems-v2/emblems.map26a \
  --rounds "$R" --fuel 50000000 -o "$OUT" > "$OUT/run.log" 2>&1 || true
cd "$OUT" && unzip -o -q ./*.repl26a
for t in a b; do tr -cd '\11\12\15\40-\176' < team-$t.stdout | grep PROBE > probe-$t.txt || true; done
echo "$OUT/probe-a.txt: $(wc -l < probe-a.txt) lines; probe-b.txt: $(wc -l < probe-b.txt) lines"
