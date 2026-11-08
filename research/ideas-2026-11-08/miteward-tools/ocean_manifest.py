"""Manifests for our side of the r2 games against Mite (the scrims), tagged with our live version."""
import json, sys
from pathlib import Path
W = Path.home() / 'tmp-offload/miteward'
ver = {}
for l in open('/home/ubuntu/cambc-autumn/research/ladder-scrims-2026-11-06/data/games.jsonl'):
    g = json.loads(l)
    if g.get('match'): ver[g['match']] = g.get('version')
out = []
for o in json.load(open(W / 'r2man/all.json')):
    if o['opponent'] != 'stellar best girl': continue
    o = dict(o, side=1 - o['side'], bot='ocean', opponent='Mite', version=ver.get(o['match']))
    out.append(o)
k = 8
(W / 'ocman').mkdir(exist_ok=True)
for i in range(k): (W / 'ocman' / f'm{i}.json').write_text(json.dumps(out[i::k]))
json.dump(out, open(W / 'ocman/all.json', 'w'))
import collections; print(len(out), collections.Counter(o['version'] for o in out))
