#!/bin/sh
set +e
cd /Users/yufan/Desktop/Development/CambridgeBattlecode2026/willow-upstream-development/provenance/willow-astraeus-clock-recovery-20261024-v1/workspace || exit 125
nice -n 19 /Users/yufan/Desktop/Development/CambridgeBattlecode2026/current-autumn/tools/runtime/cambc-3.0.5/cambc run-batch /Users/yufan/Desktop/Development/CambridgeBattlecode2026/willow-upstream-development/provenance/khaos-v34-ladder-intake-20261024-v1/deadline-bound-4-v2.pending.manifest --jobs 1 --release --fuel-quantum 100000 --json --color never > /Users/yufan/Desktop/Development/CambridgeBattlecode2026/willow-upstream-development/provenance/khaos-v34-ladder-intake-20261024-v1/logs-deadline-bound-4.stdout.log 2> /Users/yufan/Desktop/Development/CambridgeBattlecode2026/willow-upstream-development/provenance/khaos-v34-ladder-intake-20261024-v1/logs-deadline-bound-4.stderr.log
status=$?
printf '%s\n' "$status" > /Users/yufan/Desktop/Development/CambridgeBattlecode2026/willow-upstream-development/provenance/khaos-v34-ladder-intake-20261024-v1/logs-deadline-bound-4.exit.txt
exit "$status"
