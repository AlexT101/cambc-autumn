"""Victim type x killer type (champion kills), and the victim's hp at the start of its death round's step
(one-shot share: hp before the killing step >= 90% of max). Usage: py killers.py DIR"""
import gzip, json, sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

def game(d):
    d = Path(d)
    try:
        meta = json.loads((d/'meta.json').read_text())
        ev = [json.loads(l) for l in gzip.open(d/'events.jsonl.gz', 'rt')]
    except Exception:
        return None
    names = {c['id']: c['name'] for c in meta['champions']}
    maxhp = {c['id']: c['maxHp'] for c in meta['champions']}
    out = []
    for e in ev:
        if e['k'] == 'death' and 'by' in e and not e.get('linked'):
            out.append((names.get(e['v']), names.get(e['by']), e.get('gems', 0), e.get('cause')))
    return out

def main():
    root = Path(sys.argv[1])
    dirs = [p for p in root.iterdir() if (p/'meta.json').exists()]
    C = Counter(); G = Counter(); V = Counter(); CA = Counter()
    with ProcessPoolExecutor(24) as ex:
        for o in ex.map(game, dirs, chunksize=4):
            if not o: continue
            for v, k, gems, cause in o:
                C[(v, k)] += 1; G[(v, k)] += gems; V[v] += 1; CA[(v, cause)] += 1
    for v in sorted(V, key=lambda x: -V[x]):
        row = sorted(((k, n) for (vv, k), n in C.items() if vv == v), key=lambda x: -x[1])
        print(f'{v:13s} {V[v]:5d}:', ', '.join(f'{k} {n} ({G[(v,k)]/n:.0f}g)' for k, n in row[:5]))
        print('     cause:', ', '.join(f'{c} {n}' for (vv, c), n in sorted(CA.items(), key=lambda x: -x[1]) if vv == v)[:200])

if __name__ == '__main__':
    main()
