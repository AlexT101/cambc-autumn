"""Static map features with stable names, walking distances and the per-map legend.

Names are symmetric pairs numbered by walking distance from a spawn, so `Elk2` is the same pair for both teams and
the suffix is relative to the team a line is about: `Elk2.own` (on its half), `Elk2.enemy`, `Elk2.mid`."""

from collections import deque

from .vision import Vision

PRIMARY = ['Monolith', 'Golem', 'Elk', 'Wolf', 'Gem cluster', 'Gold cluster']
PREFIX = {'Monolith': 'Mono', 'Golem': 'Golem', 'Elk': 'Elk', 'Wolf': 'Wolf', 'Gem cluster': 'Gems', 'Gold cluster': 'Gold'}
LETTER = {'Monolith': 'M', 'Golem': 'O', 'Elk': 'E', 'Wolf': 'W', 'Gem cluster': 'g', 'Gold cluster': '$'}
INF = 1 << 30
N8 = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))


class Feature:
    """A named map object. `half` is 0/1 (nearer team A/B's spawn by walking) or -1; `twin` its mirror image."""

    def __init__(self, kind, base, tiles, half, info=''):
        self.kind, self.base, self.tiles, self.half, self.info = kind, base, tiles, half, info
        self.twin = None
        self.prime = False  # the second member of an equidistant pair

    def name(self, team):
        if self.half == -1:
            if self.twin is None or self.twin is self:
                return self.base + '.mid'
            return self.base + ('.mid' if self.prime == (team == 1) else ".mid'")
        return self.base + ('.own' if self.half == team else '.enemy')

    @property
    def anchor(self):
        return self.tiles[0]


