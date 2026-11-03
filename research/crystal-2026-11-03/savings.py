"""Offline: turns a teleport crystal saves on trips from our spawn, per map (static terrain, camps never landable).

    python3 research/crystal-2026-11-03/savings.py replays/ab/<run>/analysis/maps

Walking: king steps, impassable walls, holes, altars and the enemy spawn (rules: corners only check the tile stepped
onto). A crystal trip: walk to a source s, start the channel that turn, arrive at the start of the turn 3 turn ends
later, so it costs walk(s) + 2 + walk(L -> target) for a landing L within Chebyshev 3 of s (an open or bush tile,
not a camp tile or the enemy spawn). Targets: each altar's tribute tiles (within 1) and each group's adjacent tiles.
"""
import json, sys
from collections import deque
from pathlib import Path
import numpy as np

INF = 1 << 20

def bfs(block, roots):
    h, w = block.shape
    d = np.full((h, w), INF, dtype=np.int64)
    q = deque()
    for y, x in roots:
        if not block[y, x] and d[y, x] == INF:
            d[y, x] = 0; q.append((y, x))
    while q:
        y, x = q.popleft(); nd = d[y, x] + 1
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and not block[ny, nx] and d[ny, nx] > nd:
                    d[ny, nx] = nd; q.append((ny, nx))
    return d

def minfilter(a, r):
    h, w = a.shape
    p = np.pad(a, r, constant_values=INF)
    out = np.full_like(a, INF)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            out = np.minimum(out, p[r + dy:r + dy + h, r + dx:r + dx + w])
    return out

def analyse(m):
    w, h = m["width"], m["height"]
    block = np.zeros((h, w), bool)
    for x, y in m["walls"] + m["holes"] + m["altars"]: block[y, x] = True
    ours, theirs = m["spawn"][0], m["spawn"][1]
    enemy = np.zeros((h, w), bool); enemy[theirs["minY"]:theirs["maxY"] + 1, theirs["minX"]:theirs["maxX"] + 1] = True
    block_us = block | enemy
    camp = np.zeros((h, w), bool)
    for c in m["camps"]: camp[c["y"], c["x"]] = True
    landable = ~block_us & ~camp
    spawn = [(y, x) for y in range(ours["minY"], ours["maxY"] + 1) for x in range(ours["minX"], ours["maxX"] + 1)]
    walk_block = block_us | camp  # live camps block walking too
    A = bfs(walk_block, spawn)
    out = []
    def target(kind, tiles):
        tiles = [(y, x) for y, x in tiles if 0 <= y < h and 0 <= x < w and not walk_block[y, x]]
        if not tiles: return
        D = bfs(walk_block, tiles)
        walk = int(min(A[y, x] for y, x in tiles))
        H = minfilter(np.where(landable, D, INF), 3)
        hop = int(np.min(np.where(A < INF, A + 2 + H, INF)))
        out.append((kind, walk, min(walk, hop)))
    for ax, ay in m["altars"]:
        target("altar", [(ay + dy, ax + dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1)])
    for g in m["groups"]:
        if any(t in ("Wolf", "Elk", "Golem", "Monolith", "Gem cluster", "Gold cluster") for t in g["types"]):
            adj = {(y + dy, x + dx) for x, y in g["tiles"] for dy in (-1, 0, 1) for dx in (-1, 0, 1)}
            target("group", adj)
    return out

def main():
    rows = []
    for f in sorted(Path(sys.argv[1]).glob("*.json")):
        m = json.loads(f.read_text())
        for kind, walk, best in analyse(m):
            rows.append((f.stem, kind, walk, best))
    for kind in ("altar", "group"):
        r = [x for x in rows if x[1] == kind and x[2] < INF]
        unreach = sum(1 for x in rows if x[1] == kind and x[2] >= INF)
        s = np.array([x[2] - x[3] for x in r])
        print(f"{kind}: {len(r)} trips (+{unreach} unreachable on foot), saving mean {s.mean():.2f} turns; "
              f"saving >=2: {np.mean(s >= 2):.1%}, >=4: {np.mean(s >= 4):.1%}, >=8: {np.mean(s >= 8):.1%}, >=16: {np.mean(s >= 16):.1%}")
    maps = {}
    for name, kind, walk, best in rows:
        if walk < INF: maps.setdefault(name, []).append(walk - best)
    big = sorted(((max(v), n) for n, v in maps.items()), reverse=True)
    print(f"maps: {len(maps)}; with some trip saving >=8: {sum(1 for v, _ in big if v >= 8)}, >=4: {sum(1 for v, _ in big if v >= 4)}")
    print("largest:", ", ".join(f"{n} {v}" for v, n in big[:8]))

if __name__ == "__main__":
    main()
