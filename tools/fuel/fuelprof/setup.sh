#!/bin/bash
# Fuel profile by charge site (exact wasmtime fuel, native fastrunner), in a copy of the runner so the main runner,
# its cache keys and everyone's games are untouched. Profiled games' totals match the bot's fuel; the SDK's
# debug_block refunds are not subtracted (query.py drops printf frames).
#   tools/fuel/fuelprof/setup.sh                                     # once: tools/fastengine/runner-prof, built
#   CXXFLAGS=-g cambc build bots/variants/X                           # -g changes code bytes in a few functions only
#   FASTRUNNER_FUELPROF=DIR FASTRUNNER_MODE=native tools/fastengine/runner-prof/fastrunner run A B --map M -o DIR/g
#   py tools/fuel/fuelprof/symbolise.py bots/variants/X DIR/p.json DIR && py tools/fuel/fuelprof/query.py DIR/p.json [FILE]
# Each process writes DIR/prof-<pid>-<lib>.bin at exit (counts per site for every bot it ran); symbolise.py keeps the
# files whose code matches BOTDIR's bot-injected.wasm. Inline frames stop at real calls, so totals are per line, not per
# call tree. Host calls are counted at their call site; deltas outside (0, 1M) (turn boundaries, refunds) are dropped.
set -e
cd "$(dirname "$0")/../../fastengine"
mkdir -p runner-prof
cp -r runner/Cargo.toml runner/Cargo.lock runner/build.rs runner/fastrunner runner/src runner/vendor runner/wengine runner-prof/
[ -d runner-prof/target ] || cp -r runner/target runner-prof/target
(cd runner-prof && patch -p1 < ../../fuel/fuelprof/runner.patch && cargo build --release)
