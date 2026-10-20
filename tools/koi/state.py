"""Step-level champion and camp state rebuilt from events, resynced to the rounds table each round."""
POS_EVENTS = ('move', 'recall_end', 'teleport_end')


class State:
    def __init__(self, g):
        self.g = g
        self.pos, self.hp, self.alive, self.gems = {}, {}, {}, {}
        first = {}
        for e in g.events:
            if e['r'] > 1:
                break
            if 'a' in e and 'f' in e and e['a'] not in first:
                first[e['a']] = tuple(e['f'])
        for c in g.champs:
            cid = c['id']; ch = g.ch(cid)
            self.pos[cid] = first.get(cid, (ch['x'][0], ch['y'][0]))
            self.hp[cid] = ch['maxHp'][0]; self.alive[cid] = True; self.gems[cid] = 0
        self.camp_hp = {c['id']: c['hp'] for c in g.map.camps}
        self.camp_max = dict(self.camp_hp)
        self.group_camps = {gr['id']: gr['camps'] for gr in g.map.groups}
        self.camp_alive = {c: True for c in self.camp_hp}
        self.round = 1

    def sync(self, r):
        i = r - 2
        if i < 0:
            return
        for c in self.g.champs:
            cid = c['id']; ch = self.g.ch(cid)
            if i >= len(ch['x']):
                continue
            self.alive[cid] = bool(ch['alive'][i])
            self.pos[cid] = (ch['x'][i], ch['y'][i]) if ch['alive'][i] and ch['x'][i] is not None else None
            self.hp[cid] = ch['hp'][i]; self.gems[cid] = ch['gems'][i]

    def apply(self, e):
        k = e['k']
        if k in POS_EVENTS:
            self.pos[e['a']] = tuple(e['to'])
        elif k == 'respawn':
            self.pos[e['a']] = tuple(e['at']); self.alive[e['a']] = True
            self.hp[e['a']] = self.g.ch(e['a'])['maxHp'][max(0, e['r'] - 1)]
        elif k == 'death':
            self.alive[e['v']] = False; self.pos[e['v']] = None; self.hp[e['v']] = 0; self.gems[e['v']] = 0
        elif k in ('attack', 'cast'):
            if e.get('moved'):
                self.pos[e['a']] = tuple(e['moved'])
            for v, amt in e.get('dmg', []):
                if v in self.hp:
                    self.hp[v] -= amt
            if e.get('refl') and e['a'] in self.hp:
                self.hp[e['a']] -= e['refl']
            h = e.get('heal')
            if isinstance(h, list):
                for v, amt in h:
                    self.hp[v] = self.hp.get(v, 0) + amt
            for c, amt in e.get('cdmg', []):
                self.camp_hp[c] = self.camp_hp.get(c, 0) - amt
        elif k == 'camp_attack':
            if e.get('tgt') in self.hp and e.get('dmg'):
                self.hp[e['tgt']] -= e['dmg']
            for v, amt in e.get('xdmg', []):
                self.hp[v] -= amt
        elif k == 'camp_death':
            self.camp_alive[e['camp']] = False; self.camp_hp[e['camp']] = 0
        elif k == 'group_respawn':
            for c in self.group_camps.get(e['g'], []):
                self.camp_alive[c] = True; self.camp_hp[c] = self.camp_max[c]
        elif k == 'capture':
            for cid, gm, gd in e['shares']:
                self.gems[cid] = self.gems.get(cid, 0) + gm
        elif k == 'tribute_end':
            self.gems[e['a']] = 0


def walk(g, sync=True):
    """Yield (event, state) with the state as it was just before the event."""
    S = State(g)
    cur = 1
    for e in g.events:
        if e['r'] != cur:
            cur = e['r']
            if sync:
                S.sync(cur)
        S.round = cur
        yield e, S
        S.apply(e)


def turn_order(g, r, chs):
    """Champion ids in round r's turn order; dead champions keep their slot (matches event t on 99.9%)."""
    def prio(c):
        a = chs[c]['prio']; i = r - 2
        return a[i] if 0 <= i < len(a) else 0
    teams = [sorted(g.team_ids[t], key=lambda c: (-prio(c), c)) for t in (0, 1)]
    first = 0 if r % 2 == 1 else 1
    A, B = teams[first], teams[1 - first]
    out = []
    for i in range(max(len(A), len(B))):
        if i < len(A): out.append(A[i])
        if i < len(B): out.append(B[i])
    return out


def max_damage(nm, d, st, foc, cd0, cd1):
    """Most damage a champion can deal this turn to a target at distance d (walk, reset, spells)."""
    r0 = cd0 == 0; r1 = cd1 == 0; opts = [0]
    if nm == 'Stellar':
        if d <= 3: opts.append(st)
        if r0 and d <= 4: opts.append((st if d <= 3 else 0) + 2 * foc)
        if r1 and d <= 5: opts.append((st if d <= 3 else 0) + 1.4 * foc)
    elif nm == 'Cassi':
        if d <= 3: opts.append(st)
        if r0 and d <= 4: opts.append((st if d <= 3 else 0) + 2 * foc)
    elif nm == 'Tavi':
        if d <= 3: opts.append(st)
        if r0 and d <= 3: opts.append(2 * st)
        if r0 and d <= 4: opts.append(st)
        if r1 and d <= 4: opts.append((st if d <= 3 else 0) + 2.2 * foc)
    elif nm == 'Prism':
        if d <= 3: opts.append(st)
        if r0 and d <= 4: opts.append((st if d <= 3 else 0) + 1.5 * foc)
        if r1 and d <= 5: opts.append((st if d <= 3 else 0) + 1.0 * foc)
    elif nm == 'Ren':
        if d <= 2: opts.append(st)
        if r0 and d <= 4: opts.append((st if d <= 1 else 0) + 1.25 * foc)
        if r1 and d <= 4: opts.append(st)
    elif nm in ('Issac', 'Varg'):
        if d <= 2: opts.append(st * (2 if r0 else 1))
        if nm == 'Issac' and r1 and d <= 4: opts.append(st)
    elif nm == 'Ryth':
        if d <= 2: opts.append(st * (2 if r1 else 1))
        if r0 and d <= 5: opts.append((st if d <= 1 else 0) + 1.0 * foc)
    else:
        if d <= 3: opts.append(st)
    return max(opts)
