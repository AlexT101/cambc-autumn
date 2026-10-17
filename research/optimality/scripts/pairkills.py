# Isolated 1v1 exchanges ending in a kill: did the killer land the first hit of the exchange?
# Exchange = damage between a and b with no gap > 4 rounds; isolated = no third champion damaged or
# was damaged by either in the exchange window.
import json, gzip, os, sys, collections
from concurrent.futures import ProcessPoolExecutor
ROOT = r'C:\Users\alext\Github\cambc-autumn\replays\.analysis'
MELEE = {'Ryth', 'Vendetta', 'Marcella', 'Ren', 'Varg', 'Issac'}


def game(d):
    try:
        m = json.load(open(os.path.join(ROOT, d, 'meta.json'), encoding='utf-8'))
        ev = [json.loads(l) for l in gzip.open(os.path.join(ROOT, d, 'events.jsonl.gz'), 'rt')]
    except Exception:
        return []
    team = {c['id']: c['team'] for c in m['champions']}
    name = {c['id']: c['name'] for c in m['champions']}
    ev.sort(key=lambda e: e['s'])
    hits = []  # (s, r, attacker, victim)
    for e in ev:
        if e['k'] in ('attack', 'cast'):
            for v, a in (e.get('dmg') or []):
                if v in team and team[v] != team[e['a']] and a > 0:
                    hits.append((e['s'], e['r'], e['a'], v))
    deaths = [e for e in ev if e['k'] == 'death' and isinstance(e.get('by'), int) and not e.get('linked')]
    out = []
    for de in deaths:
        v, k, D = de['v'], de['by'], de['r']
        # walk back the exchange between k and v
        pair = [h for h in hits if h[0] <= de['s'] and {h[2], h[3]} == {k, v}]
        if not pair:
            continue
        start = len(pair) - 1
        while start > 0 and pair[start][1] - pair[start - 1][1] <= 4:
            start -= 1
        r0 = pair[start][1]
        involved = [h for h in hits if r0 - 2 <= h[1] <= D and (h[2] in (k, v) or h[3] in (k, v))]
        if any({h[2], h[3]} != {k, v} for h in involved):
            continue
        first = pair[start][2]
        out.append((name[k], name[v], first == k, m['teams'][team[k]]['name']))
    return out


if __name__ == '__main__':
    idxj = json.load(open(os.path.join(ROOT, 'index.json'), encoding='utf-8'))
    dirs = sorted({g['dir'] for g in idxj['games'] if g['kind'] == 'ladder' and g['ok'] and '20261016' <= g['source'].split('/')[2][:8]})[:int(sys.argv[1])]
    rows = []
    with ProcessPoolExecutor(16) as ex:
        for r in ex.map(game, dirs, chunksize=8):
            rows += r
    import collections as C
    pair = C.Counter((r[0], r[1]) for r in rows)
    names = sorted({r[0] for r in rows} | {r[1] for r in rows})
    print('isolated 1v1 kill balance by pair (row kills col : col kills row), pairs with >= 30 kills')
    out = []
    for i, a in enumerate(names):
        for b in names[i+1:]:
            x, y = pair[(a, b)], pair[(b, a)]
            if x + y >= 30: out.append((a, b, x, y))
    for a, b, x, y in sorted(out, key=lambda t: -(t[2]+t[3])):
        print(f'   {a:9s} vs {b:9s} {x:4d} : {y:4d}   row share {x/(x+y):.2f}')
    n = len(rows)
    print('isolated 1v1 kills', n, 'killer struck first', sum(r[2] for r in rows) / n)
    by = collections.defaultdict(lambda: [0, 0])
    for kn, vn, f, t in rows:
        key = ('melee' if kn in MELEE else 'ranged') + '>' + ('melee' if vn in MELEE else 'ranged')
        by[key][0] += f; by[key][1] += 1
    for k, (f, c) in sorted(by.items()):
        print(f'  killer>victim {k:16s} n {c:5d} killer first {f / c:.2f}')
