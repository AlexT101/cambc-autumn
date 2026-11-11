"""Macro: where each team's champion-turns go, gem flow, cohesion and local numbers, map control, who turns up to
fights, camp contests, and why games are lost (the gem-margin decomposition and the break round).

Everything is read from the replay alone (no bot traces), per side, so it compares any two bots. Rounds are play
rounds; a champion's round r is classified from its state at the start (end of r-1) and end of r and the events of r."""

from collections import Counter, defaultdict, deque

from . import fights as fights_mod
from . import params as params_mod
from .data import chebyshev
from .util import boot_stat, by_cluster, fmt, mean, median, pct, quantile

PHASES = [(1, 150, 'r1-150'), (151, 400, 'r151-400'), (401, 800, 'r401-800'), (801, 10**9, 'r801+')]
# First match wins: dead, fight (dealt or took champion damage), lost (stunned), channels by kind, camp (hit a camp),
# walk_bag / walk (moved, with / without gems), lost (out of fuel or bot error, still), hold (still on a claimable group's tile),
# spawn (still on own spawn), wait_camp (still within 3 of a respawning or live group's tiles without hitting it),
# wait_altar (still within 2 of an altar), idle (alive, still, none of the above).
CLASSES = ['dead', 'lost', 'fight', 'tribute', 'recall', 'teleport', 'camp', 'hold', 'walk_bag', 'walk', 'spawn', 'wait_camp',
           'wait_altar', 'idle']
WALKS = ('walk', 'walk_bag')
WORK = ('camp', 'hold', 'tribute')
DESTS = ['camp', 'hold', 'tribute', 'fight', 'recall', 'spawn', 'wait_camp', 'wait_altar', 'idle', 'dead', 'other']
BUSY = {'camp': 'camp', 'hold': 'hold', 'tribute': 'channel', 'recall': 'channel', 'teleport': 'channel', 'wait_camp': 'waiting',
        'wait_altar': 'waiting'}
CAUSES = ('farm', 'fight', 'camp', 'bank')

METRICS = {
    'mt_walk': ('alive turns walking (with or without gems)', False, False),
    'mt_walk_bag': ('alive turns walking while carrying gems', None, False),
    'mt_work': ('alive turns at work: hitting camps, holding captures, tributing', True, False),
    'mt_fight': ('alive turns in fights (dealt or took champion damage)', None, True),
    'mt_wait': ('alive turns waiting still by a respawning or live camp, or by an altar, without hitting or holding', None, False),
    'mt_idle': ('alive turns idle elsewhere off spawn', False, False),
    'mt_spawn': ('alive turns standing on own spawn', False, False),
    'mt_recall': ('alive turns channelling recalls', None, False),
    'mt_dead': ('champion turns dead', False, True),
    'regroup_share': ('alive turns on walks that end next to an ally who was 9+ away at the start (walking to allies)', None, False),
    'walk_waste': ('walked steps beyond the straight (Chebyshev) line of each walk leg / steps', False, False),
    'walk_per_gem': ('walk turns per gem earned (captures and kills)', False, True),
    'earned_per100': ('gems earned (capture shares + kill bags) per 100 rounds', True, True),
    'conversion': ('tributed / earned gems', True, True),
    'gem_latency': ('mean rounds a tributed gem was carried (gem-weighted)', None, False),
    'gem_exposed': ('carried gem-rounds in sight of an enemy / carried gem-rounds', False, True),
    'carry_top': ("share of the team's carried gem-rounds on its top carrier", None, False),
    'nn_dist': ('distance to the nearest living ally (alive, off spawn; mean)', None, False),
    'isolated': ('alive champion-rounds off spawn with no ally within 8', None, False),
    'outnumbered': ('contact champion-rounds (an enemy within 8) with more enemies than allies within 8', False, True),
    'outnumbering': ('contact champion-rounds with more allies than enemies within 8', True, True),
    'control': ('camp value nearer (walking) to our champions than theirs, gems + gold/4 per respawn, sampled', True, True),
    'control_own': ('own-half camp value under our control', True, True),
    'enemy_half': ('alive champion-rounds on the enemy half', None, True),
    'own_lost': ("gems of own-half captures taken by the enemy / own-half captured gems", False, True),
    'contest_win': ('contested camp cycles (both teams hit, held or contested) we captured', True, True),
    'fight_turnout': ('own alive champions within 8 of a fight at its start / own alive champions', True, True),
    'fight_outnum': ('fights started with fewer own champions present', False, True),
    'lonely_death': ('deaths to champions with no living ally within 8', False, True),
}
MEAN_KEYS = set()


def _phase(r):
    for k, (lo, hi, _) in enumerate(PHASES):
        if lo <= r <= hi:
            return k
    return len(PHASES) - 1


CAPTURE = 6
ABBR = {'Wolf': 'W', 'Elk': 'E', 'Gem cluster': 'G', 'Gold cluster': '$', 'Monolith': 'M', 'Golem': 'O'}


def _gkey(mp, gid):
    return ''.join(sorted(ABBR[x] for x in mp.groups[gid]['types']))


_fields = {}


def group_fields(mp):
    """Walking distance (king moves; walls, holes and altars block) from each group's camp tiles, flat x*H+y."""
    if mp.hash in _fields:
        return _fields[mp.hash]
    W, H = mp.W, mp.H
    blocked = mp.walls | mp.holes | set(mp.altars)
    pas = [(x, y) not in blocked for x in range(W) for y in range(H)]
    out = {}
    for grp in mp.groups:
        dist = [1 << 20] * (W * H)
        q = deque()
        for x, y in grp['tiles']:
            dist[x * H + y] = 0
            q.append(x * H + y)
        while q:
            k = q.popleft()
            x, y = divmod(k, H)
            d = dist[k] + 1
            for nx in (x - 1, x, x + 1):
                if 0 <= nx < W:
                    for ny in (y - 1, y, y + 1):
                        if 0 <= ny < H:
                            kk = nx * H + ny
                            if dist[kk] > d and pas[kk]:
                                dist[kk] = d
                                q.append(kk)
        out[grp['id']] = dist
    if len(_fields) > 64:
        _fields.clear()
    _fields[mp.hash] = out
    return out


def _wealth(g):
    """Per team: per-round tributed + carried gems, and per-round component deltas from the events."""
    n = g.n_rounds
    R = g.rounds
    comp = [{k: [0] * (n + 2) for k in ('cap', 'kg', 'lostc', 'lostm')} for _ in (0, 1)]
    for e in g.events:
        k, r = e['k'], e['r']
        if r > n:
            r = n
        if k == 'capture':
            for cid, gems, _ in e['shares']:
                comp[g.team_of[cid]]['cap'][r] += gems
        elif k == 'death':
            t = g.team_of[e['v']]
            if e.get('by') is not None and e['by'] in g.team_of:
                # the victim's bag, not gemsTo: gemsTo is the killer's gain over the step, repeated on each kill of a multi-kill
                comp[t]['lostc'][r] += e.get('gems', 0)
                comp[g.team_of[e['by']]]['kg'][r] += e.get('gems', 0)
            else:
                comp[t]['lostm'][r] += e.get('gems', 0)
    carried = [[0] * n for _ in (0, 1)]
    for ch in R['champions']:
        t = ch['team']
        gl = ch['gems']
        for i in range(min(n, len(gl))):
            carried[t][i] += gl[i] or 0
    wealth = [[R['gems'][t][i] + carried[t][i] for i in range(n)] for t in (0, 1)]
    return wealth, carried, comp


