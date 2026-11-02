"""Shared loaders for the turn-order measurements: an extracted game (tools/replay/extract.mjs output) with the
real per-round turn order rebuilt from `prio`, and the ast-measure trace lines from the replay zip's stdout.

Turn order of round r: each team sorted by (-priority set by the end of round r-1, id); A starts odd rounds;
alternate, the larger team's extras last (rules rounds.champion_order). `prio` in rounds.json is the value at the
end of the round, i.e. the priority that applies from the next round (validated: reproduces every event `t`).
"""
import gzip
import json
import os
import zipfile
from collections import defaultdict

ACTOR = frozenset(('move', 'attack', 'cast', 'ward', 'shop', 'sell', 'recall_start', 'tribute_start', 'lock_place',
                   'consumable', 'teleport_start', 'blocked'))


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def index(ex):
    return json.load(open(f'{ex}/index.json'))['games']


class G:
    def __init__(self, ex, d):
        self.ex, self.dir = ex, d
        self.meta = json.load(open(f'{ex}/{d}/meta.json'))
        self.R = json.load(gzip.open(f'{ex}/{d}/rounds.json.gz'))
        self.events = [json.loads(l) for l in gzip.open(f'{ex}/{d}/events.jsonl.gz', 'rt')]
        self.N = len(self.R['round'])
        self.C = self.R['champions']
        self.col = {c['id']: c for c in self.C}
        self.ids = [c['id'] for c in self.C]
        self.team = {c['id']: c['team'] for c in self.C}
        self.members = [[c for c in self.ids if self.team[c] == t] for t in (0, 1)]
        self.by_round = defaultdict(list)
        self.first = defaultdict(dict)  # round -> champion -> first actor step
        self.deaths = defaultdict(list)
        for e in self.events:
            self.by_round[e['r']].append(e)
            if e['k'] in ACTOR and e['t'] >= 0:
                self.first[e['r']].setdefault(e['a'], e['s'])
            if e['k'] == 'death':
                self.deaths[e['r']].append(e)
        self._order = {}
        self.type = {c['id']: c['name'] for c in self.meta['champions']}

    # end-of-round state (r >= 1); round 0 = start
    def at(self, c, key, r):
        return self.col[c][key][min(max(r, 1), self.N) - 1]

    def prio(self, c, r):
        return 0 if r <= 0 else self.at(c, 'prio', r)

    def alive(self, c, r):
        return self.at(c, 'alive', r) == 1

    def pos(self, c, r):
        col = self.col[c]
        i = min(max(r, 1), self.N) - 1
        return (col['x'][i], col['y'][i]) if col['alive'][i] and col['x'][i] is not None and col['x'][i] >= 0 else None

    def hp(self, c, r):
        return self.at(c, 'hp', r)

    def team_order(self, t, r):
        """Champion ids of team t by rank in round r."""
        return sorted(self.members[t], key=lambda c: (-self.prio(c, r - 1), c))

    def order(self, r):
        """(seq, slot, rank) of round r."""
        o = self._order.get(r)
        if o is not None:
            return o
        a, b = self.team_order(0, r), self.team_order(1, r)
        if r % 2 == 0:
            a, b = b, a
        seq = []
        for k in range(max(len(a), len(b))):
            seq += a[k:k + 1] + b[k:k + 1]
        slot = {c: k for k, c in enumerate(seq)}
        rank = {}
        for t in (0, 1):
            for k, c in enumerate(self.team_order(t, r)):
                rank[c] = k
        self._order[r] = o = (seq, slot, rank)
        return o

    def starts(self, r):
        """Team that starts round r."""
        return 0 if r % 2 == 1 else 1

    def died_in(self, c, r):
        return any(e['v'] == c for e in self.deaths[r])

    def death(self, c, r):
        for e in self.deaths[r]:
            if e['v'] == c:
                return e
        return None

    def pos_at(self, c, r, s):
        """Position of c at step s of round r (None if dead)."""
        last = None
        for ev in self.by_round[r]:
            if ev['s'] >= s:
                break
            if ev['k'] == 'death' and ev['v'] == c:
                return None
            if ev.get('a') == c:
                if ev['k'] == 'move':
                    last = tuple(ev['to'])
                elif ev['k'] == 'cast' and ev.get('moved'):
                    last = tuple(ev['moved'])
                elif ev['k'] in ('respawn', 'recall_end', 'teleport_end'):
                    last = tuple(ev.get('at') or ev.get('to'))
        if last is not None:
            return last
        return self.pos(c, r - 1)

    def turn_events(self, c, r):
        """Events of c's own turn in round r: its actor events (attacks, casts, moves...)."""
        return [e for e in self.by_round[r] if e.get('a') == c and e['t'] >= 0]

    def champ_damage(self, c, r):
        """Damage c dealt to enemy champions in its turn of round r, and the victims it killed."""
        dmg, kills = 0.0, []
        for e in self.by_round[r]:
            if e.get('a') == c and e['k'] in ('attack', 'cast'):
                for v, x in e.get('dmg') or []:
                    if v in self.team and self.team[v] != self.team[c]:
                        dmg += x
        for e in self.deaths[r]:
            if e.get('by') == c and not e.get('linked'):
                kills.append(e['v'])
        return dmg, kills

    def sees(self, c, r):
        return self.at(c, 'sees', r)


def stdout_lines(source, team):
    """Lines of team `team` (0 = A) from a local replay zip, NULs stripped."""
    z = zipfile.ZipFile(source)
    name = 'team-a.stdout' if team == 0 else 'team-b.stdout'
    if name not in z.namelist():
        return []
    return z.read(name).decode(errors='replace').replace('\x00', '').splitlines()


def traced_team(source, bot='ast-measure'):
    """Team (0/1) of the traced bot in a run_batched replay: -12 has bot 1 as team A."""
    base = os.path.basename(source)
    tag = base.rsplit('-', 1)[1].split('.')[0]
    return 0 if tag == '12' else 1
