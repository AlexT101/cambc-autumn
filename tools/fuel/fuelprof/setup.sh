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
# By turn class too (release builds: a debug_block refund reads as a turn boundary): with DIR/heavy and DIR/oof made
# first, each gets the same file for turns that finished on 88k+ (FASTRUNNER_FUELPROF_HEAVY sets the bound) and for
# out-of-fuel episodes (the turn that ran out with the turns up to the next one that ended in its own round), each
# instance's first two turns left out; DIR/counts-*.txt holds turns and fuel, heavy turns and fuel, episodes and fuel.
# Symbolise each directory on its own. research/fuel-2026-11-10/tools/byfn.py sums a profile by source function.
set -e
cd "$(dirname "$0")/../../fastengine"
mkdir -p runner-prof
cp -r runner/Cargo.toml runner/Cargo.lock runner/build.rs runner/fastrunner runner/src runner/vendor runner/wengine runner-prof/
[ -d runner-prof/target ] || cp -r runner/target runner-prof/target
(cd runner-prof && patch -p1 < ../../fuel/fuelprof/runner.patch && cargo build --release)
