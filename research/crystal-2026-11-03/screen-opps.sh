#!/bin/bash
# Frozen astraeus against each candidate panel opponent: ladder, gen, gen-s1, own drafts.
cd ~/cambc-autumn
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
for o in "$@"; do
  echo "=== $o $(date -u +%H:%M)"
  python3 tools/ab.py variants/astraeus-10b2313 $o --no-test-draft --name opp-ast296-vs-${o//\//-} 2>&1 | grep -E "^CAND|^  (ladder|gen|fresh/gen-s1) |Out-of"
done
