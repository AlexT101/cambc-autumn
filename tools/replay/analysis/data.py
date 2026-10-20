import gzip
import json
from functools import cached_property
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ANALYSIS = ROOT / 'replays' / '.analysis'

TYPE_ABBR = {'Wolf': 'W', 'Elk': 'E', 'Gem cluster': 'G', 'Gold cluster': '$', 'Monolith': 'M', 'Golem': 'O'}


def load_index():
    return json.loads((ANALYSIS / 'index.json').read_text(encoding='utf-8'))['games']


def _norm(p):
    path = Path(p)
    if not path.is_absolute():
        path = (Path.cwd() / path)
    try:
        return path.resolve().relative_to(ROOT).as_posix().rstrip('/')
    except ValueError:
        return path.resolve().as_posix()


def resolve(sources, index=None):
    """Analysis dirs (unique, in index order) for replay dirs/files, or analysis dir names."""
    index = index if index is not None else load_index()
    out, seen = [], set()
    for src in sources:
        name = Path(src).name
        if (ANALYSIS / name / 'meta.json').exists() and len(name) == 16:
            rows = [r for r in index if r['dir'] == name]
        else:
            p = _norm(src)
            rows = [r for r in index if r['source'] == p or r['source'].startswith(p + '/')]
        if not rows:
            raise SystemExit(f'no extracted replays under {src} (run node tools/replay/extract.mjs {src})')
        for r in rows:
            if r['ok'] and r['dir'] not in seen:
                seen.add(r['dir'])
                out.append(r['dir'])
    return out


