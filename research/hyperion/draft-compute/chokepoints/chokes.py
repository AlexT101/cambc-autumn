"""Static choke/pocket structure of a map json (replays/.analysis/maps/<hash>.json), pure Python.

open = not wall/hole/altar; 8-connected (rules: map.corners). Camps count as cleared.
A cut at t with radius r blocks square(t, r) & open; its sides are the components of the rest
that touched the ring around it. A side holding neither spawn is a dead-end pocket.
"""
from collections import deque

DIRS = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]


class Grid:
    def __init__(self, mp, dash=False):
        self.w, self.h = mp['width'], mp['height']
        blocked = set(map(tuple, mp['walls']))
        if not dash:
            blocked |= set(map(tuple, mp['holes'])) | set(map(tuple, mp['altars']))
        self.open = [[(x, y) not in blocked for x in range(self.w)] for y in range(self.h)]
        self.spawn = []
        for s in mp['spawn']:
            self.spawn.append({(x, y) for x in range(s['minX'], s['maxX'] + 1) for y in range(s['minY'], s['maxY'] + 1)})
        self.n_open = sum(sum(r) for r in self.open)

    def ok(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h and self.open[y][x]

    def width(self, x, y):
        """Shortest open run through (x, y) over the 4 axes."""
        best = 1 << 30
        for dx, dy in [(1, 0), (0, 1), (1, 1), (1, -1)]:
            n = 1
            for s in (1, -1):
                k = 1
                while self.ok(x + s * k * dx, y + s * k * dy):
                    k += 1
                n += k - 1
            best = min(best, n)
        return best


def cut_sides(g, t, r, cap=None):
    """Sides of the cut at t (list of tile sets, all but the largest exactly; the largest may be
    None when it ran past cap), or None if it does not split."""
    tx, ty = t
    block = {(x, y) for x in range(tx - r, tx + r + 1) for y in range(ty - r, ty + r + 1) if g.ok(x, y)}
    ring = [(x, y) for x in range(tx - r - 1, tx + r + 2) for y in range(ty - r - 1, ty + r + 2)
            if g.ok(x, y) and (x, y) not in block]
    if not ring:
        return None
    # local pieces of the ring
    ringset = set(ring)
    piece = {}
    pieces = []
    for p in ring:
        if p in piece:
            continue
        i = len(pieces)
        pieces.append([p])
        piece[p] = i
        dq = deque([p])
        while dq:
            x, y = dq.popleft()
            for dx, dy in DIRS:
                q = (x + dx, y + dy)
                if q in ringset and q not in piece:
                    piece[q] = i
                    pieces[i].append(q)
                    dq.append(q)
    if len(pieces) < 2:
        return None
    # alternating BFS from each piece over open - block, merging on contact
    k = len(pieces)
    owner = {}
    parent = list(range(k))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    fronts = []
    for i, pc in enumerate(pieces):
        for p in pc:
            owner[p] = i
        fronts.append(deque(pc))
    sizes = [len(pc) for pc in pieces]
    while True:
        roots = {find(i) for i in range(k)}
        if len(roots) < 2:
            return None
        live = [i for i in range(k) if fronts[i]]
        live_roots = {find(i) for i in live}
        # every root but one exhausted: the exhausted ones are closed sides
        if len(live_roots) <= 1 and len(roots) >= 2:
            break
        for i in live:
            # expand one layer of piece i
            for _ in range(len(fronts[i])):
                x, y = fronts[i].popleft()
                for dx, dy in DIRS:
                    q = (x + dx, y + dy)
                    if not g.ok(*q) or q in block:
                        continue
                    o = owner.get(q)
                    if o is None:
                        owner[q] = i
                        sizes[find(i)] += 1
                        fronts[i].append(q)
                    elif find(o) != find(i):
                        a, b = find(o), find(i)
                        parent[a] = b
                        sizes[b] += sizes[a]
    open_root = None
    for i in range(k):
        if fronts[i]:
            open_root = find(i)
    sides = {}
    for p, o in owner.items():
        sides.setdefault(find(o), set()).add(p)
    # the side still growing is the big one (truncated); else the largest
    if open_root is None:
        open_root = max(sides, key=lambda r: len(sides[r]))
    big = sides.pop(open_root)
    return list(sides.values()), big, block


def structure(mp, dash=False, max_width=3):
    """Per tile: 'pocket' (a side holding no spawn), 'enemy-side'/'ally-side' per team handled by
    caller; returns (pocket_tiles, choke_tiles, widths, cuts)."""
    g = Grid(mp, dash)
    widths = {}
    for y in range(g.h):
        for x in range(g.w):
            if g.open[y][x]:
                widths[(x, y)] = g.width(x, y)
    pocket = set()
    chokes = set()
    cuts = []
    seen_sides = set()
    for (x, y), wd in widths.items():
        if wd > max_width:
            continue
        r = 0 if wd == 1 else 1
        res = cut_sides(g, (x, y), r)
        if res is None and r == 0 and wd == 1:
            continue
        if res is None:
            continue
        sides, big, block = res
        for s in sides:
            if len(s) < 4:
                continue
            key = frozenset(s) if len(s) < 400 else (len(s), min(s))
            sp = [bool(s & g.spawn[0]), bool(s & g.spawn[1])]
            if not any(sp):
                pocket |= s
            chokes |= block
            if key not in seen_sides:
                seen_sides.add(key)
                cuts.append(((x, y), r, len(s), sp))
    return g, pocket, chokes, widths, cuts


if __name__ == '__main__':
    import json, sys, time
    mp = json.load(open(sys.argv[1]))
    t = time.time()
    g, pocket, chokes, widths, cuts = structure(mp)
    print('open', g.n_open, 'pocket', len(pocket), 'chokes', len(chokes), 'cuts', len(cuts), 'time %.2f' % (time.time() - t))
    for y in range(g.h - 1, -1, -1):
        row = ''
        for x in range(g.w):
            p = (x, y)
            if not g.open[y][x]:
                row += '#'
            elif p in g.spawn[0]:
                row += 'A'
            elif p in g.spawn[1]:
                row += 'B'
            elif p in chokes:
                row += 'X'
            elif p in pocket:
                row += 'p'
            else:
                row += '.'
        print(row)


def pockets(mp):
    """List of (pocket tiles, block tiles) for spawn-free sides; nested ones kept."""
    g = Grid(mp)
    out = {}
    for y in range(g.h):
        for x in range(g.w):
            if not g.open[y][x]:
                continue
            wd = g.width(x, y)
            if wd > 3:
                continue
            res = cut_sides(g, (x, y), 0 if wd == 1 else 1)
            if res is None:
                continue
            sides, big, block = res
            for s in sides:
                if len(s) < 4 or s & g.spawn[0] or s & g.spawn[1]:
                    continue
                key = frozenset(s)
                if key not in out:
                    out[key] = block
    return g, list(out.items())


