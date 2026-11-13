"""Per-game features for the mac13-nyx questions (Q1-Q6) from the basedbg mirror.

python3 extract_study.py [--threads N]  -> out/<dir>.json per game
"""
import gzip
import json
import os
import re
import sys
import zipfile
from collections import defaultdict, deque
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

WT = Path('/home/ubuntu/wt/mac13-nyx')
AN = WT / 'replays/.analysis/basedbg'
os.environ['CAMBC_ANALYSIS'] = str(AN)
sys.path.insert(0, str(WT / 'tools/replay'))
from analysis.data import Game, chebyshev  # noqa: E402
from analysis import fights as F  # noqa: E402
from analysis import params as P  # noqa: E402
from narrative.game import View  # noqa: E402

OUT = Path(__file__).resolve().parent / 'out'
DIRS8 = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]


def bfs(mp, sources, blocked):
    W, H = mp.W, mp.H
    dist = {}
    dq = deque()
    for s in sources:
        s = tuple(s)
        dist[s] = 0
        dq.append(s)
    while dq:
        x, y = dq.popleft()
        d = dist[(x, y)] + 1
        for dx, dy in DIRS8:
            n = (x + dx, y + dy)
            if 0 <= n[0] < W and 0 <= n[1] < H and n not in dist and n not in blocked:
                dist[n] = d
                dq.append(n)
    return dist


def parse_D(src):
    """{(round, cid): (char, farm, claim)} from both teams' stdout."""
    out = {}
    maxr = 0
    with zipfile.ZipFile(src) as z:
        for name in ('team-a.stdout', 'team-b.stdout'):
            txt = z.read(name).decode('utf-8', 'replace').replace('\x00', '')
            for m in re.finditer(r'^\s*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$', txt, re.M):
                r, c = int(m.group(1)), int(m.group(2))
                out[(r, c)] = (m.group(3), int(m.group(4)), int(m.group(5)))
                maxr = max(maxr, r)
    return out, maxr


def side_of(mp, team, p):
    """own / mid / enemy half by Chebyshev distance to the two spawn centres."""
    a = mp.spawn_center(team)
    b = mp.spawn_center(1 - team)
    da, db = chebyshev(p, a), chebyshev(p, b)
    band = max(mp.W, mp.H) / 10
    if abs(da - db) <= band:
        return 'mid'
    return 'own' if da < db else 'enemy'


def group_side(mp, team, g):
    s = mp.groups[g]['side']
    if s == -1:
        return 'mid'
    return 'own' if s == team else 'enemy'


