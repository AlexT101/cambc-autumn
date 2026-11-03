#!/bin/bash
cd ~/cambc-autumn
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
for v in "$@"; do
  echo "=== $v"
  python3 tools/ab.py variants/$v variants/astraeus-38aa25c --no-test-draft --suites $SUITES --sprt --sprt-stop low --name alext-$v-vs-ast294 2>&1 | grep -v running
done