def _window_sum(comp, a, b):
    """Component sums over rounds a..b inclusive."""
    return {k: sum(v[a:b + 1]) for k, v in comp.items()}


def classify(g):
    """Each champion-round's class (CLASSES, first match wins): {cid: [None] + [class of round r for r in 1..n]}.
    Cached on the Game, so the reports that need it share one pass."""
    if getattr(g, '_macro_cls', None) is not None:
        return g._macro_cls
    mp, n, R = g.map, g.n_rounds, g.rounds
    champs = R['champions']
    team_of = g.team_of
    camp_hit, fight, moved_by_chan = set(), set(), set()
    for e in g.events:
        k = e['k']
        if k in ('attack', 'cast'):
            a, r = e['a'], e['r']
            if e.get('cdmg'):
                camp_hit.add((a, r))
            ta = team_of.get(a)
            for v, amt in e.get('dmg') or []:
                if v in team_of and team_of[v] != ta and amt > 0:
                    fight.add((a, r))
                    fight.add((v, r))
            for v in e.get('stun') or []:
                if v in team_of and team_of[v] != ta:
                    fight.add((a, r))
                    fight.add((v, r))
        elif k in ('recall_end', 'teleport_end', 'respawn'):
            moved_by_chan.add((e['a'], e['r']))
    grows = R['groups']
    gi = 0
    gstate = {}
    near_cache = {}

    def near_groups(p):
        if p not in near_cache:
            near_cache[p] = [grp['id'] for grp in mp.groups if any(chebyshev(p, q) <= 3 for q in grp['tiles'])]
        return near_cache[p]
    cls = {c['id']: [None] * (n + 1) for c in champs}
    for i in range(n):
        r = R['round'][i] if i < len(R['round']) else i + 1
        while gi < len(grows) and grows[gi][0] <= r:
            row = grows[gi]
            gstate[row[1]] = row[2]
            gi += 1
        j = i - 1 if i > 0 else i
        for c in champs:
            cid, t = c['id'], c['team']
            p1 = (c['x'][i], c['y'][i]) if c['alive'][i] and c['x'][i] is not None else None
            p0 = (c['x'][j], c['y'][j]) if c['alive'][j] and c['x'][j] is not None else None
            tc = c['turn'][i] if i < len(c['turn']) else 0
            if tc == 4 or (p1 is None and p0 is None):
                k = 'dead'
            elif (cid, r) in fight:
                k = 'fight'
            elif tc == 5:
                k = 'lost'
            elif tc == 3:
                ch_ = c['chan'][i] or (c['chan'][j] if j != i else 0)
                k = {1: 'recall', 2: 'tribute', 3: 'teleport'}.get(ch_, 'recall')
            elif (cid, r) in camp_hit:
                k = 'camp'
            elif p1 is not None and p0 is not None and p1 != p0 and (cid, r) not in moved_by_chan:
                k = 'walk_bag' if (c['gems'][j] or 0) > 0 else 'walk'
            elif tc in (6, 7):
                # out of fuel or a bot error, still and without a hit: the turn was lost (some ladder bots run out of
                # fuel every turn after acting, so a turn that moved or hit is classed by what it did)
                k = 'lost'
            elif p1 is not None and p1 in mp.group_tiles and gstate.get(mp.group_tiles[p1]) == 2:
                k = 'hold'
            elif mp.in_spawn(t, p1):
                k = 'spawn'
            elif p1 is not None and any(gstate.get(gid) in (1, 3) for gid in near_groups(p1)):
                k = 'wait_camp'
            elif p1 is not None and mp.altar_dist(p1) <= 2:
                k = 'wait_altar'
            else:
                k = 'idle'
            cls[cid][r] = k
    g._macro_cls = cls
    return cls


