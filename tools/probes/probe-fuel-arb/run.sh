#!/bin/sh
# Builds probe-fuel-arb-big's 8 MiB table (not in git), then plays both probes as on the platform (--release).
# Usage: tools/probes/probe-fuel-arb/run.sh OUTDIR   (from the repository root)
set -e
out=${1:?usage: run.sh OUTDIR}
data=tools/probes/probe-fuel-arb-big/src/data.bin
[ -f "$data" ] || head -c 8388608 /dev/urandom > "$data"
cambc run tools/probes/probe-fuel-arb tools/probes/probe-fuel-arb-big --map 00corners --rounds 3 --release -o "$out/start"
cambc run tools/probes/probe-fuel-arb tools/probes/probe-fuel-arb-big --map 00corners --rounds 3 --release --fuel 50000000 -o "$out/ops"
