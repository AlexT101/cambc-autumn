#!/bin/bash
# The harness chain for v118b (bots/baselines/v118 against puppets of Fish r8's recorded inputs); every step skips
# finished work, so rerun it as bundles arrive.   bash research/ideas-2026-11-12/v118-fish-b/run_harness.sh [JOBS [TRACE_BOT_DIR]]
set -u
cd "$(dirname "$0")/../../.."
H=research/ideas-2026-11-12/v118-fish-b
J=${1:-24}
py $H/mkmanifest.py && py $H/mkgroups.py
py $H/h.py setup_ws.py --version v118b --no-build
node tools/replay/harness/decode_all.mjs --list replays/v118b/ladder-list.json --out replays/v118b/inputs/ladder --threads $J
py $H/h.py batch.py --version v118b --jobs $J --stages gen,build,release,validate,summary
# The trace bot (mktrace.py; tools/replay/harness/live_trace_bot.py stops on v118's fight.cc): TB is its directory under
# replays/v118b and the name of its runs (replays/v118b/runs/<TB>).
TB=${2:-}
[ -n "$TB" ] && py $H/h.py direct_batch.py --version v118b --jobs $J --bot replays/v118b/$TB --out $TB
py $H/h.py extract_all.py --version v118b --kinds ladder --threads $J
node tools/replay/extract.mjs replays/v118b/groups --out replays/v118b/analysis --threads $J > replays/v118b/logs/extract-groups.log 2>&1
echo "HARNESS-PASS-DONE $(date -u +%H:%M:%S)"
