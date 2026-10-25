"""Per-champion activity track and its segmentation into legs ending at anchor events.

Each champion-round gets one label (first match wins): dead, fight (participant of an engagement spanning the round),
tribute / recall / teleport channel, camp (hit a camp of the group), hold (ended on a cleared group's tile), shop,
move, idle. A leg is a run of move/idle rounds; it ends where the next anchor starts, so its destination is whatever
the champion did next. Idle runs of WAIT_MIN rounds or more are anchors of their own (`wait`)."""

from collections import defaultdict

from analysis.data import chebyshev

WAIT_MIN = 3
CAMP_GAP = 4      # rounds away from a group that still count as one visit
CAMP_NEAR = 5     # Chebyshev distance to a group's tiles that counts as at the group
FIGHT_GAP = 3     # rounds between a champion's hits in one engagement that still count as fighting
GROUP_COLS = ['round', 'group', 'state', 'team', 'timer', 'respawn', 'awake', 'hp']


def short_item(name):
    fam, rest = name.split(' ', 1)
    kind, stat = rest.split(' of ')
    s = fam[:3] + stat[:3]
    return s + '(E)' if kind == 'Emblem' else s


class Item:
    def __init__(self, kind, c, r0, r1, **kw):
        self.kind, self.c, self.r0, self.r1 = kind, c, r0, r1
        self.__dict__.update(kw)

    def __repr__(self):
        return f'<{self.kind} {self.c} r{self.r0}-{self.r1}>'


