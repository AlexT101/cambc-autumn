#!/usr/bin/env python3
"""altar_study.py ANA [ANA...] --out OUT.jsonl: one row per tribute start with altar geometry, company and outcome,
plus one row per bag death (carrier died holding >= 10 gems). Geometry by walk from each spawn."""
import json, gzip, os, sys, collections, argparse
from collections import deque

ap = argparse.ArgumentParser()
ap.add_argument('ana', nargs='+')
ap.add_argument('--out', required=True)
ap.add_argument('--zone', type=int, default=10)
args = ap.parse_args()

mapcache = {}

def bfs(W, H, block, sources):
    INF = 1 << 20
    d = [INF] * (W * H)
    q = deque()
    for (x, y) in sources:
        d[y * W + x] = 0; q.append((x, y))
    while q:
        x, y = q.popleft(); b = d[y * W + x]
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < W and 0 <= ny < H and not block[ny * W + nx] and d[ny * W + nx] > b + 1:
                    d[ny * W + nx] = b + 1; q.append((nx, ny))
    return d

def geom(ana, h):
    if h in mapcache: return mapcache[h]
    m = json.load(open(f'{ana}/maps/{h}.json'))
    W, H = m['width'], m['height']
    block = [0] * (W * H)
    for k in ('walls', 'holes', 'altars'):
        for x, y in m[k]: block[y * W + x] = 1
    spawns = []
    for s in m['spawn']:
        spawns.append([(x, y) for x in range(s['minX'], s['maxX'] + 1) for y in range(s['minY'], s['maxY'] + 1)])
    fields = [bfs(W, H, block, s) for s in spawns]
    alts = [tuple(a) for a in m['altars']]
    INF = 1 << 20
    walk = []  # walk[team][altar]: steps from spawn to nearest tribute tile
    for t in (0, 1):
        row = []
        for ax, ay in alts:
            best = INF
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    x, y = ax + dx, ay + dy
                    if 0 <= x < W and 0 <= y < H and not block[y * W + x]: best = min(best, fields[t][y * W + x])
            row.append(best)
        walk.append(row)
    # zones: single linkage by Chebyshev <= zone
    n = len(alts); zid = list(range(n))
    def find(i):
        while zid[i] != i: zid[i] = zid[zid[i]]; i = zid[i]
        return i
    for i in range(n):
        for j in range(i + 1, n):
            if max(abs(alts[i][0] - alts[j][0]), abs(alts[i][1] - alts[j][1])) <= args.zone: zid[find(i)] = find(j)
    zones = [find(i) for i in range(n)]
    cx, cy = (W - 1) / 2, (H - 1) / 2
    g = dict(W=W, H=H, alts=alts, walk=walk, zones=zones, nz=len(set(zones)), n=n,
             centre=[max(abs(a[0] - cx), abs(a[1] - cy)) / (max(W, H) / 2) for a in alts],
             s2s=min(fields[0][y * W + x] for (x, y) in spawns[1]))
    mapcache[h] = g
    return g

def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))

out = open(args.out, 'w')
for ana in args.ana:
    ix = json.load(open(f'{ana}/index.json'))['games']
    seen = set()
    for row in ix:
        d = row['dir']
        if d in seen or not row.get('ok', True): continue
        seen.add(d)
        try:
            m = json.load(open(f'{ana}/{d}/meta.json'))
            R = json.load(gzip.open(f'{ana}/{d}/rounds.json.gz'))
            ev = [json.loads(l) for l in gzip.open(f'{ana}/{d}/events.jsonl.gz', 'rt')]
        except Exception as e:
            print('skip', d, e, file=sys.stderr); continue
        g = geom(ana, m['map']['hash'])
        if g['n'] == 0: continue
        team = {c['id']: c['team'] for c in m['champions']}
        ctype = {c['id']: c['type'] for c in m['champions']}
        ri = {r: i for i, r in enumerate(R['round'])}
        chs = R['champions']
        def pos(cid, i):
            for c in chs:
                if c['id'] == cid:
                    return (c['x'][i], c['y'][i]) if c['alive'][i] and c['x'][i] is not None else None
        def near(t_other, p, i, r):
            n = 0
            for c in chs:
                if c['team'] == t_other and c['alive'][i] and c['x'][i] is not None and cheb((c['x'][i], c['y'][i]), p) <= r: n += 1
            return n
        winner = m['result']['winner']
        ends = collections.defaultdict(list)
        deaths = collections.defaultdict(list)
        for e in ev:
            if e['k'] in ('tribute_end', 'tribute_cancel'): ends[e['a']].append(e)
            if e['k'] == 'death': deaths[e['v']].append(e)
        for e in ev:
            if e['k'] == 'tribute_start':
                a = e['a']; t = team[a]; i = ri.get(e['r'] - 1, 0)
                alt = e['altar'] if isinstance(e['altar'], int) else None
                ap_ = tuple(e['at']) if 'at' in e else pos(a, i)
                # altar index by nearest altar tile to `at`
                k = g['alts'].index(tuple(e['altar'])) if isinstance(e.get('altar'), list) and tuple(e['altar']) in g['alts'] else (min(range(g['n']), key=lambda j: cheb(g['alts'][j], ap_)) if ap_ else 0)
                end = next((x for x in ends[a] if x['s'] > e['s']), None)
                died = next((x for x in deaths[a] if x['s'] > e['s'] and (end is None or x['s'] <= end['s'])), None)
                res = 'end' if end and end['k'] == 'tribute_end' else ('cancel:' + str(end.get('cause', '?')) if end else 'none')
                own = g['walk'][t][k]; oth = g['walk'][1 - t][k]
                nearest_own = own <= min(g['walk'][t])
                score = R['gems'][t][i]; escore = R['gems'][1 - t][i]
                out.write(json.dumps(dict(kind='trib', ana=ana, d=d, map=m['map']['name'], team=t, won=winner == t, ctype=ctype[a],
                    r=e['r'], gems=e['gems'], dur=e['dur'], res=res, died=bool(died), alt=k, n=g['n'], nz=g['nz'],
                    zsize=g['zones'].count(g['zones'][k]), own=own, oth=oth, s2s=g['s2s'], centre=g['centre'][k], nearest_own=nearest_own,
                    own_min=min(g['walk'][t]), en8=near(1 - t, ap_, i, 8) if ap_ else -1, en4=near(1 - t, ap_, i, 4) if ap_ else -1,
                    al4=near(t, ap_, i, 4) - 1 if ap_ else -1, score=score, escore=escore, winbag=score + e['gems'] >= 1000)) + '\n')
            elif e['k'] == 'death' and e.get('gems', 0) >= 10:
                v = e['v']; t = team[v]; p = tuple(e['at']) if e.get('at') else None
                if not p: continue
                k = min(range(g['n']), key=lambda j: cheb(g['alts'][j], p))
                i = ri.get(e['r'] - 1, 0)
                out.write(json.dumps(dict(kind='bagdeath', ana=ana, d=d, map=m['map']['name'], team=t, won=winner == t, gems=e['gems'],
                    r=e['r'], bycamp='camp' in e and e['camp'] is not None, altd=cheb(g['alts'][k], p), alt=k, n=g['n'], nz=g['nz'],
                    own=g['walk'][t][k], oth=g['walk'][1 - t][k], own_min=min(g['walk'][t]), s2s=g['s2s'],
                    winbag=R['gems'][t][i] + e['gems'] >= 1000)) + '\n')
out.close()
