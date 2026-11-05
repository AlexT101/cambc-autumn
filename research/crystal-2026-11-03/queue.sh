#!/bin/bash
# Fixed-sample A/B against REF (default variants/astraeus-10b2313): ladder, gen, gen-s1, fresh-92001..92100 (~52k games).
cd ~/cambc-autumn
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
REF=${REF:-variants/astraeus-10b2313}
SU="ladder,gen,fresh,$(for s in $(seq 92001 92100); do printf "maps/suites/fresh/fresh-$s,"; done)"
for v in "$@"; do
  echo "=== $v $(date -u +%H:%M)"
  python3 tools/ab.py variants/$v $REF --no-test-draft --suites ${SU%,} --name x-$v-vs-$(basename $REF) 2>&1 | grep -E "^CAND|^  (ladder|gen|fresh/gen-s1) |Out-of"
done
