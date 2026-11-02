#!/bin/bash
# Self-play baseline: the v66 trace bot (level 2 over the whole game) against itself, unbounded fuel, on 24 ladder maps.
# Each of 12 slots has its own bot copy (concurrent builds of one directory clash).
set -u
cd "$(dirname "$0")/../../../.."
D=replays/v66-analysis/simcal
MAPS=(02stalactites 00rushbait_v2 02guardians 02tangle 00elkring 02the_pack 00road_of_riches 00ribs adgato_gemcombat1 01starfish 01fracture 00corners 01boss_battle 02crossing 02geodes 00swirl 00breadcrumbs 00ambush 00interlock 00rows adgato_gemcombat5 00great_wall 00gemfight 00crater)
SLOTS=12
for s in $(seq 0 $((SLOTS-1))); do
  B=$D/bots/sp$s
  [ -d $B/src ] || { mkdir -p $B && cp -r tools/replay/harness/trace-bot-v66/src $B/ && sed -i 's/ht_trace_level = 1;/ht_trace_level = 2;/' $B/src/trace.cc; }
done
run_slot() {
  s=$1; shift
  for m in "$@"; do
    out=$D/selfplay/$m
    ls $out/*.repl26a >/dev/null 2>&1 && continue
    mkdir -p $out
    cambc run $D/bots/sp$s $D/bots/sp$s --map $m --fuel 100000000 --log-limit 2000000000 -o $out > $out/run.log 2>&1
  done
}
for s in $(seq 0 $((SLOTS-1))); do
  run_slot $s ${MAPS[$s]} ${MAPS[$((s+SLOTS))]} &
done
wait
echo done
