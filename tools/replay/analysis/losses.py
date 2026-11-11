"""Loss episodes: discrete situations where a side loses value, each priced in gems and tagged with the situation, so
recurring ones cluster, rank by cost per game against the opponent's cost in the same games, and point at code.

Kinds (disjoint, so their costs add up):
- death: killed by a champion. Cost = bag (both Cassi & Issac bags) + 0.25 x the killer's gold + dead time priced at the
  game's pooled earn rate (gems earned per alive champion-round, both teams) x rounds until respawn (or the end).
  Tags: what the victim did the round before the fatal damage began (`doing`, its analysis/macro.py turn class: walking
  with gems, walking, farming, holding, tributing, recalling, fighting = it dealt the first damage, waiting, idle), the
  numbers within `radius` then (`alone v1`, `alone v2+`, `grouped, outnumbered`, `grouped, even+`), how long it had seen
  one of its killers (`warn`: unseen, seen <6, seen 6+ rounds), whether its own walk over the 5 rounds before closed on
  the killers (`approach`) and where it was heading (`heading`: toward an altar or own spawn), the half, and two
  counterfactuals checked against the rules:
  `cf_recall` (a killer was in sight for 6+ rounds before the first hit with no damage or stun to the victim in that
  span; a recall started at its start lasts 5 turn ends and only damage or a stun cancels it, so it would have landed,
  had the enemy acted the same) and `cf_altar` (it stood within 1 of an altar the enemy had not locked, carrying at
  least half the final bag, and a tribute started then, ceil(bag / 10) turn ends long and cancelled only by stuns, which
  the victim did not take, would have completed before it died; `enemies8` says whether an enemy was near then).
- camp_death: killed by a camp. Cost = bag + dead time.
- camp_lost: the enemy captured a group we had worked on (`stolen`: we dealt at least half its monster damage this
  cycle; `contested`: we hit or held it, or a hold was contested) or a group on our half we never touched
  (`invaded`). Cost = the capture's gems + 0.25 x gold.
- stall: a run of `stall_min`+ rounds alive off spawn without walking, hitting, holding or channelling (idle or waiting
  by a camp or altar; on own spawn at full health). Cost = rounds x the earn rate. Tagged `farmable` when a group was
  claimable or up and asleep within `stall_reach` walking steps at the start (no Monolith groups), and `by a tributing ally` when an ally
  within `radius` was channelling a tribute for at least half the stall (guarding a long tribute), and `facing enemies`
  when an enemy was within `radius` + 1 for at least half of it (a standoff).

Fights are reported separately (`fight` items, the net swing of engagements the side lost): they overlap deaths."""

from collections import Counter, defaultdict

from . import fights as fights_mod
from . import macro as macro_mod
from . import params as params_mod
from .data import chebyshev
from .util import boot_stat, by_cluster, fmt, mean, pct

GOLD = 0.25
BAGS = [(0, 0, '0'), (1, 49, '1-49'), (50, 199, '50-199'), (200, 10 ** 9, '200+')]
DOING = {'walk_bag': 'walking with gems', 'walk': 'walking', 'camp': 'farming', 'hold': 'holding', 'tribute': 'tributing',
         'recall': 'recalling', 'teleport': 'teleporting', 'fight': 'fighting', 'wait_camp': 'waiting', 'wait_altar': 'waiting',
         'idle': 'idle', 'spawn': 'on spawn', 'lost': 'stunned/oof', 'dead': 'respawning', None: '?'}
STALL = ('idle', 'wait_camp', 'wait_altar', 'spawn')
KINDS = ('death', 'camp_death', 'camp_lost', 'stall')
RECALL_TURNS = 5

# Where each situation is decided in ocean and charybdis (same layout; file and function). Names checked against
# bots/ocean/src and bots/charybdis/src on 2026-11-11.
CODE = {
    ('death', 'walking with gems'): 'economy/bank.cc carry_bag / banks_bag (route and when to bank); combat/fight.cc want_home',
    ('death', 'farming'): 'combat/fight.cc want_home (leave a camp under threat); economy/farm.cc farm (target risk)',
    ('death', 'holding'): 'economy/capture.cc holding_capture / hold_capture; combat/fight.cc want_home',
    ('death', 'tributing'): 'economy/bank.cc submit_here / continue_tribute (start or keep a tribute with enemies near)',
    ('death', 'recalling'): 'economy/bank.cc continue_recall; combat/fight.cc recall_line',
    ('death', 'fighting'): 'combat/plan.cc (strike search) and combat/fight.cc prey / chase_with_guard (who to engage)',
    ('death', 'walking'): 'model/safety.cc (threat model), combat/guard.cc guard_work / step_safely (step guard)',
    ('death', 'waiting'): 'economy/farm.cc farm (waiting by a camp); combat/fight.cc want_home',
    ('death', 'idle'): 'combat/fight.cc want_home; model/safety.cc',
    ('death', 'on spawn'): 'combat/fight.cc retreat / mend (bot.cc decide)',
    ('death', 'stunned/oof'): 'fuel (FUEL-GATES.md) or combat/self_abilities.cc (stun avoidance)',
    ('cf', 'recall'): 'combat/fight.cc want_home / recall_line (recall on sight with a bag); economy/bank.cc continue_recall',
    ('cf', 'altar'): 'economy/bank.cc banks_bag / retaining_gems / submit_here (bank at the altar passed)',
    ('camp_death', ''): 'economy/camps.cc (camp damage and clear time), combat/fight.cc camp_exit_way, economy/farm.cc rated_beaten',
    ('camp_lost', 'stolen'): 'economy/capture.cc holding_capture / contest_capture; economy/crew.cc (who stays to hold)',
    ('camp_lost', 'contested'): 'economy/capture.cc contest_capture / yield_capture; combat/plan.cc (fight on the tiles)',
    ('camp_lost', 'invaded'): 'economy/farm.cc farm (target choice and map coverage); economy/altar_guard.cc guard_turn',
    ('stall', 'by a tributing ally'): 'combat/support.cc local_support / support_endpoint (who guards a tribute); economy/bank.cc banks_bag / '
                                      'retaining_gems (the bag size sets the tribute length, ceil(bag/10) turns)',
    ('stall', 'facing enemies within 9'): 'combat/fight.cc want_home / prey (engage or leave a standoff); combat/plan.cc (strike search)',
    ('stall', ''): 'bot.cc decide (no branch acted), economy/farm.cc farm (no target chosen or waiting for a respawn)',
    ('fight', ''): 'combat/support.cc local_support, model/comms.cc (calls for help), combat/plan.cc (engage at numbers)',
}