def chebyshev(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


class Map:
    def __init__(self, d):
        self.raw = d
        self.hash = d['hash']
        self.W, self.H = d['width'], d['height']
        self.symmetry = d['symmetry']
        self.champs_per_team = d['champsPerTeam']
        self.walls = {tuple(t) for t in d['walls']}
        self.holes = {tuple(t) for t in d['holes']}
        self.bushes = {tuple(t) for t in d['bushes']}
        self.altars = [tuple(t) for t in d['altars']]
        self.spawn = d['spawn']
        self.camps = d['camps']
        self.groups = d['groups']
        self.group_tiles = {}
        for g in self.groups:
            for t in g['tiles']:
                self.group_tiles[tuple(t)] = g['id']
        size = max(self.W, self.H)
        self.cell = max(2, -(-size // 22))

    def mirror(self, x, y):
        if self.symmetry == 'horizontal':
            return (self.W - 1 - x, y)
        if self.symmetry == 'vertical':
            return (x, self.H - 1 - y)
        return (self.W - 1 - x, self.H - 1 - y)

    def own(self, team, p):
        """Position in team A's frame for a team's own-side view."""
        if p is None:
            return None
        return (p[0], p[1]) if team == 0 else self.mirror(p[0], p[1])

    def own_group(self, team, g):
        return g if team == 0 else self.groups[g]['mirror']

    def group_label(self, g):
        grp = self.groups[g]
        types = ''.join(sorted(TYPE_ABBR[t] for t in grp['types']))
        x, y = grp['tiles'][0]
        side = {0: 'own', 1: 'enemy', -1: 'mid'}[grp['side']]
        return f'{types}({x},{y}){side[0]}'

    def group_side(self, g):
        return {0: 'own', 1: 'enemy', -1: 'mid'}[self.groups[g]['side']]

    def in_spawn(self, team, p):
        s = self.spawn[team]
        return p is not None and s['minX'] <= p[0] <= s['maxX'] and s['minY'] <= p[1] <= s['maxY']

    def spawn_center(self, team):
        s = self.spawn[team]
        return ((s['minX'] + s['maxX']) / 2, (s['minY'] + s['maxY']) / 2)

    def altar_dist(self, p):
        return min(chebyshev(p, a) for a in self.altars) if self.altars else 99

    def nearest_altar(self, p):
        return min(self.altars, key=lambda a: chebyshev(p, a))

    def half(self, p):
        """0 if p (team A frame) is nearer team A's spawn, 1 if nearer B's, -1 if equal."""
        a, b = self.spawn_center(0), self.spawn_center(1)
        da, db = chebyshev(p, a), chebyshev(p, b)
        return 0 if da < db else 1 if db < da else -1

    def cell_of(self, p):
        return (p[0] // self.cell, p[1] // self.cell)

    @cached_property
    def grid_size(self):
        return (-(-self.W // self.cell), -(-self.H // self.cell))

    @cached_property
    def landmarks(self):
        """Per cell: a character for the most notable feature (team A frame)."""
        cw, ch = self.grid_size
        counts = {}
        for (x, y) in self.walls:
            counts.setdefault(self.cell_of((x, y)), {}).setdefault('#', 0)
            counts[self.cell_of((x, y))]['#'] += 1
        for (x, y) in self.bushes:
            counts.setdefault(self.cell_of((x, y)), {}).setdefault('~', 0)
            counts[self.cell_of((x, y))]['~'] += 1
        for (x, y) in self.holes:
            counts.setdefault(self.cell_of((x, y)), {}).setdefault('o', 0)
            counts[self.cell_of((x, y))]['o'] += 1
        out = {}
        for c, d in counts.items():
            k = max(d, key=d.get)
            if d[k] * 3 >= self.cell * self.cell:
                out[c] = k
        for camp in self.camps:
            out[self.cell_of((camp['x'], camp['y']))] = {'W': 'w', 'E': 'e', 'G': 'g', '$': '$', 'M': 'M', 'O': 'o'}[TYPE_ABBR[camp['type']]]
        for a in self.altars:
            out[self.cell_of(a)] = 'A'
        for team, ch_ in ((0, 'S'), (1, 'X')):
            s = self.spawn[team]
            for x in range(s['minX'], s['maxX'] + 1):
                for y in range(s['minY'], s['maxY'] + 1):
                    out[self.cell_of((x, y))] = ch_
        return out


_maps = {}


def load_map(h):
    if h not in _maps:
        _maps[h] = Map(json.loads((ANALYSIS / 'maps' / f'{h}.json').read_text(encoding='utf-8')))
    return _maps[h]


class Game:
    def __init__(self, d):
        self.dir = d
        self.path = ANALYSIS / d
        self.meta = json.loads((self.path / 'meta.json').read_text(encoding='utf-8'))
        self.map = load_map(self.meta['map']['hash'])
        self.map_name = self.meta['map']['name']
        self.names = [t['name'] for t in self.meta['teams']]
        self.ratings = [t.get('ratingBefore') for t in self.meta['teams']]
        self.winner = self.meta['result']['winner']
        self.n_rounds = self.meta['result']['rounds']
        self.final_gems = self.meta['result']['gems']
        self.kind = self.meta['sourceKind']
        self.champs = self.meta['champions']
        self.idx = {c['id']: i for i, c in enumerate(self.champs)}
        self.team_of = {c['id']: c['team'] for c in self.champs}
        self.name_of = {c['id']: c['name'] for c in self.champs}
        self.team_ids = [[c['id'] for c in self.champs if c['team'] == t] for t in (0, 1)]
        self.picks = self.meta['draft']['picks']

    def __repr__(self):
        return f'Game({self.dir} {self.map_name} {self.names[0]} vs {self.names[1]})'

    @cached_property
    def events(self):
        with gzip.open(self.path / 'events.jsonl.gz', 'rt', encoding='utf-8') as f:
            return json.loads('[' + ','.join(line for line in f if line.strip()) + ']')

    @cached_property
    def rounds(self):
        with gzip.open(self.path / 'rounds.json.gz') as f:
            return json.load(f)

    def ch(self, cid):
        """Per-round arrays of a champion; index i is the state at the end of round i+1."""
        return self.rounds['champions'][self.idx[cid]]

    @staticmethod
    def at_end(r):
        return r - 1

    def start_idx(self, r):
        """Index of the state at the start of round r."""
        return max(0, r - 2)

    def pos(self, cid, i):
        c = self.ch(cid)
        if i >= len(c['x']) or not c['alive'][i] or c['x'][i] is None:
            return None
        return (c['x'][i], c['y'][i])

    def own_pos(self, cid, p):
        return self.map.own(self.team_of[cid], p)

    def gems_at(self, team, r):
        """Tributed gems of a team at the end of round r (clamped to the last round)."""
        g = self.rounds['gems'][team]
        return g[min(r, len(g)) - 1]

    def label(self, cid):
        return f'{self.name_of[cid]}#{cid}'

    def ref(self, r, extra=''):
        return f'{self.dir} r{r}' + (f' {extra}' if extra else '')

    @cached_property
    def champ_damage(self):
        """Champion-on-champion damage: (s, r, attacker, victim, amount, attacker_pos, victim_pos)."""
        out = []
        for e in self.events:
            k = e['k']
            if k not in ('attack', 'cast'):
                continue
            a = e['a']
            ta = self.team_of[a]
            if 'dmg' in e:
                for v, amt in e['dmg']:
                    if v in self.team_of and self.team_of[v] != ta and amt > 0:
                        vp = tuple(e['to']) if v == e.get('tgt') else None
                        out.append((e['s'], e['r'], a, v, amt, tuple(e['f']), vp))
            if e.get('refl') and e.get('reflBy') in self.team_of:
                out.append((e['s'], e['r'], e['reflBy'], a, e['refl'], None, tuple(e['f'])))
        return out

    @cached_property
    def camp_damage(self):
        """Camp damage to champions: (s, r, victim, amount)."""
        out = []
        for e in self.events:
            if e['k'] == 'camp_attack':
                if e.get('tgt') in self.team_of and e.get('dmg'):
                    out.append((e['s'], e['r'], e['tgt'], e['dmg']))
                for v, amt in e.get('xdmg', []):
                    if v in self.team_of:
                        out.append((e['s'], e['r'], v, amt))
        return out

    @cached_property
    def damaged_rounds(self):
        """{champion id: set of rounds it took any damage}."""
        out = {c['id']: set() for c in self.champs}
        for s, r, a, v, amt, *_ in self.champ_damage:
            out[v].add(r)
        for s, r, v, amt in self.camp_damage:
            out[v].add(r)
        return out

    @cached_property
    def deaths(self):
        return [e for e in self.events if e['k'] == 'death']

    def seen_recently(self, cid, r, k=5):
        """Whether the champion saw an enemy champion at the start of any of its turns in rounds r-k+1..r."""
        sees = self.ch(cid)['sees']
        lo = max(0, r - k)
        return any(sees[i] for i in range(lo, min(r, len(sees))))


def load_game(d):
    return Game(d)
