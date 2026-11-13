"""First Prism-on-Prism kills: who landed the first Prism spell on the other Prism (within the 20 rounds before the
kill), whether it was a stun, and how often the richer (more Focus 10 rounds before) Prism won, split by first cast.

    python3 firstcast.py EXTRACT_DIR
"""
import gzip, json, sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path


def one(d):
    d = Path(d)
    try:
        meta = json.loads((d / 'meta.json').read_text())
        R = json.load(gzip.open(d / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    except Exception:
        return None
    pr = {m['id'] for m in meta['champions'] if m['name'] == 'Prism'}
    if len(pr) != 2:
        return None
    ch = {c['id']: c for c in R['champions']}
    kill = next((e for e in ev if e['k'] == 'death' and e['v'] in pr and e.get('by') in pr), None)
    if not kill:
        return None
    K, V, r = kill['by'], kill['v'], kill['r']
    ix = max(0, r - 11)
    richer_k = ch[K]['foc'][ix] > ch[V]['foc'][ix]
    first = None
    for e in ev:
        if e['r'] < r - 20 or e['r'] > r:
            continue
        if e['k'] == 'cast' and e['a'] in pr and 'dmg' in e:
            other = (pr - {e['a']}).pop()
            if any(t == other for t, _ in e['dmg']):
                first = (e['a'] == K, other in e.get('stun', []), e['r'])
                break
    return richer_k, first


if __name__ == '__main__':
    dirs = [str(p.parent) for p in Path(sys.argv[1]).glob('*/meta.json')]
    with ProcessPoolExecutor(16) as ex:
        rs = [r for r in ex.map(one, dirs, chunksize=8) if r]
    c = Counter()
    for richer_k, first in rs:
        f = 'none' if first is None else ('killer first' if first[0] else 'victim first') + (' stun' if first[1] else ' dmg')
        c[(f, richer_k)] += 1
        c[f] += 1
    n = len(rs)
    print(n, 'duels')
    for f in ('killer first stun', 'killer first dmg', 'victim first stun', 'victim first dmg', 'none'):
        print(f'{f:20s} {c[f]:4d} ({100 * c[f] / n:4.1f}%)  killer richer in {100 * c[(f, True)] / max(c[f], 1):5.1f}%')
