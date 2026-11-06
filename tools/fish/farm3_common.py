"""Shared helpers for the farm3 study (research/fish-2026-11-05/FARM3.md).

Observer caches: replays/fish-farm3/obs/<SHA16>.json.gz (farm3_decode.mjs, one camp-phase snapshot
per round) and replays/fish-team/<SHA16>.json.gz (team_decode.mjs, actions with targets). Both are
labels and descriptive data, never policy inputs.
"""
import collections
import gzip
import json
from pathlib import Path

OBS = Path('replays/fish-farm3/obs')
TEAM = Path('replays/fish-team')
HP = [1350, 2400, 120, 120, 20000, 5000]
GOLD = [40, 90, 0, 20, 300, 160]
GEMS = [4, 15, 7, 0, 200, 36]
CAMP_NAMES = ['Wolf', 'Elk', 'Gem', 'Gold', 'Monolith', 'Golem']
NAMES = ['Ryth', 'Vesper', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'HoR']
# obs champion columns
ID, ALIVE, X, Y, HPC, MAXHP, GOLDC, GEMSC, EARNED, CT, CTIMER, KILLS, DEATHS = range(13)
# group state codes
UNKNOWN, CAMPS, EMPTY, RESPAWNING = range(4)
COHORT_MANIFESTS = [
    ('model', 'research/fish-2026-11-05/manifest.json'),
    ('confirm', 'research/fish-2026-11-05/confirmation-manifest.json'),
    ('third', 'research/fish-2026-11-05/third-manifest.json'),
    ('fourth', 'research/fish-2026-11-05/fourth-manifest.json'),
    ('fifth', 'research/fish-2026-11-05/fifth-manifest.json'),
    ('sixth', 'research/fish-2026-11-05/sixth-manifest.json'),
]


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def entries(cohorts=None):
    seen = set()
    for name, manifest in COHORT_MANIFESTS:
        if cohorts and name not in cohorts:
            continue
        for e in json.loads(Path(manifest).read_text()):
            if e['sha256'] in seen:
                continue
            seen.add(e['sha256'])
            yield name, e


def load(path):
    with gzip.open(path) as f:
        return json.load(f)


def mirror(md, p):
    x, y = p
    s = md['symmetry']
    return (md['width'] - 1 - x if s != 'vertical' else x, md['height'] - 1 - y if s != 'horizontal' else y)


def spawn_tiles(md, side):
    s = md['spawnA']  # maxima exclusive
    tiles = {(x, y) for y in range(s['minY'], s['maxY']) for x in range(s['minX'], s['maxX'])}
    return tiles if side == 0 else {mirror(md, p) for p in tiles}


def bfs(md, sources, blocked):
    seen = {p: 0 for p in sources}
    q = collections.deque(sources)
    W, H = md['width'], md['height']
    while q:
        x, y = q.popleft(); d = seen[x, y] + 1
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                p = (x + dx, y + dy)
                if (dx or dy) and 0 <= p[0] < W and 0 <= p[1] < H and p not in blocked and p not in seen:
                    seen[p] = d; q.append(p)
    return seen


class Game:
    """Static geometry of one observer game, with Fish's side as `side`."""

    def __init__(self, obs):
        self.obs = obs
        md = self.md = obs['mapData']
        self.side = obs['side']
        self.fish = [c['id'] for c in obs['roster'] if c['team'] == self.side]
        self.enemy = [c['id'] for c in obs['roster'] if c['team'] != self.side]
        self.type = {c['id']: c['type'] for c in obs['roster']}
        self.own_spawn = spawn_tiles(md, self.side)
        self.enemy_spawn = spawn_tiles(md, 1 - self.side)
        terrain = set(map(tuple, md['walls'] + md['holes'] + md['altars']))
        camps = obs['camps']
        self.camp_tiles = {(c['x'], c['y']): c['id'] for c in camps}
        # static ids: as breadth.static_groups (cardinal components, min tile first)
        remaining = set(self.camp_tiles)
        self.groups = []
        self.static_of = {}
        while remaining:
            p = min(remaining); remaining.remove(p)
            stack = [p]; tiles = []
            while stack:
                q = stack.pop(); tiles.append(q)
                for n in ((q[0] + 1, q[1]), (q[0] - 1, q[1]), (q[0], q[1] + 1), (q[0], q[1] - 1)):
                    if n in remaining:
                        remaining.remove(n); stack.append(n)
            tiles.sort()
            members = [self.camp_tiles[t] for t in tiles]
            types = [camps[k]['type'] for k in members]
            sid = len(self.groups)
            self.groups.append(dict(id=sid, tiles=tiles, members=members, types=types, live=camps[members[0]]['group'],
                                    gold=sum(GOLD[t] for t in types), gems=sum(GEMS[t] for t in types),
                                    hp=sum(HP[t] for t in types)))
        self.by_live = {g['live']: g for g in self.groups}
        self.group_of_camp = {k: g['id'] for g in self.groups for k in g['members']}
        self.group_at = {t: g['id'] for g in self.groups for t in g['tiles']}
        blocked = terrain | set(self.camp_tiles)
        self.d_own = bfs(md, sorted(self.own_spawn), blocked | self.enemy_spawn)
        self.d_enemy = bfs(md, sorted(self.enemy_spawn), blocked | self.own_spawn)
        for g in self.groups:
            adj = {(x + dx, y + dy) for x, y in g['tiles'] for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
            g['d_own'] = min((self.d_own.get(p, 999) for p in adj), default=999)
            g['d_enemy'] = min((self.d_enemy.get(p, 999) for p in adj), default=999)
            g['terr'] = g['d_enemy'] - g['d_own']  # > 0: Fish's side
            g['big'] = max(g['types'], key=lambda t: HP[t])
            g['label'] = '+'.join(sorted({CAMP_NAMES[t] for t in g['types']}))

    def side_of(self, p):
        a, b = self.d_own.get(tuple(p)), self.d_enemy.get(tuple(p))
        if a is None or b is None:
            return 0
        return (b > a) - (b < a)


def team_rounds(key):
    p = TEAM / f'{key}.json.gz'
    return {R['r']: R for R in load(p)['rounds']} if p.exists() else None


def payouts(G):
    """Capture payouts from consecutive round snapshots: (round, static group, team, recipients)."""
    out = []
    rounds = G.obs['rounds']
    for prev, cur in zip(rounds, rounds[1:]):
        for live, (st, team, timer, resp) in enumerate(cur['gs']):
            pst = prev['gs'][live]
            if st == RESPAWNING and pst[0] == EMPTY and pst[1] in (0, 1):
                g = G.by_live.get(live)
                if g is None:
                    continue
                tiles = set(g['tiles'])
                rec = [c[ID] for c in cur['ch'] if c[ALIVE] and (c[X], c[Y]) in tiles]
                out.append(dict(round=cur['r'], group=g['id'], team=pst[1], recipients=rec))
    return out


def write_json(path, obj):
    path = Path(path)
    if path.exists():
        raise SystemExit(f'refusing to overwrite {path}')
    path.write_text(json.dumps(obj, indent=1) + '\n')
