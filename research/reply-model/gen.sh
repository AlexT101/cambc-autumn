#!/bin/bash
# Lab rollouts with the hit log: gen.sh FRAMES OUTPREFIX ROUNDS BOT_OCEAN [extra fastrunner args]
# Plays ocean (BOT_OCEAN) vs itself, vs lab astraeus and astraeus vs it.
set -e
cd /home/ubuntu/cambc-autumn
frames=$1; out=$2; rounds=$3; oc=$4; shift 4
as=bots/variants/lab-astraeus-8c0343f
export FASTRUNNER_LIB=$PWD/tools/fastengine/runner/target-reply/hit/libfastrunner.so FASTRUNNER_ENGINE=wasm FASTRUNNER_MODE=native
for cfg in oo oa ao; do
  case $cfg in oo) a=$oc; b=$oc;; oa) a=$oc; b=$as;; ao) a=$as; b=$oc;; esac
  tools/fastengine/runner/fastrunner scenario $frames --bot-a $a --bot-b $b --rollouts 1 --rounds $rounds \
    --out $out-$cfg.jsonl --lab --hitlog --marks 5,10,30 --jobs 80 --slot-dir .git/cambc-slots --slots 86 "$@" > $out-$cfg.log 2>&1
done
echo finished
