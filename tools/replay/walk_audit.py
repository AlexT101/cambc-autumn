"""Why champions walk: walk legs by origin and destination, detours past nearer available groups, crews on one
group, banking trips, heal-recall cycles, idle stretches, group utilisation and the opening. Meant for unopposed
games (one side an idle bot) but runs on any; it reports the teams not named `idle` (or --team).

    py tools/replay/walk_audit.py replays/batch-X [replays/batch-Y ...] [--team NAME] [--examples N] [--threads N]

Uses turn_budget.py's per-round classes. Distances are walking distances (8-neighbour BFS; walls, holes and altars
block) unless noted. A leg is a maximal run of walking rounds (bag->* / empty->*; idle gaps of up to 2 rounds inside
are kept); its origin is the class of the round before it and its destination the class of the round after.
"""

import argparse
import os
import statistics
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, '/home/ubuntu/cambc-autumn/tools/replay')
sys.path.append(str(Path(__file__).resolve().parent))  # turn_budget; the primary checkout's analysis/ comes first

from analysis.data import ROOT, _norm, chebyshev, load_index  # noqa: E402
from turn_budget import INF, PRIMARY, classify, f1, lite_track, mapinfo, pct, rel_side, table  # noqa: E402

WALK = {'bag->altar', 'bag->camp', 'bag-other', 'empty->camp', 'empty->spawn', 'empty-other'}
WORK = {'camp', 'hold', 'hold+recall'}
GAP = 2           # idle rounds inside a leg
NEAR_PASS = 2     # Chebyshev distance to a group tile that counts as passing it
WORKED = 3        # rounds an ally's hit keeps a group "being worked"
CAPTURE = 6
CLEAR_EST = {'Wolf': 17, 'Elk': 22, 'Golem': 35, 'Monolith': 85, 'GemCl': 3, 'GoldCl': 3}  # solo clear rounds
LEN_BUCKETS = [(1, 4), (5, 9), (10, 19), (20, 39), (40, 10**9)]


def bucket(n, bks=LEN_BUCKETS):
    for lo, hi in bks:
        if lo <= n <= hi:
            return f'{lo}+' if hi >= 10**9 else f'{lo}-{hi}'
    return '?'


def near_index(M):
    """tile -> groups with a camp tile within NEAR_PASS (Chebyshev)."""
    if not hasattr(M, 'near_groups'):
        idx = defaultdict(set)
        for f in M.groups:
            for (x, y) in f.tiles:
                for dx in range(-NEAR_PASS, NEAR_PASS + 1):
                    for dy in range(-NEAR_PASS, NEAR_PASS + 1):
                        idx[(x + dx, y + dy)].add(f.gid)
        M.near_groups = idx
    return M.near_groups


def gdist(M, gid, p):
    return M.groups[gid].fd.get(p, INF) if p is not None else INF


def adist(A, tiles):
    return min((A.fd.get(t, INF) for t in tiles), default=INF)


