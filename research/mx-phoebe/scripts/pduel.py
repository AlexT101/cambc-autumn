"""First Prism-on-Prism kill (both teams have a Prism): at the kill round minus 10, Focus ratio, max-HP ratio,
allies within 8 of each Prism, side of the fight; and how each of those predicts who survives.

    python3 pduel.py EXTRACT_DIR
"""
import gzip, json, sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def one(d):
    d = Path(d)
    try:
        meta = json.loads((d / 'meta.json').read_text())
        R = json.load(gzip.open(d / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    except Exception:
        return None
    pr = {m['id'] for m in meta['champions'] if m['name'] == 'Prism'}
    ch = R['champions']
    P = {c['team']: c for c in ch if c['id'] in pr}
    if len(P) != 2:
        return None
    for e in ev:
        if e['k'] == 'death' and e['v'] in pr and e.get('by') in pr:
            r = e['r']
            ix = max(0, r - 11)
            V = next(c for c in ch if c['id'] == e['v'])
            K = P[1 - V['team']]
            def allies(c):
                p = (c['x'][ix], c['y'][ix])
                if p[0] is None:
                    return 0
                return sum(1 for o in ch if o['team'] == c['team'] and o is not c and o['alive'][ix] and o['x'][ix] is not None and cheb(p, (o['x'][ix], o['y'][ix])) <= 8)
            return {'r': r, 'kf': K['foc'][ix], 'vf': V['foc'][ix], 'kh': K['maxHp'][ix], 'vh': V['maxHp'][ix],
                    'khp': K['hp'][ix], 'vhp': V['hp'][ix], 'ka': allies(K), 'va': allies(V),
                    'kg': K['gems'][ix], 'vg': V['gems'][ix], 'kgold': K['gold'][ix], 'vgold': V['gold'][ix], 'kear': K['earned'][ix], 'vear': V['earned'][ix], 'kstr': K['str'][ix], 'vstr': V['str'][ix], 'win': meta['result']['winner'] == K['team']}
    return None


if __name__ == '__main__':
    dirs = [str(p.parent) for p in Path(sys.argv[1]).glob('*/meta.json')]
    with ProcessPoolExecutor(16) as ex:
        rs = [r for r in ex.map(one, dirs, chunksize=8) if r]
    n = len(rs)
    print(n, 'first Prism-on-Prism kills; killer team wins', sum(r['win'] for r in rs) / n)
    c = Counter()
    for r in rs:
        c['killer_more_focus'] += r['kf'] > r['vf']
        c['killer_more_maxhp'] += r['kh'] > r['vh']
        c['killer_more_hp'] += r['khp'] > r['vhp']
        c['killer_more_allies'] += r['ka'] > r['va']
        c['killer_fewer_allies'] += r['ka'] < r['va']
        c['killer_more_gems'] += r['kg'] > r['vg']
    for k, v in c.items():
        print(f'{k:22s} {100 * v / n:5.1f}%')
    import statistics as S
    for k in ('kf', 'vf', 'kh', 'vh', 'khp', 'vhp', 'ka', 'va', 'kg', 'vg', 'kgold', 'vgold', 'kear', 'vear', 'kstr', 'vstr', 'r'):
        print(k, round(S.mean(r[k] for r in rs), 1), 'median', S.median(r[k] for r in rs))
