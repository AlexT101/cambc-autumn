"""Manifests (tools/fish/extract.mjs format) for Mite's side of its r2-era capture.db games (r2list.tsv)."""
import json, hashlib, sys
from pathlib import Path
W = Path.home() / 'tmp-offload/miteward'
rows = [l.rstrip('\n').split('\t') for l in open(W / 'r2list.tsv')]
out = []
for mid, created, kind, mp, na, nb, ra, pa, pb, rp in rows:
    f = W / 'repl' / f'{mid}.repl26a'
    if not f.exists() or f.stat().st_size == 0: continue
    side = 0 if na == 'Mite' else 1
    d = hashlib.sha256(f.read_bytes()).hexdigest()
    win = (ra == 'win') == (side == 0)
    out.append(dict(sha256=d, file=str(f), map=mp, side=side, group=mid, match=mid, opponent=nb if side == 0 else na,
                    bot='Mite', split='all', kind=kind, created=created, mite_won=win))
seen = set(); uniq = [o for o in out if not (o['sha256'] in seen or seen.add(o['sha256']))]
k = int(sys.argv[1]) if len(sys.argv) > 1 else 8
(W / 'r2man').mkdir(exist_ok=True)
for i in range(k):
    (W / 'r2man' / f'm{i}.json').write_text(json.dumps(uniq[i::k]))
json.dump(uniq, open(W / 'r2man' / 'all.json', 'w'))
print(len(uniq))
