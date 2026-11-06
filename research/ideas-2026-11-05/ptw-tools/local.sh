#!/bin/bash
# local.sh BATCH_DIR TAG N : extract N replays of an ab batch and run b2b.py (cand = bot 1 = "us")
S=$(dirname "$(readlink -f "$0")")
B=$1; T=$2; N=${3:-1000}
cd /home/ubuntu/cambc-autumn
O=/home/ubuntu/tmp-offload/ptw/ex-$T; mkdir -p $O
find $B -name "*.repl26a" | sort | head -n $N > $O/files.txt
node tools/replay/extract.mjs $(cat $O/files.txt) --out $O --threads 16 > $O/extract.log 2>&1
python3 - "$O" "$T" <<'PY'
import json, sys, re
from pathlib import Path
O, T = Path(sys.argv[1]), sys.argv[2]
idx = json.load(open(O / 'index.json'))['games']
with open(O / 'games.jsonl', 'w') as f:
    for g in idx:
        m = re.search(r'-(12|21)\.repl26a$', g['source'])
        if not m or not g.get('ok'): continue
        f.write(json.dumps({'dir': str(O / g['dir']), 'us': 0 if m[1] == '12' else 1, 'tag': T}) + '\n')
PY
python3 $S/b2b.py $O $O/games.jsonl
