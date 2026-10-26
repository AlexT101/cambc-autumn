"""Prototype of the draft's cut finder (graph over cells and representative blocks) and the champion rebuild.

walls = walls | holes | altars | enemy spawn (blocked_for_us); team 0's view (spawn[0] ours).
"""
import json, sys, glob, os, math, collections
from collections import deque

DIRS = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]


def load(mp, team=0, dash=False):
    w, h = mp['width'], mp['height']
    blocked = set(map(tuple, mp['walls']))
    holes = set(map(tuple, mp['holes'])) | set(map(tuple, mp['altars']))
    if dash:
        # crossable: hole/altar with standable tiles on two opposite sides (approximation)
        cross = set()
        for (x, y) in holes:
            for dx, dy in [(1, 0), (0, 1), (1, 1), (1, -1)]:
                a, b = (x + dx, y + dy), (x - dx, y - dy)
                ok = lambda p: 0 <= p[0] < w and 0 <= p[1] < h and p not in blocked and p not in holes
                if ok(a) and ok(b):
                    cross.add((x, y))
        holes = holes - cross
    blocked |= holes
    spawns = []
    for s in mp['spawn']:
        spawns.append({(x, y) for x in range(s['minX'], s['maxX'] + 1) for y in range(s['minY'], s['maxY'] + 1)})
    blocked |= spawns[1 - team]
    op = [[(x, y) not in blocked for x in range(w)] for y in range(h)]
    return w, h, op, spawns[team], spawns[1 - team]


def flood(w, h, op, starts, block=frozenset()):
    seen = set(s for s in starts if op[s[1]][s[0]] and s not in block)
    dq = deque(seen)
    while dq:
        x, y = dq.popleft()
        for dx, dy in DIRS:
            q = (x + dx, y + dy)
            if 0 <= q[0] < w and 0 <= q[1] < h and op[q[1]][q[0]] and q not in seen and q not in block:
                seen.add(q)
                dq.append(q)
    return seen


def runwidth(w, h, op, x, y):
    best = 99
    for dx, dy in [(1, 0), (0, 1), (1, 1), (1, -1)]:
        n = 1
        for s in (1, -1):
            k = 1
            while 0 <= x + s * k * dx < w and 0 <= y + s * k * dy < h and op[y + s * k * dy][x + s * k * dx]:
                k += 1
            n += k - 1
        best = min(best, n)
    return best


RING = [(-2, -2), (-1, -2), (0, -2), (1, -2), (2, -2), (2, -1), (2, 0), (2, 1), (2, 2), (1, 2), (0, 2), (-1, 2), (-2, 2), (-2, 1), (-2, 0), (-2, -1)]


def ring_pieces(w, h, op, x, y):
    """Pieces of the open ring at distance 2 that touch an open tile of the 3x3 block."""
    ok = lambda p: 0 <= p[0] < w and 0 <= p[1] < h and op[p[1]][p[0]]
    bits = [ok((x + dx, y + dy)) for dx, dy in RING]
    att = []
    for (dx, dy), b in zip(RING, bits):
        a = False
        if b:
            for ex in (-1, 0, 1):
                for ey in (-1, 0, 1):
                    qx, qy = dx + ex, dy + ey
                    if max(abs(qx), abs(qy)) <= 1 and ok((x + qx, y + qy)):
                        a = True
        att.append(a)
    # cyclic runs; consecutive ring tiles are adjacent; across a corner (index 0,4,8,12) the two
    # neighbours are diagonal-adjacent
    n = 16
    parent = list(range(n))
    def find(i):
        while parent[i] != i:
            i = parent[i]
        return i
    for i in range(n):
        j = (i + 1) % n
        if bits[i] and bits[j]:
            parent[find(i)] = find(j)
    for c in (0, 4, 8, 12):
        a, b = (c - 1) % n, (c + 1) % n
        if bits[a] and bits[b]:
            parent[find(a)] = find(b)
    return len({find(i) for i in range(n) if att[i]})


