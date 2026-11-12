"""One pass over decoded BattleCats replays -> per-game feature dicts (feats.jsonl.gz), both teams.
Usage: python3 feat.py OUT.jsonl.gz [procs]"""
import sys, json, gzip, collections
from multiprocessing import Pool
import bl

RANGE = {'Ryth': 1, 'Vendetta': 1, 'Marcella': 1, 'Ren': 1, 'Varg': 1, 'Heart of Ruin': 1, 'Issac': 1}
CHECK = [50, 100, 150, 200, 300, 400, 600, 800, 1000, 1500, 2000]

def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))

def one(d):
    g = bl.load(d)
    if g is None: return None
    m, rd, ev, mp = g['meta'], g['rd'], g['ev'], g['map']
    champs = {c['id']: c for c in m['champions']}
    team = {c['id']: c['team'] for c in m['champions']}
    name = {c['id']: c['name'] for c in m['champions']}
    R = rd['round']; nR = len(R)
    C = {c['id']: c for c in rd['champions']}
    def at(cid, f, r):  # value at end of round r (1-based), r=0 -> start
        i = max(0, min(r - 1, nR - 1)); return C[cid][f][i]
    out = {'mid': g['mid'], 'ver': g['ver'], 'kind': g['kind'], 'opp': g['opp'], 'map': g['mapname'], 'hash': m['map']['hash'],
           'bc': g['bc'], 'win': g['win'], 'created': g['created'], 'rounds': nR, 'W': mp['width'], 'H': mp['height'],
           'altars': mp['altars'], 'spawn': mp['spawn'], 'gems_end': [rd['gems'][0][-1], rd['gems'][1][-1]],
           'champs': [[c['id'], c['team'], c['name']] for c in m['champions']],
           'items': {c['id']: c['stats']['itemsBought'] for c in m['champions']},
           'cons': {c['id']: c['stats']['consumablesBought'] for c in m['champions']},
           'stats': {c['id']: {k: c['stats'][k] for k in ('collectedGems', 'submittedGems', 'championDamageDone', 'championDamageTaken', 'monsterDamageDone', 'healingDone', 'shieldingDone')} | {'kills': c['kills'], 'deaths': c['deaths'], 'earned': c['earnedGold']} for c in m['champions']},
           'groups': [[q['id'], q['types'], q['gems'], q['gold'], q['tiles'], q.get('side')] for q in mp['groups']]}
    out['ck'] = {r: {'gems': [rd['gems'][0][r - 1], rd['gems'][1][r - 1]],
                     'earned': [sum(at(c, 'earned', r) for c in C if team[c] == t) for t in (0, 1)],
                     'kills': [sum(at(c, 'kills', r) for c in C if team[c] == t) for t in (0, 1)],
                     'carry': [sum(at(c, 'gems', r) for c in C if team[c] == t and at(c, 'alive', r)) for t in (0, 1)]}
                 for r in CHECK if r <= nR}
    caps, clears, wakes, tribs, locks, lockdes, deaths, tps, recalls, shops, wards, targ, casts = ([] for _ in range(13))
    active_trib = {}  # cid -> [start r, altar, gems]
    trib_open = {}
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
    for e in ev:
        r = e['r']
        if r != cur_r: reset_round(r); cur_r = r
        k = e['k']
        if k == 'capture': caps.append([r, e['g'], e['team'], e['shares']])
        elif k == 'group_clear': clears.append([r, e['g'], e.get('by')])
        elif k == 'group_wake': wakes.append([r, e['g'], e.get('by')])
        elif k == 'tribute_start':
            trib_open[e['a']] = len(tribs); tribs.append([r, e['a'], e['gems'], e['dur'], e['altar'], None, None, None])
        elif k in ('tribute_end', 'tribute_cancel'):
            i = trib_open.pop(e['a'], None)
            if i is not None:
                tribs[i][5] = 'end' if k == 'tribute_end' else e.get('cause'); tribs[i][6] = r; tribs[i][7] = e.get('total', e.get('gems'))
        elif k == 'lock_place':
            alt = e['to']; et = [[tribs[i][1], tribs[i][2]] for c2, i in trib_open.items() if team[c2] != e['team'] and tuple(tribs[i][4]) == tuple(alt)]
            near = min([cheb(pos[c2], alt) for c2 in C if team[c2] != e['team'] and pos.get(c2)] or [99])
            locks.append([r, e['a'], e['team'], alt, et, near])
        elif k == 'lock_destroyed': lockdes.append([r, e['team'], e['at']])
        elif k == 'death':
            deaths.append([r, e['v'], e.get('by'), e.get('gems'), e.get('hp'), e.get('cause'), e.get('assists'), e.get('at'), e.get('gemsTo')])
            pos[e['v']] = None
        elif k == 'teleport_start': tps.append([r, e['a'], e['f'], e['to'], at(e['a'], 'gems', r - 1) if r > 1 else 0])
        elif k == 'teleport_end': pos[e['a']] = tuple(e['to'])
        elif k == 'recall_end':
            recalls.append([r, e['a'], e.get('gems'), e.get('f')]); pos[e['a']] = tuple(e['to'])
        elif k == 'respawn': pos[e['a']] = tuple(e['at']); hp[e['a']] = C[e['a']]['maxHp'][min(r - 1, nR - 1)]
        elif k == 'shop': shops.append([r, e['a'], e.get('items'), e.get('gold')])
        elif k == 'ward': wards.append([r, e['a'], e['to']])
        elif k == 'move': pos[e['a']] = tuple(e['to'])
        elif k in ('attack', 'cast'):
            a = e['a']
            if k == 'cast' and e.get('moved'): pos[a] = tuple(e['moved'])
            tg = e.get('tgt')
            is_champ = tg is not None and tg in team and team[tg] != team[a]
            if k == 'cast':
                casts.append([r, a, e.get('ab'), tg if is_champ else None, 'camp' if e.get('camp') is not None else None,
                              [x[0] for x in e.get('dmg', [])]])
            if is_champ and pos.get(a):
                rng = (RANGE.get(name[a], 3)) if k == 'attack' else 4
                cands = []
                for c2 in C:
                    if team[c2] == team[a] or not pos.get(c2): continue
                    dd = cheb(pos[a], pos[c2])
                    if dd <= rng or c2 == tg:
                        mh = C[c2]['maxHp'][min(r - 1, nR - 1)]
                        cands.append([c2, round(hp[c2] / mh, 3), round(hp[c2]), at(c2, 'gems', r - 1) if r > 1 else 0, dd, name[c2]])
                targ.append([r, a, k if k == 'attack' else e.get('ab'), tg, cands])
            for x in e.get('dmg', []):
                if x[0] in hp: hp[x[0]] = max(0, hp[x[0]] - x[1])
    # per-round contact rows: champions with an enemy within 6 at the previous round end
    fights = []
    att_round = collections.defaultdict(set)
    for t in targ: att_round[(t[0], t[1])].add(t[3])
    ids = list(C)
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
            near = min(en, key=lambda x: cheb(P[c], P[x]))
            dafter = cheb(Q[c], Q[near]) if Q[c] and Q[near] else None
            dafter_same = cheb(Q[c], P[near]) if Q[c] else None
            mh = at(c, 'maxHp', r - 1)
            fights.append([r, c, round(at(c, 'hp', r - 1) / mh, 3), at(c, 'gems', r - 1), dn, len(ne), len(al), dafter, dafter_same,
                           1 if att_round.get((r, c)) else 0, 1 if at(c, 'alive', r) else 0,
                           round(sum(at(x, 'hp', r - 1) for x in ne)), round(sum(at(x, 'hp', r - 1) for x in al) + at(c, 'hp', r - 1))])
    out.update(caps=caps, clears=clears, wakes=wakes, tribs=tribs, locks=locks, lockdes=lockdes, deaths=deaths, tps=tps,
               recalls=recalls, shops=shops, wards=wards, targ=targ, casts=casts, fights=fights)
    # priorities of BattleCats' bodies (for the classifier): value changes only, with whether any enemy saw it that round
    pri = {}
    for c in ids:
        if team[c] != g['bc']: continue
        sb = C[c].get('seenBy'); last = None; seq = []
        for i, p in enumerate(C[c]['prio']):
            if p != last: seq.append([i + 1, p, (sb[i] if sb else None)]); last = p
        pri[c] = seq
    out['pri'] = pri
    return out

if __name__ == '__main__':
    outp = sys.argv[1]; procs = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    ds = bl.dirs()
    with Pool(procs) as P, gzip.open(outp, 'wt') as f:
        n = 0
        for o in P.imap_unordered(one, ds, chunksize=4):
            if o is None: continue
            f.write(json.dumps(o) + '\n'); n += 1
    print('wrote', n)