def work(task):
    from narrative.game import View
    d, teams, mhash = task['dir'], task['teams'], task['mapHash']
    M = mapinfo(mhash)
    near = near_index(M)
    v = View(d, M, teams)
    g = v.g
    N = v.N
    team = v.team
    ginfo = {grp['id']: grp for grp in M.raw['groups']}
    camp_type = {c['id']: c['type'] for c in M.raw['camps']}
    gtype = {}
    for gid, grp in ginfo.items():
        prim = min((camp_type[c] for c in grp['camps']), key=PRIMARY.index)
        gtype[gid] = {'Gem cluster': 'GemCl', 'Gold cluster': 'GoldCl'}.get(prim, prim)
    ours = [t for t in (0, 1) if teams[t] == task['team'] or (task['team'] is None and teams[t] != 'idle')]
    tr = lite_track(v, [])
    dmg_rounds = set()
    for s, r, a, x, *_ in g.champ_damage:
        dmg_rounds |= {(a, r), (x, r)}
    respawn_rounds = {(e['a'], e['r']) for e in g.events if e['k'] == 'respawn'}
    cnt = Counter()
    legs, tribs, recs, idles, lat, ex = [], [], [], [], [], []

    def gstate(gid, r):
        return tr.group_at(gid, r) or {}

    for t in ours:
        ids = [c for c in v.ids if team[c] == t]
        cnt['champs'] += len(ids)
        cnt['champ_rounds'] += N * len(ids)
        C, LAB = {}, {}
        for c in ids:
            C[c], LAB[c], _ = classify(v, M, tr, c, dmg_rounds, respawn_rounds)

        def gid_of(c, r):
            k, key = LAB[c][r]
            if k in ('camp', 'hold'):
                return key
            on = M.tile_group.get(v.pos(c, r))
            return on.gid if on is not None else None

        # who works each group each round (camp hits only)
        hitters = defaultdict(set)
        for c in ids:
            for r in range(1, N + 1):
                if C[c][r] == 'camp':
                    hitters[(LAB[c][r][1], r)].add(c)
        for (gid, r), hs in hitters.items():
            cnt['hit_rounds'] += len(hs)
            cnt['hit_rounds_shared'] += len(hs) if len(hs) > 1 else 0

        def worked_by_other(gid, r, c):
            return any(hitters.get((gid, rr), set()) - {c} for rr in range(r - WORKED, r + 1))

        paid = defaultdict(set)   # champion -> rounds it received a capture share
        for e in g.events:
            if e['k'] == 'capture':
                for cid, gems, gold in e['shares']:
                    paid[cid].add(e['r'])
        spawn = M.spawn_set[t]
        dsp = M.dspawn[t]
        # ---- 1-3. legs
        heading = defaultdict(list)  # gid -> [(r0, r1, c)]
        for c in ids:
            cls = C[c]
            r = 1
            while r <= N:
                if cls[r] not in WALK:
                    r += 1
                    continue
                r0, r1 = r, r
                j = r + 1
                while j <= N:
                    if cls[j] in WALK:
                        r1 = j
                        j += 1
                    elif cls[j] == 'idle-off':
                        k = j
                        while k <= N and cls[k] == 'idle-off' and k - j < GAP:
                            k += 1
                        if k <= N and cls[k] in WALK:
                            j = k
                        else:
                            break
                    else:
                        break
                r = r1 + 1
                prev = cls[r0 - 1] if r0 > 1 else 'start'
                if prev == 'hold':
                    origin = 'payout' if any(rr in paid[c] for rr in range(r0 - 2, r0 + 1)) else 'left hold'
                elif prev in ('recall', 'hold+recall'):
                    origin = 'recall arrival' if v.start_pos(c, r0) in spawn else 'recall cancelled'
                else:
                    origin = {'camp': 'camp', 'tribute': 'tribute', 'dead': 'respawn', 'idle-off': 'idle',
                              'idle-spawn': 'spawn', 'spawn-heal': 'spawn'}.get(prev, prev)
                nxt = cls[r1 + 1] if r1 < N else 'end'
                dgid = None
                if nxt in ('camp', 'hold'):
                    dgid = LAB[c][r1 + 1][1]
                    dest = f'{nxt}:{gtype[dgid]}'
                elif nxt == 'hold+recall':
                    dgid = gid_of(c, r1 + 1)
                    dest = f'hold:{gtype[dgid]}' if dgid is not None else 'recall'
                else:
                    dest = {'tribute': 'altar', 'recall': 'recall', 'idle-spawn': 'spawn', 'spawn-heal': 'spawn',
                            'idle-off': 'idle', 'dead': 'died'}.get(nxt, nxt)
                    if v.pos(c, r1) in spawn and dest == 'idle':
                        dest = 'spawn'
                path = [v.start_pos(c, r0)] + [v.pos(c, rr) for rr in range(r0, r1 + 1)]
                steps = sum(1 for i in range(1, len(path)) if path[i] != path[i - 1])
                leg = {'c': c, 'r0': r0, 'r1': r1, 'rounds': r1 - r0 + 1, 'steps': steps, 'origin': origin, 'dest': dest,
                       'bag': v.at(c, 'gems', r0 - 1) if r0 > 1 else 0}
                if dgid is not None and nxt == 'camp':
                    heading[dgid].append((r0, r1, c))
                    leg['_d'] = (dgid, path)
                legs.append(leg)

        def headed_by_other(gid, r, c):
            return any(c2 != c and a0 <= r <= b1 for a0, b1, c2 in heading.get(gid, ()))

        for leg in legs:
            if '_d' not in leg or team[leg['c']] != t:
                continue
            dgid, path = leg.pop('_d')
            c, r0, r1 = leg['c'], leg['r0'], leg['r1']
            p = path[0]
            st = gstate(dgid, r0 - 1)
            leg['dest_state'] = st.get('state')
            dd = gdist(M, dgid, p)
            # Groups beyond holes are reached only by dash: no walking distance, so left out.
            avail = [gid for gid in ginfo if gstate(gid, r0 - 1).get('state') == 1 and not worked_by_other(gid, r0 - 1, c)
                     and not headed_by_other(gid, r0, c) and gdist(M, gid, p) < INF]
            leg['unreachable'] = dd >= INF
            if avail and dd < INF:
                gn = min(avail, key=lambda x: gdist(M, x, p))
                dn = gdist(M, gn, p)
                leg.update(dest_d=dd, near_d=dn, near_gems=ginfo[gn]['gems'], dest_gems=ginfo[dgid]['gems'],
                           nearest=gn == dgid or dd <= dn, dest_avail=dgid in avail)
            passed = set()
            for rr, q in zip(range(r0, r1 + 1), path[1:]):
                for gid in near.get(q, ()):
                    if gid != dgid and gstate(gid, rr - 1).get('state') == 1 and not worked_by_other(gid, rr - 1, c):
                        passed.add(gid)
            leg['passed'] = len(passed)
            leg['passed_gems'] = sum(ginfo[x]['gems'] for x in passed)
            # another ally working or (in hindsight) headed to the same group at the leg's start
            leg['crew'] = worked_by_other(dgid, r1, c) or any(c2 != c and a0 <= r1 and b1 >= r0 for a0, b1, c2 in heading[dgid])

        # ---- 4. banking
        for e in g.events:
            if e['k'] != 'tribute_start' or team[e['a']] != t:
                continue
            c, rt = e['a'], e['r']
            cls = C[c]
            altar = tuple(e['altar'])
            A_used = next((A for A in M.altars if tuple(A.tiles[0]) == altar), None)
            te = rt
            for rr in range(rt, N + 1):
                if cls[rr] != 'tribute':
                    break
                te = rr
            rl = next((rr for rr in range(rt - 1, 0, -1) if cls[rr] in WORK), None)
            rn = next((rr for rr in range(te + 1, N + 1) if cls[rr] in WORK), None)
            if rl is None or A_used is None:
                continue
            g1 = gid_of(c, rl)
            g2 = gid_of(c, rn) if rn else None
            mid = cls[rl + 1:rt]
            rec = {'c': c, 'r': rt, 'gems': e['gems'], 'to': rt - rl - 1, 'back': (rn - te - 1) if rn else None,
                   'recall_between': any(x in ('recall', 'hold+recall') for x in mid) or
                   (rn is not None and any(x in ('recall', 'hold+recall') for x in cls[te + 1:rn])),
                   'camp_between': 0}
            if g1 is not None and adist(A_used, M.groups[g1].tiles) < INF:
                t1 = M.groups[g1].tiles
                rec['d_used'] = adist(A_used, t1)
                rec['d_near'] = min(adist(A, t1) for A in M.altars)
                if g2 is not None:
                    t2 = M.groups[g2].tiles
                    ow = min(adist(A, t1) + adist(A, t2) for A in M.altars)
                    ra = min(adist(A, M.spawn[t]) + adist(A, t2) for A in M.altars)
                    dr = min(M.groups[g1].fd.get(q, INF) for q in t2)
                    if ow < INF and ra < INF and dr < INF:
                        rec['opt_walk'], rec['recall_alt'], rec['direct'] = ow - 2, 5 + ra - 2, dr
                    rec['same_group'] = g1 == g2
            tribs.append(rec)

        # ---- 5. heal cycles
        for rc in tr.recalls:
            c = rc['c']
            if team[c] != t:
                continue
            i = rc['r0'] - 2
            hp = v.col[c]['hp'][i] / v.col[c]['maxHp'][i] if i >= 0 else 1
            prev = next((rr for rr in range(rc['r0'] - 1, 0, -1) if C[c][rr] in WORK), None)
            rn = next((rr for rr in range(rc['r1'] + 1, N + 1) if C[c][rr] in WORK), None) if rc['done'] else None
            gn = gid_of(c, rn) if rn else None
            gp = gid_of(c, prev) if prev else None
            # What the recall cost against walking straight from the last group worked to the next one.
            extra = None
            if gn is not None and gp is not None:
                d_out = min(dsp.get(t_, INF) for t_ in M.groups[gn].tiles)
                d_dir = min(M.groups[gp].fd.get(t_, INF) for t_ in M.groups[gn].tiles)
                if d_out < INF and d_dir < INF:
                    # Recall rounds spent on a capture tile overlap a hold the champion makes anyway.
                    extra = sum(1 for rr in range(rc['r0'], rc['r1'] + 1) if C[c][rr] == 'recall') + d_out - d_dir
            # A bag recalled home and then walked to an altar, against walking from the last group to the nearest altar.
            bag_alt = None
            if rc['done'] and rc['gems'] > 0 and gp is not None:
                rt_ = next((rr for rr in range(rc['r1'] + 1, N + 1) if C[c][rr] in WORK | {'tribute'}), None)
                if rt_ is not None and C[c][rt_] == 'tribute':
                    direct = min(adist(A, M.groups[gp].tiles) for A in M.altars)
                    if direct < INF:
                        bag_alt = (5 + rt_ - rc['r1'], direct - 1)
            shop = any(e['k'] == 'shop' and e.get('a') == c for rr in range(rc['r1'], rc['r1'] + 3) for e in v.by_round.get(rr, []))
            od = min(dsp.get(t_, INF) for t_ in M.groups[gn].tiles) if gn is not None else INF
            recs.append({'c': c, 'done': rc['done'], 'hp': hp, 'gems': rc['gems'], 'from': min(dsp.get(rc['from'], 99), 99),
                         'out': (rn - rc['r1']) if rn else None, 'out_d': od if od < INF else None, 'extra': extra, 'bag_alt': bag_alt,
                         'same': gn is not None and gn == gp, 'shop': shop, 'hold': C[c][rc['r0']] == 'hold+recall'})

        # ---- 6. idle stretches
        for c in ids:
            cls = C[c]
            r = 1
            while r <= N:
                if cls[r] != 'idle-off':
                    r += 1
                    continue
                j = r
                while j + 1 <= N and cls[j + 1] == 'idle-off':
                    j += 1
                p = v.pos(c, r)
                ctx, wait = 'elsewhere', None
                close = [f for f in M.groups if min(chebyshev(p, q) for q in f.tiles) <= 4]
                if close:
                    f = min(close, key=lambda f: min(chebyshev(p, q) for q in f.tiles))
                    st = gstate(f.gid, r - 1)
                    s_ = st.get('state')
                    if s_ == 3:
                        ctx, wait = 'by respawning group', st.get('respawn')
                    elif s_ == 1:
                        ctx = 'by live group (asleep)' if st.get('awake') != 1 else 'by live group (awake)'
                    elif s_ == 2:
                        ctx = 'by cleared group, held' if st.get('team') in (0, 1) else 'by cleared group, unheld'
                if ctx == 'elsewhere' and M.altar_field.get(p, INF) <= 2:
                    ctx = 'at altar with bag' if v.at(c, 'gems', r) > 0 else 'at altar'
                idles.append({'c': c, 'r': r, 'len': j - r + 1, 'ctx': ctx, 'wait': wait, 'p': p})
                r = j + 1

        # ---- 7. utilisation
        up_since = {gid: 1 for gid in ginfo}
        first_hit = {}
        clears = []
        for e in g.events:
            k = e['k']
            if k == 'group_respawn':
                up_since[e['g']] = e['r']
            elif k in ('attack', 'cast') and e.get('cdmg') and team[e['a']] == t:
                for camp, amt in e['cdmg']:
                    gid = M.camp_group[camp]
                    if up_since.get(gid) is not None:
                        lat.append((gid, up_since[gid], e['r'] - up_since[gid], False))
                        first_hit[gid] = e['r']
                        up_since[gid] = None
            elif k == 'group_clear' and e['g'] in first_hit:
                clears.append((gtype[e['g']], e['r'] - first_hit.pop(e['g'])))
            elif k == 'capture' and e['team'] == t:
                cnt[('cap', rel_side(ginfo[e['g']]['side'], t))] += sum(s_[1] for s_ in e['shares'])
        for gid, r0 in up_since.items():
            if r0 is not None:
                lat.append((gid, r0, N - r0, True))
        lat = [(gid, r0, x, cens, min(dsp.get(q, INF) for q in M.groups[gid].tiles), ginfo[gid]['gems'], gtype[gid])
               for gid, r0, x, cens in lat]
        for gid, grp in ginfo.items():
            cyc = grp['respawn'] + CLEAR_EST[gtype[gid]] + CAPTURE
            cnt[('supply', rel_side(grp['side'], t))] += grp['gems'] * N / cyc
        cnt['clear_rounds'] += sum(x for _, x in clears)
        cnt['clears'] += len(clears)

        # ---- 8. opening
        caps = sorted((e['r'], sum(s_[1] for s_ in e['shares'])) for e in g.events if e['k'] == 'capture' and e['team'] == t)
        trs = sorted((e['r'], e['gems']) for e in g.events if e['k'] == 'tribute_end' and team[e['a']] == t)
        gems_t = g.rounds['gems'][t]
        r1000 = next((i + 1 for i, x in enumerate(gems_t) if x >= 1000), None)
        cnt['open_games'] += 1
        opening = {'first_cap': caps[0][0] if caps else None, 'first_trib': trs[0][0] if trs else None,
                   'cap100': sum(x for r_, x in caps if r_ <= 100), 'cap200': sum(x for r_, x in caps if r_ <= 200),
                   'trib200': gems_t[min(200, N) - 1], 'r1000': r1000, 'N': N, 'champs': len(ids),
                   'walk': sum(1 for c in ids for r in range(1, N + 1) if C[c][r] in WALK),
                   'alive': sum(1 for c in ids for r in range(1, N + 1) if C[c][r] != 'dead')}
    return {'dir': d, 'source': task['source'], 'map': g.map_name, 'N': N, 'cnt': cnt, 'legs': legs, 'tribs': tribs,
            'recs': recs, 'idles': idles, 'lat': lat, 'opening': opening if ours else None,
            'types': {c: g.name_of[c] for c in v.ids}}


