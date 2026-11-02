# Python port of v66's fight simulator (bots/baselines/v66/src/model/safety.cc: Side, act, simulate, trade),
# full play-out (the simulate<true> path, no early exits). Inputs are the level-2 `TE k=sides` fighters plus each
# fighter's kit (type, Focus). Hooks let callers change the model (counterfactuals): see simulate()'s options.
import math
NEVER = 2147483647
CD = 8
HORIZON = 2 * CD + 1

# type -> (ranged, abilities[(kind, mult, stuns, duration)], passive)
R, D, S, DA, HE, SH = 'reset', 'damage', 'stun', 'dash', 'heal', 'shield'
FACTS = {
    'ryth': ((D, 1, True, 0, 'ground'), (R, 0, False, 0, '')), 'vesper': ((R, 0, False, 0, ''), (DA, 0, False, 0, '')),
    'vendetta': ((R, 0, False, 0, ''), (DA, 0, False, 0, '')), 'cassi': ((D, 2, False, 0, 'unit'), (S, 0, True, 0, 'unit')),
    'issac': ((R, 0, False, 0, ''), (DA, 0, False, 0, '')), 'stellar': ((D, 2, False, 0, 'unit'), (D, 1.4, False, 0, 'ground')),
    'prism': ((D, 1.5, True, 0, 'unit'), (D, 1, False, 0, 'ground')), 'marcella': ((R, 0, True, 0, ''), (D, 2, False, 0, 'unit')),
    'willow': ((HE, 3, False, 0, 'ally'), (R, 0, False, 0, '')), 'ren': ((D, 1.1, True, 0, 'unit'), (DA, 0, False, 0, '')),
    'varg': ((R, 0, False, 0, ''), (SH, 2.5, False, 5, 'self')), 'tavi': ((R, 0, False, 0, ''), (D, 1.6, True, 0, 'unit')),
    'hor': ((SH, 1.5, False, 5, 'self'), ('land', 1.5, True, 0, 'land')),
}
BASE_STR = {'ryth': 45, 'vesper': 45, 'vendetta': 70, 'cassi': 30, 'issac': 45, 'stellar': 30, 'prism': 35, 'marcella': 45, 'willow': 55,
            'ren': 35, 'varg': 45, 'tavi': 45, 'hor': 30}
BASE_HP = {'ryth': 1200, 'vesper': 1000, 'vendetta': 1000, 'cassi': 600, 'issac': 900, 'stellar': 650, 'prism': 700, 'marcella': 1200,
           'willow': 700, 'ren': 900, 'varg': 1000, 'tavi': 900, 'hor': 1000}


def make_kit(typ, strength, focus_scaled, focus_raw):
    kit = []
    for (kind, mult, stuns, dur, tgt) in FACTS[typ]:
        e = dict(value=0.0, damage=0.0, heal=0.0, heals_self=False, stuns=stuns, heals_ally=False, hits=1, duration=dur, kind=kind)
        resets = kind == R
        damages = kind in (D, 'land')
        if resets: e['damage'] = strength
        if damages: e['damage'] = mult * focus_scaled
        if kind in (SH, HE): e['heal'] = mult * focus_raw
        e['heals_self'] = kind == SH
        e['heals_ally'] = e['heal'] != 0 and not e['heals_self']
        e['hits'] = 2 if resets or damages else 1
        e['value'] = (strength if stuns else 0) + e['damage'] + e['heal']
        e['ground'] = tgt in ('ground', 'land')
        kit.append(e)
    pref = [1, 0] if kit[1]['value'] > kit[0]['value'] else [0, 1]
    return kit, pref


class Fighter:
    __slots__ = ('typ', 'kit', 'pref', 'strength', 'ready', 'next_cast', 'arrives', 'stun_immune', 'linked', 'health', 'max_health', 'shield',
                 'shield_until', 'retaliation', 'taken', 'link', 'focus_raw', 'focus_scaled', 'base_strength', 'hor', 'ident', 'dealt', 'took',
                 'vendetta', 'hor0', 'acts', 'dealt5', 'acts5', 'health0', 'mult', 'untarget')

    def copy(self):
        f = Fighter.__new__(Fighter)
        for k in Fighter.__slots__: setattr(f, k, getattr(self, k))
        f.ready = list(self.ready)
        return f


