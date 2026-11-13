"""Deaths to an enemy champion: did the victim see its killer in the 3 rounds before (its own `sees`), and did any
teammate? The share where only a teammate saw it is what shared sightings could have told the victim.
py intel.py ANALYSIS_DIR"""
import gzip, json, sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
def one(d):
    try:
        meta = json.loads((d / 'meta.json').read_text())
        R = json.load(gzip.open(d / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    except Exception:
        return []
    C = R['champions']; idx = {c['id']: i for i, c in enumerate(C)}; team = {c['id']: c['team'] for c in C}
    name = {c['id']: c['name'] for c in meta['champions']}
    rid = {r: i for i, r in enumerate(R['round'])}
    out = []
    for e in ev:
        if e['k'] != 'death' or e.get('linked') or 'by' not in e or e['by'] is None: continue
        v, k = e['v'], e['by']
        if team.get(k) == team.get(v): continue
        i = rid.get(e['r'])
        if i is None: continue
        rng = range(max(0, i - 3), i + 1)
        own = any(k in (C[idx[v]]['sees'][j] or []) for j in rng)
        mate = any(k in (c['sees'][j] or []) for c in C if c['team'] == team[v] and c['id'] != v for j in rng)
        out.append((name[k], own, mate))
    return out
if __name__ == '__main__':
    root = Path(sys.argv[1]); dirs = [p for p in root.iterdir() if (p / 'meta.json').exists()]
    rows = []
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(one, dirs, chunksize=16): rows += r
    for who in ('Prism', None):
        S = [r for r in rows if who is None or r[0] == who]
        c = Counter((r[1], r[2]) for r in S)
        print(f"killer {who or 'any'}: {len(S)} kills; victim saw killer in r-3..r: {sum(v for (o,m),v in c.items() if o)}; "
              f"only a teammate saw it: {c[(False, True)]} ({100*c[(False,True)]/len(S):.1f}%); nobody: {c[(False, False)]} ({100*c[(False,False)]/len(S):.1f}%)")