def code_for(key):
    kind = key[0]
    if kind == 'death':
        return CODE.get(('death', key[3]), '')
    if kind == 'camp_lost':
        return CODE.get(('camp_lost', key[1]), '')
    if kind == 'stall':
        return CODE.get(('stall', key[3]), CODE[('stall', '')])
    return CODE.get((kind, ''), '')


def bag_bucket(b):
    for lo, hi, name in BAGS:
        if lo <= b <= hi:
            return name
    return BAGS[-1][2]


def _group_states(g):
    """{group: [None] + [dict of groupCols at the end of round r]} forward-filled."""
    n = g.n_rounds
    cols = g.rounds['groupCols']
    rows = defaultdict(list)
    for row in g.rounds['groups']:
        rows[row[1]].append(row)
    out = {}
    for gid, rs in rows.items():
        arr = [None] * (n + 2)
        j, cur = 0, None
        for r in range(1, n + 1):
            while j < len(rs) and rs[j][0] <= r:
                cur = dict(zip(cols, rs[j]))
                j += 1
            arr[r] = cur
        out[gid] = arr
    return out


def _partner(g, a, b):
    return g.name_of[a] in ('Cassi', 'Issac') and g.name_of[b] in ('Cassi', 'Issac') and abs(a - b) == 1 and g.team_of[a] == g.team_of[b]