def find_cuts(mp, team=0, dash=False, spacing=4, min_side=4):
    w, h, op, ours, theirs = load(mp, team, dash)
    tiles = [(x, y) for y in range(h) for x in range(w) if op[y][x]]
    tiers = {1: [], 2: [], 3: []}
    for (x, y) in tiles:
        r = runwidth(w, h, op, x, y)
        if r <= 3 and ring_pieces(w, h, op, x, y) >= 2:
            tiers[r].append((x, y))
    forbid = set()
    reps = []
    for t in (1, 2, 3):
        for p in tiers[t]:
            if p in forbid:
                continue
            reps.append(p)
            for dx in range(-(spacing - 1), spacing):
                for dy in range(-(spacing - 1), spacing):
                    forbid.add((p[0] + dx, p[1] + dy))
    block_of = {}
    B = set()
    for i, (x, y) in enumerate(reps):
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                q = (x + dx, y + dy)
                if 0 <= q[0] < w and 0 <= q[1] < h and op[q[1]][q[0]]:
                    B.add(q)
                    block_of[q] = i
    label = {}
    cells = []
    for p in tiles:
        if p in B or p in label:
            continue
        c = flood(w, h, op, [p], B)
        for q in c:
            label[q] = len(cells)
        cells.append(c)
    nc = len(cells)
    # bipartite graph: cell nodes 0..nc-1, rep nodes nc..
    adj = collections.defaultdict(set)
    for i, (x, y) in enumerate(reps):
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if max(abs(dx), abs(dy)) != 2:
                    continue
                q = (x + dx, y + dy)
                if q not in label:
                    continue
                # attached: adjacent to an open block tile of this rep
                att = False
                for ex, ey in DIRS:
                    r_ = (q[0] + ex, q[1] + ey)
                    if block_of.get(r_) == i:
                        att = True
                        break
                if att:
                    adj[nc + i].add(label[q])
                    adj[label[q]].add(nc + i)
    root = next((label[p] for p in sorted(ours) if p in label), None)
    enemy_cells = set()
    for (x, y) in theirs:
        for dx, dy in DIRS:
            q = (x + dx, y + dy)
            if q in label:
                enemy_cells.add(label[q])
    # sizes per node (cells: tiles; reps: block tiles)
    size = [len(c) for c in cells] + [sum(1 for q in B if block_of[q] == i) for i in range(len(reps))]
    # iterative Tarjan from root
    n = nc + len(reps)
    disc = [-1] * n
    low = [0] * n
    sub = [0] * n  # subtree tile count
    subenemy = [False] * n
    parent = [-1] * n
    timer = 0
    cut_children = collections.defaultdict(list)
    if root is None:
        return reps, [], (w, h, op, ours)
    stack = [(root, iter(sorted(adj[root])))]
    disc[root] = low[root] = timer; timer += 1
    sub[root] = size[root]; subenemy[root] = root in enemy_cells
    while stack:
        v, it = stack[-1]
        nxt = next(it, None)
        if nxt is None:
            stack.pop()
            if stack:
                u = stack[-1][0]
                low[u] = min(low[u], low[v])
                sub[u] += sub[v]
                subenemy[u] = subenemy[u] or subenemy[v]
                if low[v] >= disc[u] and u != root:
                    cut_children[u].append(v)
            continue
        if disc[nxt] == -1:
            parent[nxt] = v
            disc[nxt] = low[nxt] = timer; timer += 1
            sub[nxt] = size[nxt]
            subenemy[nxt] = nxt in enemy_cells
            stack.append((nxt, iter(sorted(adj[nxt]))))
        elif nxt != parent[v]:
            low[v] = min(low[v], disc[nxt])
    # candidate cut reps: articulation rep nodes with separated children, none holding the enemy spawn
    sent = []
    for u, kids in cut_children.items():
        if u < nc:
            continue
        if any(subenemy[k] for k in kids):
            continue
        if sum(sub[k] for k in kids) < min_side:
            continue
        sent.append(u)
    # outermost: drop a rep whose node lies in another sent rep's separated subtree (ancestor check)
    sent_set = set(sent)
    outer = []
    for u in sent:
        a = parent[u]
        nested = False
        while a != -1:
            if a in sent_set:
                nested = True
                break
            a = parent[a]
        if not nested:
            outer.append(reps[u - nc])
    return reps, outer, (w, h, op, ours)


def rebuild(w, h, op, ours, cuts):
    block = set()
    for (x, y) in cuts:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                q = (x + dx, y + dy)
                if 0 <= q[0] < w and 0 <= q[1] < h and op[q[1]][q[0]]:
                    block.add(q)
    foot = flood(w, h, op, list(ours))
    main = flood(w, h, op, list(ours), block)
    return foot - main - block, block


def rice_bits(vals, k):
    return sum((v >> k) + 1 + k for v in vals)


def encode_bits(w, cuts):
    idx = sorted(y * w + x for x, y in cuts)
    gaps = [idx[0]] + [b - a - 1 for a, b in zip(idx, idx[1:])] if idx else []
    best = min((rice_bits(gaps, k), k) for k in range(0, 16)) if gaps else (0, 0)
    count_bits = rice_bits([len(cuts)], 2)
    return count_bits + 4 + best[0]


if __name__ == '__main__':
    import time
    paths = sys.argv[1:]
    for path in paths:
        mp = json.load(open(path))
        t = time.time()
        reps, cuts, (w, h, op, ours) = find_cuts(mp)
        pocket, block = rebuild(w, h, op, ours, cuts)
        dreps, dcuts, dctx = find_cuts(mp, dash=True)
        dpocket, _ = rebuild(*dctx, dcuts)
        nopen = sum(sum(r) for r in op)
        print('%-28s %3dx%-3d open %5d reps %4d cuts %3d pocket %5d (%4.1f%%) bits %4d | dash cuts %3d pocket %5d same %s  %.1fs' % (
            os.path.basename(path)[:28], w, h, nopen, len(reps), len(cuts), len(pocket), 100 * len(pocket) / nopen,
            encode_bits(w, cuts), len(dcuts), len(dpocket), sorted(dcuts) == sorted(cuts), time.time() - t))
