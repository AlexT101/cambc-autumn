"""One game's opening for team A: every 5 rounds each champion's tile, hp, gems, gold, D branch/farm group.
py opening.py EXTRACT_DIR GAMEID [HI]"""
import gzip, json, sys, zipfile, os
from pathlib import Path
d = Path(sys.argv[1]) / sys.argv[2]
HI = int(sys.argv[3]) if len(sys.argv) > 3 else 150
meta = json.loads((d / 'meta.json').read_text())
R = json.load(gzip.open(d / 'rounds.json.gz'))
mp = json.load(open(os.path.join(d, meta['mapFile'])))
z = zipfile.ZipFile(meta['source'])
br = {}
for line in z.read('team-a.stdout').decode(errors='replace').splitlines():
    if line.startswith('D '):
        p = line.split()
        br[(int(p[1]), int(p[2]))] = (p[3], p[4], p[5])
names = {int(c['id']): c['name'][:6] for c in meta['champions']}
print('map', meta['map']['name'], 'spawn', mp['spawn'][0], 'result', meta['result'])
cen = {}
for g in mp['groups']:
    t = g['tiles']
    cen[g['id']] = (round(sum(x for x, _ in t) / len(t)), round(sum(y for _, y in t) / len(t)),
                    '/'.join(sorted(set(x[:3] for x in g['types']))), g['gems'], g['gold'])
used = set()
for r in range(1, HI, 5):
    i = r - 1
    row = []
    for c in R['champions']:
        if int(c['team']) != 0:
            continue
        cid = int(c['id'])
        b = br.get((r, cid), ('?', '?', '?'))
        if b[1].lstrip('-').isdigit() and int(b[1]) >= 0:
            used.add(int(b[1]))
        row.append(f"{names[cid]}({c['x'][i]},{c['y'][i]}) hp{int(c['hp'][i])} g{c['gems'][i]} au{int(c['gold'][i])} {b[0]}{b[1]}")
    print(r, ' | '.join(row))
for g in sorted(used):
    print('group', g, cen.get(g))
