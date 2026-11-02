#!/usr/bin/env bash
# Profile `cambc run` games with samply (needs perf_event_paranoid <= 1) and time them unprofiled.
#   tools/fastengine/profile_games.sh OUTDIR "botA botB map" ["botA botB map" ...]
# Writes OUTDIR/<n>.json.gz (+ .syms.json), OUTDIR/<n>.time (3 unprofiled wall times), OUTDIR/<n>/ replays.
set -uo pipefail
out=$1; shift
mkdir -p "$out"
export CAMBC_WASMTIME_CACHE=${CAMBC_WASMTIME_CACHE:-$(realpath "$(git rev-parse --git-common-dir)")/cambc-wasmtime} RAYON_NUM_THREADS=1 NO_COLOR=1
i=0
for spec in "$@"; do
  read -r a b map <<<"$spec"
  i=$((i+1)); name="$i-$(basename "$a")-$(basename "$b")-$(basename "$map" .map26a)"
  cambc run "bots/$a" "bots/$b" --map "$map" --release -o "$out/$name" >/dev/null 2>&1   # build + warm cache
  : > "$out/$name.time"
  for r in 1 2 3; do
    s=$(date +%s.%N); cambc run "bots/$a" "bots/$b" --map "$map" --release -o "$out/$name" > "$out/$name.log" 2>&1; e=$(date +%s.%N)
    python3 -c "print(round($e - $s, 3))" >> "$out/$name.time"
  done
  samply record -r 4000 --save-only --unstable-presymbolicate -o "$out/$name.json.gz" -- \
    cambc run "bots/$a" "bots/$b" --map "$map" --release -o "$out/$name" >/dev/null 2>&1
  echo "$name: $(tr '\n' ' ' < "$out/$name.time") $(grep -E 'finished' "$out/$name.log")"
done
