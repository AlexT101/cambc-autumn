#!/bin/bash
# ab.sh CAND NAME FIRST LAST: A/B bots/CAND against variants/astraeus-5b66bde on maps/fresh-FIRST..LAST (own drafts,
# real budget), then scratch/res/NAME.metrics (OOF, cuts, by camp-group bucket), then the batch replays are deleted.
cd /home/ubuntu/cambc-autumn/.claude/worktrees/agent-a257b2d79d7ff4d76
source /home/ubuntu/venv/bin/activate
export PATH=$HOME/.cargo/bin:$PATH CAMBC_SLOTS=86 CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
cand=$1 name=$2
mkdir -p scratch/res
suites=$(seq -f "maps/fresh-%g" "$3" "$4" | paste -sd,)
python tools/ab.py "$cand" variants/astraeus-5b66bde --no-test-draft --suites "$suites" --name "$name" > scratch/res/$name.log 2>&1
dirs=$(ls -d replays/batch-*-ab-$name-fresh-*)
{
    echo "== $name"
    tail -n 6 scratch/res/$name.log
    echo "== oof_bot"
    python tools/fuel/oof_bot.py $dirs 2>&1 | tail -n 60
    echo "== shortcuts"
    python scratch/tools/shortcuts.py $dirs 2>&1 | tail -n 10
    echo "== bymap"
    python scratch/tools/bymap.py replays/ab/$name 2>&1 | tail -n 10
} > scratch/res/$name.metrics
[ -s scratch/res/$name.metrics ] && grep -q "== bymap" scratch/res/$name.metrics && rm -rf $dirs
echo done $name
