"""One pass over decoded Mite games (ml.py) -> per-game feature dicts, both teams.
Usage: python3 feat.py OUT.jsonl.gz [procs]"""
import sys, json, gzip, collections
from multiprocessing import Pool
import ml

MELEE = {'Ryth', 'Vendetta', 'Marcella', 'Ren', 'Varg', 'Heart of Ruin', 'Issac'}
CHECK = [50, 100, 150, 200, 300, 400, 500, 600, 800, 1000, 1500, 2000]
def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))

def blockers(mp):
    s = set(map(tuple, mp['walls'])) | set(map(tuple, mp['holes'])) | set(map(tuple, mp['altars']))
    return s

def bfs(mp, blk, src, limit=400):
    W, H = mp['width'], mp['height']
    dist = {tuple(src): 0}; q = collections.deque([tuple(src)])
    while q:
        p = q.popleft(); d = dist[p]
        if d >= limit: continue
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                n = (p[0] + dx, p[1] + dy)
                if n in dist or not (0 <= n[0] < W and 0 <= n[1] < H) or n in blk: continue
                dist[n] = d + 1; q.append(n)
    return dist

def one(sd):
    try:
        g = ml.load(sd)
    except Exception as e:
        return None
    if g is None: return None
    m, rd, ev, mp = g['meta'], g['rd'], g['ev'], g['map']
    team = {c['id']: c['team'] for c in m['champions']}
    name = {c['id']: c['name'] for c in m['champions']}
    R = rd['round']; nR = len(R)
    C = {c['id']: c for c in rd['champions']}
    ids = list(C)
    MT = g['mite']
    def at(cid, f, r):  # value at end of round r (1-based), r=0 -> start
        i = max(0, min(r - 1, nR - 1)); return C[cid][f][i]
    blk = blockers(mp)
    sp = [((s['minX'] + s['maxX']) // 2, (s['minY'] + s['maxY']) // 2) for s in mp['spawn']]
    dsp = [bfs(mp, blk - {sp[t]}, sp[t]) for t in (0, 1)]
    def side_of(p, t):  # own / mid / enemy relative to team t, by walk distance to the two spawns
        a, b = dsp[t].get(tuple(p)), dsp[1 - t].get(tuple(p))
        if a is None or b is None:
            a, b = cheb(p, sp[t]), cheb(p, sp[1 - t])
        if a < b * 0.8: return 'own'
        if b < a * 0.8: return 'enemy'
        return 'mid'
    def gside(gr, t):
        tl = gr['tiles'][0]; return side_of(tl, t)
    groups = {q['id']: q for q in mp['groups']}
    out = {'mid': g['mid'], 'src': g['src'], 'ver': g['ver'], 'opp': g['opp'], 'map': g['mapname'], 'hash': m['map']['hash'],
           'mite': MT, 'win': g['win'], 'created': g['created'], 'rounds': nR, 'W': mp['width'], 'H': mp['height'],
           'nalt': len(mp['altars']), 'altars': mp['altars'], 'spawn': mp['spawn'], 'gems_end': [rd['gems'][0][-1], rd['gems'][1][-1]],
           'champs': [[c['id'], c['team'], c['name']] for c in m['champions']], 'mpicks': g['mpicks'],
           'picks': m['draft']['picks'],
           'stats': {c['id']: {k: c['stats'][k] for k in ('collectedGems', 'submittedGems', 'championDamageDone', 'championDamageTaken', 'monsterDamageDone', 'healingDone', 'shieldingDone')} | {'kills': c['kills'], 'deaths': c['deaths'], 'earned': c['earnedGold']} for c in m['champions']},
           'groups': [[q['id'], q['types'], q['gems'], q['gold'], len(q['tiles']), gside(q, 0), dsp[0].get(tuple(q['tiles'][0])), dsp[1].get(tuple(q['tiles'][0]))] for q in mp['groups']]}
    out['ck'] = {r: {'gems': [rd['gems'][0][r - 1], rd['gems'][1][r - 1]],
                     'earned': [sum(at(c, 'earned', r) for c in C if team[c] == t) for t in (0, 1)],
                     'kills': [sum(at(c, 'kills', r) for c in C if team[c] == t) for t in (0, 1)],
                     'carry': [sum(at(c, 'gems', r) for c in C if team[c] == t and at(c, 'alive', r)) for t in (0, 1)],
                     'cc': {c: at(c, 'gems', r) if at(c, 'alive', r) else 0 for c in C},
                     'str': {c: at(c, 'str', r) for c in C}, 'foc': {c: at(c, 'foc', r) for c in C}, 'mhp': {c: at(c, 'maxHp', r) for c in C}}
                 for r in CHECK if r <= nR}
    caps, clears, wakes, tribs, locks, lockdes, lockhits, deaths, tps, recalls, shops, wards, targ, casts = ([] for _ in range(14))
    trib_open = {}; rec_open = {}
    pos = {}; hp = {}
    cur_r = 0
    def reset_round(r):
        for cid in C:
            if r <= 1:
                pos[cid] = (C[cid]['x'][0], C[cid]['y'][0]) if C[cid]['x'][0] is not None else None
                hp[cid] = C[cid]['maxHp'][0]
            else:
                a = at(cid, 'alive', r - 1)
                pos[cid] = (at(cid, 'x', r - 1), at(cid, 'y', r - 1)) if a else None
                hp[cid] = at(cid, 'hp', r - 1) if a else 0
    def near_enemy(cid, p=None):
        p = p or pos.get(cid)
        if not p: return 99
        return min([cheb(p, pos[c2]) for c2 in C if team[c2] != team[cid] and pos.get(c2)] or [99])
    def allies_near(cid, k, p=None):
        p = p or pos.get(cid)
        if not p: return 0
        return sum(1 for c2 in C if team[c2] == team[cid] and c2 != cid and pos.get(c2) and cheb(p, pos[c2]) <= k)
    def hpf(cid, r):
        return round(hp[cid] / max(1, C[cid]['maxHp'][min(max(r - 2, 0), nR - 1)]), 3)
    for e in ev:
        r = e['r']
        if r != cur_r: reset_round(r); cur_r = r
        k = e['k']
        if k == 'capture':
            gr = groups.get(e['g'])
            caps.append([r, e['g'], e['team'], e['shares'], gr['types'] if gr else None, gr['gems'] if gr else 0, gr['gold'] if gr else 0,
                         gside(gr, e['team']) if gr else None, dsp[e['team']].get(tuple(gr['tiles'][0])) if gr else None])
        elif k == 'group_clear': clears.append([r, e['g'], e.get('by')])
        elif k == 'group_wake': wakes.append([r, e['g'], e.get('by')])
        elif k == 'tribute_start':
            a = e['a']
            trib_open[a] = len(tribs)
            banked = rd['gems'][team[a]][max(0, r - 2)]
            ebanked = rd['gems'][1 - team[a]][max(0, r - 2)]
            tribs.append([r, a, team[a], e['gems'], e['dur'], e['altar'], None, None, None, near_enemy(a, tuple(e.get('at') or pos.get(a) or e['altar'])),
                          allies_near(a, 3, tuple(e.get('at') or pos.get(a) or e['altar'])), side_of(e['altar'], team[a]), banked, ebanked, hpf(a, r)])
        elif k in ('tribute_end', 'tribute_cancel'):
            i = trib_open.pop(e['a'], None)
            if i is not None:
                tribs[i][6] = 'end' if k == 'tribute_end' else e.get('cause'); tribs[i][7] = r; tribs[i][8] = e.get('total', e.get('gems'))
        elif k == 'lock_place':
            alt = e['to']; et = [[tribs[i][1], tribs[i][3]] for c2, i in trib_open.items() if team[c2] != e['team'] and tuple(tribs[i][5]) == tuple(alt)]
            near = min([cheb(pos[c2], alt) for c2 in C if team[c2] != e['team'] and pos.get(c2)] or [99])
            locks.append([r, e['a'], e['team'], alt, et, near, side_of(alt, e['team']), at(e['a'], 'gems', r - 1) if r > 1 else 0])
        elif k == 'lock_destroyed': lockdes.append([r, e.get('team'), e.get('at')])
        elif k == 'death':
            deaths.append([r, e['v'], e.get('by'), e.get('gems'), e.get('hp'), e.get('cause'), e.get('assists'), e.get('at'), e.get('gemsTo'), team[e['v']],
                           near_enemy(e['v']), allies_near(e['v'], 5)])
            pos[e['v']] = None
        elif k == 'teleport_start':
            a = e['a']; f = tuple(e['f']); to = tuple(e['to'])
            wd = bfs(mp, blk, f, limit=30).get(to)
            tps.append([r, a, team[a], f, to, at(a, 'gems', r - 1) if r > 1 else 0, cheb(f, to), wd, near_enemy(a, f), hpf(a, r),
                        side_of(f, team[a]), side_of(to, team[a])])
        elif k == 'teleport_end': pos[e['a']] = tuple(e['to'])
        elif k == 'recall_start':
            a = e['a']; rec_open[a] = [r, e.get('gems', 0), hpf(a, r), near_enemy(a), tuple(e['at']) if e.get('at') else pos.get(a), allies_near(a, 5)]
        elif k == 'recall_cancel':
            rec_open.pop(e['a'], None)
        elif k == 'recall_end':
            s = rec_open.pop(e['a'], None)
            recalls.append([r, e['a'], team[e['a']], e.get('gems'), s, side_of(e['f'], team[e['a']]) if e.get('f') else None])
            pos[e['a']] = tuple(e['to'])
        elif k == 'respawn': pos[e['a']] = tuple(e['at']); hp[e['a']] = C[e['a']]['maxHp'][min(r - 1, nR - 1)]
        elif k == 'shop': shops.append([r, e['a'], e.get('items'), e.get('gold'), 1 if not at(e['a'], 'alive', max(r - 1, 1)) else 0])
        elif k == 'ward': wards.append([r, e['a'], e['to']])
        elif k == 'move': pos[e['a']] = tuple(e['to'])
        elif k == 'attack' and e.get('lock'):
            lockhits.append([r, e['a'], team[e['a']], e['to'], at(e['a'], 'gems', r - 1) if r > 1 else 0, near_enemy(e['a'])])
        if k in ('attack', 'cast'):
            a = e['a']
            if k == 'cast' and e.get('moved'): pos[a] = tuple(e['moved'])
            tg = e.get('tgt')
            is_champ = tg is not None and tg in team and team[tg] != team[a] and not e.get('lock') and e.get('camp') is None
            if k == 'cast':
                casts.append([r, a, e.get('ab'), tg if is_champ else None, 'camp' if e.get('camp') is not None else None,
                              [x[0] for x in e.get('dmg', [])], e.get('stun'), e.get('to')])
            if is_champ and pos.get(a):
                rng = (1 if name[a] in MELEE else 3) if k == 'attack' else 4
                cands = []
                for c2 in C:
                    if team[c2] == team[a] or not pos.get(c2): continue
                    dd = cheb(pos[a], pos[c2])
                    if dd <= rng or c2 == tg:
                        mh = C[c2]['maxHp'][min(r - 1, nR - 1)]
                        ch = C[c2]['chan'][max(r - 2, 0)]
                        cands.append([c2, round(hp[c2] / mh, 3), round(hp[c2]), at(c2, 'gems', r - 1) if r > 1 else 0, dd, name[c2], ch,
                                      1 if (a in (C[c2]['seenBy'][max(r - 2, 0)] or [])) else 0])
                targ.append([r, a, k if k == 'attack' else e.get('ab'), tg, cands])
            for x in e.get('dmg', []):
                if x[0] in hp: hp[x[0]] = max(0, hp[x[0]] - x[1])
    # per-round contact rows: champions with an enemy within 6 at the previous round end
    fights = []
    hitr = collections.defaultdict(lambda: collections.defaultdict(float))  # (r, attacker team) -> target -> dmg
    att_round = collections.defaultdict(set); camp_round = set()
    for e in ev:
        if e['k'] in ('attack', 'cast'):
            a = e['a']
            for x in e.get('dmg', []):
                if x[0] in team and team[x[0]] != team[a]:
                    att_round[(e['r'], a)].add(x[0]); hitr[(e['r'], team[a])][x[0]] += x[1]
            if e.get('camp') is not None or e.get('cdmg'): camp_round.add((e['r'], a))
    recst = set((e['r'], e['a']) for e in ev if e['k'] == 'recall_start')
    for r in range(2, nR + 1):
        P = {c: (at(c, 'x', r - 1), at(c, 'y', r - 1)) if at(c, 'alive', r - 1) else None for c in ids}
        Q = {c: (at(c, 'x', r), at(c, 'y', r)) if at(c, 'alive', r) else None for c in ids}
        for c in ids:
            if not P[c]: continue
            en = [x for x in ids if team[x] != team[c] and P[x]]
            if not en: continue
            dn = min(cheb(P[c], P[x]) for x in en)
            if dn > 6: continue
            al = [x for x in ids if team[x] == team[c] and x != c and P[x] and cheb(P[c], P[x]) <= 5]
            ne = [x for x in en if cheb(P[c], P[x]) <= 5]
            near = min(en, key=lambda x: (cheb(P[c], P[x]), x))
            dafter = cheb(Q[c], Q[near]) if Q[c] and Q[near] else None
            dafter_same = cheb(Q[c], P[near]) if Q[c] else None
            mh = at(c, 'maxHp', r - 1)
            seen = 1 if any(x in (C[c]['sees'][r - 2] or []) for x in ne) else 0
            nh = at(near, 'hp', r - 1) / max(1, at(near, 'maxHp', r - 1))
            fights.append([r, c, round(at(c, 'hp', r - 1) / mh, 3), at(c, 'gems', r - 1), dn, len(ne), len(al), dafter, dafter_same,
                           1 if att_round.get((r, c)) else 0, 1 if at(c, 'alive', r) else 0,
                           round(sum(at(x, 'hp', r - 1) for x in ne)), round(sum(at(x, 'hp', r - 1) for x in al) + at(c, 'hp', r - 1)),
                           at(c, 'prio', r - 1), at(c, 'prio', r), seen, round(nh, 3), at(near, 'gems', r - 1), name[near],
                           1 if (r, c) in camp_round else 0, 1 if (r, c) in recst else 0, at(c, 'chan', r - 1), at(c, 'cd0', r - 1), at(c, 'cd1', r - 1),
                           at(near, 'chan', r - 1)])
    # focus: per round and attacking team, damage per target
    focus = [[r, t, {str(k): round(v) for k, v in d.items()}] for (r, t), d in sorted(hitr.items())]
    # engagement convergence: for each team, first contact (enemy within 3) after >= 8 quiet rounds
    conv = []
    last = {0: -99, 1: -99}
    for r in range(2, nR - 12):
        for t in (0, 1):
            P = {c: (at(c, 'x', r), at(c, 'y', r)) if at(c, 'alive', r) else None for c in ids}
            con = [(c, x) for c in ids if team[c] == t and P[c] for x in ids if team[x] != t and P[x] and cheb(P[c], P[x]) <= 3]
            if not con: continue
            if r - last[t] >= 8:
                c0, x0 = con[0]; pt = P[c0]
                rows_ = []
                for c in ids:
                    if team[c] != t or c == c0 or not P[c]: continue
                    ds = []
                    for dr in (0, 3, 6, 10):
                        rr = r + dr
                        q = (at(c, 'x', rr), at(c, 'y', rr)) if at(c, 'alive', rr) else None
                        qx = (at(x0, 'x', rr), at(x0, 'y', rr)) if at(x0, 'alive', rr) else pt
                        ds.append(cheb(q, qx) if q else None)
                    rows_.append([c, name[c], ds, at(c, 'gems', r), 1 if any(camp_round.__contains__((rr, c)) for rr in range(r, r + 4)) else 0])
                en_ = [x for x in ids if team[x] != t and P[x] and cheb(P[x], pt) <= 8]
                fr_ = [c for c in ids if team[c] == t and P[c] and cheb(P[c], pt) <= 8]
                kills = [0, 0]
                for d in deaths:
                    if r <= d[0] <= r + 12 and d[2] is not None and name[d[1]] != 'Issac':
                        kills[0 if d[9] != t else 1] += 1
                conv.append([r, t, c0, x0, rows_, len(fr_), len(en_), kills, side_of(pt, t)])
            last[t] = r
    out.update(caps=caps, clears=clears, wakes=wakes, tribs=tribs, locks=locks, lockdes=lockdes, lockhits=lockhits, deaths=deaths, tps=tps,
               recalls=recalls, shops=shops, wards=len(wards), targ=targ, casts=casts, fights=fights, focus=focus, conv=conv)
    pri = {}
    for c in ids:
        sb = C[c].get('seenBy'); last_ = None; seq = []
        for i, p in enumerate(C[c]['prio']):
            if p != last_: seq.append([i + 1, p, 1 if (sb and sb[i]) else 0]); last_ = p
        pri[c] = seq
    out['pri'] = pri
    return out

if __name__ == '__main__':
    outp = sys.argv[1]; procs = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    ds = ml.all_dirs()
    with Pool(procs) as P, gzip.open(outp, 'wt') as f:
        n = 0
        for o in P.imap_unordered(one, ds, chunksize=2):
            if o is None: continue
            f.write(json.dumps(o) + '\n'); n += 1
    print('wrote', n)
