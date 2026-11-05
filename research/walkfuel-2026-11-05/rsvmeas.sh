#!/bin/bash
# rsvmeas.sh SRCBOT TAG: the reserve study's RSV instrumentation (research/rsvfuel-2026-11-05/instrument.py) on a copy of
# bots/SRCBOT, against 5b66bde at the real budget on maps/gen and the ladder maps (768 games), parsed into
# wfscratch/rsv-TAG.pkl (rsv_an.py); the batches are deleted.
. /home/ubuntu/cambc-autumn/.claude/worktrees/agent-ab4ebc4c0ecb8a725/wfscratch/env.sh
src=$1 tag=$2
v=bots/variants/astraeus-rsv-$tag
rsync -a --delete --exclude .cambc --exclude build --exclude target --exclude .cache --exclude compile_commands.json bots/$src/ $v/
python3 research/rsvfuel-2026-11-05/instrument.py $v/src > wfscratch/rsv-$tag.inst 2>&1 || exit 1
: > wfscratch/rsv-$tag.dirs
for d in maps/gen maps; do
    python tools/run_batched.py variants/astraeus-rsv-$tag variants/astraeus-5b66bde --maps-dir $d > wfscratch/rsv-$tag.$(basename $d).log 2>&1
    grep -o "replays/batch-[0-9-]*" wfscratch/rsv-$tag.$(basename $d).log | tail -n 1 >> wfscratch/rsv-$tag.dirs
done
python3 research/rsvfuel-2026-11-05/rsv_an.py wfscratch/rsv-$tag.pkl $(cat wfscratch/rsv-$tag.dirs) > wfscratch/rsv-$tag.an 2>&1
if [ -s wfscratch/rsv-$tag.pkl ]; then
    for d in $(cat wfscratch/rsv-$tag.dirs); do rm -rf "./$d"; done
fi
echo done > wfscratch/rsv-$tag.done