def extract(g, P=None):
    P = P or params_mod.DEFAULTS
    RAD = P['radius']
    JOIN = P.get('macro_join', 3)
    WIN = P.get('macro_window', 100)
    EVERY = P.get('macro_every', 5)
    mp, n, R = g.map, g.n_rounds, g.rounds
    champs = R['champions']
    team_of, name_of = g.team_of, g.name_of
    ids = [c['id'] for c in champs]
    camp_group = {c['id']: c['group'] for c in mp.camps}
    gval = {grp['id']: (grp['gems'] + 0.25 * grp['gold']) / max(1, grp['respawn']) for grp in mp.groups}

    # --- wealth, components and the break round (computed first: the window's turns are counted in the main loop)
    wealth, carried, comp = _wealth(g)
    winner = g.winner
    loser = 1 - winner
    brk = 0
    for i in range(n):
        if wealth[loser][i] >= wealth[winner][i]:
            brk = i + 1
    w0, w1 = brk + 1, min(n, brk + WIN)

    cls = classify(g)   # cls[cid][r]
    fields = group_fields(mp)
    H = mp.H

    turns = [[Counter() for _ in PHASES] for _ in (0, 1)]
    win_turns = [Counter(), Counter()]
    types = [defaultdict(Counter) for _ in (0, 1)]
    coh = [defaultdict(float) for _ in (0, 1)]
    coh_ph = [[defaultdict(float) for _ in PHASES] for _ in (0, 1)]
    gem_rounds = defaultdict(float)
    exposed = [0.0, 0.0]
    ctrl = [[0.0, 0.0] for _ in PHASES]   # [team0 value, total] per phase (team1 = total - team0)
    ctrl_own = [[0.0, 0.0], [0.0, 0.0]]   # per team: [held own-half value, own-half value]
    timeline = []
    BIN = 50
    tl_acc = [Counter(), Counter()]

    for i in range(n):
        r = R['round'][i] if i < len(R['round']) else i + 1
        ph = _phase(r)
        pos_end = {}
        for c in champs:
            if c['alive'][i] and c['x'][i] is not None:
                pos_end[c['id']] = (c['x'][i], c['y'][i])
        for c in champs:
            cid, t = c['id'], c['team']
            p1 = pos_end.get(cid)
            k = cls[cid][r]
            turns[t][ph][k] += 1
            types[t][name_of[cid]][k] += 1
            if w0 <= r <= w1:
                win_turns[t][k] += 1
            tl_acc[t][k] += 1
            bag = c['gems'][i] or 0
            if bag and p1 is not None:
                gem_rounds[cid] += bag
                if c['seenBy'][i]:
                    exposed[t] += bag
        # cohesion and local numbers (end-of-round positions)
        alive = [[(cid, p) for cid, p in pos_end.items() if team_of[cid] == t] for t in (0, 1)]
        for t in (0, 1):
            field = [(cid, p) for cid, p in alive[t] if not mp.in_spawn(t, p)]
            acc, acc_ph = coh[t], coh_ph[t][ph]
            for cid, p in field:
                dn = min((chebyshev(p, q) for c2, q in alive[t] if c2 != cid), default=None)
                acc['field'] += 1
                acc_ph['field'] += 1
                if dn is not None:
                    acc['nn'] += dn
                    acc['nn_n'] += 1
                if dn is None or dn > RAD:
                    acc['iso'] += 1
                    acc_ph['iso'] += 1
                allies = sum(1 for c2, q in alive[t] if chebyshev(p, q) <= RAD)
                enemies = sum(1 for c2, q in alive[1 - t] if chebyshev(p, q) <= RAD)
                if enemies:
                    acc['contact'] += 1
                    acc['outn'] += enemies > allies
                    acc['outg'] += allies > enemies
                    acc_ph['contact'] += 1
                    acc_ph['outn'] += enemies > allies
                acc['enemy_half'] += mp.half(mp.own(t, p)) == 1
            if len(field) >= 2:
                ds = [chebyshev(a[1], b[1]) for x, a in enumerate(field) for b in field[x + 1:]]
                acc['spread'] += sum(ds) / len(ds)
                acc['spread_n'] += 1
        # map control
        if r % EVERY == 0:
            for grp in mp.groups:
                fd = fields[grp['id']]
                d = [min((fd[p[0] * H + p[1]] for _, p in alive[t]), default=1 << 20) for t in (0, 1)]
                v = gval[grp['id']]
                share0 = 1.0 if d[0] < d[1] else 0.0 if d[1] < d[0] else 0.5
                ctrl[ph][0] += v * share0
                ctrl[ph][1] += v
                side = grp['side']
                if side in (0, 1):
                    ctrl_own[side][0] += v * (share0 if side == 0 else 1 - share0)
                    ctrl_own[side][1] += v
        if r % BIN == 0 or i == n - 1:
            row = {'r': r, 'wealth': [wealth[0][i], wealth[1][i]], 'tributed': [R['gems'][0][i], R['gems'][1][i]],
                   'turns': [dict(tl_acc[0]), dict(tl_acc[1])]}
            timeline.append(row)
            tl_acc = [Counter(), Counter()]

    # --- walk legs: destination, regrouping, straightness
    legs = [Counter() for _ in (0, 1)]
    leg_n = [Counter() for _ in (0, 1)]
    regroup = [0, 0]
    regroup_dest = [Counter(), Counter()]
    steps, straight = [0, 0], [0, 0]
    for c in champs:
        cid, t = c['id'], c['team']
        q = cls[cid]
        r = 1
        while r <= n:
            if q[r] not in WALKS:
                r += 1
                continue
            a = r
            while r <= n and q[r] in WALKS:
                r += 1
            b = r - 1
            end = q[r] if r <= n else 'other'
            dest = end if end in DESTS else ('recall' if end == 'teleport' else 'other')
            if end in ('lost', 'walk', 'walk_bag', None):
                dest = 'other'
            length = b - a + 1
            legs[t][dest] += length
            leg_n[t][dest] += 1
            p0 = (c['x'][max(0, a - 2)], c['y'][max(0, a - 2)]) if c['alive'][max(0, a - 2)] else None
            p1 = (c['x'][b - 1], c['y'][b - 1]) if c['alive'][b - 1] else None
            if p0 and p1 and p0[0] is not None and p1[0] is not None:
                steps[t] += length
                straight[t] += min(length, chebyshev(p0, p1))
                if not mp.in_spawn(t, p1):
                    for c2 in champs:
                        if c2['id'] == cid or c2['team'] != t:
                            continue
                        s0, s1 = max(0, a - 2), b - 1
                        if not (c2['alive'][s0] and c2['alive'][s1]) or c2['x'][s0] is None or c2['x'][s1] is None:
                            continue
                        if chebyshev(p1, (c2['x'][s1], c2['y'][s1])) <= JOIN and chebyshev(p0, (c2['x'][s0], c2['y'][s0])) > RAD:
                            regroup[t] += length
                            regroup_dest[t][dest] += length
                            break

    # --- gem flow: FIFO bags for latency
    bags = {cid: deque() for cid in ids}
    age_sum, age_n = [0.0, 0.0], [0, 0]
    tribute_gems = [0, 0]
    for e in g.events:
        k, r = e['k'], e['r']
        if k == 'capture':
            for cid, gems, _ in e['shares']:
                if gems:
                    bags[cid].append([r, gems])
        elif k == 'death':
            bags[e['v']].clear()
            if e.get('by') in bags and e.get('gems'):
                bags[e['by']].append([r, e['gems']])
        elif k == 'tribute_end':
            t = team_of[e['a']]
            for r0, m in bags[e['a']]:
                age_sum[t] += (r - r0) * m
                age_n[t] += m
            tribute_gems[t] += e['gems']
            bags[e['a']].clear()

    # --- fights: turnout and why the absent were absent
    fl, _ = fights_mod.engagements(g, P)
    fstat = [Counter() for _ in (0, 1)]
    absent = [Counter() for _ in (0, 1)]
    by_numbers = [defaultdict(lambda: [0, 0.0]) for _ in (0, 1)]
    for f in fl:
        r0 = f['r0']
        i0 = g.start_idx(r0)
        loc = tuple(f.get('loc0') or f['loc'])
        for t in (0, 1):
            alive_ids = [cid for cid in g.team_ids[t] if g.pos(cid, i0)]
            if not alive_ids:
                continue
            here = f['present'][t]
            fstat[t]['n'] += 1
            fstat[t]['present'] += here
            fstat[t]['alive'] += len(alive_ids)
            fstat[t]['outnum'] += here < f['present'][1 - t]
            joined = set(f['ids'][t])
            for cid in alive_ids:
                p = g.pos(cid, i0)
                if chebyshev(p, loc) <= RAD:
                    continue
                if cid in joined:
                    absent[t]['joined later'] += 1
                    continue
                k = cls[cid][r0] or 'idle'
                if k == 'dead':  # died during the fight's first round
                    absent[t]['dead'] += 1
                    continue
                why = BUSY.get(k) or ('walking' if k in WALKS else k if k in ('spawn', 'idle', 'fight', 'dead') else 'other')
                if why == 'fight':
                    why = 'another fight'
                d = chebyshev(p, loc)
                absent[t][f'{why} {"<=16" if d <= 16 else ">16"}'] += 1
            diff = max(-2, min(2, here - f['present'][1 - t]))
            sw = f['swing'] if t == 0 else -f['swing']
            by_numbers[t][diff][0] += 1
            by_numbers[t][diff][1] += sw
        for t in (0, 1):
            for cid in g.team_ids[t]:
                if g.pos(cid, i0) is None:
                    absent[t]['dead'] += 1

    # --- deaths: support at the moment of death
    dstat = [Counter() for _ in (0, 1)]
    deaths_win = [[], []]
    for e in g.deaths:
        if e.get('linked') is not None:
            continue
        t = team_of[e['v']]
        r = e['r']
        if w0 <= r <= w1:
            deaths_win[t].append({'r': r, 'who': name_of[e['v']], 'bag': e.get('gems', 0),
                                  'by': name_of.get(e['by'], 'champion') if e.get('by') is not None else 'camp'})
        if e.get('by') is None:
            continue
        at = tuple(e['at'])
        i0 = g.start_idx(r)
        allies = sum(1 for cid in g.team_ids[t] if cid != e['v'] and (p := g.pos(cid, i0)) and chebyshev(p, at) <= RAD
                     and not (name_of[cid] in ('Cassi', 'Issac') and name_of[e['v']] in ('Cassi', 'Issac') and abs(cid - e['v']) == 1))
        enemies = sum(1 for cid in g.team_ids[1 - t] if (p := g.pos(cid, i0)) and chebyshev(p, at) <= RAD)
        dstat[t]['n'] += 1
        dstat[t]['lonely'] += allies == 0
        dstat[t]['outnum'] += enemies > allies + 1

    # --- camp cycles: contests and own-half captures
    cyc = defaultdict(lambda: {'hit': set(), 'held': set(), 'contested': False, 'cleared': None})
    contests = [Counter() for _ in (0, 1)]
    contest_types = [Counter() for _ in (0, 1)]
    half_caps = [Counter() for _ in (0, 1)]   # per capturing team: gems by the group's side relative to it
    caps_type = [Counter() for _ in (0, 1)]
    capacity = Counter()   # capture cycles each group type could at most give in this game: one per respawn + capture time
    for grp in mp.groups:
        capacity[_gkey(mp, grp['id'])] += n / (grp['respawn'] + CAPTURE)
    for e in g.events:
        k = e['k']
        if k in ('attack', 'cast') and e.get('cdmg'):
            for camp, amt in e['cdmg']:
                gid = camp_group.get(camp)
                if gid is not None and amt > 0:
                    cyc[gid]['hit'].add(team_of[e['a']])
        elif k == 'capture_hold':
            cyc[e['g']]['held'].add(e['team'])
        elif k == 'capture_reset' and e.get('contested'):
            cyc[e['g']]['contested'] = True
        elif k == 'group_clear' and e.get('by') in team_of:
            cyc[e['g']]['cleared'] = team_of[e['by']]
        elif k == 'capture':
            gid, t = e['g'], e['team']
            c_ = cyc.pop(gid, None) or {'hit': set(), 'held': set(), 'contested': False, 'cleared': None}
            gems = sum(s[1] for s in e['shares'])
            both = len(c_['hit'] | c_['held']) == 2 or c_['contested']
            key = _gkey(mp, gid)
            if both:
                contests[t]['won'] += 1
                contests[t]['won_gems'] += gems
                contests[1 - t]['lost'] += 1
                contests[1 - t]['lost_gems'] += gems
                contest_types[t][key + ' won'] += 1
                contest_types[1 - t][key + ' lost'] += 1
            if c_['cleared'] is not None and c_['cleared'] != t:
                contests[t]['steals'] += 1
                contests[1 - t]['stolen'] += 1
            side = mp.groups[gid]['side']
            rel = 'mid' if side == -1 else 'own' if side == t else 'enemy'
            half_caps[t][rel] += gems
            caps_type[t][key] += 1
            caps_type[t][key + ' gems'] += gems

    # --- assemble per-side metrics
    tot_ctrl = sum(c[1] for c in ctrl)
    sides, detail = [], []
    for t in (0, 1):
        tt = Counter()
        for c in turns[t]:
            tt.update(c)
        alive_t = sum(v for k, v in tt.items() if k != 'dead')
        allt = sum(tt.values())
        walk = tt['walk'] + tt['walk_bag']
        cap = sum(comp[t]['cap'])
        kg = sum(comp[t]['kg'])
        lostc, lostm = sum(comp[t]['lostc']), sum(comp[t]['lostm'])
        earned = cap + kg
        top = max((gem_rounds[cid] for cid in g.team_ids[t]), default=0)
        all_gr = sum(gem_rounds[cid] for cid in g.team_ids[t])
        co = coh[t]
        ct = contests[t]
        nct = ct['won'] + ct['lost']
        own_cap = half_caps[t]['own'] + half_caps[1 - t]['enemy']
        fs = fstat[t]
        s = {
            'mt_walk': walk / alive_t if alive_t else None,
            'mt_walk_bag': tt['walk_bag'] / alive_t if alive_t else None,
            'mt_work': sum(tt[k] for k in WORK) / alive_t if alive_t else None,
            'mt_fight': tt['fight'] / alive_t if alive_t else None,
            'mt_wait': (tt['wait_camp'] + tt['wait_altar']) / alive_t if alive_t else None,
            'mt_idle': tt['idle'] / alive_t if alive_t else None,
            'mt_spawn': tt['spawn'] / alive_t if alive_t else None,
            'mt_recall': tt['recall'] / alive_t if alive_t else None,
            'mt_dead': tt['dead'] / allt if allt else None,
            'regroup_share': regroup[t] / alive_t if alive_t else None,
            'walk_waste': 1 - straight[t] / steps[t] if steps[t] else None,
            'walk_per_gem': walk / earned if earned else None,
            'earned_per100': 100 * earned / n,
            'conversion': g.final_gems[t] / earned if earned else None,
            'gem_latency': age_sum[t] / age_n[t] if age_n[t] else None,
            'gem_exposed': exposed[t] / all_gr if all_gr else None,
            'carry_top': top / all_gr if all_gr else None,
            'nn_dist': co['nn'] / co['nn_n'] if co['nn_n'] else None,
            'isolated': co['iso'] / co['field'] if co['field'] else None,
            'outnumbered': co['outn'] / co['contact'] if co['contact'] else None,
            'outnumbering': co['outg'] / co['contact'] if co['contact'] else None,
            'control': (sum(c[0] for c in ctrl) if t == 0 else tot_ctrl - sum(c[0] for c in ctrl)) / tot_ctrl if tot_ctrl else None,
            'control_own': ctrl_own[t][0] / ctrl_own[t][1] if ctrl_own[t][1] else None,
            'enemy_half': co['enemy_half'] / co['field'] if co['field'] else None,
            'own_lost': half_caps[1 - t]['enemy'] / own_cap if own_cap else None,
            'contest_win': ct['won'] / nct if nct else None,
            'fight_turnout': fs['present'] / fs['alive'] if fs['alive'] else None,
            'fight_outnum': fs['outnum'] / fs['n'] if fs['n'] else None,
            'lonely_death': dstat[t]['lonely'] / dstat[t]['n'] if dstat[t]['n'] else None,
            # components (gems, whole game)
            'g_cap': cap, 'g_kill': kg, 'g_lost_champ': lostc, 'g_lost_camp': lostm, 'g_carried_end': carried[t][n - 1],
            'g_tributed': g.final_gems[t], 'g_contests': nct, 'spread': co['spread'] / co['spread_n'] if co['spread_n'] else None,
        }
        sides.append(s)
        detail.append({
            'turns': [dict(c) for c in turns[t]],
            'legs': dict(legs[t]), 'leg_n': dict(leg_n[t]), 'regroup': regroup[t], 'regroup_dest': dict(regroup_dest[t]),
            'types': {k: dict(v) for k, v in types[t].items()},
            'type_gems': {name_of[cid]: gem_rounds[cid] for cid in g.team_ids[t]},
            'type_cap': {}, 'coh_ph': [dict(x) for x in coh_ph[t]],
            'ctrl_ph': [(c[0] if t == 0 else c[1] - c[0], c[1]) for c in ctrl],
            'absent': dict(absent[t]), 'fights': dict(fs), 'by_numbers': {k: list(v) for k, v in by_numbers[t].items()},
            'contests': dict(ct), 'contest_types': dict(contest_types[t]), 'half_caps': dict(half_caps[t]),
            'caps_type': dict(caps_type[t]), 'capacity': dict(capacity),
            'deaths': dict(dstat[t]), 'win_turns': dict(win_turns[t]),
            'tribute_identity': g.final_gems[t] - (cap + kg - lostc - lostm - carried[t][n - 1]),
        })
    for e in g.events:
        if e['k'] == 'capture':
            for cid, gems, _ in e['shares']:
                tc = detail[team_of[cid]]['type_cap']
                tc[name_of[cid]] = tc.get(name_of[cid], 0) + gems

    # --- why the loser lost: whole game and the window after the break
    def parts(a, b):
        W_, L_ = _window_sum(comp[winner], a, b), _window_sum(comp[loser], a, b)
        return {'farm': W_['cap'] - L_['cap'], 'fight': (W_['kg'] - W_['lostc']) - (L_['kg'] - L_['lostc']),
                'camp': L_['lostm'] - W_['lostm']}
    whole = parts(1, n)
    whole['bank'] = carried[loser][n - 1] - carried[winner][n - 1]
    win = parts(w0, w1) if w0 <= w1 else {k: 0 for k in ('farm', 'fight', 'camp')}
    cause = max(('farm', 'fight', 'camp'), key=lambda k: win[k]) if w0 <= w1 else 'bank'
    if w0 > w1 or max(win.values()) <= 0:
        cause = 'bank' if wealth[loser][n - 1] >= wealth[winner][n - 1] else cause
    game = {'winner': winner, 'break': brk, 'window': [w0, w1], 'cause': cause, 'win_parts': win, 'whole': whole,
            'gap_after': (wealth[winner][w1 - 1] - wealth[loser][w1 - 1]) if w0 <= w1 else 0,
            'deaths_win': deaths_win, 'timeline': timeline,
            'wealth_at': {str(x): [wealth[0][min(x, n) - 1], wealth[1][min(x, n) - 1]] for x in (150, 400, 800)}}
    return {'sides': sides, 'detail': detail, 'game': game}


