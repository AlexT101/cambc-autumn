"""Per champion type time budget (rounds <= LIMIT): dead, recall, tribute, hold, camp-hit, champ-fight, move, idle, spawn."""
import sys, json, gzip, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 400
def one(d):
    d = Path(d)
    try:
        meta = json.loads((d/'meta.json').read_text()); R = json.load(gzip.open(d/'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d/'events.jsonl.gz','rt')]
        mp = json.loads((d/meta['mapFile']).read_text())
    except Exception as ex: return None
    name = {c['id']: c['name'] for c in meta['champions']}
    team = {c['id']: c['team'] for c in meta['champions']}
    tiles = set(tuple(t) for g in mp['groups'] for t in g['tiles'])
    sp = mp['spawn']
    r0 = R['round'][0]
    camp = set(); fight = set(); recall = set(); trib = set()
    for e in ev:
        k = e.get('k'); r = e['r']
        if k in ('attack','cast') and 'a' in e:
            if 'camp' in e or e.get('cdmg'): camp.add((e['a'], r))
            if e.get('dmg') and any(team.get(h[0]) is not None and team[h[0]] != team[e['a']] for h in e['dmg']): fight.add((e['a'], r))
            if e.get('tgt') in team and team[e['tgt']] != team[e['a']]: fight.add((e['a'], r))
    out = collections.defaultdict(collections.Counter)
    for c in R['champions']:
        cid = c['id']; nm = name[cid]; s = sp[c['team']]
        for i, r in enumerate(R['round']):
            if r > LIMIT: break
            if not c['alive'][i]: cls = 'dead'
            elif c['chan'][i] == 1 and (c['chanT'][i] or 0) <= 3: cls = 'recall'
            elif c['chan'][i] == 2: cls = 'tribute'
            elif (cid, r) in fight: cls = 'fight'
            elif (cid, r) in camp: cls = 'camp'
            elif (c['x'][i], c['y'][i]) in tiles: cls = 'ontile'
            elif s['minX'] <= c['x'][i] <= s['maxX'] and s['minY'] <= c['y'][i] <= s['maxY']: cls = 'spawn'
            elif i > 0 and (c['x'][i], c['y'][i]) != (c['x'][i-1], c['y'][i-1]): cls = 'move'
            else: cls = 'idle'
            out[nm][cls] += 1
    return out
if __name__ == '__main__':
    dirs = [p for p in Path(sys.argv[1]).iterdir() if (p/'meta.json').exists()]
    tot = collections.defaultdict(collections.Counter)
    with ProcessPoolExecutor(24) as ex:
        for o in ex.map(one, dirs, chunksize=8):
            if not o: continue
            for k, v in o.items(): tot[k].update(v)
    keys = sorted({k for v in tot.values() for k in v})
    print('type'.ljust(14), ' '.join(k.rjust(7) for k in keys))
    for nm, v in sorted(tot.items(), key=lambda t: -sum(t[1].values())):
        n = sum(v.values())
        print(nm.ljust(14), ' '.join(f"{100*v[k]/n:7.1f}" for k in keys), n)
