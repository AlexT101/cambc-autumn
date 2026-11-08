"""Shared loader for the Mite ward study: one actor cache (tools/fish/extract.mjs) as a game with its static map."""
import gzip, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools/replay/narrative'))
from vision import Vision

TYPES = {0: 'Ryth', 1: 'Vesper', 2: 'Vendetta', 3: 'Cassi', 4: 'Issac', 5: 'Prism', 6: 'Stellar', 7: 'Marcella',
         8: 'Tavi', 9: 'Willow', 10: 'Varg', 11: 'HoR', 12: 'Ren'}
RANGED = {'Vesper', 'Cassi', 'Prism', 'Stellar', 'Tavi', 'Willow'}


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def mirror(m, x, y):
    s = m['symmetry']
    if s == 'horizontal': return (m['width'] - 1 - x, y)
    if s == 'vertical': return (x, m['height'] - 1 - y)
    return (m['width'] - 1 - x, m['height'] - 1 - y)


def clusters(bushes):
    B = {tuple(b) for b in bushes}; cid = {}; k = 0
    for b in sorted(B):
        if b in cid: continue
        st = [b]; cid[b] = k
        while st:
            p = st.pop()
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (p[0] + d[0], p[1] + d[1])
                if n in B and n not in cid: cid[n] = k; st.append(n)
        k += 1
    return cid


class Game:
    def __init__(self, path):
        d = json.load(gzip.open(path))
        self.d = d
        self.path = str(path)
        m = d['map']; self.m = m
        self.W, self.H = m['width'], m['height']
        self.walls = {tuple(t) for t in m['walls']}
        self.holes = {tuple(t) for t in m['holes']}
        self.bush_c = clusters(m['bushes'])
        self.bushes = set(self.bush_c)
        self.csize = {}
        for t, c in self.bush_c.items(): self.csize[c] = self.csize.get(c, 0) + 1
        self.altars = [tuple(a) for a in m['altars']]
        self.camps = [(c['type'], (c['x'], c['y'])) for c in m['camps']]
        sa = m['spawnA']
        A = {(x, y) for x in range(sa['minX'], sa['maxX'] + 1) for y in range(sa['minY'], sa['maxY'] + 1)}
        B = {mirror(m, x, y) for x, y in A}
        self.side = d['side']
        self.own_spawn, self.foe_spawn = (A, B) if self.side == 0 else (B, A)
        self.V = Vision(self.W, self.H, self.walls, self.bush_c)
        self.roster = {r['id']: r for r in d['roster']}
        self.turns = d['turns']

    def fov(self, p, r=8):
        return self.V.fov(tuple(p), r)

    def legal_ward(self, t):
        return (0 <= t[0] < self.W and 0 <= t[1] < self.H and t not in self.walls and t not in self.holes
                and t not in self.altars and t not in self.foe_spawn)

    def name(self, cid):
        return self.roster[cid]['name']


def pos(u):
    return (u['x'], u['y'])
