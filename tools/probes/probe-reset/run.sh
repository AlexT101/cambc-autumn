#!/usr/bin/env bash
# Usage: bash tools/probes/probe-reset/run.sh <scenario> [rounds] [outdir]
# Writes scenario.h, mirrors src/ into probe-reset-b (SIDE=1), builds both, runs probe-reset (team A) vs probe-reset-b (team B)
# on packs with fuel 50M, extracts PROBE lines into probe-a.txt / probe-b.txt and the engine's capture timeline into timeline.txt.
set -e
cd "$(dirname "$0")/../../.."
SC=$1; R=${2:-80}
OUT=${3:-${TMPDIR:-/tmp}/probes/reset/s$SC}
P=tools/probes
printf '#pragma once\n#define SCENARIO %s\n' "$SC" > $P/probe-reset/src/scenario.h
printf '#pragma once\n#define SIDE 0\n' > $P/probe-reset/src/side.h
cp $P/probe-reset/src/main.cpp $P/probe-reset/src/scenario.h $P/probe-reset-b/src/
printf '#pragma once\n#define SIDE 1\n' > $P/probe-reset-b/src/side.h
cambc build $P/probe-reset 2>&1 | grep -iE " error|error:" || true
cambc build $P/probe-reset-b 2>&1 | grep -iE " error|error:" || true
rm -rf "$OUT"; mkdir -p "$OUT"
cambc run $P/probe-reset $P/probe-reset-b --map packs --rounds "$R" --fuel 50000000 -o "$OUT" > "$OUT/run.log" 2>&1 || true
REPLAY=$(ls "$OUT"/*.repl26a | head -1)
node $P/probe-reset/timeline.mjs "$REPLAY" > "$OUT/timeline.txt"
cd "$OUT" && unzip -o -q "$REPLAY"
tr -cd '\11\12\15\40-\176' < team-a.stdout | grep PROBE > probe-a.txt || true
tr -cd '\11\12\15\40-\176' < team-b.stdout | grep PROBE > probe-b.txt || true
echo "$OUT: a=$(wc -l < probe-a.txt) b=$(wc -l < probe-b.txt) timeline=$(wc -l < timeline.txt) lines"
