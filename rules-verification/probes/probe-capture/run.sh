#!/usr/bin/env bash
# Usage: rules-verification/probes/probe-capture/run.sh <scenario> <map> <rounds> [outdir]
# Rewrites src/scenario.h, builds (fuel raised to 50M so turns never suspend), runs probe-capture (team A) vs probe-capture-b (passive), prints PROBE lines.
set -e
cd "$(dirname "$0")/../../.."
SC=$1; MAP=$2; R=$3
OUT=${4:-${TMPDIR:-/tmp}/probes/capture/s$SC-$MAP}
printf '#pragma once\n#define SCENARIO %s\n' "$SC" > rules-verification/probes/probe-capture/src/scenario.h
cambc build rules-verification/probes/probe-capture 2>&1 | grep -iE " error|error:" || true
rm -rf "$OUT"; mkdir -p "$OUT"
cambc run rules-verification/probes/probe-capture rules-verification/probes/probe-capture-b --map "$MAP" --rounds "$R" --fuel 50000000 --statistics "$OUT/stats.json" -o "$OUT" > "$OUT/run.log" 2>&1 || true
cd "$OUT" && unzip -o -q ./*.repl26a
tr -cd '\11\12\15\40-\176' < team-a.stdout | grep PROBE | grep -v survey > probe.txt || true
echo "$OUT/probe.txt: $(wc -l < probe.txt) lines"
