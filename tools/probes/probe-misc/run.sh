#!/usr/bin/env bash
# Usage: bash tools/probes/probe-misc/run.sh <scenario> <map> <rounds> [outdir]
# Writes scenario.h, mirrors src/ into probe-misc-b (SIDE=1), builds both, runs probe-misc (team A) vs probe-misc-b (team B)
# with fuel 50M, and extracts PROBE lines into probe-a.txt / probe-b.txt.
set -e
cd "$(dirname "$0")/../../.."
SC=$1; MAP=$2; R=$3
OUT=${4:-${TMPDIR:-/tmp}/probes/misc/s$SC-$MAP}
printf '#pragma once\n#define SCENARIO %s\n' "$SC" > tools/probes/probe-misc/src/scenario.h
printf '#pragma once\n#define SIDE 0\n' > tools/probes/probe-misc/src/side.h
for f in bot.cpp bot.h draft.cpp draft.h main.cpp scenario.cpp scenario.h; do cp tools/probes/probe-misc/src/$f tools/probes/probe-misc-b/src/$f; done
printf '#pragma once\n#define SIDE 1\n' > tools/probes/probe-misc-b/src/side.h
cambc build tools/probes/probe-misc 2>&1 | grep -iE " error|error:" || true
cambc build tools/probes/probe-misc-b 2>&1 | grep -iE " error|error:" || true
rm -rf "$OUT"; mkdir -p "$OUT"
cambc run tools/probes/probe-misc tools/probes/probe-misc-b --map "$MAP" --rounds "$R" --fuel 50000000 -o "$OUT" > "$OUT/run.log" 2>&1 || true
cd "$OUT" && unzip -o -q ./*.repl26a
tr -cd '\11\12\15\40-\176' < team-a.stdout | grep PROBE > probe-a.txt || true
tr -cd '\11\12\15\40-\176' < team-b.stdout | grep PROBE > probe-b.txt || true
echo "$OUT: a=$(wc -l < probe-a.txt) b=$(wc -l < probe-b.txt) lines"
