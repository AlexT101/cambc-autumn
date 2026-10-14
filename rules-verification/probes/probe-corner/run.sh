#!/usr/bin/env bash
# Usage: bash rules-verification/probes/probe-corner/run.sh [outdir]
# Builds the map and the probe, plays it against itself, and extracts PROBE lines into probe-a.txt / probe-b.txt.
set -e
cd "$(dirname "$0")/../../.."
OUT=${1:-${TMPDIR:-/tmp}/probes/corner}
node rules-verification/probes/probe-corner/makemap.mjs > /dev/null
cambc build rules-verification/probes/probe-corner 2>&1 | grep -iE " error|error:" || true
rm -rf "$OUT"; mkdir -p "$OUT"
cambc run rules-verification/probes/probe-corner rules-verification/probes/probe-corner --map rules-verification/probes/probe-corner/corner.map26a \
  --rounds 400 --fuel 50000000 -o "$OUT" > "$OUT/run.log" 2>&1 || true
cd "$OUT" && unzip -o -q ./*.repl26a
tr -cd '\11\12\15\40-\176' < team-a.stdout | grep PROBE > probe-a.txt || true
tr -cd '\11\12\15\40-\176' < team-b.stdout | grep PROBE > probe-b.txt || true
echo "$OUT: a=$(wc -l < probe-a.txt) b=$(wc -l < probe-b.txt) lines"
