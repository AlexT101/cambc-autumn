#!/bin/sh
set +e
runtime=/Users/yufan/Desktop/Development/CambridgeBattlecode2026/willow-upstream-development/provenance/willow-astraeus-clock-recovery-20261024-v1/workspace
cli=/Users/yufan/Desktop/Development/CambridgeBattlecode2026/current-autumn/tools/runtime/cambc-3.0.5/cambc
cd "$runtime" || exit 125
run_one() {
  name="$1"
  manifest="$2"
  nice -n 19 "$cli" run-batch "$manifest" --jobs 1 --release --fuel-quantum 100000 --json --color never > "$name.stdout.log" 2> "$name.stderr.log"
  status=$?
  printf '%s\n' "$status" > "$name.exit.txt"
  if [ "$status" -ne 0 ]; then exit "$status"; fi
}
run_one deadline-vs-f475 /Users/yufan/Desktop/Development/CambridgeBattlecode2026/willow-upstream-development/provenance/khaos-v34-ladder-intake-20261024-v1/deadline-bound-published-comparison/candidate-vs-f475.v2.pending.manifest || exit $?
run_one deadline-vs-v33 /Users/yufan/Desktop/Development/CambridgeBattlecode2026/willow-upstream-development/provenance/khaos-v34-ladder-intake-20261024-v1/deadline-bound-published-comparison/candidate-vs-v33.v2.pending.manifest || exit $?
run_one v48-vs-v33 /Users/yufan/Desktop/Development/CambridgeBattlecode2026/willow-upstream-development/provenance/khaos-v34-ladder-intake-20261024-v1/deadline-bound-published-comparison/v48-vs-v33.v2.pending.manifest || exit $?
exit 0
