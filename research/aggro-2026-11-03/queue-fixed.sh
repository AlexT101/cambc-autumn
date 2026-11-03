#!/bin/bash
# Fixed-sample screen: ladder, gen, gen-s1 and the 100 fresh suites 92001-92100 (~52k games), no early stop.
cd ~/cambc-autumn
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
SU="ladder,gen,fresh,$(for s in $(seq 92001 92100); do printf "maps/fresh-$s,"; done)"
for v in "$@"; do
  echo "=== $v $(date -u +%H:%M)"
  python3 tools/ab.py variants/$v variants/astraeus-38aa25c --no-test-draft --suites ${SU%,} --name fix-$v-vs-ast294 2>&1 | grep -v running | grep -v "^  fresh-9"
done
