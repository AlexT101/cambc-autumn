#!/bin/bash
# Map-conditioned constants diagnostic (research/ideas-2026-11-05/mapcond.md). Data goes to $MAPCOND_DIR (default: cwd).
# Reads replays/tune/{oc2,oc3} and the replays/ab batches; plays no games.
set -e
T=$(cd "$(dirname "$0")" && pwd); R=$(cd "$T/../../.." && pwd); D=${MAPCOND_DIR:-$PWD}; export MAPCOND_DIR=$D
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 NPERM=${NPERM:-500}
cd "$R"
node tools/mapgen/mapgen.mjs check --json maps > "$D/ladder-check.jsonl" || true   # one ladder map fails validation:
node "$T/met1.mjs" maps/adgato-gemcombat5.map26a > "$D/adgato.jsonl"              # its metrics, unvalidated
python3 "$T/feats.py"
for r in oc2 oc3; do python3 "$T/recon.py" $r "$D/$r-iters.json"; python3 "$T/spsa_het.py" $r; done
python3 "$T/ab_het.py"; python3 "$T/ab_buckets.py"; python3 "$T/ab_control.py"; python3 "$T/prize.py"