def mean(xs):
    xs = [x for x in xs if x is not None]
    return statistics.mean(xs) if xs else None


def med(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('sources', nargs='+')
    ap.add_argument('--team', help='team name to audit (default: every team not named idle)')
    ap.add_argument('--threads', type=int, default=min(90, os.cpu_count() or 4))
    ap.add_argument('--examples', type=int, default=5)
    a = ap.parse_args()
    index = load_index()
    tasks, seen = [], set()
    for src in a.sources:
        p = _norm(src) if Path(src).exists() or Path(src).is_absolute() else _norm(ROOT / src)
        rows = [r for r in index if r['source'] == p or r['source'].startswith(p + '/')]
        if not rows:
            sys.exit(f'no extracted replays under {src} (run node tools/replay/extract.mjs {src})')
        for r in rows:
            if r['ok'] and r['dir'] not in seen:
                seen.add(r['dir'])
                tasks.append({'dir': r['dir'], 'source': r['source'], 'teams': r['teams'], 'mapHash': r['mapHash'], 'team': a.team})
    with ProcessPoolExecutor(a.threads) as ex:
        res = [x for x in ex.map(work, tasks, chunksize=1) if x['opening']]
    G = len(res)
    C = Counter()
    for x in res:
        C.update(x['cnt'])
    legs = [dict(l_, g=x) for x in res for l_ in x['legs']]
    tribs = [dict(t_, g=x) for x in res for t_ in x['tribs']]
    recs = [dict(r_, g=x) for x in res for r_ in x['recs']]
    idles = [dict(i_, g=x) for x in res for i_ in x['idles']]
    out = []
    P = out.append
    cr = C['champ_rounds']
    P(f'# Walk audit: {G} games, {C["champs"] / G:.1f} champions per game, {cr / G:.0f} champion-rounds per game\n')

    # ---- 1. legs
    P('## 1. Walk legs\n')
    wr = sum(l_['rounds'] for l_ in legs)
    P(f'{len(legs) / G:.0f} legs per game, {wr / G:.0f} walking rounds per game ({pct(wr, cr)}% of champion-rounds); '
      f'mean {wr / len(legs):.1f} rounds, {mean(l_["steps"] for l_ in legs):.1f} steps; median {med(l_["rounds"] for l_ in legs)}.\n')
    bk = Counter()
    for l_ in legs:
        bk[bucket(l_['rounds'])] += l_['rounds']
    P('Walking rounds by leg length: ' + ', '.join(f'{b} {pct(bk[b], wr)}%' for b in [bucket(lo) for lo, _ in LEN_BUCKETS]) + '\n')
    pair = defaultdict(list)
    for l_ in legs:
        pair[(l_['origin'], l_['dest'])].append(l_)
    rows = []
    for (o, dst), ls in sorted(pair.items(), key=lambda kv: -sum(l_['rounds'] for l_ in kv[1]))[:22]:
        rr = sum(l_['rounds'] for l_ in ls)
        rows.append([o, dst, f'{len(ls) / G:.1f}', f1(mean(l_['rounds'] for l_ in ls)), f1(mean(l_['steps'] for l_ in ls)),
                     f1(rr / G), pct(rr, wr), pct(sum(1 for l_ in ls if l_['bag'] > 0), len(ls))])
    P(table(['origin', 'destination', 'legs/game', 'rounds/leg', 'steps/leg', 'rounds/game', '% of walking', '% with bag'], rows) + '\n')
    for key in ('origin', 'dest'):
        agg = defaultdict(int)
        for l_ in legs:
            agg[l_[key] if key == 'origin' else l_[key].split(':')[0]] += l_['rounds']
        P(f'By {key}: ' + ', '.join(f'{k} {pct(n, wr)}%' for k, n in sorted(agg.items(), key=lambda kv: -kv[1])) + '\n')

    # ---- 2. detours
    P('## 2. Walks to a camp: detours and pass-bys\n')
    cl = [l_ for l_ in legs if 'dest_d' in l_]
    av = [l_ for l_ in cl if l_['dest_avail']]
    rows = []
    for name, ls in (('all to-camp legs', cl), ('destination available at start', av),
                     ('destination respawning/cleared at start', [l_ for l_ in cl if not l_['dest_avail']])):
        if not ls:
            continue
        far = [l_ for l_ in ls if not l_['nearest']]
        rows.append([name, f'{len(ls) / G:.1f}', pct(len(far), len(ls)), f1(mean(l_['dest_d'] - l_['near_d'] for l_ in far)),
                     f1(sum(l_['dest_d'] - l_['near_d'] for l_ in far) / G),
                     pct(sum(1 for l_ in far if l_['near_gems'] >= l_['dest_gems']), len(far)),
                     f1(mean(l_['dest_gems'] for l_ in far)), f1(mean(l_['near_gems'] for l_ in far)),
                     pct(sum(1 for l_ in ls if l_['passed']), len(ls)), f1(mean(l_['passed_gems'] for l_ in ls if l_['passed'])),
                     pct(sum(1 for l_ in ls if l_.get('crew')), len(ls))])
    P(f'({sum(1 for l_ in legs if l_.get("unreachable")) / G:.1f} to-camp legs per game go to a group with no walking path '
      f'(dash-only), left out.)\n')
    P(table(['legs', 'per game', '% not to nearest available', 'extra steps (those)', 'extra steps/game',
             '% nearer had >= gems', 'dest gems', 'nearer gems', '% passed an available group', 'gems passed',
             '% ally on same group'], rows) + '\n')
    by = defaultdict(list)
    for l_ in av:
        by[l_['dest'].split(':')[1]].append(l_)
    rows = [[ty, len(ls), pct(sum(1 for l_ in ls if not l_['nearest']), len(ls)),
             f1(mean(l_['dest_d'] - l_['near_d'] for l_ in ls if not l_['nearest'])), f1(mean(l_['steps'] for l_ in ls)),
             pct(sum(1 for l_ in ls if l_['passed']), len(ls))] for ty, ls in sorted(by.items(), key=lambda kv: -len(kv[1]))]
    P('Available destinations by type:\n\n' + table(['type', 'legs', '% not nearest', 'extra steps', 'steps/leg', '% passed another'], rows) + '\n')

    # ---- 3. crews
    P('## 3. Crews\n')
    P(f'Camp-hit champion-rounds on a group another ally hits the same round: {pct(C["hit_rounds_shared"], C["hit_rounds"])}%; '
      f'to-camp legs whose group an ally works or heads to meanwhile: {pct(sum(1 for l_ in cl if l_.get("crew")), len(cl))}%; '
      f'mean clear {f1(C["clear_rounds"] / max(1, C["clears"]))} rounds from first hit.\n')

    # ---- 4. banking
    P('## 4. Banking trips (last group worked -> altar -> next group worked)\n')
    tb = [t_ for t_ in tribs if 'd_used' in t_]
    full = [t_ for t_ in tb if t_.get('opt_walk') is not None and t_['back'] is not None and not t_['recall_between']]
    P(f'{len(tribs) / G:.1f} tributes per game, mean bag {f1(mean(t_["gems"] for t_ in tribs))} '
      f'(median {med(t_["gems"] for t_ in tribs)}); {pct(sum(1 for t_ in tribs if t_["gems"] < 20), len(tribs))}% under 20 gems.\n')
    rows = []
    for name, ls in (('all', tb), ('bag < 20', [t_ for t_ in tb if t_['gems'] < 20]), ('bag 20-59', [t_ for t_ in tb if 20 <= t_['gems'] < 60]),
                     ('bag 60+', [t_ for t_ in tb if t_['gems'] >= 60])):
        fl = [t_ for t_ in full if t_ in ls]
        rows.append([name, len(ls), f1(mean(t_['to'] for t_ in ls)), f1(mean(t_['back'] for t_ in ls)),
                     f1(mean(t_['to'] + t_['back'] for t_ in fl)), f1(mean(t_['direct'] for t_ in fl)),
                     f1(mean(t_['to'] + t_['back'] - t_['direct'] for t_ in fl)),
                     f1(sum(t_['to'] + t_['back'] - t_['direct'] for t_ in fl) / G), f1(mean(t_['opt_walk'] for t_ in fl)),
                     f1(mean(t_['recall_alt'] for t_ in fl)), pct(sum(1 for t_ in ls if t_['d_used'] > t_['d_near'] + 2), len(ls)),
                     f1(mean(t_['d_used'] - t_['d_near'] for t_ in ls)),
                     pct(sum(1 for t_ in fl if t_['recall_alt'] < t_['to'] + t_['back']), len(fl)),
                     pct(sum(1 for t_ in fl if t_['recall_alt'] < t_['opt_walk']), len(fl)),
                     f1(sum(t_['to'] + t_['back'] for t_ in ls if t_['back'] is not None) / max(1, sum(t_['gems'] for t_ in ls if t_['back'] is not None)))])
    P(table(['tributes', 'n', 'rounds to altar', 'rounds back', 'trip (no recall)', 'direct walk last->next group',
             'overhead/trip', 'overhead rounds/game', 'best walk via any altar',
             'recall+walk alt', '% used altar 3+ farther than nearest', 'extra altar dist', '% recall alt < actual',
             '% recall alt < best walk', 'trip rounds per gem'], rows) + '\n')
    P(f'Trips with a recall in them: {pct(sum(1 for t_ in tb if t_["recall_between"]), len(tb))}%; next group is the same as the last: '
      f'{pct(sum(1 for t_ in tb if t_.get("same_group")), sum(1 for t_ in tb if "same_group" in t_))}%.\n')

    # ---- 5. heal cycles
    P('## 5. Recalls\n')
    done = [r_ for r_ in recs if r_['done']]
    P(f'{len(recs) / C["champs"]:.1f} real recalls per champion per game ({pct(len(done), len(recs))}% complete); '
      f'{pct(sum(1 for r_ in recs if r_["hold"]), len(recs))}% start on a capture tile (hold+recall).\n')
    rows = []
    for name, ls in (('all completed', done), ('hp < 50%', [r_ for r_ in done if r_['hp'] < 0.5]),
                     ('hp 50-80%', [r_ for r_ in done if 0.5 <= r_['hp'] < 0.8]), ('hp >= 80%', [r_ for r_ in done if r_['hp'] >= 0.8])):
        rows.append([name, f'{len(ls) / C["champs"]:.1f}', f1(mean(r_['from'] for r_ in ls)), pct(sum(1 for r_ in ls if r_['gems'] > 0), len(ls)),
                     pct(sum(1 for r_ in ls if r_['shop']), len(ls)), f1(mean(r_['out'] for r_ in ls)), f1(mean(r_['out_d'] for r_ in ls)),
                     pct(sum(1 for r_ in ls if r_['same']), len(ls)), f1(sum(5 + (r_['out'] or 0) for r_ in ls) / G)])
    ex_ = [r_['extra'] for r_ in done if r_['extra'] is not None]
    ba = [r_['bag_alt'] for r_ in done if r_['bag_alt']]
    P(f'Recall detour: recall rounds off a capture tile + walk spawn->next group - walk last group->next group = mean {f1(mean(ex_))} rounds '
      f'(n={len(ex_)}; {f1(sum(x for x in ex_ if x > 0) / G)} rounds/game where positive; recall faster in {pct(sum(1 for x in ex_ if x < 0), len(ex_))}%). '
      f'Bag recalls then walked to an altar: {len(ba) / G:.1f}/game taking {f1(mean(x[0] for x in ba))} rounds '
      f'(recall + walk) vs {f1(mean(x[1] for x in ba))} to walk from the last group to its nearest altar; '
      f'{f1(sum(max(0, x[0] - x[1]) for x in ba) / G)} rounds/game lost.\n')
    P(table(['recalls', 'per champion-game', 'walk dist from spawn at start', '% with bag', '% shop on arrival',
             'rounds arrival -> next camp', 'walk-out distance', '% back to the same group', 'recall+walk-out rounds/game'], rows) + '\n')

    # ---- 6. idles
    P('## 6. Idle off spawn\n')
    ir = sum(i_['len'] for i_ in idles)
    P(f'{ir / G:.0f} idle-off rounds per game ({pct(ir, cr)}% of champion-rounds).\n')
    ctxs = Counter()
    lens = defaultdict(Counter)
    for i_ in idles:
        ctxs[i_['ctx']] += i_['len']
        lens[i_['ctx']][bucket(i_['len'], [(1, 2), (3, 9), (10, 49), (50, 10**9)])] += i_['len']
    rows = [[k, f1(n / G), pct(n, ir)] + [pct(lens[k][b], n) for b in ('1-2', '3-9', '10-49', '50+')] +
            [f1(mean(i_['wait'] for i_ in idles if i_['ctx'] == k))] for k, n in ctxs.most_common()]
    P(table(['where', 'rounds/game', '% of idle', '% in runs 1-2', '3-9', '10-49', '50+', 'respawn timer left at start'], rows) + '\n')

    # ---- 7. utilisation
    P('## 7. Group utilisation\n')
    lat = [(x, l_) for x in res for l_ in x['lat']]
    q = defaultdict(list)
    for x, (gid, r0, la, cens, dist, gems, ty) in lat:
        q[x['dir']].append(dist)
    rows = []
    QN = ['Q1 (nearest)', 'Q2', 'Q3', 'Q4 (farthest)']
    agg = defaultdict(lambda: [0.0, 0.0, 0, 0, 0.0])
    for x, (gid, r0, la, cens, dist, gems, ty) in lat:
        ds = sorted(q[x['dir']])
        qi = min(3, sum(1 for d_ in (ds[len(ds) // 4], ds[len(ds) // 2], ds[3 * len(ds) // 4]) if dist > d_))
        for key in (QN[qi], ty):
            a_ = agg[key]
            a_[0] += la * gems
            a_[1] += gems
            a_[2] += 1
            a_[3] += cens
            a_[4] += la
    for key in QN + ['Wolf', 'Elk', 'Golem', 'Monolith', 'GemCl', 'GoldCl']:
        a_ = agg.get(key)
        if a_ and a_[2]:
            rows.append([key, a_[2], f1(a_[4] / a_[2]), f1(a_[0] / a_[1]) if a_[1] else '-', pct(a_[3], a_[2])])
    P(table(['groups', 'respawns', 'mean rounds up before first hit', 'gem-weighted', '% never hit before game end'], rows) + '\n')
    sup = sum(C[('supply', s_)] for s_ in ('own', 'mid', 'enemy'))
    capt = sum(C[('cap', s_)] for s_ in ('own', 'mid', 'enemy'))
    P(f'Captured {capt / G:.0f} gems per game of a supply bound of {sup / G:.0f} (every group farmed on cooldown: gems x rounds / '
      f'(respawn + typical clear + 6)) = {pct(capt, sup)}%; by side ' +
      ', '.join(f'{s_} {pct(C[("cap", s_)], C[("supply", s_)])}% of {C[("supply", s_)] / G:.0f}' for s_ in ('own', 'mid', 'enemy')) + '.\n')

    # ---- 8. opening
    P('## 8. Opening\n')
    op = [x['opening'] for x in res]
    P(table(['metric', 'mean', 'median'], [
        ['round of first capture', f1(mean(o['first_cap'] for o in op)), f1(med(o['first_cap'] for o in op))],
        ['round of first tribute', f1(mean(o['first_trib'] for o in op)), f1(med(o['first_trib'] for o in op))],
        ['gems captured by r100', f1(mean(o['cap100'] for o in op)), f1(med(o['cap100'] for o in op))],
        ['gems captured by r200', f1(mean(o['cap200'] for o in op)), f1(med(o['cap200'] for o in op))],
        ['gems tributed by r200', f1(mean(o['trib200'] for o in op)), f1(med(o['trib200'] for o in op))],
        ['round reaching 1000 tributed', f1(mean(o['r1000'] for o in op)), f1(med(o['r1000'] for o in op))],
        ['games not reaching 1000', sum(1 for o in op if o['r1000'] is None), ''],
    ]) + '\n')

    # ---- examples
    P('## Examples\n')

    def show(title, items, fmt):
        P(f'**{title}**\n')
        once = set()
        for it in items:
            if it['g']['dir'] in once:
                continue
            once.add(it['g']['dir'])
            P(f'- `{it["g"]["source"]}` ' + fmt(it))
            if len(once) >= a.examples:
                break
        P('')
    show('Longest detours past a nearer available group', sorted((l_ for l_ in av if not l_['nearest'] and l_['near_gems'] >= l_['dest_gems']),
                                                                  key=lambda l_: l_['near_d'] - l_['dest_d']),
         lambda l_: f'r{l_["r0"]} {l_["g"]["types"][l_["c"]]}#{l_["c"]}: {l_["dest"]} ({l_["dest_gems"]} gems) at {l_["dest_d"]} steps, '
                    f'nearest available {l_["near_d"]} steps ({l_["near_gems"]} gems)')
    show('Longest walk-outs after a recall', sorted((r_ for r_ in done if r_['out']), key=lambda r_: -r_['out']),
         lambda r_: f'{r_["g"]["types"][r_["c"]]}#{r_["c"]}: {r_["out"]} rounds from arrival to the next camp (distance {r_["out_d"]})')
    show('Longest idle stretches', sorted(idles, key=lambda i_: -i_['len']),
         lambda i_: f'r{i_["r"]} {i_["g"]["types"][i_["c"]]}#{i_["c"]} idle {i_["len"]} rounds at {i_["p"]} ({i_["ctx"]})')
    show('Longest banking trips', sorted((t_ for t_ in full), key=lambda t_: -(t_['to'] + t_['back'])),
         lambda t_: f'r{t_["r"]} {t_["g"]["types"][t_["c"]]}#{t_["c"]}: {t_["gems"]} gems, {t_["to"]} rounds to the altar + {t_["back"]} back '
                    f'(best walk {t_["opt_walk"]}, recall alt {t_["recall_alt"]})')
    print('\n'.join(out))


if __name__ == '__main__':
    main()
