#!/bin/bash
# bench.sh BOT [SETS]: real-budget (and 100M with R suffix absent) benches vs oc-retest-clean. Out: replays/fuel/ptw/BOT-<set>.json
MAIN=/home/ubuntu/cambc-autumn; cd $MAIN; source /home/ubuntu/venv/bin/activate
export CAMBC_BIN=$MAIN/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
D=$MAIN/replays/fuel/ptw; G=$D/g; mkdir -p $G; F=$MAIN/replays/fuel/fc7
b=$1; shift; n=${b##*/}
OPP=variants/oc-retest-clean
sets=${*:-poolR bigR heavyR}
for s in $sets; do
  case $s in
    def) a="--jobs 16" ;;
    pool) a="--opp $OPP --maps $(cat $F/poolset.txt) --jobs 86" ;;
    poolR) a="--fuel 0 --opp $OPP --maps $(cat $F/poolset.txt) --jobs 86" ;;
    bigR) a="--fuel 0 --opp $OPP --maps $(cat $F/bigset.txt) --jobs 32" ;;
    heavyR) a="--fuel 0 --opp $OPP --maps $(cat $F/heavyset.txt) --jobs 50" ;;
    defR) a="--fuel 0 --jobs 16" ;;
  esac
  python3 tools/fuel/bench.py run $b --per-map $a --out $D/$n-$s.json --games $G/$n-$s > $D/$n-$s.log 2>&1 &
done
wait
for s in $sets; do echo "$n $s: $(tail -n 1 $D/$n-$s.log | cut -c1-260)"; done
