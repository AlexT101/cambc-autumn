"""Deaths to an enemy Prism: how far the killer was when the victim's current sighting of it began, and how many
rounds it had seen it. Usage: py ambush.py DIR"""
import gzip, json, sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

def cheb(a, b): return max(abs(a[0]-b[0]), abs(a[1]-b[1]))

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
        if e['k'] != 'death' or e.get('linked') or names.get(e.get('by')) != 'Prism': continue
        v, k, r = e['v'], e['by'], e['r']
        if v not in idx or k not in idx: continue
        cv, ck = ch[idx[v]], ch[idx[k]]
        i = rix.get(r - 1)
        if i is None: continue
        # walk back while the victim sees the killer
        j = i; seen = 0
        while j >= 0 and k in (cv['sees'][j] or []) and seen < 40:
            j -= 1; seen += 1
        if seen == 0:
            out.append((names[v], 'unseen', None)); continue
        j0 = j + 1
        if cv['x'][j0] is None or ck['x'][j0] is None:
            out.append((names[v], seen, None)); continue
        dd = cheb((cv['x'][j0], cv['y'][j0]), (ck['x'][j0], ck['y'][j0]))
        out.append((names[v], seen, dd))
    return out

def main():
    root = Path(sys.argv[1])
    dirs = [p for p in root.iterdir() if (p/'meta.json').exists()]
    D = defaultdict(Counter); S = defaultdict(Counter)
    with ProcessPoolExecutor(24) as ex:
        for o in ex.map(game, dirs, chunksize=4):
            if not o: continue
            for n, seen, dd in o:
                D[n]['unseen' if seen == 'unseen' else ('?' if dd is None else ('<=4' if dd <= 4 else '5-6' if dd <= 6 else '7-8'))] += 1
                if seen != 'unseen':
                    S[n]['1' if seen <= 1 else '2-3' if seen <= 3 else '4-8' if seen <= 8 else '9+'] += 1
    for n in sorted(D, key=lambda x: -sum(D[x].values())):
        t = sum(D[n].values())
        print(f'{n:13s} {t:5d} first-sight dist:', ' '.join(f'{k}:{100*v/t:.0f}%' for k, v in sorted(D[n].items())),
              '| rounds seen before death:', ' '.join(f'{k}:{100*v/t:.0f}%' for k, v in sorted(S[n].items())))

if __name__ == '__main__':
    main()
