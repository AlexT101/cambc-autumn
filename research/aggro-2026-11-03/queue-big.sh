#!/bin/bash
# Big screen: ladder, gen, gen-s1 and the 40 fresh suites 92001-92040; SPRT 0.50 vs 0.51, either way.
cd ~/cambc-autumn
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
SU="ladder,gen,fresh,$(for s in $(seq 92001 92040); do printf "maps/suites/fresh/fresh-$s,"; done)"
for v in "$@"; do
  echo "=== $v"
  python3 tools/ab.py variants/$v variants/astraeus-38aa25c --no-test-draft --suites ${SU%,} --sprt 0.50,0.51 --sprt-stop both --name big-$v-vs-ast294 2>&1 | grep -v running
done