def fighter(typ, health, max_health, shield, strength, arrives, ready, focus_raw, focus_scaled=None, taken=1.0, ident=None):
    f = Fighter()
    f.typ = typ; f.strength = strength; f.ready = list(ready); f.arrives = arrives
    f.health = health; f.max_health = max_health; f.shield = shield
    f.shield_until = NEVER  # set by caller if shielded (unknown in traces: shield_turns)
    f.stun_immune = typ == 'marcella'; f.linked = typ in ('cassi', 'issac'); f.link = -1
    f.focus_raw = focus_raw
    f.focus_scaled = focus_scaled if focus_scaled is not None else focus_raw
    f.retaliation = 0.2 * focus_raw if typ == 'ren' else 0.0
    f.taken = taken; f.ident = ident; f.hor = typ == 'hor'; f.vendetta = typ == 'vendetta'
    f.kit, f.pref = make_kit(typ, strength, f.focus_scaled, focus_raw)
    f.next_cast = min(f.ready)
    f.dealt = 0.0; f.took = 0.0; f.acts = 0; f.dealt5 = 0.0; f.acts5 = 0; f.health0 = health; f.mult = 1.0; f.untarget = False
    f.base_strength = strength
    f.hor0 = hor_scale(f)  # the passive at the health the fight starts from, which the kit holds
    return f


class Side:
    def __init__(self, fighters, self_idx=-1, camp=0.0):
        self.f = [x.copy() for x in fighters][:6]
        self.f0 = [x.copy() for x in self.f]  # as the fight starts
        for i, g in enumerate(self.f):
            g.link = -1
        for i, g in enumerate(self.f):
            if g.linked:
                for j in range(i):
                    if self.f[j].linked: g.link = j; self.f[j].link = i
        self.alive = sum(g.health > 0 for g in self.f)
        self.turn = 0; self.self = self_idx; self.stunned = 0; self.camp = camp

    def weakest(self):
        best = -1
        for i, g in enumerate(self.f):
            if g.health > 0 and not g.untarget and (best < 0 or g.health + g.shield < self.f[best].health + self.f[best].shield): best = i
        return best

    def weakest_hurt(self, caster):
        best = -1
        for i, g in enumerate(self.f):
            if i != caster and g.health > 0 and g.health < g.max_health and (best < 0 or g.health < self.f[best].health): best = i
        return best

    def take(self, i, damage):
        f = self.f[i]
        d = damage * f.taken
        if f.shield != 0:
            a = min(d, f.shield); f.shield -= a; d -= a
        lost = min(d, f.health)
        f.health -= lost; f.took += lost
        damage = (d - lost) / f.taken
        if f.health > 0: return damage
        self.alive -= 1
        if f.link >= 0:
            self.alive -= self.f[f.link].health > 0
            self.f[f.link].health = 0
        return damage

    def hurt(self, damage, first=None):
        if damage <= 0: return
        i = self.weakest() if first is None else first
        if i < 0: return
        while i >= 0:
            damage = self.take(i, damage)
            i = self.weakest() if damage > 0 else -1

    def hurt_one(self, i, damage):
        if damage <= 0 or self.f[i].health <= 0: return
        self.take(i, damage)


class Opts:
    """Model changes for counterfactuals (defaults = v66)."""
    def __init__(self, **kw):
        self.hor_dynamic = False      # Heart of Ruin's passive from current health each turn
        self.vendetta_reset = False   # a kill by their side readies Vendetta's slots
        self.splash = 1.0             # ground casts / HoR landing hit this many members (expected)
        self.their_rate = 1.0         # their side's damage multiplier
        self.our_rate = 1.0           # our side's damage multiplier
        self.our_basic_share = 1.0    # share of our turns each of our fighters lands its basic attack
        self.their_basic_share = 1.0
        self.focus_spread = None      # their damage: 'even' spreads over our members in reach instead of the weakest
        self.__dict__.update(kw)


def cast(f, fi, turn, self, other, opts):
    for s in f.pref:
        c = f.kit[s]
        if f.ready[s] > turn: continue
        target = self.weakest_hurt(fi) if c['heals_ally'] else -1
        if c['heals_ally'] and target < 0: continue
        f.ready[s] = turn + CD
        f.next_cast = min(f.ready)
        other.stunned += c['stuns']
        if c['heals_self']:
            f.shield = c['heal']; f.shield_until = turn + c['duration']
        elif target >= 0:
            t = self.f[target]; t.health = min(t.max_health, t.health + c['heal'])
        dmg = c['damage']
        if opts.hor_dynamic and f.hor and not c['heals_self']: dmg *= hor_scale(f) / f.hor0
        return c['hits'], dmg * (opts.splash if c['ground'] else 1.0)
    return 1, 0.0


