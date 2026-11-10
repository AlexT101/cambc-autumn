#!/bin/bash
# After CAL and its gate: the full registry, the screen's stages and first allocation, then the run (in tmux).
# Stages: cumulative n_eff an edit and how many stay, the six-step halving that matched the plan's three rounds for
# 22% fewer appearances in simulation (research/ideas-2026-11-10/emblab5/simsched2.py).
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
L=replays/emblab/r5
cp $L/edits-full.json $L/edits.json
python3 - <<'P'
import json
L = 'replays/emblab/r5'
c = json.load(open(f'{L}/config.json'))
c.update(auto=[], none_share=0.08, solo_share=0.12)
json.dump(c, open(f'{L}/config.json', 'w'), indent=1)
n = len(json.load(open(f'{L}/edits.json'))['edits'])
keep = [round(n * k / 330) for k in (250, 180, 120, 75, 45)] + [20]
json.dump({"stages": [[t, k] for t, k in zip((6000, 12000, 20000, 32000, 48000, 80000), keep)], "stage": 0, "alive": list(range(1, n + 1)),
           "history": [], "capacity": 330000}, open(f'{L}/stage.json', 'w'))
print(n, 'edits; keeps', keep)
P
python3 tools/emblab/efit.py step --lab r5
tmux new -d -s emb5-screen 'research/ideas-2026-11-10/emblab5/scripts/run-lab.sh r5 35 80000 80'
