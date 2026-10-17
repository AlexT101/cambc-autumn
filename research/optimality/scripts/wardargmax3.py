"""Ward argmax under V(w) = |Vis_ward(w) & B(p)|, B(p) = walkable tiles within 6 of work tile p that p cannot see.
Line of sight approximated by supercover-free Bresenham between tile centres (walls and foreign bush tiles opaque).
Static: it uses only the maps of the selected games.

  py wardargmax3.py                                           # the report: ladder maps played since 10-16
  py wardargmax3.py --src replays/batch-20261017-091937-928141  # the maps of a local batch
Selection options: gamesel.py.
"""
import json, os, collections, statistics as st
import gamesel
ROOT = gamesel.ROOT
maps = gamesel.maps(gamesel.select(gamesel.parser(__doc__).parse_args()))


def line(a, b):
    (x0, y0), (x1, y1) = a, b
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx, sy = (1 if x1 > x0 else -1), (1 if y1 > y0 else -1)
    err = dx - dy
    pts = []
    x, y = x0, y0
    while (x, y) != (x1, y1):
        e2 = 2 * err
        if e2 > -dy: err -= dy; x += sx
        if e2 < dx: err += dx; y += sy
        pts.append((x, y))
    return pts[:-1]


def analyse(m):
    W, H = m['width'], m['height']
    walls = set(map(tuple, m['walls'])); bushes = set(map(tuple, m['bushes']))
    holes = set(map(tuple, m['holes'])); altars = set(map(tuple, m['altars']))
    camps = {(c['x'], c['y']) for c in m['camps']}
    cid = {}
    for t in bushes:
        if t in cid: continue
        stack = [t]; cid[t] = t
        while stack:
            x, y = stack.pop()
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if n in bushes and n not in cid: cid[n] = t; stack.append(n)
    walk = lambda t: 0 <= t[0] < W and 0 <= t[1] < H and t not in walls and t not in holes and t not in altars and t not in camps

    def vis(v, r):
        out = set()
        for x in range(v[0] - r, v[0] + r + 1):
            for y in range(v[1] - r, v[1] + r + 1):
                t = (x, y)
                if not (0 <= x < W and 0 <= y < H) or t in walls: continue
                if t in bushes and cid.get(v) != cid[t]: continue
                ok = True
                for q in line(v, t):
                    if q in walls or (q in bushes and cid.get(v) != cid[q]): ok = False; break
                if ok: out.add(t)
        return out
    res = collections.Counter(); gains = []
    for g in m['groups']:
        if g['side'] != 0 or not any(t in ('Wolf', 'Elk', 'Monolith') for t in g['types']): continue
        tiles = [tuple(t) for t in g['tiles']]
        work = {(x + dx, y + dy) for (x, y) in tiles for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
        work = [p for p in work if walk(p)][:6]
        for p in work:
            vp = vis(p, 8)
            B = {(x, y) for x in range(p[0] - 5, p[0] + 6) for y in range(p[1] - 5, p[1] + 6)
                 if (x, y) in bushes and cid[(x, y)] != cid.get(p) and p in vis((x, y), 5)}
            if not B: res['no_threat_bush'] += 1; continue
            best, bv = None, -1
            for dx in range(-6, 7):
                for dy in range(-6, 7):
                    w = (p[0] + dx, p[1] + dy)
                    if not (0 <= w[0] < W and 0 <= w[1] < H) or w in walls or w in holes or w in altars: continue
                    if w not in bushes: continue
                    v = len(vis(w, 6) & B)
                    if v > bv: bv, best = v, w
            res['bush' if best in bushes else 'open'] += 1
            res['full_cover'] += bv == len(B)
            res['blind_bush_tiles'] += sum(1 for t in B if t in bushes); res['blind_tiles'] += len(B)
            gains.append(bv / len(B))
    return res, gains


tot = collections.Counter(); allg = []
for name, h in sorted(maps.items()):
    m = json.load(open(os.path.join(ROOT, 'maps', h + '.json')))
    r, g = analyse(m)
    tot += r; allg += g
    n = r['bush'] + r['open']
    if n: print(f"{name:14s} work tiles {n:3d}  argmax ward on a bush {r['bush'] / n:.2f}  blind tiles that are bushes {r['blind_bush_tiles'] / max(1, r['blind_tiles']):.2f}  covered share {st.mean(g):.2f}")
n = tot['bush'] + tot['open']
print('one ward covers the whole threat set at', tot['full_cover'], 'of', n, 'work tiles')
print('work tiles with no threatening bush:', tot['no_threat_bush'], 'with:', n)
print(f"ALL work tiles {n}: argmax on bush {tot['bush'] / n:.2f}; blind tiles that are bushes {tot['blind_bush_tiles'] / tot['blind_tiles']:.2f}; mean share of blind set one ward covers {st.mean(allg):.2f}")