def hor_scale(f):
    return 1 + 0.5 * min(1, max(0, 1 - f.health / f.max_health))


def strength_now(f, opts):
    if opts.hor_dynamic and f.hor: return f.strength * hor_scale(f) / f.hor0
    return f.strength


def stun_skips(self, turn):
    skip = 0
    for _ in range(self.stunned):
        best = -1
        for i, f in enumerate(self.f):
            if not (skip >> i & 1) and f.health > 0 and f.arrives <= turn and not f.stun_immune and (best < 0 or f.strength > self.f[best].strength):
                best = i
        if best < 0: break
        skip |= 1 << best
    return skip


def act(self, other, opts, ours):
    turn = self.turn; self.turn += 1
    target = other.weakest()
    back = other.f[target].retaliation if target >= 0 else 0.0
    skip = stun_skips(self, turn); self.stunned = 0
    damage = 0.0
    hits = [0] * len(self.f)
    share = opts.our_basic_share if ours else opts.their_basic_share
    for i, f in enumerate(self.f):
        if f.shield_until <= turn: f.shield = 0; f.shield_until = NEVER
        if f.health <= 0: continue
        if f.arrives <= turn and not (skip >> i & 1):
            d = strength_now(f, opts) * share
            h = 1
            if turn >= f.next_cast:
                h, cd = cast(f, i, turn, self, other, opts)
                d += cd
            d *= f.mult
            damage += d; f.dealt += d; hits[i] = h; f.acts += 1
            if turn < 5: f.dealt5 += d; f.acts5 += 1
    damage *= opts.our_rate if ours else opts.their_rate
    if target < 0: return damage
    killed_before = other.alive
    if opts.focus_spread == 'even' and not ours:
        live = [i for i, g in enumerate(other.f) if g.health > 0]
        for i in live: other.hurt(damage / len(live), i) if other.f[i].health > 0 else other.hurt(damage / len(live))
    else:
        other.hurt(damage, target)
    if back > 0:
        for i in range(len(self.f)):
            if hits[i] > 0: self.hurt_one(i, hits[i] * back)
    if opts.vendetta_reset and other.alive < killed_before:
        for f in self.f:
            if f.vendetta and f.health > 0:
                f.ready = [turn + 1 if r != NEVER else r for r in f.ready]  # ready on its next turn
                f.next_cast = min(f.ready)
    return damage


def simulate(us, them, they_first=True, horizon=HORIZON, opts=None, trace=None):
    """Full play-out. Returns dict(we_kill, they_kill, self_falls, self_fall_turn, ...)."""
    opts = opts or Opts()
    ours = theirs = 0
    watched = us.self
    falls = False; fall_turn = None
    for t in range(2 * horizon):
        their_turn = (t % 2 == 0) == they_first
        if their_turn:
            d = act(them, us, opts, False)
            if us.camp > 0:
                if us.self < 0 or us.f[us.self].health <= 0: us.hurt(us.camp)
                else: us.hurt(us.camp, us.self)
            theirs += 1
            if trace is not None: trace.append(('them', theirs, d))
        else:
            d = act(us, them, opts, True)
            ours += 1
            if trace is not None: trace.append(('us', ours, d))
        if watched >= 0 and us.f[watched].health <= 0:
            falls = True; fall_turn = theirs; watched = -1
        if us.alive == 0: return dict(we_kill=0, they_kill=max(1, theirs), self_falls=falls, fall_turn=fall_turn, ours=ours, theirs=theirs)
        if them.f and them.alive == 0: return dict(we_kill=max(1, ours), they_kill=0, self_falls=falls, fall_turn=fall_turn, ours=ours, theirs=theirs)
    return dict(we_kill=0, they_kill=0, self_falls=falls, fall_turn=fall_turn, ours=ours, theirs=theirs)


def parse_fighters(s):
    out = []
    for x in s.split(';'):
        h, m, sh, st, arr, rd = x.split('/')
        r0, r1 = rd.split(',')
        out.append(dict(health=float(h), max=float(m), shield=float(sh), strength=float(st), arrives=int(arr), ready=[int(r0), int(r1)]))
    return out
