"""One extracted game with exact turn-order lookups: who acted when, and what each champion saw at its turn start."""

from collections import defaultdict

import json

from analysis.data import ANALYSIS, Game

SHORT = {'Vesper Vale': 'Vesper', 'Heart of Ruin': 'HoR'}
ACTOR = frozenset(('move', 'attack', 'cast', 'ward', 'shop', 'sell', 'recall_start', 'tribute_start', 'lock_place',
                   'consumable', 'teleport_start', 'blocked'))
ARRIVE = ('respawn', 'recall_end', 'teleport_end')
_enums = {}


def enums(root=ANALYSIS):
    if root not in _enums:
        _enums[root] = json.loads((root / 'enums.json').read_text(encoding='utf-8'))
    return _enums[root]


class View:
    def __init__(self, d, mapinfo, teams=None):
        g = self.g = Game(d)
        self.dir = d
        self.M = mapinfo
        self.meta = g.meta
        names = list(teams or g.names)
        if names[0] == names[1]:
            names = [names[0] + '#A', names[1] + '#B']
        self.team_name = names
        self.N = len(g.rounds['round'])
        assert g.rounds['round'][0] == 1 and g.rounds['round'][-1] == self.N
        self.C = g.rounds['champions']
        self.ids = [c['id'] for c in self.C]
        self.col = {c['id']: c for c in self.C}
        self.team = {c['id']: c['team'] for c in self.C}
        self.type = {c['id']: SHORT.get(g.name_of[c['id']], g.name_of[c['id']]) for c in self.C}
        self.by_round = defaultdict(list)
        self.first, self.last = defaultdict(dict), defaultdict(dict)
        self.arrive = {}
        self.deaths = defaultdict(list)
        for e in g.events:
            r = e['r']
            self.by_round[r].append(e)
            k = e['k']
            if k in ACTOR and e['t'] >= 0:
                self.first[r].setdefault(e['a'], e['s'])
                self.last[r][e['a']] = e['s']
            elif k in ARRIVE:
                self.arrive[(r, e['a'])] = tuple(e.get('at') or e.get('to'))
            elif k == 'death':
                self.deaths[r].append(e)
        self._slots = {}
        self.item_names = enums()['items']

    # ---- labels

    def tn(self, c):
        """`[Team] Type` for a champion."""
        return f'[{self.team_name[self.team[c]]}] {self.type[c]}'

    def rel(self, c, me):
        """Another champion named relative to `me`: `ally Ryth` / `enemy Prism`."""
        return ('ally ' if self.team[c] == self.team[me] else 'enemy ') + self.type[c]

    def ally_enemy(self, c, team):
        return ('' if self.team[c] == team else 'enemy ') + self.type[c]

    # ---- per-round state (end of round r)

    def at(self, c, key, r):
        a = self.col[c][key]
        return a[min(max(r, 1), self.N) - 1]

    def pos(self, c, r):
        """End-of-round position (None while dead); r = 0 gives the start position."""
        if r <= 0:
            for e in self.by_round[1]:
                if e.get('a') == c and 'f' in e:
                    return tuple(e['f'])
            r = 1
        col = self.col[c]
        i = min(r, self.N) - 1
        return (col['x'][i], col['y'][i]) if col['alive'][i] and col['x'][i] is not None else None

    def start_pos(self, c, r):
        """Position at the start of c's own turn in round r (after a respawn or channel arrival at that turn start)."""
        if (r, c) in self.arrive:
            return self.arrive[(r, c)]
        return self.pos(c, r - 1) if not self.died_before_turn(c, r) else None

    # ---- turn order

    def slots(self, r):
        """Champion ids in turn order for round r (rules.rounds.champion_order; reproduces every recorded `t`)."""
        s = self._slots.get(r)
        if s is not None:
            return s
        i = max(r - 2, 0)
        order = []
        for team in (0, 1):
            tid = [c for c in self.ids if self.team[c] == team]
            order.append(sorted(tid, key=lambda x: (-self.col[x]['prio'][i] if r > 1 else 0, x)))
        a, b = (order[0], order[1]) if r % 2 == 1 else (order[1], order[0])
        seq = []
        for k in range(max(len(a), len(b))):
            seq += a[k:k + 1] + b[k:k + 1]
        self._slots[r] = s = {c: k for k, c in enumerate(seq)}
        s['_seq'] = seq
        return s

    def turn_step(self, c, r):
        """Step at which c's turn in round r starts (fractional when it did nothing recorded)."""
        f = self.first[r].get(c)
        if f is not None:
            return f
        sl = self.slots(r)
        k = sl[c]
        lo = max((self.last[r][q] for q in sl['_seq'][:k] if q in self.last[r]), default=None)
        if lo is None:
            ev = self.by_round[r]
            lo = ev[0]['s'] - 1 if ev else 0
        return lo + 0.5

    def died_before_turn(self, c, r):
        ts = self.turn_step(c, r)
        return any(e['v'] == c and e['s'] < ts for e in self.deaths[r])

    def sees_before(self, c, r, s):
        """Enemy ids c saw at its latest turn start before step s of round r."""
        if self.turn_step(c, r) < s:
            return self.at(c, 'sees', r)
        return self.at(c, 'sees', r - 1) if r > 1 else []

    def pos_at(self, e, r, s):
        """Position of e at step s of round r (None if dead)."""
        last = None
        for ev in self.by_round[r]:
            if ev['s'] >= s:
                break
            if ev['k'] == 'death' and ev['v'] == e:
                return None
            if ev.get('a') == e:
                if ev['k'] == 'move':
                    last = tuple(ev['to'])
                elif ev['k'] == 'cast' and ev.get('moved'):
                    last = tuple(ev['moved'])
                elif ev['k'] in ARRIVE:
                    last = tuple(ev.get('at') or ev.get('to'))
        if last is not None:
            return last
        p = self.pos(e, r - 1)
        if p is None and (r, e) in self.arrive and self.turn_step(e, r) < s:
            return self.arrive[(r, e)]
        return p
