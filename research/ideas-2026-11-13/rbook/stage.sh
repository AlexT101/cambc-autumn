#!/bin/bash
# Builds one book stage and runs every check on it: stage.sh BOT WORK KEYS --opp NAME:REFSET ...   (from the repo root)
#   BOT under bots/variants (a copy of the final host), KEYS from pick_entries.py, the rest are rbuild arguments.
# Results: WORK/stage.out, done-marker WORK/stage.DONE. Pass: verify N/N, bundle <= 4.9 MB, fallback test with no
# invalid read, 100M bench 52/52 identical to chy-525f.
BOT=$1; W=$2; KEYS=$3; shift 3   # PRIO=plain|seeded (rbuild --prio; default plain)
R=research/ideas-2026-11-13/rbook; B=~/tmp-offload/rbook/bench
rm -f $W/stage.DONE
{
  python3 $R/rbuild.py --host variants/$BOT --work $W --prio ${PRIO:-plain} --keys $KEYS "$@" 2>&1 | grep -v '^cell \|^dropped '
  echo "== fallback"; (cd $R && python3 fallbacktest.py --host variants/$BOT --work $W --plain) 2>&1 | tail -8
  echo "== fresh maps"; python3 $R/freshcheck.py $W/book.jsonl ~/tmp-offload/rbook/freshids/part??.json 2>&1 | grep -v "^  SAME"
  python3 tools/fuel/bench.py run variants/$BOT --set wide --jobs 32 --out $B/$BOT-100M.json > $B/$BOT-100M.log 2>&1
  echo "== 100M"; python3 tools/fuel/bench.py compare $B/chy-525f-100M.json $B/$BOT-100M.json 2>&1 | grep -v "^round1\|^turns\|^  "
  python3 tools/fuel/bench.py run variants/$BOT --maps $(cat ~/tmp-offload/rbook/fresh_bench.txt) --fuel 0 --jobs 32 --out $B/$BOT-fresh-0.json > $B/$BOT-fresh-0.log 2>&1
  echo "== fresh real fuel"; python3 tools/fuel/bench.py compare $B/chy-525f-fresh-0.json $B/$BOT-fresh-0.json 2>&1 | grep -v "^round1\|^turns\|^  " | cut -c1-200
} > $W/stage.out 2>&1
touch $W/stage.DONE
