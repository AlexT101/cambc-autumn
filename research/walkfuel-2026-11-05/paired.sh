#!/bin/bash
# paired.sh SRCBOT TAG [FUEL]: a WLK-instrumented copy of bots/SRCBOT (variants/astraeus-wi-TAG) against 5b66bde on
# maps/wf-prof (64 fresh-192300 maps, both sides) at FUEL (default 100M), parsed into wfscratch/TAG.pkl; replays deleted.
. /home/ubuntu/cambc-autumn/.claude/worktrees/agent-ab4ebc4c0ecb8a725/wfscratch/env.sh
src=$1 tag=$2 fuel=${3:-100000000}
rsync -a --delete --exclude .cambc --exclude build --exclude target --exclude .cache --exclude compile_commands.json bots/$src/ bots/variants/astraeus-wi-$tag/
python3 research/walkfuel-2026-11-05/winst.py bots/variants/astraeus-wi-$tag/src > wfscratch/$tag.inst 2>&1 || exit 1
python tools/run_batched.py variants/astraeus-wi-$tag variants/astraeus-5b66bde --maps-dir maps/wf-prof --fuel $fuel > wfscratch/$tag.log 2>&1
d=$(grep -o "replays/batch-[0-9-]*" wfscratch/$tag.log | tail -n 1)
python3 research/walkfuel-2026-11-05/wan.py $d --pkl wfscratch/$tag.pkl > wfscratch/$tag.txt 2>&1
[ -s wfscratch/$tag.pkl ] && rm -rf "./$d"
echo done > wfscratch/$tag.done