class Track:
    def __init__(self, v, fights):
        self.v = v
        self.M = v.M
        self.fights = fights
        N = v.N
        self.gstate = self._groups()
        self.fight_of = {}
        for f in fights:
            hit = defaultdict(set)
            for s, r, a, x, *_ in f.its:
                hit[a].add(r)
                hit[x].add(r)
            for c, rs in hit.items():
                rs = sorted(rs)
                for i, r in enumerate(rs):
                    nxt = rs[i + 1] if i + 1 < len(rs) else r
                    for rr in range(r, nxt + 1 if nxt - r <= FIGHT_GAP else r + 1):
                        self.fight_of.setdefault((c, rr), f)
        self.recalls, self.feints = self._recalls()
        self.items = {c: self._segment(c) for c in v.ids}

    def _groups(self):
        """Per group, per round (end state): dict of GROUP_COLS, forward-filled."""
        v = self.v
        rows = defaultdict(list)
        for row in v.g.rounds['groups']:
            rows[row[1]].append(row)
        out = {}
        for gid, rs in rows.items():
            arr = [None] * (v.N + 2)
            j = 0
            cur = None
            for r in range(1, v.N + 1):
                while j < len(rs) and rs[j][0] <= r:
                    cur = dict(zip(GROUP_COLS, rs[j]))
                    j += 1
                arr[r] = cur
            out[gid] = arr
        return out

    def group_at(self, gid, r):
        a = self.gstate.get(gid)
        return a[min(max(r, 1), self.v.N)] if a else None

    def _recalls(self):
        """Real recalls: completed, or ended (any cause) at least 2 rounds after the start. One cancelled in the next
        round is indistinguishable from a feint (start and cancel every turn) and is only counted."""
        v = self.v
        out, feints = [], defaultdict(int)
        open_ = {}
        for e in v.g.events:
            k = e['k']
            if k == 'recall_start':
                open_[e['a']] = e
            elif k == 'recall_end' and e['a'] in open_:
                st = open_.pop(e['a'])
                out.append({'c': e['a'], 'r0': st['r'], 'r1': e['r'], 'from': tuple(st['at']), 'gems': st['gems'],
                            'done': True})
            elif k == 'recall_cancel' and e['a'] in open_:
                st = open_.pop(e['a'])
                if e['r'] - st['r'] <= 1:
                    feints[e['a']] += 1
                else:
                    out.append({'c': e['a'], 'r0': st['r'], 'r1': e['r'], 'from': tuple(st['at']), 'gems': st['gems'],
                                'done': False, 'cause': 'aborted by itself' if e.get('cause') == 'manual' else e.get('cause')})
        return out, feints

    # ---- labels

    def _labels(self, c):
        v, M = self.v, self.M
        N = v.N
        lab = [None] * (N + 1)
        rec_rounds = {}
        for rc in self.recalls:
            if rc['c'] == c:
                for r in range(rc['r0'], rc['r1'] + 1):
                    rec_rounds[r] = rc
        info = defaultdict(dict)
        for r in range(1, N + 1):
            ev = [e for e in v.by_round[r] if e.get('a') == c]
            camp_hit = defaultdict(float)
            for e in ev:
                if e['k'] in ('attack', 'cast') and e.get('cdmg'):
                    for camp, amt in e['cdmg']:
                        camp_hit[M.camp_group[camp]] += amt
            kinds = {e['k'] for e in ev}
            alive_end = v.at(c, 'alive', r)
            alive_start = v.start_pos(c, r) is not None
            p0, p1 = v.start_pos(c, r), v.pos(c, r)
            info[r] = {'camp_hit': camp_hit, 'ev': ev}
            f = self.fight_of.get((c, r))
            chan = v.at(c, 'chan', r)
            if not alive_start and not alive_end:
                lab[r] = ('dead', None)
            elif not alive_end:
                lab[r] = ('fight', f) if f else ('died', None)
            elif 'tribute_start' in kinds or 'tribute_end' in kinds or chan == 2:
                lab[r] = ('trib', None)
            elif r in rec_rounds:
                lab[r] = ('recall', id(rec_rounds[r]))
            elif 'teleport_start' in kinds or chan == 3 or 'teleport_end' in kinds:
                lab[r] = ('tp', None)
            elif f:
                lab[r] = ('fight', f)
            elif camp_hit:
                lab[r] = ('camp', max(camp_hit, key=camp_hit.get))
            elif p1 in M.tile_group and (self.group_at(M.tile_group[p1].gid, r) or {}).get('state') == 2:
                lab[r] = ('hold', M.tile_group[p1].gid)
            elif 'shop' in kinds or 'sell' in kinds:
                lab[r] = ('shop', None)
            elif p0 != p1:
                lab[r] = ('move', None)
            else:
                lab[r] = ('idle', None)
        return lab, info

    def _segment(self, c):
        v, M = self.v, self.M
        lab, info = self._labels(c)
        N = v.N
        runs = []
        r = 1
        while r <= N:
            k = lab[r]
            j = r
            while j + 1 <= N and lab[j + 1] == k:
                j += 1
            runs.append([k[0], k[1], r, j])
            r = j + 1
        # Merge camp/hold runs of one group (with short excursions near it) into visits.
        merged = []
        for run in runs:
            kind = 'camp' if run[0] in ('camp', 'hold') else run[0]
            if kind == 'camp':
                gid = run[1]
                # look back over short move/idle runs to a visit of the same group
                back = []
                while merged and merged[-1][0] in ('move', 'idle') and merged[-1][3] - merged[-1][2] + 1 <= CAMP_GAP:
                    back.append(merged.pop())
                if merged and merged[-1][0] == 'camp' and merged[-1][1] == gid and all(
                        self._near_group(c, gid, b[2], b[3]) for b in back):
                    merged[-1][3] = run[3]
                    continue
                merged += reversed(back)
                merged.append(['camp', gid, run[2], run[3]])
            else:
                merged.append(run)
        flat = []
        for run in merged:
            if run[0] in ('move', 'idle') and flat and flat[-1][0] == 'move':
                flat[-1][3] = run[3]
            else:
                flat.append(['move' if run[0] == 'idle' else run[0]] + run[1:])
        items = []
        for kind, key, r0, r1 in flat:
            if kind in ('move', 'idle'):
                items += self._legs(c, r0, r1, info)
            elif kind == 'camp':
                items.append(self._camp(c, key, r0, r1, info))
            elif kind == 'fight':
                items.append(Item('fight', c, r0, r1, fight=key))
            elif kind in ('dead', 'died'):
                if kind == 'dead' and r0 > 1 and lab[r0 - 1][0] == 'fight' and not v.at(c, 'alive', r0 - 1):
                    r0 -= 1
                if items and items[-1].kind == 'dead':
                    items[-1].r1 = r1
                else:
                    items.append(Item('dead', c, r0, r1))
            elif kind == 'trib':
                items += self._trib(c, r0, r1)
            elif kind == 'recall':
                rc = next(x for x in self.recalls if id(x) == key)
                items.append(Item('recall', c, r0, r1, rc=rc))
            elif kind == 'shop':
                items.append(Item('shop', c, r0, r1))
            elif kind == 'tp':
                items.append(Item('tp', c, r0, r1))
        # Point anchors: wards, locks, hidden-blocker bumps go into the item covering the round.
        self._attach_points(c, items, info)
        return items

    def _near_group(self, c, gid, r0, r1):
        tiles = self.M.group(gid).tiles
        for r in range(r0, r1 + 1):
            p = self.v.pos(c, r)
            if p is None or min(chebyshev(p, t) for t in tiles) > CAMP_NEAR:
                return False
        return True

    def _legs(self, c, r0, r1, info):
        """Split a move/idle run at idle stretches >= WAIT_MIN and at ward placements."""
        v = self.v
        out = []
        cut = set()
        for r in range(r0, r1 + 1):
            pass
        start = r0
        r = r0
        while r <= r1:
            if v.pos(c, r) == v.start_pos(c, r):
                j = r
                while j + 1 <= r1 and v.pos(c, j + 1) == v.pos(c, j) and (j + 1) not in cut:
                    j += 1
                if j - r + 1 >= WAIT_MIN:
                    if r > start:
                        out.append(self._leg(c, start, r - 1))
                    out.append(Item('wait', c, r, j, at=v.pos(c, r)))
                    start = j + 1
                    r = j + 1
                    continue
            if r in cut:
                out.append(self._leg(c, start, r))
                start = r + 1
            r += 1
        if start <= r1:
            out.append(self._leg(c, start, r1))
        return out

    def _leg(self, c, r0, r1):
        v, M = self.v, self.M
        a, b = v.start_pos(c, r0), v.pos(c, r1)
        path = [a] + [v.pos(c, r) for r in range(r0, r1 + 1)]
        steps = sum(1 for i in range(1, len(path)) if path[i] != path[i - 1])
        dashes = sum(1 for r in range(r0, r1 + 1) for e in v.by_round[r]
                     if e.get('a') == c and e['k'] == 'cast' and e.get('moved'))
        fd = M.field([b], need={p for p in path if p}) if b else {}
        dec = mv = 0
        for i in range(1, len(path)):
            if path[i] != path[i - 1] and path[i] and path[i - 1]:
                mv += 1
                if fd.get(path[i], 1 << 30) < fd.get(path[i - 1], 1 << 30):
                    dec += 1
        d = fd.get(a, None) if a else None
        return Item('leg', c, r0, r1, a=a, b=b, steps=steps, dashes=dashes, d=d, mono=dec / mv if mv else 1.0,
                    path=path, fd=fd)

    def _camp(self, c, gid, r0, r1, info):
        v = self.v
        dealt = sum(info[r]['camp_hit'].get(gid, 0) for r in range(r0, r1 + 1))
        g0 = self.group_at(gid, r0 - 1) or {}
        it = Item('camp', c, r0, r1, gid=gid, dealt=dealt, hp0=g0.get('hp'), state0=g0.get('state'))
        it.cleared = it.capture = it.reset = it.woke = None
        it.allies = set()
        it.taken = 0.0
        it.held = [r for r in range(r0, r1 + 1) if v.pos(c, r) in self.M.tile_group and self.M.tile_group[v.pos(c, r)].gid == gid]
        for r in range(r0, r1 + 8):
            for e in v.by_round.get(r, []):
                k = e['k']
                if e.get('g') != gid and k not in ('camp_attack', 'attack', 'cast'):
                    continue
                if k == 'group_clear' and e['g'] == gid and r <= r1 + 1 and it.cleared is None:
                    it.cleared = (r, e.get('by'))
                elif k == 'group_wake' and e['g'] == gid and r <= r1:
                    it.woke = (r, e.get('by'))
                elif k == 'capture' and e['g'] == gid and (r <= r1 + 1 or e['team'] == v.team[c]):
                    if it.capture is None and (r <= r1 + 1 or it.cleared):
                        it.capture = (r, e['team'], e['shares'])
                elif k == 'capture_reset' and e['g'] == gid and r <= r1:
                    it.reset = (r, e.get('left'), e.get('contested'), e['team'])
                elif k == 'camp_attack' and r <= r1:
                    if e.get('tgt') == c:
                        it.taken += e.get('dmg', 0)
                    it.taken += sum(a for x, a in e.get('xdmg', []) if x == c)
                elif k in ('attack', 'cast') and r0 <= r <= r1 and e.get('cdmg') and e['a'] != c \
                        and v.team[e['a']] == v.team[c] and any(self.M.camp_group[x] == gid for x, _ in e['cdmg']):
                    it.allies.add(e['a'])
        return it

    def _trib(self, c, r0, r1):
        """One item per tribute channel in the run (back-to-back channels at one altar are separate)."""
        v = self.v
        out = []
        it = None
        for r in range(r0, min(v.N, r1 + 1) + 1):
            for e in v.by_round[r]:
                if e.get('a') != c:
                    continue
                if e['k'] == 'tribute_start':
                    it = Item('trib', c, r, r, start=e, end=None, cancel=None)
                    out.append(it)
                elif e['k'] in ('tribute_end', 'tribute_cancel') and it is not None and it.end is None and it.cancel is None:
                    setattr(it, 'end' if e['k'] == 'tribute_end' else 'cancel', e)
                    it.r1 = r
        if not out:
            out.append(Item('trib', c, r0, r1, start=None, end=None, cancel=None))
        for it in out:
            it.r1 = max(it.r1, it.r0)
            seen = set()
            for r in range(it.r0, it.r1 + 1):
                seen |= set(v.at(c, 'sees', r))
            it.seen = seen
            it.hit = sum(x[4] for f in self.fights if f.r0 <= it.r1 and f.r1 >= it.r0 for x in f.its
                         if x[3] == c and it.r0 <= x[1] <= it.r1)
        return out

    def _attach_points(self, c, items, info):
        for it in items:
            it.points = []
            for r in range(it.r0, it.r1 + 1):
                for e in info[r]['ev'] if r in info else []:
                    if e['k'] in ('ward', 'lock_place', 'blocked', 'consumable', 'tribute_blocked', 'shop', 'sell'):
                        it.points.append(e)