class MapInfo:
    def __init__(self, m):
        self.raw = m
        self.W, self.H = m['width'], m['height']
        self.sym = m['symmetry']
        self.walls = {tuple(t) for t in m['walls']}
        self.holes = {tuple(t) for t in m['holes']}
        self.bushes = {tuple(t) for t in m['bushes']}
        self.altar_tiles = [tuple(t) for t in m['altars']]
        W, H = self.W, self.H
        blocked = self.walls | self.holes | set(self.altar_tiles)
        self.passable = [[(x, y) not in blocked for y in range(H)] for x in range(W)]
        self.spawn = [[(x, y) for x in range(s['minX'], s['maxX'] + 1) for y in range(s['minY'], s['maxY'] + 1)]
                      for s in m['spawn']]
        self.spawn_set = [set(s) for s in self.spawn]
        self.dspawn = [self.field(s) for s in self.spawn]
        self.bush_cluster = {}
        self.clusters = []
        for t in sorted(self.bushes):
            if t in self.bush_cluster:
                continue
            cid = len(self.clusters)
            tiles, st = [], [t]
            self.bush_cluster[t] = cid
            while st:
                p = st.pop()
                tiles.append(p)
                for q in ((p[0] + 1, p[1]), (p[0] - 1, p[1]), (p[0], p[1] + 1), (p[0], p[1] - 1)):
                    if q in self.bushes and q not in self.bush_cluster:
                        self.bush_cluster[q] = cid
                        st.append(q)
            self.clusters.append(sorted(tiles))
        self.vision = Vision(W, H, self.walls, self.bush_cluster)
        self._fields = {}
        self._build_features()

    # ---- geometry

    def mirror(self, p):
        x, y = p
        if self.sym == 'horizontal':
            return (self.W - 1 - x, y)
        if self.sym == 'vertical':
            return (x, self.H - 1 - y)
        return (self.W - 1 - x, self.H - 1 - y)

    def field(self, seeds, limit=INF, need=None):
        """Walking distance (8-neighbour; walls, holes and altars block) from any seed; seeds may be blocked tiles.
        With `need`, stops once every tile of it is reached (other tiles may then be missing)."""
        W, H, P = self.W, self.H, self.passable
        dist = {}
        dq = deque()
        for s in seeds:
            if s not in dist:
                dist[s] = 0
                dq.append(s)
        left = None
        if need is not None:
            left = set(need) - set(dist)
            if not left:
                return dist
        while dq:
            p = dq.popleft()
            d = dist[p] + 1
            if d > limit:
                continue
            x, y = p
            for dx, dy in N8:
                nx, ny = x + dx, y + dy
                if 0 <= nx < W and 0 <= ny < H and P[nx][ny] and (nx, ny) not in dist:
                    dist[(nx, ny)] = d
                    dq.append((nx, ny))
                    if left is not None:
                        left.discard((nx, ny))
                        if not left:
                            return dist
        return dist

    def field_to(self, tile):
        f = self._fields.get(tile)
        if f is None:
            if len(self._fields) > 4000:
                self._fields.clear()
            f = self._fields[tile] = self.field([tile])
        return f

    def walk(self, a, b):
        return self.field_to(b).get(a, INF)

    def half_of(self, p):
        da, db = self.dspawn[0].get(p, INF), self.dspawn[1].get(p, INF)
        return 0 if da < db else 1 if db < da else -1

    # ---- features

    def _pair(self, feats, key):
        by_key = {key(f): f for f in feats}
        for f in feats:
            f.twin = by_key.get(key(f, mirror=True))

    def _number(self, feats):
        """Number pairs per base prefix by walking distance from the nearer spawn of the pair's own member."""
        groups = {}
        for f in feats:
            groups.setdefault(f.base, []).append(f)
        for base, fs in groups.items():
            reps, seen = [], set()
            for f in fs:
                if id(f) in seen:
                    continue
                seen.add(id(f))
                if f.twin is not None:
                    seen.add(id(f.twin))
                a = f if f.half != 1 else (f.twin or f)
                d = a.dsp[0] if a.half != -1 else min(a.dsp)
                reps.append((d, min(a.tiles), f))
            reps.sort(key=lambda r: (r[0], r[1]))
            for n, (_, _, f) in enumerate(reps, 1):
                for g in {id(f): f, id(f.twin): f.twin}.values():
                    if g is not None:
                        g.base = f'{base}{n}' if len(reps) > 1 or base == 'B' else base

    def _feat(self, kind, base, tiles, info='', fieldless=False):
        """A feature with its walking distance from each spawn (blocked tiles such as altars are reached via a neighbour)."""
        if fieldless:
            fd = None
            dsp = [min(self.dspawn[k].get(t, INF) for t in tiles) for k in (0, 1)]
        else:
            fd = self.field(tiles)
            dsp = [min(fd.get(t, INF) for t in self.spawn[k]) for k in (0, 1)]
        f = Feature(kind, base, tiles, 0 if dsp[0] < dsp[1] else 1 if dsp[1] < dsp[0] else -1, info)
        f.dsp, f.fd = dsp, fd
        return f

    def _build_features(self):
        m = self.raw
        camp_by_id = {c['id']: c for c in m['camps']}
        self.camp_group = {c['id']: c['group'] for c in m['camps']}
        self.groups = []
        for g in m['groups']:
            types = [camp_by_id[c]['type'] for c in g['camps']]
            prim = min(types, key=PRIMARY.index)
            tiles = [tuple(t) for t in g['tiles']]
            comp = '+'.join(f'{types.count(t)}{LETTER[t]}' if types.count(t) > 1 else LETTER[t]
                            for t in PRIMARY if t in types)
            f = self._feat('camp', PREFIX[prim], tiles,
                           f"{comp} {g['gems']}gems {g['gold']}gold respawn {g['respawn']}")
            f.gid = g['id']
            f.mirror_gid = g['mirror']
            f.hp = sum(camp_by_id[c]['hp'] for c in g['camps'])
            self.groups.append(f)
        for f in self.groups:
            f.twin = self.groups[f.mirror_gid]
        self.altars = [self._feat('altar', 'Alt', [t]) for t in self.altar_tiles]
        self._pair(self.altars, lambda f, mirror=False: self.mirror(f.anchor) if mirror else f.anchor)
        self.bush_feats = [self._feat('bush', 'B', tiles, f'{len(tiles)} tiles', fieldless=True) for tiles in self.clusters]
        self._pair(self.bush_feats, lambda f, mirror=False: (self.bush_cluster.get(self.mirror(f.anchor)) if mirror
                                                              else self.bush_cluster[f.anchor]))
        for fs in (self.groups, self.altars, self.bush_feats):
            for f in fs:
                if f.half == -1 and f.twin is not None and f.twin is not f:
                    f.prime = min(f.tiles) > min(f.twin.tiles)
            self._number(fs)
        sp = [self._feat('spawn', 'spawn', self.spawn[t]) for t in (0, 1)]
        sp[0].twin, sp[1].twin = sp[1], sp[0]
        self.spawns = sp
        self.landmarks = self.groups + self.altars + self.spawns
        # Nearest landmark per tile: multi-source walk with labels.
        W, H, P = self.W, self.H, self.passable
        self.near = {}
        dq = deque()
        for f in self.landmarks:
            for t in f.tiles:
                if t not in self.near:
                    self.near[t] = (0, f)
                    dq.append(t)
        while dq:
            p = dq.popleft()
            d, f = self.near[p]
            for dx, dy in N8:
                q = (p[0] + dx, p[1] + dy)
                if 0 <= q[0] < W and 0 <= q[1] < H and P[q[0]][q[1]] and q not in self.near:
                    self.near[q] = (d + 1, f)
                    dq.append(q)
        self.tile_group = {}
        for f in self.groups:
            for t in f.tiles:
                self.tile_group[t] = f
        self.lm_fields = {id(f): f.fd for f in self.landmarks}

    def dist_to(self, f, p):
        return self.lm_fields[id(f)].get(p, INF)

    def nearest(self, p, feats):
        best = min(feats, key=lambda f: self.dist_to(f, p), default=None)
        return best, (self.dist_to(best, p) if best else INF)

    def group(self, gid):
        return self.groups[gid]

    def bush_of(self, p):
        c = self.bush_cluster.get(p)
        return None if c is None else self.bush_feats[c]

    def where(self, p, team):
        """Short tile description relative to a team: `(x,y) Elk2.own+3 bush:B4.own`."""
        if p is None:
            return '-'
        p = tuple(p)
        s = f'({p[0]},{p[1]})'
        if p in self.spawn_set[team]:
            return s + ' spawn.own'
        if p in self.spawn_set[1 - team]:
            return s + ' spawn.enemy'
        d, f = self.near.get(p, (None, None))
        if f is not None:
            s += f' {f.name(team)}' + (f'+{d}' if d else '')
        b = self.bush_of(p)
        if b is not None:
            s += f' bush:{b.name(team)}'
        return s

    def place(self, p, team, max_d=3):
        """Landmark name when within max_d steps of one, else the coordinates with the nearest landmark."""
        if p is None:
            return '-'
        p = tuple(p)
        if p in self.spawn_set[team]:
            return 'spawn.own'
        d, f = self.near.get(p, (None, None))
        b = self.bush_of(p)
        if f is not None and d <= max_d and b is None:
            return f.name(team) + (f'+{d}' if d else '')
        return self.where(p, team)

    # ---- legend

    def legend(self, name):
        out = [f'MAP {name} {self.W}x{self.H} symmetry={self.sym} spawn A {self.box(self.spawn[0])} B {self.box(self.spawn[1])}',
               'Names: pairs are numbered by walking distance from a spawn; in every line .own/.enemy is relative to the '
               "team the line is about (.mid: equidistant; .mid' its mirror twin). +N = N steps from it. d= walking distance.",
               'Camp groups (tiles = capture tiles; comp: M monolith, O golem, E elk, W wolf, g gem cluster, $ gold cluster):']
        for f in sorted(self.groups, key=lambda f: (f.base, f.half)):
            out.append(f'  {f.name(0):12} for team A = {f.name(1):12} for team B  tiles {self.tiles_str(f.tiles)}  {f.info} hp {f.hp:.0f}  '
                       f'walk from spawn A {self.dmin(0, f)} B {self.dmin(1, f)}')
        out.append('Altars:')
        for f in sorted(self.altars, key=lambda f: (f.base, f.half)):
            out.append(f'  {f.name(0):12} for team A = {f.name(1):12} for team B  at {self.tiles_str(f.tiles)}  '
                       f'walk from spawn A {self.dmin(0, f)} B {self.dmin(1, f)}')
        out.append(f'Bush clusters ({len(self.bush_feats)}; edge-connected, sight-blocking; only the own cluster is seen from inside):')
        for f in sorted(self.bush_feats, key=lambda f: (int(f.base[1:]) if f.base[1:].isdigit() else 0, f.half)):
            if f.half == 1 and f.twin is not None and f.twin is not f:
                continue
            xs = [t[0] for t in f.tiles]
            ys = [t[1] for t in f.tiles]
            d, lm = self.near.get(min(f.tiles, key=lambda t: self.near.get(t, (INF,))[0]), (INF, None))
            twin = f' = {f.name(1)} for B; twin {f.twin.name(0)} {self.box(f.twin.tiles)}' if f.twin is not None and f.twin is not f else ''
            out.append(f'  {f.name(0):12} {len(f.tiles):3} tiles {self.box(f.tiles)}'
                       f'  nearest {lm.name(0) if lm else "-"}+{d}{twin}')
        out.append('ASCII (north up; S/X spawn A/B, A altar, M O E W g $ camp tiles, # wall, o hole, " bush, . open):')
        out += self.ascii()
        return out

    @staticmethod
    def dmin(team, f):
        return f.dsp[team]

    @staticmethod
    def box(tiles):
        xs = [t[0] for t in tiles]
        ys = [t[1] for t in tiles]
        return f'x{min(xs)}-{max(xs)} y{min(ys)}-{max(ys)}'

    @staticmethod
    def tiles_str(tiles):
        return ' '.join(f'({x},{y})' for x, y in tiles[:6]) + (' ...' if len(tiles) > 6 else '')

    def ascii(self):
        ch = {}
        for t in self.walls:
            ch[t] = '#'
        for t in self.holes:
            ch[t] = 'o'
        for t in self.bushes:
            ch[t] = '"'
        for c in self.raw['camps']:
            ch[(c['x'], c['y'])] = LETTER[c['type']]
        for t in self.altar_tiles:
            ch[t] = 'A'
        for team, c in ((0, 'S'), (1, 'X')):
            for t in self.spawn[team]:
                ch[t] = c
        step = 1 if max(self.W, self.H) <= 60 else 2
        rows = []
        prio = {'S': 9, 'X': 9, 'A': 8, 'M': 7, 'O': 7, 'E': 7, 'W': 7, 'g': 6, '$': 6, '#': 3, 'o': 2, '"': 1, '.': 0}
        for y in range(self.H - 1, -1, -step):
            row = []
            for x in range(0, self.W, step):
                cs = [ch.get((x + i, y - j), '.') for i in range(step) for j in range(step)
                      if x + i < self.W and y - j >= 0]
                row.append(max(cs, key=lambda c: prio.get(c, 0)))
            rows.append(f'{y:3} ' + ''.join(row))
        if step > 1:
            rows.append('    (2x2 tiles per character)')
        return rows
