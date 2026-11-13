"""Shared helpers for the s3 Prism-war study: game loading from replays/.s3cache and map geometry."""
import collections, glob, gzip, os, pickle

ROOT = '/home/ubuntu/wt/mac13-kronos'
CACHE = os.path.join(ROOT, 'replays/.s3cache')
UNREACH = 10 ** 6


def files():
    return sorted(glob.glob(os.path.join(CACHE, '*.pkl.gz')))


def load(f):
    return pickle.load(gzip.open(f))


def cheb(ax, ay, bx, by):
    return max(abs(ax - bx), abs(ay - by))


def rect_dist(x, y, s):
    return max(0, s['minX'] - x, x - s['maxX'], s['minY'] - y, y - s['maxY'])


def steps_field(mp, t):
    """Walking steps from team t's spawn (8-neighbour; walls, holes, altars block), as own_ground reads them."""
    w, h = mp['w'], mp['h']
    blocked = bytearray(w * h)
    for key in ('walls', 'holes', 'altars'):
        for x, y in mp[key]:
            blocked[y * w + x] = 1
    dist = [UNREACH] * (w * h)
    s = mp['spawn'][t]
    q = collections.deque()
    for x in range(s['minX'], s['maxX'] + 1):
        for y in range(s['minY'], s['maxY'] + 1):
            dist[y * w + x] = 0
            q.append((x, y))
    while q:
        x, y = q.popleft()
        d = dist[y * w + x] + 1
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                nx, ny = x + dx, y + dy
                if (dx or dy) and 0 <= nx < w and 0 <= ny < h:
                    k = ny * w + nx
                    if not blocked[k] and dist[k] > d:
                        dist[k] = d
                        q.append((nx, ny))
    return dist


class Game:
    def __init__(self, g):
        self.g = g
        self.mp = g['map']
        self.ch = g['ch']
        self.T = len(g['rounds'])
        self.names, self.team = g['names'], g['team']
        self.winner = g['result']['winner']
        self.prisms = [i for i, n in self.names.items() if n == 'Prism']
        self.D = g['D']
        self._fields = {}
        self.ev_by_round = collections.defaultdict(list)
        for e in g['ev']:
            self.ev_by_round[e['r']].append(e)

    def field(self, t):
        if t not in self._fields:
            self._fields[t] = steps_field(self.mp, t)
        return self._fields[t]

    def steps(self, t, x, y):
        if x is None:
            return UNREACH
        return self.field(t)[y * self.mp['w'] + x]

    def own_ground(self, t, x, y):
        """own_ground for team t: no farther from t's spawn than from the other's."""
        us, them = self.steps(t, x, y), self.steps(1 - t, x, y)
        return us >= UNREACH or them >= UNREACH or us <= them

    def pos(self, cid, i):
        c = self.ch[cid]
        return c['x'][i], c['y'][i]

    def alive(self, cid, i):
        return 0 <= i < self.T and self.ch[cid]['alive'][i] and self.ch[cid]['x'][i] is not None

    def dist(self, a, b, i):
        ca, cb = self.ch[a], self.ch[b]
        return cheb(ca['x'][i], ca['y'][i], cb['x'][i], cb['y'][i])

    def power(self, cid, i):
        c = self.ch[cid]
        return c['foc'][i] * c['hp'][i]

    def branch(self, cid, i):
        """D line of round i+1 (index i): (branch, farm_group, claim) or None."""
        return self.D.get((i + 1, cid))

    def sees(self, a, b, i):
        return b in (self.ch[a]['sees'][i] or ())

    def allies(self, cid):
        return [c for c in self.ch if self.team[c] == self.team[cid] and c != cid]

    def enemies(self, cid):
        return [c for c in self.ch if self.team[c] != self.team[cid]]

    def nearest(self, cid, others, i):
        x, y = self.pos(cid, i)
        best = UNREACH
        for o in others:
            if self.alive(o, i):
                ox, oy = self.pos(o, i)
                best = min(best, cheb(x, y, ox, oy))
        return best

    def nearest_altar(self, x, y):
        return min((cheb(x, y, ax, ay) for ax, ay in self.mp['altars']), default=UNREACH)

    def group_tiles(self, gid):
        if 0 <= gid < len(self.mp['groups']):
            return self.mp['groups'][gid]['tiles']
        return []
