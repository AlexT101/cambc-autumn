"""Engagements (the clustering of analysis/fights.py, plus stun-only hits) with per-turn transcripts and defined tags.

Tags, all from recorded data:
- blind: the victim's latest turn-start vision (`sees`) before the hit did not include the attacker.
- ambush: a blind first hit whose attacker was seen by no enemy at their turn starts in the 3 rounds before and spent
  them in a bush or without moving.
- retreat (turn): moved, dealt no damage, and ended farther (Chebyshev) from every enemy it saw at its turn start.
- kite (turn): dealt damage and ended the turn farther from its target than it started.
- chase (turn): moved closer to an enemy whose previous turn was a retreat.
- disengaged at hp X%: the first of >= 2 consecutive retreat turns after which it dealt no more damage in the fight."""

from collections import defaultdict

from analysis.data import chebyshev
from analysis.fights import _cluster, _split
from analysis.params import DEFAULTS

RADIUS, GAP, MAX_DUR = DEFAULTS['radius'], DEFAULTS['gap'], DEFAULTS['max_dur']
CLOSE = 4          # ability range: stepping within it of a seen enemy counts as closing in
CLOSE_WINDOW = 5   # rounds before the first hit searched for the closing move


def instances(v):
    """(s, r, attacker, victim, amount, attacker tile, victim tile) for champion damage and stun-only hits."""
    g = v.g
    out = list(g.champ_damage)
    for e in g.events:
        if e['k'] in ('attack', 'cast') and e.get('stun'):
            hit = {x for x, _ in e.get('dmg', [])}
            for x in e['stun']:
                if x in v.team and v.team[x] != v.team[e['a']] and x not in hit:
                    out.append((e['s'], e['r'], e['a'], x, 0.0, tuple(e['f']), tuple(e['to']) if x == e.get('tgt') else None))
    res = []
    for s, r, a, x, amt, ap, vp in out:
        ap = ap or v.pos(a, r - 1)
        vp = vp or v.pos(x, r - 1)
        res.append((s, r, a, x, amt, ap, vp))
    res.sort()
    return res


class Fight:
    pass


def engagements(v):
    inst = instances(v)
    clusters = []
    for its in _cluster(inst, RADIUS, GAP):
        clusters += _split(its, MAX_DUR)
    fights = []
    for its in clusters:
        its.sort()
        f = Fight()
        f.its = its
        f.r0, f.r1 = its[0][1], its[-1][1]
        f.s0, f.s1 = its[0][0], its[-1][0]
        f.part = set()
        for s, r, a, x, *_ in its:
            f.part |= {a, x}
        pts = [p for it in its for p in (it[5], it[6]) if p]
        f.loc = (round(sum(p[0] for p in pts) / len(pts)), round(sum(p[1] for p in pts) / len(pts))) if pts else None
        fights.append(f)
    fights.sort(key=lambda f: (f.r0, f.s0))
    for n, f in enumerate(fights, 1):
        f.id = f'F{n}'
        _analyse(v, f)
    return fights


def _analyse(v, f):
    M = v.M
    s, r, a, x, amt, ap, vp = f.its[0]
    f.first = (s, r, a, x, amt, ap, vp)
    f.first_team = v.team[a]
    f.answered = any(it[1] == r and v.team[it[2]] != f.first_team and it[4] > 0 for it in f.its)
    f.blind = a not in v.sees_before(x, r, s)
    f.from_bush = M.bush_of(ap) if ap else None
    lurk = r > 3
    stayed = True
    for rr in range(r - 3, r):
        if rr < 1 or v.at(a, 'seenBy', rr) or not v.at(a, 'alive', rr):
            lurk = False
            break
        if v.pos(a, rr) != v.pos(a, rr - 1):
            stayed = False
    before = [M.bush_of(v.pos(a, rr)) if v.pos(a, rr) else None for rr in range(max(1, r - 3), r)]
    in_bush = bool(before) and all(b is not None for b in before)
    f.lurk_bush = before[-1] if in_bush else None
    f.ambush = f.blind and lurk and (in_bush or stayed)
    f.ambush_how = ('bush' if in_bush else 'still') if f.ambush else ''
    # Who was around at the start: alive within RADIUS of the first hit, end of the previous round.
    c0 = ap or f.loc
    f.present = [[], []]
    for c in v.ids:
        p = v.pos(c, r - 1)
        if p and chebyshev(p, c0) <= RADIUS:
            f.present[v.team[c]].append(c)
    f.closing = _closing(v, f, s, r)
    f.kills, f.camp_deaths = [], []
    for rr in range(f.r0, f.r1 + 2):
        for e in v.deaths[rr]:
            if e['v'] not in f.part:
                continue
            if 'by' in e and e['by'] in v.team and f.s0 <= e['s'] <= f.s1 + 1:
                if 'linked' not in e:
                    f.kills.append(e)
            elif 'camp' in e and rr <= f.r1 + 1:
                f.camp_deaths.append(e)
    f.dealt, f.taken, f.stuns = defaultdict(float), defaultdict(float), defaultdict(int)
    for s_, r_, a_, x_, amt_, *_ in f.its:
        f.dealt[a_] += amt_
        f.taken[x_] += amt_
        if amt_ == 0:
            f.stuns[a_] += 1
    _turns(v, f)


