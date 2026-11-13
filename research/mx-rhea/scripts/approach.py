"""For deaths to an enemy Prism: Chebyshev distance victim-killer at the end of rounds r-1..r-6, and whether the
victim moved toward or away. Usage: py approach.py DIR [VictimName]"""
import gzip, json, sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

def cheb(a, b): return max(abs(a[0]-b[0]), abs(a[1]-b[1]))
WHO = sys.argv[2] if len(sys.argv) > 2 else 'Cassi'

def game(d):
    d = Path(d)
    try:
        meta = json.loads((d/'meta.json').read_text())
        R = json.load(gzip.open(d/'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d/'events.jsonl.gz', 'rt')]
    except Exception:
        return None
    names = {c['id']: c['name'] for c in meta['champions']}
    ch = R['champions']; idx = {c['id']: i for i, c in enumerate(ch)}
    rix = {r: i for i, r in enumerate(R['round'])}
    out = []
    for e in ev:
        if e['k'] != 'death' or e.get('linked') or names.get(e.get('by')) != 'Prism' or names.get(e['v']) != WHO: continue
        cv, ck = ch[idx[e['v']]], ch[idx[e['by']]]
        ds = []
        for back in range(1, 7):
            i = rix.get(e['r'] - back)
            if i is None or cv['x'][i] is None or ck['x'][i] is None: ds.append(None); continue
            ds.append(cheb((cv['x'][i], cv['y'][i]), (ck['x'][i], ck['y'][i])))
        hp = []
        for back in range(1, 4):
            i = rix.get(e['r'] - back)
            hp.append(None if i is None else round(cv['hp'][i] / max(1, cv['maxHp'][i]), 1))
        out.append((tuple(ds), tuple(hp)))
    return out

def main():
    root = Path(sys.argv[1])
    dirs = [p for p in root.iterdir() if (p/'meta.json').exists()]
    pat = Counter(); d1 = Counter(); hp1 = Counter(); n = 0
    with ProcessPoolExecutor(24) as ex:
        for o in ex.map(game, dirs, chunksize=4):
            if not o: continue
            for ds, hp in o:
                n += 1
                d1[ds[0]] += 1
                hp1[hp[0]] += 1
                pat[ds[:4]] += 1
    print(WHO, 'deaths to Prism', n)
    print('dist at end of r-1:', sorted(d1.items(), key=lambda x: (x[0] is None, x[0])))
    print('hp frac at end of r-1:', sorted(hp1.items(), key=lambda x: (x[0] is None, x[0])))
    print('top distance paths (r-1, r-2, r-3, r-4):')
    for k, v in pat.most_common(15): print('  ', k, v)

if __name__ == '__main__':
    main()
