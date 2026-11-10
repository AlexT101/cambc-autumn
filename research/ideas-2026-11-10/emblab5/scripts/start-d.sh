#!/bin/bash
# Round D, the replication: the screen's survivors on new games only (estimates from the first D batch on), to
# n_eff 150,000 each. The screen's stage.json is kept as stage-screen.json.
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
L=replays/emblab/r5
python3 - <<'P'
import json, shutil
from pathlib import Path
L = Path('replays/emblab/r5')
st = json.loads((L / 'stage.json').read_text())
assert st['stage'] >= len(st['stages']), 'the screen has not finished'
shutil.copy(L / 'stage.json', L / 'stage-screen.json')
first = len(sorted((L / 'batches').glob('b[0-9][0-9][0-9]')))
json.dump({"stages": [[150000, len(st['alive'])]], "stage": 0, "alive": st['alive'], "from": first, "history": [], "capacity": 330000}, open(L / 'stage.json', 'w'))
(L / 'stop').unlink(missing_ok=True)
print('round D from batch', first, 'with', st['alive'])
P
python3 tools/emblab/efit.py step --lab r5
tmux new -d -s emb5-d 'research/ideas-2026-11-10/emblab5/scripts/run-lab.sh r5 35 80000 40'