def extract(g, P=None):
    P = P or params_mod.DEFAULTS
    RAD = P['radius']
    STALL_MIN = P.get('stall_min', 10)
    REACH = P.get('stall_reach', 20)
    ALTAR_LOOK = P.get('altar_look', 40)
    mp, n, R = g.map, g.n_rounds, g.rounds
    H = mp.H
    team_of, name_of = g.team_of, g.name_of
    cls = macro_mod.classify(g)
    fields = macro_mod.group_fields(mp)
    camp_group = {c['id']: c['group'] for c in mp.camps}
    camp_type = {c['id']: c['type'] for c in mp.camps}

    # pooled earn rate: gems earned (capture shares + kill bags) per alive champion-round, both teams
    earned = [0, 0]
    for e in g.events:
        if e['k'] == 'capture':
            for cid, gems, _ in e['shares']:
                earned[team_of[cid]] += gems
        elif e['k'] == 'death' and e.get('by') in team_of:
            earned[team_of[e['by']]] += e.get('gems', 0)
    alive_rounds = [0, 0]
    for c in R['champions']:
        alive_rounds[c['team']] += sum(1 for a in c['alive'][:n] if a)
    rate = sum(earned) / max(1, sum(alive_rounds))

    # damage and stuns taken per champion per round
    hit_by = defaultdict(lambda: defaultdict(set))   # victim -> round -> attackers (champion damage)
    dmg_any = defaultdict(set)                         # victim -> rounds with any damage (champions or camps)
    for s, r, a, v, amt, *_ in g.champ_damage:
        hit_by[v][r].add(a)
        dmg_any[v].add(r)
    for s, r, v, amt in g.camp_damage:
        dmg_any[v].add(r)
    stunned = defaultdict(set)
    for e in g.events:
        if e['k'] in ('attack', 'cast') and e.get('stun'):
            for v in e['stun']:
                if v in team_of and team_of[v] != team_of.get(e['a']):
                    stunned[v].add(e['r'])
    gst = _group_states(g)

    def pos_end(cid, r):
        return g.pos(cid, r - 1) if r >= 1 else None

    def pos_start(cid, r):
        return g.pos(cid, g.start_idx(r)) if r >= 2 else pos_end(cid, 1)

    eps = []

    # --- deaths (one episode per kill: a Cassi & Issac pair dying together is one, with both bags)
    by_step = defaultdict(list)
    for e in g.deaths:
        by_step[e['s']].append(e)
    for s, es in by_step.items():
        for e in es:
            if e.get('linked') is not None:
                continue
            cid, r = e['v'], e['r']
            t = team_of[cid]
            bag = e.get('gems', 0) + sum(x.get('gems', 0) for x in es if x.get('linked') == cid)
            bodies = 1 + sum(1 for x in es if x.get('linked') == cid)
            dead = min(60, max(0, n - r)) * bodies
            at = tuple(e['at'])
            if e.get('by') is None:
                camp = e.get('camp')
                third = any(rr in hit_by[cid] for rr in range(r - 5, r + 1))
                ch = g.ch(cid)
                i0 = max(0, r - 11)
                hp0 = ch['hp'][i0] / ch['maxHp'][i0] if ch['alive'][i0] and ch['maxHp'][i0] else None
                doing = DOING.get(cls[cid][r - 1] if r > 1 else None, '?')
                key = ('camp_death', name_of[cid], camp_type.get(camp, '?'), bag_bucket(bag), 'also hit by champions' if third else 'camp only')
                eps.append({'kind': 'camp_death', 'team': t, 'cid': cid, 'r': r, 'cost': bag + rate * dead, 'bag': bag, 'time': rate * dead,
                            'gold': 0, 'key': key, 'at': at, 'tags': {'camp': camp_type.get(camp, '?'), 'doing': doing,
                                                                   'hp10': hp0, 'third': third}})
                continue
            # the fatal sequence: champion damage with gaps of at most 2 rounds, back from the death
            r_hit = r
            rr = r - 1
            while rr >= max(1, r - 40):
                if rr in hit_by[cid]:
                    r_hit = rr
                elif not any(x in hit_by[cid] for x in (rr - 1, rr - 2)):
                    break
                rr -= 1
            killers = set()
            for x in range(r_hit, r + 1):
                killers |= hit_by[cid].get(x, set())
            killers.add(e['by'])
            # warning: the last run of turn starts (gaps of 1 allowed) in which the victim saw one of its killers
            sees = g.ch(cid)['sees']
            first_seen = None
            gap = 0
            for x in range(r_hit, max(0, r_hit - 60), -1):
                if x - 1 < len(sees) and set(sees[x - 1]) & killers:
                    first_seen, gap = x, 0
                else:
                    gap += 1
                    if gap > 1:
                        break
            warn = (r_hit - first_seen) if first_seen is not None else -1
            wtag = 'unseen' if warn < 0 else 'seen <6' if warn < RECALL_TURNS + 1 else 'seen 6+'
            before = cls[cid][r_hit - 1] if r_hit > 1 else None
            doing = DOING.get(before, '?')
            p = pos_start(cid, r_hit) or at
            allies = sum(1 for c2 in g.team_ids[t] if c2 != cid and not _partner(g, c2, cid) and (q := pos_start(c2, r_hit)) and chebyshev(p, q) <= RAD)
            near16 = sum(1 for c2 in g.team_ids[t] if c2 != cid and not _partner(g, c2, cid) and (q := pos_start(c2, r_hit)) and RAD < chebyshev(p, q) <= 2 * RAD)
            enemies = max(1, sum(1 for c2 in g.team_ids[1 - t] if (q := pos_start(c2, r_hit)) and chebyshev(p, q) <= RAD))
            if allies == 0:
                num = 'alone v1' if enemies <= 1 else 'alone v2+'
            else:
                num = 'grouped, outnumbered' if allies + 1 < enemies else 'grouped, even+'
            ch = g.ch(cid)
            bag_hit = ch['gems'][g.start_idx(r_hit)] or 0
            # the victim's own walk over the 5 rounds before the first hit, against where its killers stood then
            a0 = max(1, r_hit - 5)
            v0, v1 = pos_start(cid, a0), pos_start(cid, r_hit)
            ks = [q for k_ in killers if (q := pos_start(k_, a0))]
            approach = 'unknown'
            if v0 and v1 and ks:
                d0, d1 = min(chebyshev(v0, q) for q in ks), min(chebyshev(v1, q) for q in ks)
                approach = 'walked toward them' if d1 <= d0 - 2 else 'walked away' if d1 >= d0 + 2 else 'held its ground'
            heading = '-'
            if v0 and v1:
                sc = mp.spawn_center(t)
                if mp.altar_dist(v1) <= mp.altar_dist(v0) - 2:
                    heading = 'toward an altar'
                elif chebyshev(v1, sc) <= chebyshev(v0, sc) - 2:
                    heading = 'toward own spawn'
                elif v0 != v1:
                    heading = 'elsewhere'
            # counterfactual: a recall in the safe window (killer in sight, no damage or stun to the victim) of 6+ rounds before the first hit
            cf_recall = None
            if bag > 0 and first_seen is not None:
                s0 = first_seen
                for x in range(r_hit - 1, first_seen - 1, -1):
                    if x in dmg_any[cid] or x in stunned[cid]:
                        s0 = x + 1
                        break
                if r_hit - s0 >= RECALL_TURNS + 1 and not mp.in_spawn(t, pos_start(cid, s0)) and (ch['chan'][g.start_idx(s0)] or 0) != 2:
                    close = min((chebyshev(pv, q) for x in range(s0, r_hit) if (pv := pos_start(cid, x))
                                 for c2 in g.team_ids[1 - t] if (q := pos_start(c2, x))), default=99)
                    cf_recall = {'r': s0, 'closest': close}
            # counterfactual: the last altar passed whose tribute would have completed before the death
            cf_altar = None
            if bag > 0:
                for x in range(r - 1, max(0, r - ALTAR_LOOK), -1):
                    i = x - 1
                    if i < 0 or not ch['alive'][i] or ch['x'][i] is None:
                        break
                    b = ch['gems'][i] or 0
                    if b < max(1, bag // 2):
                        break
                    if (ch['chan'][i] or 0) == 2:
                        continue
                    q = (ch['x'][i], ch['y'][i])
                    locked = {(lx, ly) for lt, lx, ly, _ in R['locks'][i] if lt != t} if i < len(R['locks']) else set()
                    if not any(chebyshev(q, a) <= 1 and a not in locked for a in mp.altars):
                        continue
                    d = max(1, -(-b // 10))
                    if x + 1 + d - 1 < r and not any(y in stunned[cid] for y in range(x + 1, x + d + 1)):
                        en = sum(1 for c2 in g.team_ids[1 - t] if (q2 := g.pos(c2, i)) and chebyshev(q, q2) <= RAD)
                        cf_altar = {'r': x, 'bag': b, 'dur': d, 'enemies8': en}
                        break
            gold = e.get('gold', 0)
            half = mp.half(mp.own(t, at))
            key = ('death', name_of[cid], bag_bucket(bag), doing, num, wtag)
            eps.append({'kind': 'death', 'team': t, 'cid': cid, 'r': r, 'r_hit': r_hit, 'cost': bag + GOLD * gold + rate * dead,
                        'bag': bag, 'gold': GOLD * gold, 'time': rate * dead, 'key': key, 'at': at,
                        'tags': {'doing': doing, 'num': num, 'warn': warn, 'approach': approach, 'heading': heading, 'wtag': wtag, 'allies8': allies, 'allies16': near16,
                                 'enemies8': enemies, 'half': {0: 'own', 1: 'enemy', -1: 'mid'}[half], 'bag_hit': bag_hit,
                                 'killers': sorted(killers), 'altar_d': mp.altar_dist(at), 'first_seen': first_seen,
                                 'prev': [cls[cid][x] for x in range(max(1, r_hit - 8), r_hit)]},
                        'cf': {'recall': cf_recall, 'altar': cf_altar}})

    # --- camps lost: per group cycle (respawn to capture), who hit and held it
    cyc = defaultdict(lambda: {'dmg': [0.0, 0.0], 'held': set(), 'contested': False, 'hitters': [set(), set()], 'hold_r': {}})
    for e in g.events:
        k = e['k']
        if k in ('attack', 'cast') and e.get('cdmg'):
            ta = team_of.get(e['a'])
            for camp, amt in e['cdmg']:
                gid = camp_group.get(camp)
                if gid is not None and amt > 0 and ta is not None:
                    cyc[gid]['dmg'][ta] += amt
                    cyc[gid]['hitters'][ta].add(e['a'])
        elif k == 'capture_hold':
            cyc[e['g']]['held'].add(e['team'])
            cyc[e['g']]['hold_r'][e['team']] = e['r']
        elif k == 'capture_reset' and e.get('contested'):
            cyc[e['g']]['contested'] = True
        elif k == 'capture':
            gid, ct = e['g'], e['team']
            c_ = cyc.pop(gid, None) or {'dmg': [0.0, 0.0], 'held': set(), 'contested': False, 'hitters': [set(), set()], 'hold_r': {}}
            t = 1 - ct
            gems = sum(x[1] for x in e['shares'])
            gold = sum(x[2] for x in e['shares'])
            tot = c_['dmg'][0] + c_['dmg'][1]
            share = c_['dmg'][t] / tot if tot else 0.0
            side = mp.groups[gid]['side']
            rel = 'mid' if side == -1 else 'own' if side == t else 'enemy'
            r = e['r']
            touched = c_['dmg'][t] > 0 or t in c_['held'] or c_['contested']
            if share >= 0.5:
                sub = 'stolen'
            elif touched:
                sub = 'contested'
            elif rel == 'own':
                sub = 'invaded'
            else:
                continue
            gk = ' '.join(f'{v}{k}' for k, v in sorted(Counter(macro_mod.ABBR[x] for x in mp.groups[gid]['types']).items()))
            r0 = c_['hold_r'].get(ct, r - 6)
            if sub == 'invaded':
                ds = [(fields[gid][q[0] * H + q[1]], c2) for c2 in g.team_ids[t] if (q := pos_start(c2, r0))]
                if ds:
                    dmin, near = min(ds)
                    why = 'ours within 8' if dmin <= 8 else 'ours 9-20 away' if dmin <= 20 else 'ours 21+ away'
                    near_doing = DOING.get(cls[near][r0], '?')
                else:
                    why, near_doing, dmin = 'all ours dead', '-', None
            else:
                ours = c_['hitters'][t]
                died = any(x['v'] in ours for x in g.deaths if r0 - 30 <= x['r'] <= r)
                tiles = mp.groups[gid]['tiles']
                present = any((q := pos_start(c2, r)) and min(chebyshev(q, tuple(tt)) for tt in tiles) <= 3 for c2 in g.team_ids[t])
                ours8 = sum(1 for c2 in g.team_ids[t] if (q := pos_start(c2, r0)) and min(chebyshev(q, tuple(tt)) for tt in tiles) <= RAD)
                theirs8 = sum(1 for c2 in g.team_ids[ct] if (q := pos_start(c2, r0)) and min(chebyshev(q, tuple(tt)) for tt in tiles) <= RAD)
                why = 'ours died' if died else 'ours within 3, outheld' if present else \
                    'ours left, outnumbered' if theirs8 > ours8 else 'ours left at even numbers or better'
                near_doing, dmin = f'{ours8} of ours v {theirs8} within {RAD} at their hold', None
            key = ('camp_lost', sub, gk, rel, why)
            eps.append({'kind': 'camp_lost', 'team': t, 'cid': None, 'r': r, 'cost': gems + GOLD * gold, 'bag': 0, 'gold': GOLD * gold,
                        'time': 0, 'key': key, 'at': tuple(mp.groups[gid]['tiles'][0]),
                        'tags': {'group': mp.group_label(mp.own_group(t, gid)), 'share': share, 'gems': gems, 'near_doing': near_doing,
                                 'near_dist': dmin, 'hold_r': r0}})

    # --- stalls
    for c in R['champions']:
        cid, t = c['id'], c['team']
        q = cls[cid]
        r = 1
        while r <= n:
            k = q[r]
            if k not in STALL or (k == 'spawn' and c['hp'][r - 1] < c['maxHp'][r - 1]):
                r += 1
                continue
            a = r
            mix = Counter()
            while r <= n and q[r] in STALL and not (q[r] == 'spawn' and c['hp'][r - 1] < c['maxHp'][r - 1]):
                mix[q[r]] += 1
                r += 1
            length = r - a
            if length < STALL_MIN or a == 1:
                continue
            p = g.pos(cid, a - 1)
            farmable = None
            if p:
                for grp in mp.groups:
                    st = gst.get(grp['id'], [None] * (n + 2))[a]
                    if not st:
                        continue
                    # a Monolith (20000 hp, 200 Strength) is a team's job, not a stalled champion's
                    ok = ((st['state'] == 2 and st['team'] == 2) or (st['state'] == 1 and st['awake'] == 0)) and 'Monolith' not in grp['types']
                    if ok:
                        d = fields[grp['id']][p[0] * H + p[1]]
                        if d <= REACH and (farmable is None or d < farmable[0]):
                            farmable = (d, mp.group_label(mp.own_group(t, grp['id'])))
            escort = standoff = 0
            for x in range(a, r):
                pe = g.pos(cid, x - 1)
                if pe and any(c2 != cid and (q2 := g.pos(c2, x - 1)) and chebyshev(pe, q2) <= RAD and (g.ch(c2)['chan'][x - 1] or 0) == 2
                              for c2 in g.team_ids[t]):
                    escort += 1
                if pe and any((q2 := g.pos(c2, x - 1)) and chebyshev(pe, q2) <= RAD + 1 for c2 in g.team_ids[1 - t]):
                    standoff += 1
            main = mix.most_common(1)[0][0]
            main = 'waiting' if main.startswith('wait') else main
            nxt = q[r] if r <= n else 'end'
            from_ = macro_mod._phase(a)
            ctx_ = 'by a tributing ally' if escort * 2 >= length else 'facing enemies within 9' if standoff * 2 >= length else \
                'farmable group in reach' if farmable else 'nothing in reach'
            key = ('stall', name_of[cid], main, ctx_, macro_mod.PHASES[from_][2])
            eps.append({'kind': 'stall', 'team': t, 'cid': cid, 'r': a, 'cost': rate * length, 'bag': 0, 'gold': 0, 'time': rate * length,
                        'key': key, 'at': p, 'tags': {'len': length, 'mix': dict(mix), 'next': nxt, 'farmable': farmable, 'escort': escort, 'standoff': standoff,
                                                       'gems': c['gems'][a - 1] or 0}})

    # --- fights the side lost on net swing (overlap deaths; reported apart)
    fl, _ = fights_mod.engagements(g, P)
    fitems = []
    for f in fl:
        i0 = g.start_idx(f['r0'])
        loc = tuple(f.get('loc0') or f['loc'])
        for t in (0, 1):
            sw = f['swing'] if t == 0 else -f['swing']
            joined = set(f['ids'][t])
            absent16 = []
            for cid in g.team_ids[t]:
                q = g.pos(cid, i0)
                if q and RAD < chebyshev(q, loc) <= 2 * RAD and cid not in joined:
                    absent16.append(cid)
            diff = max(-2, min(2, f['present'][t] - f['present'][1 - t]))
            fitems.append({'team': t, 'r': f['r0'], 'r1': f['r1'], 'swing': sw, 'num': diff, 'init': f['init'] == t,
                           'absent16': len(absent16), 'absent_what': [DOING.get(cls[x][f['r0']], '?') for x in absent16],
                           'half': {0: 'own', 1: 'enemy', -1: 'mid'}[mp.half(mp.own(t, loc))], 'present': f['present'][t],
                           'opp_present': f['present'][1 - t], 'kills': f['kills'][t], 'deaths': f['kills'][1 - t], 'loc': loc})

    exposure = {0: Counter(), 1: Counter()}
    doing_rounds = {0: Counter(), 1: Counter()}
    for c in R['champions']:
        nm = name_of[c['id']]
        for i in range(n):
            if c['alive'][i]:
                exposure[c['team']][(nm, bag_bucket(c['gems'][i] or 0))] += 1
        for r in range(1, n + 1):
            doing_rounds[c['team']][DOING.get(cls[c['id']][r], '?')] += 1

    sides = []
    for t in (0, 1):
        mine = [e for e in eps if e['team'] == t]
        s = {f'loss_{k}_per100': 100 * sum(e['cost'] for e in mine if e['kind'] == k) / n for k in KINDS}
        s['loss_total_per100'] = 100 * sum(e['cost'] for e in mine) / n
        s['loss_bag_per100'] = 100 * sum(e['bag'] for e in mine) / n
        s['cf_recall_gems_per100'] = 100 * sum(e['bag'] for e in mine if e['kind'] == 'death' and e['cf']['recall']) / n
        s['cf_altar_gems_per100'] = 100 * sum(e['cf']['altar']['bag'] for e in mine if e['kind'] == 'death' and e['cf']['altar'] and not e['cf']['altar']['enemies8']) / n
        sides.append(s)
    return {'sides': sides, 'episodes': eps, 'fights': fitems, 'rate': rate, 'n': n, 'exposure': {t: dict(v) for t, v in exposure.items()},
            'doing_rounds': {t: dict(v) for t, v in doing_rounds.items()}}


METRICS = {
    'loss_total_per100': ('gems lost to episodes (deaths, camp deaths, camps lost, stalls) per 100 rounds', False, True),
    'loss_death_per100': ('death episode cost (bag + gold/4 + dead time) per 100 rounds', False, True),
    'loss_camp_death_per100': ('camp death cost per 100 rounds', False, False),
    'loss_camp_lost_per100': ('camps lost to the enemy (stolen, contested, own half invaded) per 100 rounds', False, True),
    'loss_stall_per100': ('stall cost (still, off spawn, 10+ rounds) per 100 rounds', False, False),
    'loss_bag_per100': ('carried gems lost on death per 100 rounds', False, True),
    'cf_recall_gems_per100': ('gems lost in deaths a recall in sight of the killer would have saved, per 100 rounds', False, True),
    'cf_altar_gems_per100': ('gems lost in deaths after passing an altar, no enemy within 8, where a tribute would have completed, per 100 rounds', False, True),
}


# ----------------------------------------------------------------------------------------------------- rendering

def _keystr(key):
    k = key[0]
    if k == 'death':
        return f'{key[1]} killed carrying {key[2]} gems while {key[3]}, {key[4]}, killer {key[5]}'
    if k == 'camp_death':
        return f'{key[1]} killed by a {key[2]} camp carrying {key[3]} gems, {key[4]}'
    if k == 'camp_lost':
        return f'{key[1]} {key[2]} group ({key[3]} half): {key[4]}'
    if k == 'stall':
        return f'{key[1]} {key[2]} 10+ rounds, {key[3]}, {key[4]}'
    return ' '.join(map(str, key))


def _tagstr(e):
    t = e['tags']
    if e['kind'] == 'death':
        cf = e['cf']
        out = f'first hit r{e["r_hit"]}, warned {t["warn"]} rounds, {t["approach"]}, heading {t["heading"]}, allies 8/16: {t["allies8"]}/{t["allies16"]}, enemies 8: {t["enemies8"]}, altar {t["altar_d"]} away'
        if cf['recall']:
            out += f'; recall from r{cf["recall"]["r"]} would have landed (closest enemy {cf["recall"]["closest"]})'
        if cf['altar']:
            out += f'; tribute at r{cf["altar"]["r"]} ({cf["altar"]["bag"]} gems, {cf["altar"]["dur"]} rounds) would have completed'
        return out
    if e['kind'] == 'camp_lost':
        return f'{t["group"]}, our damage share {pct(t["share"], 0)}, ' + (f'nearest of ours {t["near_dist"]} steps ({t["near_doing"]})' if t.get('near_dist') is not None else t['near_doing'])
    if e['kind'] == 'stall':
        return f'{t["len"]} rounds, then {t["next"]}' + (f', {t["farmable"][1]} {t["farmable"][0]} steps away' if t['farmable'] else '')
    if e['kind'] == 'camp_death':
        return f'{t["camp"]}, {t["doing"]}, hp 10 rounds before {pct(t["hp10"], 0)}'
    return ''


def ckey(e):
    """The coarse cluster an episode ranks under (its full key's leading fields)."""
    k = e['key']
    if k[0] == 'death':
        return k[:4]
    if k[0] == 'camp_death':
        return k[:3]
    if k[0] == 'camp_lost':
        return (k[0], k[1], k[3], k[4])
    if k[0] == 'stall':
        return k[:4]
    return k


def _ckeystr(key):
    k = key[0]
    if k == 'death':
        return f'{key[1]} killed with {key[2]} gems while {key[3]}'
    if k == 'camp_death':
        return f'{key[1]} killed by a {key[2]} camp'
    if k == 'camp_lost':
        return f'camp {key[1]} ({key[2]} half): {key[3]}'
    if k == 'stall':
        return f'{key[1]} {key[2]} 10+ rounds, {key[3]}'
    return ' '.join(map(str, key))


def _mix(eps):
    """The secondary tags of a cluster's focus episodes: each tag's top value and its share."""
    if not eps:
        return '-'
    k = eps[0]['kind']
    fields = {'death': (('num', lambda e: e['tags']['num']), ('warn', lambda e: e['tags']['wtag']), ('half', lambda e: e['tags']['half'] + ' half'),
                        ('approach', lambda e: e['tags']['approach']), ('heading', lambda e: 'heading ' + e['tags']['heading'])),
              'camp_death': (('bag', lambda e: e['key'][3] + ' gems'), ('third', lambda e: e['key'][4])),
              'camp_lost': (('group', lambda e: e['key'][2]),),
              'stall': (('phase', lambda e: e['key'][4]), ('then', lambda e: 'then ' + str(e['tags']['next'])))}.get(k, ())
    out = []
    for _, fn in fields:
        c = Counter(fn(e) for e in eps)
        v, m = c.most_common(1)[0]
        out.append(f'{v} {pct(m / len(eps), 0)}')
    return ', '.join(out)


def entries(ctx):
    """(game info, focus side, other side, data) per game: the focus team with --team, else the loser."""
    out = []
    for gi in ctx.games:
        d = ctx.data[gi['dir']].get('losses')
        if not d:
            continue
        if ctx.focus:
            for t in ctx.focus_teams(gi):
                out.append((gi, t, 1 - t, d))
        else:
            out.append((gi, 1 - gi['winner'], gi['winner'], d))
    return out


def cluster_table(ents, keyfn, B=300):
    """Per cluster: focus cost and count per game, opponent's in the same games, excess with a CI, examples."""
    ng = len(ents)
    per = defaultdict(lambda: {'f': defaultdict(float), 'o': defaultdict(float), 'nf': 0, 'no': 0, 'ex': [], 'eps': []})
    for gi, a, b, d in ents:
        for e in d['episodes']:
            k = keyfn(e)
            if k is None:
                continue
            c = per[k]
            if e['team'] == a:
                c['f'][gi['dir']] += e['cost']
                c['nf'] += 1
                c['eps'].append((gi, e))
            else:
                c['o'][gi['dir']] += e['cost']
                c['no'] += 1
    clusters = {gi['dir']: gi['cluster'] for gi, *_ in ents}
    rows = []
    for k, c in per.items():
        fsum, osum = sum(c['f'].values()), sum(c['o'].values())
        rows.append({'key': k, 'f': fsum / ng, 'o': osum / ng, 'nf': c['nf'] / ng, 'no': c['no'] / ng, 'eps': c['eps'], 'per': c})
    rows.sort(key=lambda x: -(x['f'] - x['o']))
    # CIs for the top rows only (bootstrap over map pairs or ladder groups)
    for x in rows[:40]:
        diffs = [(clusters[gi['dir']], x['per']['f'].get(gi['dir'], 0) - x['per']['o'].get(gi['dir'], 0)) for gi, *_ in ents]
        lo, hi = boot_stat(list(by_cluster(diffs).values()), lambda xs: sum(xs) / len(xs), B=B)
        x['ci'] = (lo, hi)
    return rows


def _ci(x):
    lo, hi = x.get('ci', (None, None))
    return f'[{fmt(lo)} .. {fmt(hi)}]' if lo is not None else ''


def _examples(eps, k=3):
    eps = sorted(eps, key=lambda ge: -ge[1]['cost'])[:k]
    return '; '.join(f'{gi["dir"]} r{e["r"]}' + (f' #{e["cid"]}' if e.get('cid') is not None else '') + f' ({fmt(e["cost"])})' for gi, e in eps)


def render(ctx, rep):
    ents = entries(ctx)
    if not ents:
        rep.p('No games.')
        return
    A, B = (ctx.focus, 'opponent') if ctx.focus else ('loser', 'winner')
    ng = len(ents)
    won = sum(1 for gi, a, b, d in ents if gi['winner'] == a)
    rep.p(f'Set: {ctx.describe()}; {ng} games, {A} won {won}. Each side\'s losses are split into disjoint episodes priced in gems '
          '(deaths: bag + kill gold/4 + dead time at the game\'s earn rate; camp deaths; camps lost to the enemy; stalls of 10+ rounds), '
          f'tagged with the situation and clustered. Costs are per game; "excess" is {A} minus {B} in the same games, with a 95% '
          'cluster-bootstrap CI over map pairs or ladder groups. ' + ('' if ctx.focus else 'Without --team the focus side is each game\'s loser, which partly measures losing. ')
          + 'Examples are `analysis dir rROUND #champion (cost)`: open them with `py tools/replay/triage.py DIR --team NAME` '
          '(the game\'s turning points) or `py tools/replay/narrate.py` for a turn-level transcript.')

    rate = mean([d['rate'] for gi, a, b, d in ents])
    rep.p(f'Earn rate (gems per alive champion-round, both teams): mean {fmt(rate, 3)}, so a 60-round death costs about {fmt(60 * rate)} gems of time.')

    # by kind
    rep.h('Cost by kind')
    rows = []
    for k in KINDS:
        f = sum(e['cost'] for gi, a, b, d in ents for e in d['episodes'] if e['kind'] == k and e['team'] == a) / ng
        o = sum(e['cost'] for gi, a, b, d in ents for e in d['episodes'] if e['kind'] == k and e['team'] == b) / ng
        fw = mean([sum(e['cost'] for e in d['episodes'] if e['kind'] == k and e['team'] == a) for gi, a, b, d in ents if gi['winner'] == a])
        fl = mean([sum(e['cost'] for e in d['episodes'] if e['kind'] == k and e['team'] == a) for gi, a, b, d in ents if gi['winner'] != a])
        rows.append([k, fmt(f), fmt(o), fmt(f - o), fmt(fw), fmt(fl)])
    rep.table(['kind', f'{A} cost/game', f'{B} cost/game', 'excess', f'{A} in its wins', f'{A} in its losses'], rows, 'kinds')

    # top clusters
    MIN_N, MIN_G = 4, 3
    rows = cluster_table(ents, ckey)
    rep.h('Top weaknesses: clusters by excess cost')
    rep.p(f'Every episode kind, clustered by champion and situation (deaths: bag and what the victim was doing the round before the fatal damage '
          f'began). Sorted by {A}\'s cost per game minus {B}\'s for the same cluster in the same games; clusters with fewer than {MIN_N} focus episodes '
          f'or {MIN_G} games are left to the list of single expensive episodes below. "mix" gives each secondary tag\'s most common value among the focus '
          'episodes. cf columns: share of the cluster\'s focus bag gems that a recall in the safe window / a tribute at the last altar passed would have saved.')
    out = []
    shown = 0
    for x in rows:
        if x['f'] - x['o'] <= 0 or shown >= 25:
            break
        eps = [e for _, e in x['eps']]
        if len(eps) < MIN_N or len({gi['dir'] for gi, _ in x['eps']}) < MIN_G:
            continue
        shown += 1
        bag = sum(e['bag'] for e in eps)
        cr = sum(e['bag'] for e in eps if (e.get('cf') or {}).get('recall'))
        ca = sum(e['cf']['altar']['bag'] for e in eps if (e.get('cf') or {}).get('altar') and not e['cf']['altar']['enemies8'])
        out.append([_ckeystr(x['key']), fmt(x['nf'], 2), fmt(x['no'], 2), fmt(x['f']), fmt(x['o']), f'{fmt(x["f"] - x["o"])} {_ci(x)}', _mix(eps),
                    pct(cr / bag, 0) if bag else '-', pct(ca / bag, 0) if bag else '-', code_for(x['key']), _examples(x['eps'])])
        if x.get('ci', (None,))[0] is not None and x['ci'][0] > 0 and shown <= 6:
            rep.highlight(f'{A}: {_ckeystr(x["key"])}: {fmt(x["f"])} gems a game against {fmt(x["o"])} for {B} ({fmt(x["nf"], 2)} a game, {_mix(eps)}); '
                          f'look at {code_for(x["key"])}; e.g. {_examples(x["eps"], 2)}')
    rep.table(['situation', f'{A} n/game', f'{B} n/game', f'{A} cost/game', f'{B} cost/game', 'excess [95% CI]', 'mix', 'cf recall', 'cf altar',
               'look at', 'examples'], out, 'clusters')

    rows = cluster_table(ents, lambda e: ckey(e) if e['kind'] == 'camp_lost' else (e['kind'], 'any') + ckey(e)[2:])
    rep.p('The same without the champion (kind and situation only):')
    out = []
    for x in rows[:15]:
        eps = [e for _, e in x['eps']]
        if not eps:
            continue
        out.append([_ckeystr(x['key']).replace('any ', 'any champion ', 1), fmt(x['nf'], 2), fmt(x['no'], 2), fmt(x['f']), fmt(x['o']),
                    f'{fmt(x["f"] - x["o"])} {_ci(x)}', _mix(eps), _examples(x['eps'], 2)])
    rep.table(['situation', f'{A} n/game', f'{B} n/game', f'{A} cost/game', f'{B} cost/game', 'excess [95% CI]', 'mix', 'examples'], out, 'situations')

    big = sorted(((gi, e) for gi, a, b, d in ents for e in d['episodes'] if e['team'] == a), key=lambda ge: -ge[1]['cost'])[:15]
    rep.p(f'{A}\'s single most expensive episodes (rare situations the clusters above leave out):')
    rep.table(['game / round', 'episode', 'cost', 'tags'],
              [[f'{gi["dir"]} r{e["r"]}' + (f' #{e["cid"]}' if e.get('cid') is not None else ''), _keystr(e['key']), fmt(e['cost']),
                _tagstr(e)] for gi, e in big], 'expensive')

    # marginals: deaths by each tag
    rep.h('Deaths by situation')
    rep.p('Death episodes only (killed by champions), one tag at a time. cost = bag + kill gold/4 + dead time.')
    for name, fn in (('champion', lambda e: e['key'][1]), ('bag', lambda e: e['key'][2]), ('doing before the first hit', lambda e: e['key'][3]),
                     ('numbers at the first hit', lambda e: e['key'][4]), ('warning', lambda e: e['key'][5]),
                     ('half', lambda e: e['tags']['half'])):
        rs = cluster_table(ents, lambda e, fn=fn: fn(e) if e['kind'] == 'death' else None)
        out = [[x['key'], fmt(x['nf'], 2), fmt(x['no'], 2), fmt(x['f']), fmt(x['o']), f'{fmt(x["f"] - x["o"])} {_ci(x)}', _examples(x['eps'], 2)] for x in rs]
        rep.p(f'**{name}**')
        rep.table([name, f'{A} deaths/game', f'{B} deaths/game', f'{A} cost/game', f'{B} cost/game', 'excess [95% CI]', 'examples'], out,
                  'deaths_' + name.split()[0])

    # counterfactuals
    rep.h('Avoidable bag losses')
    rep.p('Deaths with gems where the replay shows a rule-checked alternative, had the enemy acted the same. **recall window**: a killer was in '
          'the victim\'s sight with no damage or stun to it for 6+ rounds before the first hit, so a recall started at the window\'s start (5 turn '
          'ends; only damage or a stun cancels it) would have landed first; with an enemy within 4 during the window the recall may itself have drawn '
          'the attack, so those gems are also given apart. '
          '**altar**: within 40 rounds before dying it stood within 1 of an altar the enemy had not locked, carrying at least half the final bag, and a '
          'tribute started then (ceil(bag/10) turn ends; only a stun cancels it) would have completed before the death, with no stun on it in that span; '
          'split by whether an enemy was within 8 then (with one near, the tribute itself may have drawn the attack sooner). '
          f'Look at: recall {CODE[("cf", "recall")]}; altar {CODE[("cf", "altar")]}.')
    rows = []
    for side, lab in ((0, A), (1, B)):
        dd = [(gi, e) for gi, a, b, d in ents for e in d['episodes'] if e['kind'] == 'death' and e['team'] == (a if side == 0 else b)]
        bag = sum(e['bag'] for _, e in dd)
        cr = [(gi, e) for gi, e in dd if e['cf']['recall']]
        ca = [(gi, e) for gi, e in dd if e['cf']['altar'] and not e['cf']['altar']['enemies8']]
        cn = [(gi, e) for gi, e in dd if e['cf']['altar'] and e['cf']['altar']['enemies8']]
        crc = [(gi, e) for gi, e in cr if e['cf']['recall']['closest'] > ctx.params['radius'] // 2]
        rows.append([lab, fmt(bag / ng), fmt(len(cr) / ng, 2), fmt(sum(e['bag'] for _, e in cr) / ng), fmt(sum(e['bag'] for _, e in crc) / ng), fmt(len(ca) / ng, 2),
                     fmt(sum(e['cf']['altar']['bag'] for _, e in ca) / ng), fmt(len(cn) / ng, 2), fmt(sum(e['cf']['altar']['bag'] for _, e in cn) / ng)])
    rep.table(['side', 'bag gems lost/game', 'recall window/game', 'gems', 'gems, no enemy within 4 in the window', 'altar, no enemy within 8/game', 'gems',
               'altar, enemy within 8/game', 'gems'],
              rows, 'cf')
    for kind in ('recall', 'altar'):
        dd = [(gi, e) for gi, a, b, d in ents for e in d['episodes'] if e['kind'] == 'death' and e['team'] == a and e['cf'][kind]]
        dd.sort(key=lambda ge: -ge[1]['bag'])
        lines = []
        for gi, e in dd[:8]:
            tg = e['tags']
            if kind == 'recall':
                lines.append(f'{gi["dir"]} r{e["r"]} #{e["cid"]} {e["key"][1]} bag {e["bag"]}: killer in sight from r{tg["first_seen"]}, no damage from '
                             f'r{e["cf"]["recall"]["r"]} (closest enemy {e["cf"]["recall"]["closest"]}), first hit r{e["r_hit"]}; {tg["doing"]}, {tg["num"]}, {tg["half"]} half')
            else:
                cf = e['cf']['altar']
                lines.append(f'{gi["dir"]} r{e["r"]} #{e["cid"]} {e["key"][1]} bag {e["bag"]}: by an altar at r{cf["r"]} with {cf["bag"]} '
                             f'(tribute {cf["dur"]} rounds, {cf["enemies8"]} enemies within 8), died {e["r"] - cf["r"]} rounds later, {tg["doing"]}')
        if lines:
            rep.p(f'Largest {A} {kind}-avoidable deaths:')
            rep.bullets(lines)

    rep.h('Death hazard by activity')
    rep.p('Champion-rounds spent on each activity (analysis/macro.py turn classes) and deaths to champions whose fatal damage began right '
          'after that activity, per 1000 such rounds, so a side is not penalised for doing more of something. Gems = bag gems lost in those deaths.')
    hz = [defaultdict(lambda: [0, 0, 0]), defaultdict(lambda: [0, 0, 0])]
    for gi, a, b, d in ents:
        for side, t in ((0, a), (1, b)):
            for k, v in d.get('doing_rounds', {}).get(t, {}).items():
                hz[side][k][0] += v
            for e in d['episodes']:
                if e['team'] == t and e['kind'] == 'death':
                    hz[side][e['tags']['doing']][1] += 1
                    hz[side][e['tags']['doing']][2] += e['bag']
    rows = []
    for k in sorted(set(hz[0]) | set(hz[1]), key=lambda k: -(hz[0][k][1] + hz[1][k][1])):
        f, o = hz[0][k], hz[1][k]
        if not (f[1] or o[1]) or k == 'respawning':
            continue
        rows.append([k, fmt(f[0] / ng), fmt(1000 * f[1] / f[0], 2) if f[0] else '-', fmt(f[2] / ng), fmt(o[0] / ng), fmt(1000 * o[1] / o[0], 2) if o[0] else '-',
                     fmt(o[2] / ng)])
    rep.table(['activity', f'{A} rounds/game', f'{A} deaths per 1000', f'{A} gems lost/game', f'{B} rounds/game', f'{B} deaths per 1000', f'{B} gems lost/game'],
              rows, 'hazard')

    # exposure: carried bags and deaths per carried round, by champion and bag bucket
    rep.h('Bag exposure')
    rep.p('Champion-rounds alive carrying a bag of each size, and deaths with that bag per 1000 such rounds (a hazard rate, so a side that carries '
          'more is not penalised for carrying).')
    # exposure is recomputed from the episodes' denominators below
    expo = [defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0])]
    for gi, a, b, d in ents:
        for side, t in ((0, a), (1, b)):
            for (typ, bk), rounds in d.get('exposure', {}).get(t, {}).items():
                expo[side][(typ, bk)][0] += rounds
            for e in d['episodes']:
                if e['team'] == t and e['kind'] in ('death', 'camp_death') and e['bag'] > 0:
                    expo[side][(e['key'][1], e['key'][2] if e['kind'] == 'death' else e['key'][3])][1] += 1
    keys = sorted(set(expo[0]) | set(expo[1]), key=lambda k: (k[0], [b[2] for b in BAGS].index(k[1])))
    rows = []
    for k in keys:
        if k[1] == '0':
            continue
        f, o = expo[0][k], expo[1][k]
        rows.append([k[0], k[1], fmt(f[0] / ng), f[1], fmt(1000 * f[1] / f[0], 2) if f[0] else '-', fmt(o[0] / ng), o[1], fmt(1000 * o[1] / o[0], 2) if o[0] else '-'])
    rep.table(['champion', 'bag', f'{A} rounds/game', f'{A} deaths', f'{A} per 1000', f'{B} rounds/game', f'{B} deaths', f'{B} per 1000'], rows, 'exposure')

    # fights
    rep.h('Fights lost')
    rep.p('Engagements (analysis/fights.py) the side lost on net swing (kill gems + gold/4 - bags lost); these overlap the death episodes. '
          'numbers = own minus enemy champions within 8 at the start; absent = own champions 9-16 away at the start that never joined.')
    agg = defaultdict(lambda: [[0, 0.0, []], [0, 0.0, []]])
    for gi, a, b, d in ents:
        for f in d['fights']:
            if f['swing'] >= 0:
                continue
            side = 0 if f['team'] == a else 1
            k = (f'{f["num"]:+d}' if abs(f['num']) < 2 else ('+2+' if f['num'] > 0 else '-2-'), 'we started' if f['init'] else 'they started',
                 'absent ally 9-16' if f['absent16'] else 'no ally 9-16')
            agg[k][side][0] += 1
            agg[k][side][1] += -f['swing']
            agg[k][side][2].append((gi, f))
    rows = []
    for k, (fo, op) in sorted(agg.items(), key=lambda kv: -(kv[1][0][1] - kv[1][1][1])):
        ex = '; '.join(f'{gi["dir"]} r{f["r"]} ({fmt(-f["swing"])})' for gi, f in sorted(fo[2], key=lambda x: x[1]['swing'])[:2])
        rows.append(list(k) + [fmt(fo[0] / ng, 2), fmt(fo[1] / ng), fmt(op[0] / ng, 2), fmt(op[1] / ng), fmt((fo[1] - op[1]) / ng), ex])
    rep.table(['numbers', 'initiator', 'help in reach', f'{A} lost/game', f'{A} gems/game', f'{B} lost/game', f'{B} gems/game', 'excess', 'examples'],
              rows, 'fights', limit=20)
    ab = [Counter(), Counter()]
    for gi, a, b, d in ents:
        for f in d['fights']:
            if f['swing'] < 0:
                ab[0 if f['team'] == a else 1].update(f['absent_what'])
    rep.p(f'Absent allies 9-16 away in lost fights, by what they were doing: {A}: ' + ', '.join(f'{k} {v}' for k, v in ab[0].most_common(6))
          + f'; {B}: ' + ', '.join(f'{k} {v}' for k, v in ab[1].most_common(6)) + '.')

    # wins vs losses: what goes with losing
    if ctx.focus:
        rep.h(f'{A}\'s losses against its wins')
        rep.p('Cluster cost per game in the focus team\'s losses minus its wins (top 12): the situations that most separate a loss from a win. '
              'Partly reverse causality (a losing side is behind and fights at a disadvantage); the round column shows when they happen.')
        Lg = [e for e in ents if e[0]['winner'] != e[1]]
        Wg = [e for e in ents if e[0]['winner'] == e[1]]
        if Lg and Wg:
            acc = defaultdict(lambda: [0.0, 0.0, []])
            for gi, a, b, d in Lg:
                for e in d['episodes']:
                    if e['team'] == a:
                        acc[e['key']][0] += e['cost'] / len(Lg)
                        acc[e['key']][2].append(e['r'])
            for gi, a, b, d in Wg:
                for e in d['episodes']:
                    if e['team'] == a:
                        acc[e['key']][1] += e['cost'] / len(Wg)
            rows = []
            for k, (l, w, rs) in sorted(acc.items(), key=lambda kv: -(kv[1][0] - kv[1][1]))[:12]:
                rows.append([_keystr(k), fmt(l), fmt(w), fmt(l - w), fmt(sorted(rs)[len(rs) // 2]) if rs else '-'])
            rep.table(['situation', 'in losses', 'in wins', 'difference', 'median round'], rows, 'winloss')