# ----------------------------------------------------------------------------------------------------- rendering

def _fm(key, v):
    if v is None:
        return '-'
    if key in ('nn_dist', 'gem_latency', 'walk_per_gem', 'earned_per100', 'spread') or key.startswith('g_'):
        return fmt(v)
    return pct(v, 1)


def _entries(ctx):
    """(gi, focus side, other side) per game: the focus team's side when --team is set, else the winner's."""
    out = []
    for gi in ctx.games:
        d = ctx.data[gi['dir']].get('macro')
        if not d:
            continue
        if ctx.focus:
            for t in ctx.focus_teams(gi):
                out.append((gi, t, 1 - t, d))
        else:
            out.append((gi, gi['winner'], 1 - gi['winner'], d))
    return out


def _pair_row(key, ents):
    pairs = [(d['sides'][a][key], d['sides'][b][key], gi['cluster']) for gi, a, b, d in ents]
    pairs = [p for p in pairs if p[0] is not None and p[1] is not None]
    if not pairs:
        return None
    f = _pp if key in RATEISH else fmt
    groups = list(by_cluster([(c, a - b) for a, b, c in pairs]).values())
    lo, hi = boot_stat(groups, lambda xs: sum(xs) / len(xs), B=300)
    diff = mean([a - b for a, b, _ in pairs])
    dtxt = f(diff) + (f' [{f(lo)} .. {f(hi)}]' if lo is not None else '')
    gt = sum(1 for a, b, _ in pairs if a > b) / len(pairs)
    return [key, _fm(key, mean([p[0] for p in pairs])), _fm(key, mean([p[1] for p in pairs])), dtxt, pct(gt), len(pairs)], (diff, lo, hi)


