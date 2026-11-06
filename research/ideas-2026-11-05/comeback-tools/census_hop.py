#!/usr/bin/env python3
"""census_hop.py MAPS_JSON_DIR [--floor 20]: how often a crystal-hop wipe site (gambit g) exists.

For team A against each worthy group on team B's side (gems + gold/5 >= floor): landing tiles are the group's camp
tiles and the walkable tiles beside them; wait tiles are walkable tiles within 3 (crystal range) of a landing tile
that no camp or landing tile sees (radius-8 line of sight, walls and other bush clusters opaque). `wall`: the walk
from the wait tile to the nearest landing tile is at least 5 (behind a wall or across a hole). A site needs k wait
tiles (k = 2, 3). Also the camp constraint: their count of worthy groups and this group's share of their worth."""
import json, os, sys, collections
from collections import deque

def los(grid_opaque, a, b):
    (x0, y0), (x1, y1) = a, b
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx, sy = (1 if x1 > x0 else -1), (1 if y1 > y0 else -1)
    err = dx - dy
    x, y = x0, y0
    while (x, y) != (x1, y1):
        e2 = 2 * err
        if e2 > -dy: err -= dy; x += sx
        if e2 < dx: err += dx; y += sy
        if (x, y) != (x1, y1) and grid_opaque(x, y): return False
    return True

def bfs(W, H, walk, sources):
    d = {s: 0 for s in sources}
    q = deque(sources)
    while q:
        p = q.popleft()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                n = (p[0] + dx, p[1] + dy)
                if n in d or not (0 <= n[0] < W and 0 <= n[1] < H) or not walk(n): continue
                d[n] = d[p] + 1; q.append(n)
    return d

def census(m, floor):
    W, H = m['width'], m['height']
    walls = set(map(tuple, m['walls'])); holes = set(map(tuple, m['holes'])); bushes = set(map(tuple, m['bushes']))
    altars = set(tuple(a['pos']) if isinstance(a, dict) else tuple(a) for a in m['altars'])
    camp = set()
    for g in m['groups']: camp |= set(map(tuple, g['tiles']))
    walkable = lambda p: p not in walls and p not in holes and p not in altars and p not in camp
    # bush clusters (edge-connected)
    cl = {}
    for b in bushes:
        if b in cl: continue
        cid = len(cl) + 1; q = [b]; cl[b] = cid
        while q:
            p = q.pop()
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (p[0] + d[0], p[1] + d[1])
                if n in bushes and n not in cl: cl[n] = cid; q.append(n)
    sp = m['spawn'][0]
    sa = [(x, y) for x in range(sp['minX'], sp['maxX'] + 1) for y in range(sp['minY'], sp['maxY'] + 1)]
    dist_a = bfs(W, H, lambda p: p not in walls and p not in holes and p not in altars, sa)
    def far_side(g):
        # team B's side: farther from A's spawn (by walk) than its mirror
        return g['side'] == 1
    worth = lambda g: g['gems'] + g['gold'] / 5
    theirs = [g for g in m['groups'] if far_side(g)]
    hv = [g for g in theirs if worth(g) >= floor]
    total = sum(worth(g) for g in hv) or 1
    sites = []
    for g in hv:
        C = set(map(tuple, g['tiles']))
        L = set(C)
        for (x, y) in C:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    p = (x + dx, y + dy)
                    if 0 <= p[0] < W and 0 <= p[1] < H and walkable(p): L.add(p)
        watchers = C | L
        dL = bfs(W, H, walkable, [p for p in L if walkable(p)] or list(L))
        cand_any, cand_wall = [], []
        xs = [p[0] for p in L]; ys = [p[1] for p in L]
        for x in range(max(0, min(xs) - 3), min(W, max(xs) + 4)):
            for y in range(max(0, min(ys) - 3), min(H, max(ys) + 4)):
                p = (x, y)
                if not walkable(p) or p in L: continue
                if min(max(abs(p[0] - q[0]), abs(p[1] - q[1])) for q in L) > 3: continue
                if p not in dist_a: continue  # we must be able to walk there
                def opaque_from(q):
                    def f(x_, y_):
                        t = (x_, y_)
                        if t in walls: return True
                        if t in bushes: return cl.get(t) != cl.get(q)
                        return False
                    return f
                seen = False
                for q in watchers:
                    if max(abs(p[0] - q[0]), abs(p[1] - q[1])) > 8: continue
                    if p in bushes and cl.get(p) != cl.get(q): continue  # a bush is unseen from outside its cluster
                    if los(opaque_from(q), q, p): seen = True; break
                if seen: continue
                cand_any.append(p)
                if dL.get(p, 99) >= 5: cand_wall.append(p)
        sites.append({'worth': worth(g), 'share': worth(g) / total, 'any': len(cand_any), 'wall': len(cand_wall)})
    return {'hv': len(hv), 'sites': sites}

def main():
    d = sys.argv[1]
    floor = float(sys.argv[sys.argv.index('--floor') + 1]) if '--floor' in sys.argv else 20
    lim = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else 10 ** 9
    rows = []
    for f in sorted(os.listdir(d))[:lim]:
        m = json.load(open(f'{d}/{f}'))
        try: rows.append(census(m, floor))
        except Exception as e: print('skip', f, e, file=sys.stderr)
    n = len(rows)
    print(f'maps {n}, floor {floor}')
    for kind in ('any', 'wall'):
        for k in (1, 2, 3):
            has = sum(any(s[kind] >= k for s in r['sites']) for r in rows)
            print(f'  {kind} wait tiles >= {k}: {has} maps ({100 * has / n:.1f}%)')
    by = collections.defaultdict(list)
    for r in rows: by[min(r['hv'], 6)].append(r)
    print('by their worthy-group count: maps, share with a wall site of 3 / an any site of 3')
    for k in sorted(by):
        v = by[k]
        print(f'  {k}{"+" if k == 6 else ""}: {len(v)}  wall3 {100 * sum(any(s["wall"] >= 3 for s in r["sites"]) for r in v) / len(v):.1f}%  any3 {100 * sum(any(s["any"] >= 3 for s in r["sites"]) for r in v) / len(v):.1f}%')
    # sites on groups holding a big share of their worth
    for s_min in (0.3, 0.5):
        has = sum(any(s['wall'] >= 3 and s['share'] >= s_min for s in r['sites']) for r in rows)
        print(f'  wall3 site on a group with >= {s_min} of their worth: {100 * has / n:.1f}%')

if __name__ == '__main__':
    main()
