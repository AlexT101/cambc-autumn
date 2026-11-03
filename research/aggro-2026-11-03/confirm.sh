#!/bin/bash
# Confirmation on unused seeds: fresh-91001..91020 and fresh-94001..94080 (~51k games), no early stop.
cd ~/cambc-autumn
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
SU="$(for s in $(seq 91001 91020) $(seq 94001 94080); do printf "maps/fresh-$s,"; done)"
for v in "$@"; do
  echo "=== $v $(date -u +%H:%M)"
  python3 tools/ab.py variants/$v variants/astraeus-38aa25c --no-test-draft --suites ${SU%,} --name confirm-$v-vs-ast294 2>&1 | grep -v running | grep -v "^  fresh-9"
done