RATEISH = {k for k in METRICS if k not in ('nn_dist', 'gem_latency', 'walk_per_gem', 'earned_per100')}


def _pp(x):
    return '-' if x is None else f'{100 * x:+.1f}pt'


def _share_table(counters, classes):
    tot = [sum(c.values()) for c in counters]
    return [[k] + [pct(c.get(k, 0) / t, 1) if t else '-' for c, t in zip(counters, tot)] for k in classes]


def render(ctx, rep):
    ents = _entries(ctx)
    if not ents:
        rep.p('No games.')
        return
    A, B = (ctx.focus, 'opponent') if ctx.focus else ('winner', 'loser')
    rep.p(f'Set: {ctx.describe()}. Sides: {A} vs {B} in the same game ({len(ents)} pairs). '
          + ('Paired by game: the focus team against its opponent.' if ctx.focus else 'Without --team each game is read winner against loser, which partly measures winning.'),
          'Every number is read from the replay alone (no bot traces). Turn classes are per champion-round, first match wins: '
          'dead, fight (dealt or took champion damage), lost (stunned), tribute/recall/teleport channel, camp (hit a camp), '
          'walk_bag/walk (moved, carrying gems or not), lost (out of fuel or bot error without moving or hitting), hold (still on a claimable group tile), spawn (still on own spawn), idle. '
          'Distances are Chebyshev unless noted; camp control uses walking distance. Differences are mean '
          f'{A} minus {B} with a 95% cluster-bootstrap CI over map pairs or ladder groups.')

    # headline
    rows, eff = [], []
    for key, (desc, better, opp) in METRICS.items():
        res = _pair_row(key, ents)
        if not res:
            continue
        row, (diff, lo, hi) = res
        rows.append(row + [desc])
        if lo is not None and (lo > 0 or hi < 0):
            eff.append((key, diff, desc, better))
    rep.h('Macro metrics, paired')
    rep.table(['metric', A, B, f'{A} - {B} [95% CI]', f'{A} higher', 'games', 'definition'], rows, 'paired')
    for key, diff, desc, better in eff[:8]:
        tag = '' if better is None else (' (better)' if (diff > 0) == better else ' (worse)')
        rep.highlight(f'{A} vs {B}: {desc}: {_pp(diff) if key in RATEISH else ("+" if diff > 0 else "") + fmt(diff)}{tag}')

    if ctx.focus:
        won = [e for e in ents if e[0]['winner'] == e[1]]
        lost = [e for e in ents if e[0]['winner'] != e[1]]
        rows = []
        for key in METRICS:
            fw = [d['sides'][a][key] for gi, a, b, d in won]
            fl = [d['sides'][a][key] for gi, a, b, d in lost]
            ow = [d['sides'][b][key] for gi, a, b, d in won]
            ol = [d['sides'][b][key] for gi, a, b, d in lost]
            rows.append([key] + [_fm(key, mean(x)) for x in (fw, fl, ow, ol)])
        rep.h(f'{A} in its wins and losses')
        rep.p(f'{len(won)} wins, {len(lost)} losses. Opponent columns are the same games from the other side.')
        rep.table(['metric', f'{A} won', f'{A} lost', f'{B} when {A} won', f'{B} when {A} lost'], rows, 'winloss')

    # early game, paired: before most breaks, so less of it is the result of winning
    def early(d, t):
        tc = d['detail'][t]['turns'][0]
        al = sum(v for k, v in tc.items() if k != 'dead')
        co = d['detail'][t]['coh_ph'][0]
        cv = d['detail'][t]['ctrl_ph'][0]
        return {'walk': sum(tc.get(k, 0) for k in WALKS) / al if al else None,
                'work': sum(tc.get(k, 0) for k in WORK) / al if al else None,
                'wait': (tc.get('wait_camp', 0) + tc.get('wait_altar', 0)) / al if al else None,
                'dead': tc.get('dead', 0) / sum(tc.values()) if tc else None,
                'isolated': co.get('iso', 0) / co['field'] if co.get('field') else None,
                'outnumbered': co.get('outn', 0) / co['contact'] if co.get('contact') else None,
                'control': cv[0] / cv[1] if cv[1] else None}
    ek = ['walk', 'work', 'wait', 'dead', 'isolated', 'outnumbered', 'control']
    E = [(gi, early(d, a), early(d, b), gi['winner'] == a) for gi, a, b, d in ents]
    rows = []
    for k in ek:
        pr = [(x[k], y[k], gi['cluster'], won) for gi, x, y, won in E if x[k] is not None and y[k] is not None]
        if not pr:
            continue
        groups = list(by_cluster([(c, a_ - b_) for a_, b_, c, _ in pr]).values())
        lo, hi = boot_stat(groups, lambda xs: sum(xs) / len(xs), B=300)
        hi_side = [w for a_, b_, c, w in pr if a_ > b_]
        lo_side = [w for a_, b_, c, w in pr if a_ < b_]
        rows.append([k, pct(mean([p[0] for p in pr]), 1), pct(mean([p[1] for p in pr]), 1),
                     _pp(mean([a_ - b_ for a_, b_, _, _ in pr])) + (f' [{_pp(lo)} .. {_pp(hi)}]' if lo is not None else ''),
                     f'{pct(mean(hi_side), 0)} (n={len(hi_side)})' if hi_side else '-', f'{pct(mean(lo_side), 0)} (n={len(lo_side)})' if lo_side else '-'])
    if ctx.focus:
        rep.h('Rounds 1-150, paired')
        rep.p(f'The same quantities over the first 150 rounds only (most break rounds come later), with {A}\'s win rate in the games where its value '
              f'was higher or lower than {B}\'s.')
        rep.table(['r1-150', A, B, f'{A} - {B} [95% CI]', f'{A} win rate when higher', f'{A} win rate when lower'], rows, 'early')
    else:
        rep.h('Rounds 1-150, paired')
        rep.p('The same quantities over the first 150 rounds only (most break rounds come later). Win-rate columns: the share of games the winner had the higher or lower value.')
        rep.table(['r1-150', A, B, 'difference [95% CI]', 'winner higher', 'winner lower'], rows, 'early')

    # per map family
    fam = defaultdict(list)
    for e in ents:
        parts = e[0]['map'].split('-')
        if len(parts) > 1 and parts[-1].isdigit():
            parts = parts[:-1]
        if len(parts) > 1 and parts[0] == 'gen':
            parts = parts[1:]
        fam['-'.join(parts)].append(e)
    if len(fam) > 1:
        keys = ['mt_walk', 'mt_work', 'mt_dead', 'control', 'outnumbered', 'own_lost', 'contest_win']
        rows = []
        for f, es in sorted(fam.items(), key=lambda kv: -len(kv[1])):
            wr_ = mean([gi['winner'] == a for gi, a, b, d in es])
            diffs = []
            for k in keys:
                v = [d['sides'][a][k] - d['sides'][b][k] for gi, a, b, d in es if d['sides'][a][k] is not None and d['sides'][b][k] is not None]
                diffs.append(_pp(mean(v)) if v else '-')
            ls = [d['game']['cause'] for gi, a, b, d in es if gi['winner'] != a]
            top = Counter(ls).most_common(1)
            rows.append([f, len(es), pct(wr_, 0)] + diffs + [f'{top[0][0]} {top[0][1]}/{len(ls)}' if top else '-'])
        rep.h('By map family')
        rep.p(f'Maps by family (the name without its trailing seed and `gen-` prefix); {A} minus {B} per game, mean. '
              f'{"Win rate is the focus team's." if ctx.focus else "Without --team the first side is the winner, so the win rate is 100%."}')
        rep.table(['family', 'games', f'{A} won'] + [f'd {k}' for k in keys] + [f'{A} losses: top cause'], rows, 'families', limit=25)

    # turn budget
    tb = [Counter(), Counter()]
    tb_ph = [[Counter() for _ in PHASES] for _ in (0, 1)]
    for gi, a, b, d in ents:
        for s, t in ((0, a), (1, b)):
            for k, c in enumerate(d['detail'][t]['turns']):
                tb[s].update(c)
                tb_ph[s][k].update(c)
    rep.h('Where the turns go')
    rep.p('Share of all champion-rounds (dead included), whole game and per phase.')
    heads = ['class', A, B] + [f'{A} {p[2]}' for p in PHASES] + [f'{B} {p[2]}' for p in PHASES]
    cols = [tb[0], tb[1]] + tb_ph[0] + tb_ph[1]
    rep.table(heads, _share_table(cols, CLASSES), 'turns')

    lg = [Counter(), Counter()]
    rg = [Counter(), Counter()]
    alive = [0, 0]
    for gi, a, b, d in ents:
        for s, t in ((0, a), (1, b)):
            lg[s].update(d['detail'][t]['legs'])
            rg[s].update(d['detail'][t]['regroup_dest'])
            alive[s] += sum(v for c in d['detail'][t]['turns'] for k, v in c.items() if k != 'dead')
    rep.h('What the walking was for')
    rep.p('Walk turns by what the walk led to (the class of the first turn after the leg), as a share of alive turns. '
          '"regroup" counts the walks that end within 3 of an ally who was more than 8 away when the walk began, by destination.')
    rows = [[k, pct(lg[0][k] / alive[0], 1) if alive[0] else '-', pct(lg[1][k] / alive[1], 1) if alive[1] else '-',
             pct(rg[0][k] / alive[0], 1) if alive[0] else '-', pct(rg[1][k] / alive[1], 1) if alive[1] else '-'] for k in DESTS]
    rep.table(['walk led to', A, B, f'{A} regroup', f'{B} regroup'], rows, 'walks')

    # champion roles
    rep.h('Champion roles')
    rep.p('Per champion type, pooled over games: turn mix (alive turns), share of the team\'s capture gems and of its carried gem-rounds.')
    for s, label in ((0, A), (1, B)):
        ty = defaultdict(Counter)
        tg, tc = Counter(), Counter()
        tot_g, tot_c = 0, 0
        for gi, a, b, d in ents:
            t = a if s == 0 else b
            dt = d['detail'][t]
            for k, v in dt['types'].items():
                ty[k].update(v)
            tg.update(dt['type_gems'])
            tc.update(dt['type_cap'])
            tot_g += sum(dt['type_gems'].values())
            tot_c += sum(dt['type_cap'].values())
        rows = []
        for k in sorted(ty, key=lambda k: -sum(ty[k].values())):
            c = ty[k]
            al = sum(v for kk, v in c.items() if kk not in ('dead', 'wait'))
            c['wait'] = c['wait_camp'] + c['wait_altar']
            rows.append([k, sum(c.values()) - c['wait']] + [pct(c[x] / al, 0) if al else '-' for x in ('walk', 'walk_bag', 'camp', 'hold', 'fight', 'recall', 'wait', 'idle')]
                        + [pct(c['dead'] / (sum(c.values()) - c['wait']), 0), pct(tc[k] / tot_c, 0) if tot_c else '-', pct(tg[k] / tot_g, 0) if tot_g else '-'])
        rep.p(f'**{label}**')
        rep.table(['type', 'rounds', 'walk', 'walk_bag', 'camp', 'hold', 'fight', 'recall', 'wait', 'idle', 'dead', 'capture gems', 'gem-rounds'], rows,
                  f'roles_{"focus" if s == 0 else "other"}')

    # gem flow
    rep.h('Gem flow')
    rep.p('Per game means. tributed = captured + taken by kills - lost to champions - lost to camps - carried at the end '
          '(the identity holds exactly in every game unless noted).')
    keys = ['g_cap', 'g_kill', 'g_lost_champ', 'g_lost_camp', 'g_carried_end', 'g_tributed']
    rows = [[k[2:], fmt(mean([d['sides'][a][k] for gi, a, b, d in ents])), fmt(mean([d['sides'][b][k] for gi, a, b, d in ents]))] for k in keys]
    rep.table(['gems', A, B], rows, 'gemflow')
    bad = sum(1 for gi, a, b, d in ents for t in (0, 1) if d['detail'][t]['tribute_identity'])
    if bad:
        rep.p(f'Identity off in {bad} sides (Prospector rounding or extraction gaps).')

    # cohesion, control by phase
    rep.h('Cohesion and map control by phase')
    rows = []
    for k, (lo, hi, name) in enumerate(PHASES):
        row = [name]
        for s in (0, 1):
            acc = Counter()
            cv = [0.0, 0.0]
            for gi, a, b, d in ents:
                t = a if s == 0 else b
                acc.update(d['detail'][t]['coh_ph'][k])
                c = d['detail'][t]['ctrl_ph'][k]
                cv[0] += c[0]
                cv[1] += c[1]
            row += [pct(acc['iso'] / acc['field'], 0) if acc['field'] else '-', pct(acc['outn'] / acc['contact'], 0) if acc['contact'] else '-',
                    pct(cv[0] / cv[1], 0) if cv[1] else '-']
        rows.append(row)
    rep.table(['phase', f'{A} isolated', f'{A} outnumbered', f'{A} control', f'{B} isolated', f'{B} outnumbered', f'{B} control'], rows, 'phases')
    rep.p('isolated: field champion-rounds with no ally within 8; outnumbered: contact rounds with more enemies than allies within 8; '
          'control: share of camp value nearer by walking to that team\'s champions.')

    # fights
    rep.h('Who turns up to fights')
    rep.p('At each engagement\'s first round (analysis/fights.py clustering), every own champion alive and more than 8 from the fight, by what it was doing; '
          '"joined later" are those that dealt or took damage in it anyway. Distances are to the fight\'s first location.')
    ab = [Counter(), Counter()]
    fsum = [Counter(), Counter()]
    bn = [defaultdict(lambda: [0, 0.0]), defaultdict(lambda: [0, 0.0])]
    for gi, a, b, d in ents:
        for s, t in ((0, a), (1, b)):
            ab[s].update(d['detail'][t]['absent'])
            fsum[s].update(d['detail'][t]['fights'])
            for k, v in d['detail'][t]['by_numbers'].items():
                bn[s][int(k)][0] += v[0]
                bn[s][int(k)][1] += v[1]
    keys = sorted(set(ab[0]) | set(ab[1]), key=lambda k: -(ab[0][k] + ab[1][k]))
    rows = [[k, fmt(ab[0][k] / max(1, fsum[0]['n']), 2), fmt(ab[1][k] / max(1, fsum[1]['n']), 2)] for k in keys]
    rep.table(['absent ally was', f'{A} per fight', f'{B} per fight'], rows, 'absent')
    rows = [[f'{k:+d}' if abs(k) < 2 else ('+2 or more' if k > 0 else '-2 or fewer'), bn[0][k][0], fmt(bn[0][k][1] / bn[0][k][0], 1) if bn[0][k][0] else '-',
             bn[1][k][0], fmt(bn[1][k][1] / bn[1][k][0], 1) if bn[1][k][0] else '-'] for k in (-2, -1, 0, 1, 2)]
    rep.p('Net swing (gems from kills - own bags lost + gold/4) by champions present at the start, own minus enemy:')
    rep.table(['numbers', f'{A} fights', f'{A} mean swing', f'{B} fights', f'{B} mean swing'], rows, 'numbers')

    # contests
    rep.h('Camp contests')
    rep.p('A camp cycle (from respawn to capture) is contested when both teams hit its monsters or held its tiles, or a hold was reset as contested. '
          'Steals: captured by the team that did not land the clearing blow.')
    ct = [Counter(), Counter()]
    cty = [Counter(), Counter()]
    hc = [Counter(), Counter()]
    for gi, a, b, d in ents:
        for s, t in ((0, a), (1, b)):
            ct[s].update(d['detail'][t]['contests'])
            cty[s].update(d['detail'][t]['contest_types'])
            hc[s].update(d['detail'][t]['half_caps'])
    ng = len(ents)
    rows = [[k, fmt(ct[0][k] / ng, 2), fmt(ct[1][k] / ng, 2)] for k in ('won', 'lost', 'won_gems', 'lost_gems', 'steals', 'stolen')]
    rows += [[f'captured gems, {k} half', fmt(hc[0][k] / ng), fmt(hc[1][k] / ng)] for k in ('own', 'mid', 'enemy')]
    rep.table(['per game', A, B], rows, 'contests')
    kinds = sorted({k.rsplit(' ', 1)[0] for k in cty[0]})
    rows = []
    for k in kinds:
        w, l = cty[0][k + ' won'], cty[0][k + ' lost']
        rows.append([k, w, l, pct(w / (w + l), 0) if w + l else '-'])
    rows.sort(key=lambda r: -(r[1] + r[2]))
    rep.table(['group', f'{A} won', f'{A} lost', f'{A} share'], rows, 'contest_types', limit=15)

    cap = Counter()
    ctp = [Counter(), Counter()]
    for gi, a, b, d in ents:
        cap.update(d['detail'][a]['capacity'])
        ctp[0].update(d['detail'][a]['caps_type'])
        ctp[1].update(d['detail'][b]['caps_type'])
    rep.h('Which camps get taken')
    rep.p('Captures per group type against capacity: the cycles each type could give at most (game rounds / (respawn + 6 capture rounds), '
          'summed over the map\'s groups of that type, both halves). Low shares on strong groups are camps nobody farms.')
    rows = []
    for k in sorted(cap, key=lambda k: -cap[k]):
        rows.append([k, fmt(cap[k] / ng, 1), fmt(ctp[0][k] / ng, 1), fmt(ctp[1][k] / ng, 1), pct(ctp[0][k] / cap[k], 0), pct(ctp[1][k] / cap[k], 0),
                     pct((ctp[0][k] + ctp[1][k]) / cap[k], 0), fmt(ctp[0][k + ' gems'] / ng), fmt(ctp[1][k + ' gems'] / ng)])
    rep.table(['group', 'capacity a game', f'{A} captures', f'{B} captures', f'{A} share', f'{B} share', 'taken (both)', f'{A} gems', f'{B} gems'],
              rows, 'capacity', limit=20)

    # losses
    lost = [(gi, a, b, d) for gi, a, b, d in ents if gi['winner'] != a] if ctx.focus else ents
    who = f'{A}\'s losses' if ctx.focus else 'all games (loser\'s view)'
    rep.h(f'Why games are lost: {who}')
    rep.p('The break round is the last round the loser had at least the winner\'s wealth (tributed + carried gems); 0 means it was never level after round 1. '
          f'The window is the {ctx.params.get("macro_window", 100)} rounds after it. Its cause is the largest of: farm (capture gems, winner - loser), '
          'fight (kill gems taken minus bags lost to champions, winner - loser), camp (bags lost to camps, loser - winner); "bank" when the loser lost while '
          'holding at least as much wealth (gems carried, not tributed). Whole-game components are over all rounds.')
    cc = Counter(d['game']['cause'] for gi, a, b, d in lost)
    brks = [d['game']['break'] for gi, a, b, d in lost]
    rows = []
    for c in CAUSES:
        sel = [d for gi, a, b, d in lost if d['game']['cause'] == c]
        mix = [Counter(), Counter()]
        for d in sel:
            w = d['game']['winner']
            mix[0].update(d['detail'][1 - w]['win_turns'])
            mix[1].update(d['detail'][w]['win_turns'])
        def sh(m, ks):
            tot = sum(m.values())
            return pct(sum(m[k] for k in ks) / tot, 0) if tot else '-'
        rows.append([c, cc[c], pct(cc[c] / len(lost), 0) if lost else '-', fmt(median([d['game']['break'] for d in sel])) if sel else '-']
                    + [sh(mix[x], ks) for ks in (('dead',), WORK, WALKS) for x in (0, 1)])
    rep.table(['cause of the break window', 'games', 'share', 'median break', 'loser dead', 'winner dead', 'loser work', 'winner work',
               'loser walk', 'winner walk'], rows, 'causes')
    rep.p('Turn shares are over the windows of that cause (work = camp, hold, tribute). A farm window with a high loser dead share is a '
          'farm deficit that follows deaths; one with level dead shares is out-farming with bodies alive.')
    if brks:
        rep.p(f'Break round: median {fmt(median(brks))} (p25 {fmt(quantile(brks, .25))}, p75 {fmt(quantile(brks, .75))}); '
              f'{sum(1 for x in brks if x == 0)} never level, {sum(1 for x in brks if 0 < x <= 150)} in rounds 1-150, '
              f'{sum(1 for x in brks if 150 < x <= 400)} in 151-400, {sum(1 for x in brks if x > 400)} after 400.')
        wk = ['farm', 'fight', 'camp', 'bank']
        rows = [[k, fmt(mean([d['game']['whole'][k] for gi, a, b, d in lost])), fmt(mean([d['game']['win_parts'].get(k) for gi, a, b, d in lost if k in d['game']['win_parts']]))] for k in wk]
        rep.table(['component (winner advantage, gems)', 'whole game', 'break window'], rows, 'components')
        wt = [Counter(), Counter()]
        for gi, a, b, d in lost:
            w = d['game']['winner']
            wt[0].update(d['detail'][1 - w]['win_turns'])
            wt[1].update(d['detail'][w]['win_turns'])
        rep.p('Turn mix in the break windows (loser vs winner):')
        rep.table(['class', 'loser', 'winner'], _share_table(wt, CLASSES), 'window_turns')
        dl = Counter()
        bags = []
        for gi, a, b, d in lost:
            for x in d['game']['deaths_win'][1 - d['game']['winner']]:
                dl[x['who']] += 1
                bags.append(x['bag'])
        rep.p(f'Loser deaths in the break windows: {sum(dl.values())} over {len(lost)} games ({fmt(sum(dl.values()) / len(lost), 2)} a game), '
              f'by type {", ".join(f"{k} {v}" for k, v in dl.most_common())}; bag at death median {fmt(median(bags))}, '
              f'{sum(1 for x in bags if x >= 50)} with 50+.' if bags else 'No loser deaths in the break windows.')
        trig = Counter()
        for gi, a, b, d in lost:
            G = d['game']
            first = [x for x in G['deaths_win'][1 - G['winner']] if x['r'] <= G['break'] + 10]
            if G['cause'] == 'bank':
                trig['ended holding the larger wealth'] += 1
            elif not first:
                trig['no loser death within 10 rounds'] += 1
            else:
                x = max(first, key=lambda x: x['bag'])
                trig[f'{x["who"]} died with {"200+" if x["bag"] >= 200 else "50-199" if x["bag"] >= 50 else "<50"} gems'] += 1
        rep.p('What opened the window: the loser\'s largest-bag death within 10 rounds of the break, if any:')
        rep.table(['trigger', 'games', 'share'], [[k, v, pct(v / len(lost), 0)] for k, v in trig.most_common()], 'triggers', limit=12)
        rows = []
        for gi, a, b, d in sorted(lost, key=lambda e: -e[3]['game']['gap_after'])[:25]:
            G = d['game']
            L = 1 - G['winner']
            dw = '; '.join(f'r{x["r"]} {x["who"]} bag {x["bag"]} by {x["by"]}' for x in G['deaths_win'][L][:4])
            rows.append([f'{gi["dir"]} r{G["break"]}', gi['map'], G['cause'], G['gap_after'],
                         ' '.join(f'{k} {v:+d}' for k, v in G['win_parts'].items()), dw or '-'])
        rep.p('Largest windows (gap = winner minus loser wealth at the window\'s end):')
        rep.table(['game / break', 'map', 'cause', 'gap', 'window components', 'loser deaths in the window'], rows, 'breaks', limit=25)
        top = cc.most_common(1)[0]
        rep.highlight(f'{who}: break window cause {top[0]} in {top[1]}/{len(lost)}; break round median {fmt(median(brks))}; '
                      f'whole-game winner advantage farm {fmt(mean([d["game"]["whole"]["farm"] for gi, a, b, d in lost]))}, '
                      f'fight {fmt(mean([d["game"]["whole"]["fight"] for gi, a, b, d in lost]))} gems')