def work(d):
    g = Game(d)
    V = View(d, None)
    mp = g.map
    N = len(g.rounds['round'])
    src = WT / [s['source'] for s in g.meta['sources'] if s['source'].endswith('-12.repl26a')][0]
    D, dmax = parse_D(src)
    W = g.winner
    team_of = g.team_of
    ids = [c['id'] for c in g.champs]
    name = g.name_of
    C = {c: g.ch(c) for c in ids}
    partner = {}
    for t in (0, 1):
        ci = [c for c in g.team_ids[t] if name[c] in ('Cassi', 'Issac')]
        if len(ci) == 2:
            partner[ci[0]], partner[ci[1]] = ci[1], ci[0]

    def spos(c, r):  # position at the start of round r (end of r-1), None if dead
        return g.pos(c, g.start_idx(r)) if r > 1 else V.pos(c, 0)

    def dchar(c, r):
        x = D.get((r, c))
        return x[0] if x else '?'

    blocked_base = set(mp.walls) | set(mp.holes) | set(mp.altars)
    spawn_tiles = []
    for t in (0, 1):
        s = mp.spawn[t]
        spawn_tiles.append([(x, y) for x in range(s['minX'], s['maxX'] + 1) for y in range(s['minY'], s['maxY'] + 1)])
    spawn_dist = [bfs(mp, spawn_tiles[t], blocked_base | set(spawn_tiles[1 - t])) for t in (0, 1)]
    gdist = {grp['id']: bfs(mp, grp['tiles'], blocked_base) for grp in mp.groups}
    gtile_set = {grp['id']: {tuple(t) for t in grp['tiles']} for grp in mp.groups}
    has_mono = {grp['id']: 'Monolith' in grp['types'] for grp in mp.groups}

    # group state at the start of round r: forward-filled rows with round <= r-1
    cols = g.rounds['groupCols']
    rows = sorted(g.rounds['groups'], key=lambda x: x[0])
    ng = len(mp.groups)
    gstate = [[None] * ng for _ in range(N + 2)]  # gstate[r][gid] = row at start of round r
    cur = [None] * ng
    k = 0
    for r in range(1, N + 2):
        while k < len(rows) and rows[k][0] <= r - 1:
            cur[rows[k][1]] = rows[k]
            k += 1
        gstate[r] = list(cur)
    # round-1 start: use the round-1 rows
    gstate[1] = [next((x for x in rows if x[1] == gi), None) for gi in range(ng)]

    ev = g.events
    camp_hits = defaultdict(set)      # (r) -> set of (champ, group)
    champ_camp_r = defaultdict(set)   # champ -> rounds it hit a camp
    camp_group = {c['id']: c['group'] for c in mp.camps}
    # runtime camp ids may differ from map camp ids: use event g where available, else the camp table
    for e in ev:
        if e['k'] in ('attack', 'cast') and e.get('cdmg'):
            for cid_, amt in e['cdmg']:
                gid = camp_group.get(cid_)
                camp_hits[e['r']].add((e['a'], gid))
            champ_camp_r[e['a']].add(e['r'])
    cd = g.champ_damage
    champ_dmg_r = defaultdict(set)  # attacker -> rounds dealt champ damage
    took_dmg_r = defaultdict(set)
    for s, r, a, v, amt, ap, vp in cd:
        champ_dmg_r[a].add(r)
        took_dmg_r[v].add(r)
    clear_by = []  # (s, g, team)
    for e in ev:
        if e['k'] == 'group_clear' and e.get('by') in team_of:
            clear_by.append((e['s'], e['r'], e['g'], team_of[e['by']]))

    res = {'dir': d, 'map': g.map_name, 'winner': W, 'rounds': N, 'dmax': dmax, 'W': mp.W, 'H': mp.H,
           'names': {str(c): name[c] for c in ids}}

    # ---------------- Q1: information gaps
    q1 = []
    first_hit = {}
    deaths = [e for e in g.deaths if 'by' in e and 'linked' not in e]
    for e in deaths:
        v, rd, sd = e['v'], e['r'], e['s']
        vt = team_of[v]
        hits = sorted([x for x in cd if x[3] == v or (x[3] == partner.get(v))], key=lambda x: x[0])
        hits = [x for x in hits if x[0] <= sd]
        if not hits:
            continue
        # first hit of the run (gaps <= 2 rounds)
        j = len(hits) - 1
        while j > 0 and hits[j][1] - hits[j - 1][1] <= 2:
            j -= 1
        s0, r0 = hits[j][0], hits[j][1]
        killers = sorted({x[2] for x in hits if x[1] >= rd - 5})
        first_hit[(v, rd)] = (r0, s0)
        vseen_last = set(V.sees_before(v, r0, s0))
        vseen3 = set(vseen_last)
        for rr in range(max(1, r0 - 3), r0):
            vseen3 |= set(V.at(v, 'sees', rr))
        allies = [c for c in g.team_ids[vt] if c != v]
        ally_seen = set()
        for c in allies:
            for rr in range(max(1, r0 - 5), r0):
                ally_seen |= set(V.at(c, 'sees', rr))
            ally_seen |= set(V.sees_before(c, r0, s0))
        vp = V.start_pos(v, r0) or spos(v, r0)
        per = []
        for kk in killers:
            kp = spos(kk, r0)
            dist = chebyshev(vp, kp) if (vp and kp) else None
            cls = 'victim' if kk in vseen_last else ('victim3' if kk in vseen3 else ('ally' if kk in ally_seen else 'none'))
            per.append({'k': kk, 'cls': cls, 'dist': dist, 'kbush': (tuple(kp) in mp.bushes) if kp else None})
        order = {'victim': 0, 'victim3': 1, 'ally': 2, 'none': 3}
        best = min((p['cls'] for p in per), key=order.get) if per else 'none'
        worst = max((p['cls'] for p in per), key=order.get) if per else 'none'
        q1.append({'v': v, 'vt': vt, 'won': vt == W, 'r': rd, 'r0': r0, 'vtype': name[v], 'gems': e['gems'],
                   'killers': per, 'best': best, 'worst': worst, 'vbush': (tuple(vp) in mp.bushes) if vp else None})
    res['q1'] = q1
    # general rate: champion-rounds with an enemy within 10
    gen = {t: [0, 0, 0, 0] for t in (0, 1)}  # pairs, unseen by champ, unseen-by-champ-but-seen-by-ally, unseen by all
    gen_close = {t: [0, 0, 0, 0] for t in (0, 1)}  # same within 8
    for r in range(2, N + 1):
        i = r - 1
        sees_r = {c: set(C[c]['sees'][i]) for c in ids}
        pos_r = {c: spos(c, r) for c in ids}
        for t in (0, 1):
            mine = [c for c in g.team_ids[t] if pos_r[c] and C[c]['alive'][i]]
            team_sees = set()
            for c in mine:
                team_sees |= sees_r[c]
            for c in mine:
                for e2 in g.team_ids[1 - t]:
                    pe = pos_r[e2]
                    if not pe:
                        continue
                    dd = chebyshev(pos_r[c], pe)
                    if dd > 10:
                        continue
                    for bucket, lim in ((gen, 10), (gen_close, 8)):
                        if dd > lim:
                            continue
                        b = bucket[t]
                        b[0] += 1
                        if e2 not in sees_r[c]:
                            b[1] += 1
                            if e2 in team_sees:
                                b[2] += 1
                            else:
                                b[3] += 1
    res['q1gen'] = {str(t): gen[t] for t in (0, 1)}
    res['q1gen8'] = {str(t): gen_close[t] for t in (0, 1)}

    # ---------------- Q2: engagement participation
    inst = []
    for s, r, a, v, amt, ap, vp in cd:
        i = g.start_idx(r)
        inst.append((s, r, a, v, amt, ap or g.pos(a, i), vp or g.pos(v, i)))
    raw = F._cluster(inst, P.DEFAULTS['radius'], P.DEFAULTS['gap'])
    clusters = []
    for its in raw:
        clusters += F._split(its, P.DEFAULTS['max_dur'])
    q2 = []
    for its in clusters:
        its.sort()
        s0, r0, a0, v0 = its[0][:4]
        r1 = its[-1][1]
        tp = its[0][6] or spos(v0, r0)
        if not tp:
            continue
        steps = {x[0] for x in its}
        partset = {x[2] for x in its} | {x[3] for x in its}
        kills = [0, 0]
        killed = []
        for e in g.deaths:
            if 'by' in e and 'linked' not in e and r0 <= e['r'] <= r1 + 1 and e['v'] in partset:
                kills[team_of[e['by']]] += 1
                killed.append(name[e['v']])
        sides = {}
        for t in (0, 1):
            near = [c for c in g.team_ids[t] if spos(c, r0) and chebyshev(spos(c, r0), tp) <= 8]
            dealt = [c for c in near if any(rr in champ_dmg_r[c] for rr in range(r0, r0 + 3))]
            camp = [c for c in near if c not in dealt and any(rr in champ_camp_r[c] for rr in range(r0, r0 + 3))]
            other = [c for c in near if c not in dealt and c not in camp]
            far16 = [c for c in g.team_ids[t] if spos(c, r0) and 8 < chebyshev(spos(c, r0), tp) <= 16]
            mem = [(c, 'dealt' if c in dealt else 'camp' if c in camp else 'other', c == v0 or c == partner.get(v0),
                    chebyshev(spos(c, r0), tp), dchar(c, r0 - 1) + dchar(c, r0)) for c in near]
            sides[t] = {'mem': mem, 'near': len(near), 'dealt': len(dealt), 'camp': len(camp),
                        'other_chars': [dchar(c, r0) + dchar(c, r0 + 1) + dchar(c, r0 + 2) for c in other],
                        'camp_chars': [dchar(c, r0) + dchar(c, r0 + 1) + dchar(c, r0 + 2) for c in camp],
                        'near_types': [name[c] for c in near], 'far16': len(far16)}
        q2.append({'r0': r0, 'r1': r1, 'def': team_of[v0], 'sides': {str(t): sides[t] for t in (0, 1)},
                   'kills': kills, 'killed': killed})
    res['q2'] = q2

    # ---------------- Q3: home cycle
    q3 = []
    rstarts = defaultdict(list)
    for e in ev:
        if e['k'] == 'recall_start':
            rstarts[e['a']].append(e)
    starts_n = defaultdict(int)
    cancels = defaultdict(lambda: defaultdict(int))
    for e in ev:
        if e['k'] == 'recall_start':
            starts_n[team_of[e['a']]] += 1
        if e['k'] == 'recall_cancel':
            cancels[team_of[e['a']]][e.get('cause', '?') + ('_1' if e.get('left') == 4 else '')] += 1
    shops = defaultdict(list)
    tribs = defaultdict(list)
    for e in ev:
        if e['k'] == 'shop':
            shops[e['a']].append(e)
        if e['k'] == 'tribute_start':
            tribs[e['a']].append(e)
    hold_r = defaultdict(set)  # champ -> rounds it stood (end of round) on a claimable group tile
    for c in ids:
        for r in range(1, N + 1):
            p = g.pos(c, r - 1)
            if p and p in mp.group_tiles:
                gi = mp.group_tiles[p]
                row = gstate[min(r + 1, N + 1)][gi]
                if row and row[2] == 2:
                    hold_r[c].add(r)
    death_r = defaultdict(list)
    for e in g.deaths:
        death_r[e['v']].append(e['r'])
    for e in ev:
        if e['k'] != 'recall_end':
            continue
        c, ra = e['a'], e['r']
        t = team_of[c]
        st = [x for x in rstarts[c] if x['s'] < e['s']][-1]
        rs = st['r']
        i = g.start_idx(rs)
        hpf = C[c]['hp'][i] / C[c]['maxHp'][i]
        gold = C[c]['gold'][i]
        pre = ''.join(dchar(c, rr) for rr in range(rs - 3, rs + 1))
        # next work
        nxt, kind = None, None
        dead_first = False
        for rr in range(ra, min(N, ra + 300) + 1):
            if any(ra <= x <= rr for x in death_r[c]):
                dead_first = True
                break
            if rr in champ_camp_r[c]:
                nxt, kind = rr, 'camp'
                break
            if rr in hold_r[c]:
                nxt, kind = rr, 'hold'
                break
        wpos = g.pos(c, nxt - 1) if nxt else None
        walk = spawn_dist[t].get(tuple(wpos)) if wpos else None
        # leave spawn round
        leave = None
        for rr in range(ra, min(N, ra + 300) + 1):
            p = g.pos(c, rr - 1)
            if p is None or not mp.in_spawn(t, p):
                leave = rr
                break
        shop_gold = -sum(x['gold'] for x in shops[c] if ra <= x['r'] <= (leave or ra))
        trib_next = [x['r'] for x in tribs[c] if ra <= x['r'] <= (nxt or ra + 60)]
        q3.append({'c': c, 't': t, 'won': t == W, 'type': name[c], 'rs': rs, 'ra': ra, 'hpf': hpf,
                   'gems': st['gems'], 'gold': gold, 'pre': pre, 'from_dist': spawn_dist[t].get(tuple(st['at'])),
                   'next': nxt, 'kind': kind, 'gap': (nxt - ra) if nxt else None, 'walk': walk, 'dead_first': dead_first,
                   'stay': (leave - ra) if leave else None, 'shop_gold': shop_gold,
                   'trib_after': (trib_next[0] - ra) if trib_next else None, 'farm': D.get((rs, c), (None, -9, -9))[1]})
    # walk-in spawn visits (not recall arrival or respawn)
    arrive_r = {(e['r'], e['a']) for e in ev if e['k'] in ('recall_end', 'respawn', 'teleport_end')}
    walkins = {0: 0, 1: 0}
    walkin_list = []
    for c in ids:
        t = team_of[c]
        prev_in = True
        for r in range(1, N + 1):
            p = g.pos(c, r - 1)
            now_in = p is not None and mp.in_spawn(t, p)
            if now_in and not prev_in and (r, c) not in arrive_r:
                walkins[t] += 1
                i = g.start_idx(r)
                walkin_list.append({'t': t, 'won': t == W, 'r': r, 'type': name[c],
                                    'hpf': C[c]['hp'][i] / C[c]['maxHp'][i], 'gems': C[c]['gems'][i],
                                    'gold': C[c]['gold'][i], 'ch': dchar(c, r)})
            prev_in = now_in if p is not None else True
    res['q3'] = q3
    res['q3walkin'] = walkin_list
    res['q3starts'] = {str(t): starts_n[t] for t in (0, 1)}
    res['q3cancels'] = {str(t): dict(cancels[t]) for t in (0, 1)}

    # ---------------- Q4: decisive divergence
    dl = sorted([e for e in g.deaths if 'linked' not in e], key=lambda e: e['s'])
    cnt = [0, 0]
    div = None
    for e in dl:
        cnt[team_of[e['v']]] += 1
        if abs(cnt[0] - cnt[1]) >= 2:
            div = e
            break

    def death_info(e):
        v = e['v']
        rd = e['r']
        ts = V.turn_step(v, rd)
        rr = rd if ts < e['s'] else rd - 1
        p = tuple(e['at'])
        fh = first_hit.get((v, rd))
        pre = None
        pside = None
        php = None
        if fh:
            r0, s0 = fh
            rr0 = r0 if V.turn_step(v, r0) < s0 else r0 - 1
            pre = ''.join(dchar(v, x) for x in range(rr0 - 2, rr0 + 1))
            pp = V.start_pos(v, r0) or spos(v, r0)
            pside = side_of(mp, team_of[v], pp) if pp else None
            i0 = g.start_idx(r0)
            php = C[v]['hp'][i0] / C[v]['maxHp'][i0]
        return {'pre': pre, 'pside': pside, 'php': php, 'r0': fh[0] if fh else None, 'v': v, 'vt': team_of[v], 'won': team_of[v] == W, 'type': name[v], 'r': rd, 'ch': dchar(v, rr),
                'ch3': ''.join(dchar(v, x) for x in range(rr - 2, rr + 1)), 'side': side_of(mp, team_of[v], p),
                'gems': e['gems'], 'camp': 'camp' in e}
    res['q4'] = {'first': [death_info(e) for e in dl[:2]],
                 'div_r': div['r'] if div else None,
                 'div_team': team_of[div['v']] if div else None,
                 'div_deaths': [death_info(e) for e in dl if div and team_of[e['v']] == team_of[div['v']] and e['s'] <= div['s']],
                 'n_deaths': [sum(1 for e in dl if team_of[e['v']] == t) for t in (0, 1)],
                 'n_camp_deaths': [sum(1 for e in dl if team_of[e['v']] == t and 'camp' in e) for t in (0, 1)]}

    # ---------------- Q5 helpers: decision chars x turn kind
    q5 = defaultdict(lambda: defaultdict(int))  # (team won?, type, char) -> turn kind counts
    for c in ids:
        t = team_of[c]
        for r in range(1, N + 1):
            i = r - 1
            if not C[c]['alive'][i]:
                continue
            ch = dchar(c, r)
            tk = C[c]['turn'][i]
            moved = spos(c, r + 1) != spos(c, r) if r < N else False
            key = f"{int(t == W)}|{name[c]}|{ch}"
            q5[key]['n'] += 1
            q5[key]['idle'] += tk == 2
            q5[key]['chan'] += tk == 3
            q5[key]['oof'] += tk == 6
            q5[key]['camp'] += r in champ_camp_r[c]
            q5[key]['fight'] += r in champ_dmg_r[c] or r in took_dmg_r[c]
            q5[key]['moved'] += bool(moved)
            p = spos(c, r)
            q5[key]['onspawn'] += bool(p and mp.in_spawn(t, p))
    res['q5'] = {k: dict(v) for k, v in q5.items()}

    # ---------------- Q6: stale camp knowledge
    walks = []
    for c in ids:
        t = team_of[c]
        run = []

        def wait_after(c, gi, endr):
            # rounds from reaching (within 4) until the group is alive again
            for rr in range(endr, min(N, endr + 150) + 1):
                row = gstate[rr][gi]
                if row and row[2] == 1:
                    return rr - endr
            return 150

        def flush(run, endr):
            if len(run) < 3:
                return
            gi = run[0][1]
            dead_rounds = [x for x in run if x[2] != 1]
            if len(dead_rounds) < 3:
                walks.append({'c': c, 't': t, 'won': t == W, 'g': gi, 'n': len(run), 'dead': len(dead_rounds), 'stale': False})
                return
            r_first = dead_rounds[0][0]
            st = dead_rounds[0][2]
            row = gstate[r_first][gi]
            # who emptied: latest clear of this group before r_first
            cl = [x for x in clear_by if x[2] == gi and x[1] <= r_first]
            emptier = ('own' if cl[-1][3] == t else 'enemy') if cl else 'unknown'
            holder = row[3] if row else 2
            nxt = endr
            nr = D.get((endr, c))
            if nr is None or not C[c]['alive'][endr - 1]:
                why = 'died/none'
            elif nr[1] != gi:
                why = 'switched'
            elif gdist[gi].get(spos(c, endr), 99) <= 4:
                why = 'reached'
            else:
                why = 'other'
            walks.append({'c': c, 't': t, 'won': t == W, 'g': gi, 'n': len(run), 'dead': len(dead_rounds), 'stale': True,
                          'state': st, 'emptier': emptier,
                          'holder': 'none' if holder == 2 else ('own' if holder == t else 'enemy'),
                          'gside': group_side(mp, t, gi), 'gems': mp.groups[gi]['gems'], 'mono': has_mono[gi],
                          'resp_left': row[5] if row else None, 'dist0': run[0][3], 'why': why, 'r': run[0][0],
                          'type': name[c], 'chars': ''.join(sorted({x[4] for x in run})),
                          'arrive_late': (row[5] is not None and row[5] >= 0 and st == 3 and row[5] <= run[0][3]),
                          'end_alive': bool(gstate[min(endr + 2, N + 1)][gi] and gstate[min(endr + 2, N + 1)][gi][2] == 1),
                          'first_dead_idx': run.index(dead_rounds[0]),
                          'wait_after': wait_after(c, gi, endr) if why == 'reached' else None})

        for r in range(1, N + 1):
            x = D.get((r, c))
            p = spos(c, r)
            ok = (x is not None and x[1] >= 0 and p is not None and C[c]['alive'][r - 1] and C[c]['turn'][r - 1] != 3
                  and x[0] in 'F' and gdist[x[1]].get(p, 99) > 4) if x and x[1] < ng else False
            if ok and run and run[-1][1] == x[1] and run[-1][0] == r - 1:
                row = gstate[r][x[1]]
                run.append((r, x[1], row[2] if row else 1, gdist[x[1]].get(p, 99), x[0]))
                continue
            flush(run, r)
            run = []
            if ok:
                row = gstate[r][x[1]]
                run.append((r, x[1], row[2] if row else 1, gdist[x[1]].get(p, 99), x[0]))
        flush(run, N)
    res['q6walks'] = walks
    # unworked alive groups with an ally within 12 steps that is idle, walking to a dead target, or to a farther one
    agg = defaultdict(float)
    for r in range(2, N + 1):
        hits_r = camp_hits.get(r, set())
        i = r - 1
        for gi in range(ng):
            row = gstate[r][gi]
            if not row or row[2] != 1 or has_mono[gi]:
                continue
            gems_ = mp.groups[gi]['gems']
            if any(gg == gi for a, gg in hits_r):
                continue  # worked by someone this round
            for t in (0, 1):
                best = None
                planned = any(D.get((r, c2), (0, -9))[1] == gi for c2 in g.team_ids[t])
                for c in ([] if planned else g.team_ids[t]):
                    p = spos(c, r)
                    if not p or not C[c]['alive'][i] or C[c]['turn'][i] in (3, 4, 5) or mp.in_spawn(t, p):
                        continue
                    if r in champ_camp_r[c] or r in champ_dmg_r[c] or r in took_dmg_r[c]:
                        continue
                    dd = gdist[gi].get(p, 99)
                    if dd > 12:
                        continue
                    x = D.get((r, c))
                    if not x:
                        continue
                    ch, fg = x[0], x[1]
                    p2 = spos(c, r + 1) if r < N else p
                    moved = p2 is not None and p2 != p
                    if ch in 'PGUTKQWkt':
                        continue  # holding, sieging, guarding, channelling
                    if fg == gi:
                        continue  # it is headed there
                    kind = None
                    if not moved and ch in 'F-B':
                        kind = 'still'
                    elif ch == 'F' and moved and 0 <= fg < ng:
                        frow = gstate[r][fg]
                        if frow and frow[2] == 2:
                            kind = 'to_claimable'
                        elif frow and frow[2] == 3:
                            kind = 'to_resp_early' if frow[5] > gdist[fg].get(p, 99) + 5 else 'to_resp_timed'
                        elif gdist[fg].get(p, 99) > dd + 4:
                            kind = 'to_farther'
                    if kind:
                        pri = {'to_resp_early': 0, 'to_claimable': 1, 'to_resp_timed': 2, 'still': 3, 'to_farther': 4}[kind]
                        if best is None or pri < best[0]:
                            best = (pri, kind, ch, name[c])
                if best:
                    tys = mp.groups[gi]['types']
                    top = 'Golem' if 'Golem' in tys else 'Elk' if 'Elk' in tys else 'Wolf' if 'Wolf' in tys else 'clusters'
                    key = f"{int(t == W)}|{group_side(mp, t, gi)}|{best[1]}|{best[2]}|{best[3]}|{top}"
                    agg[key + '|gems'] += gems_
                    agg[key + '|n'] += 1
    res['q6unworked'] = dict(agg)
    OUT.mkdir(exist_ok=True)
    (OUT / f'{d}.json').write_text(json.dumps(res))
    return d


if __name__ == '__main__':
    th = int(sys.argv[sys.argv.index('--threads') + 1]) if '--threads' in sys.argv else 12
    idx = json.loads((AN / 'index.json').read_text())['games']
    dirs = sorted({r['dir'] for r in idx if r['ok']})
    if '--one' in sys.argv:
        dirs = dirs[:1]
        print(work(dirs[0]))
        sys.exit()
    with ProcessPoolExecutor(th) as ex:
        for d in ex.map(work, dirs):
            pass
    print('done', len(dirs))
