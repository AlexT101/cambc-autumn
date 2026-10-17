#!/usr/bin/env bash
# Usage: bash rules-verification/probes/probe-denial/run.sh <scenario> [rounds] [outdir]
# Builds the map, writes scenario.h, mirrors src/ into probe-denial-b (SIDE=1), builds both, runs probe-denial (team A)
# vs probe-denial-b (team B) on denial.map26a with fuel 50M, extracts PROBE lines into probe-a.txt / probe-b.txt and
# the engine's group timeline (probe-reset/timeline.mjs) into timeline.txt.
set -e
cd "$(dirname "$0")/../../.."
SC=$1; R=${2:-200}
OUT=${3:-${TMPDIR:-/tmp}/probes/denial/s$SC}
P=rules-verification/probes
node $P/probe-denial/makemap.mjs > /dev/null
printf '#pragma once\n#define SCENARIO %s\n' "$SC" > $P/probe-denial/src/scenario.h
printf '#pragma once\n#define SIDE 0\n' > $P/probe-denial/src/side.h
cp $P/probe-denial/src/main.cpp $P/probe-denial/src/scenario.h $P/probe-denial-b/src/
printf '#pragma once\n#define SIDE 1\n' > $P/probe-denial-b/src/side.h
cambc build $P/probe-denial 2>&1 | grep -iE " error|error:" || true
cambc build $P/probe-denial-b 2>&1 | grep -iE " error|error:" || true
rm -rf "$OUT"; mkdir -p "$OUT"
cambc run $P/probe-denial $P/probe-denial-b --map $P/probe-denial/denial.map26a --rounds "$R" --fuel 50000000 -o "$OUT" > "$OUT/run.log" 2>&1 || true
REPLAY=$(ls "$OUT"/*.repl26a | head -1)
node $P/probe-reset/timeline.mjs "$REPLAY" > "$OUT/timeline.txt"
cd "$OUT" && unzip -o -q "$REPLAY"
tr -cd '\11\12\15\40-\176' < team-a.stdout | grep PROBE > probe-a.txt || true
tr -cd '\11\12\15\40-\176' < team-b.stdout | grep PROBE > probe-b.txt || true
echo "$OUT: a=$(wc -l < probe-a.txt) b=$(wc -l < probe-b.txt) timeline=$(wc -l < timeline.txt) lines"