def _closing(v, f, s0, r0):
    """The last turn before the first hit in which a champion walked or dashed from beyond CLOSE tiles to within CLOSE
    of an enemy it saw at its turn start: (round, champion, enemy)."""
    best = None
    near = set(f.present[0] + f.present[1]) | f.part
    for r in range(max(1, r0 - CLOSE_WINDOW), r0 + 1):
        for c in v.slots(r)['_seq']:
            if c not in near:
                continue
            ts = v.turn_step(c, r)
            if ts > s0:
                continue
            p0 = v.start_pos(c, r)
            p1 = v.pos_at(c, r, s0 + 0.5) if r == r0 else v.pos(c, r)
            if not p0 or not p1 or p0 == p1:
                continue
            for e in v.at(c, 'sees', r):
                pe = v.pos_at(e, r, ts)
                if pe and chebyshev(p0, pe) > CLOSE >= chebyshev(p1, pe):
                    best = (r, c, e)
                    break
    return best


def _turns(v, f):
    """Per-turn tags for participants from 2 rounds before to 2 after."""
    f.tags = defaultdict(list)  # (r, c) -> tags
    f.exit = {}
    lo, hi = max(1, f.r0 - 2), min(v.N, f.r1 + 2)
    last_retreat = {}
    dealt_round = defaultdict(set)
    for s, r, a, x, amt, *_ in f.its:
        if amt > 0:
            dealt_round[a].add(r)
    hit_any = defaultdict(set)  # rounds a champion damaged any enemy champion, in or outside this fight
    for r in range(lo, hi + 1):
        for e in v.by_round[r]:
            if e['k'] in ('attack', 'cast') and any(x in v.team and v.team[x] != v.team[e['a']] for x, _ in e.get('dmg', [])):
                hit_any[e['a']].add(r)
    targets = defaultdict(dict)
    for s, r, a, x, amt, *_ in f.its:
        targets[a].setdefault(r, x)
    for r in range(lo, hi + 1):
        for c in v.slots(r)['_seq']:
            if c not in f.part:
                continue
            p0, p1 = v.start_pos(c, r), v.pos(c, r)
            if p0 is None or p1 is None:
                continue
            ts = v.turn_step(c, r)
            seen = [e for e in v.at(c, 'sees', r) if e in v.team]
            enemies = {e: v.pos_at(e, r, ts) for e in seen}
            enemies = {e: p for e, p in enemies.items() if p}
            moved = p0 != p1
            tags = []
            if moved and r not in hit_any[c] and enemies:
                if all(chebyshev(p1, p) > chebyshev(p0, p) for p in enemies.values()):
                    tags.append('retreat')
            if r in dealt_round[c] and moved:
                t = targets[c].get(r)
                tp = v.pos_at(t, r, ts) if t is not None else None
                if tp and chebyshev(p1, tp) > chebyshev(p0, tp):
                    tags.append('kite')
            if moved:
                for e, p in enemies.items():
                    if last_retreat.get(e) and chebyshev(p1, p) < chebyshev(p0, p):
                        tags.append('chase ' + v.type[e])
                        break
            last_retreat[c] = 'retreat' in tags
            if tags:
                f.tags[(r, c)] = tags
    for c in f.part:
        died = [e for e in f.kills + f.camp_deaths if e['v'] == c]
        if died:
            f.exit[c] = f'died r{died[0]["r"]}'
            continue
        involved = [it[1] for it in f.its if c in (it[2], it[3])]
        last_dmg = max(dealt_round[c] | {min(involved)}, default=0)
        rounds = sorted(r for (r, cc), t in f.tags.items() if cc == c and 'retreat' in t and r >= last_dmg)
        run = [r for i, r in enumerate(rounds) if i + 1 < len(rounds) and rounds[i + 1] == r + 1]
        if run:
            r = run[0]
            hp = v.at(c, 'hp', r - 1) / max(1, v.at(c, 'maxHp', r - 1))
            f.exit[c] = f'disengaged r{r} at hp {hp:.0%}'
        else:
            f.exit[c] = 'stayed'
        for rr in range(f.r1, min(v.N, f.r1 + 10) + 1):
            if any(e['k'] == 'recall_end' and e['a'] == c for e in v.by_round[rr]):
                f.exit[c] += f', recalled (home r{rr})'
                break
