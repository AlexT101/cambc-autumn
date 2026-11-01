# Per-game features for camp targeting, economy curves, tributes/locks, recalls.
# Run from repo root: python3 feat.py  -> opp/feat/<dir>.json
import sys, os, json, gzip
from collections import deque, defaultdict, Counter
from multiprocessing import Pool
sys.path.insert(0, 'research/v66-replays/scripts/extract')
from common import *
OUT = S + '/opp/feat'
CK = [50, 100, 150, 200, 300, 400, 500, 750, 1000, 1500, 2000]
PRI = ['Monolith', 'Golem', 'Elk', 'Wolf', 'Gem cluster', 'Gold cluster']
CLS = {'Monolith': 'mono', 'Golem': 'golem', 'Elk': 'elk', 'Wolf': 'wolf', 'Gem cluster': 'gem', 'Gold cluster': 'gold'}


def gclass(grp):
    for t in PRI:
        if t in grp['types']:
            return CLS[t]


def bfs(mj, team):
    W, H = mj['width'], mj['height']
    block = {tuple(t) for t in mj['walls']} | {tuple(t) for t in mj['holes']} | {tuple(t) for t in mj['altars']}
    sp = mj['spawn'][team]
    D = {}
    q = deque()
    for x in range(sp['minX'], sp['maxX'] + 1):
        for y in range(sp['minY'], sp['maxY'] + 1):
            D[(x, y)] = 0; q.append((x, y))
    while q:
        p = q.popleft()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                n = (p[0] + dx, p[1] + dy)
                if n in D or not (0 <= n[0] < W and 0 <= n[1] < H) or n in block: continue
                D[n] = D[p] + 1; q.append(n)
    return D


def one(r):
    d = r['dir']
    try:
        m = meta(d); mj = mapj(m); ev = events(d); R = rounds(d)
    except Exception as e:
        return d, str(e)
    us = r['us']; N = len(R['round'])
    team = {c['id']: c['team'] for c in m['champions']}
    ctype = {c['id']: c['name'] for c in m['champions']}
    D = [bfs(mj, 0), bfs(mj, 1)]
    groups = mj['groups']
    camp_group = {c['id']: c['group'] for c in mj['camps']}
    gd = []
    for g in groups:
        ds = [min(D[t].get(tuple(x), 999) for x in g['tiles']) for t in (0, 1)]
        gd.append(ds)
    # distance rank of each group per team
    rank = [{}, {}]
    for t in (0, 1):
        order = sorted(range(len(groups)), key=lambda i: gd[i][t])
        for k, i in enumerate(order): rank[t][i] = k
    def rel(gi, t):
        s = groups[gi]['side']
        return 'mid' if s == -1 else ('own' if s == t else 'enemy')
    ch = R['champions']
    idx = {c['id']: i for i, c in enumerate(ch)}

    # ---- group cycles
    cyc = {}
    cycles = []
    def cur(g):
        if g not in cyc:
            cyc[g] = dict(g=g, dmg=[0.0, 0.0], waker=None, wake_r=None, clearer=None, clear_r=None, holds=set(), resets=0, cresets=0, cap=None, cap_r=None, shares=0, first_dmg_r=[None, None])
        return cyc[g]
    gain = [Counter(), Counter()]   # round -> gems gained
    killgems = [0, 0]
    trib = []; tcancel = []; locks = []; tblocked = []; tele = []; cons = []
    rstart = []; rcancel = []; rend = []
    last_actor_s = {}
    for e in ev:
        k = e['k']
        if k in ('attack', 'cast') and e.get('cdmg'):
            t = team[e['a']]
            for cid, amt in e['cdmg']:
                g = camp_group.get(cid)
                if g is None: continue
                c = cur(g); c['dmg'][t] += amt
                if c['first_dmg_r'][t] is None: c['first_dmg_r'][t] = e['r']
        elif k == 'camp_attack' and e.get('refl'):
            pass
        elif k == 'group_wake':
            c = cur(e['g'])
            if e.get('by') is not None and e['by'] in team:
                c['waker'] = team[e['by']]; c['wake_r'] = e['r']
        elif k == 'group_clear':
            c = cur(e['g']); c['clear_r'] = e['r']
            if e.get('by') is not None and e['by'] in team: c['clearer'] = team[e['by']]
        elif k == 'capture_hold':
            cur(e['g'])['holds'].add(e['team'])
        elif k == 'capture_reset':
            c = cur(e['g']); c['resets'] += 1; c['cresets'] += bool(e.get('contested'))
        elif k == 'capture':
            c = cur(e['g']); c['cap'] = e['team']; c['cap_r'] = e['r']; c['shares'] = len(e['shares'])
            c['sharers'] = [ctype[x[0]] for x in e['shares']]
            for cid, gm, gold in e['shares']:
                gain[team[cid]][e['r']] += gm
            cc = dict(c); cc['holds'] = sorted(c['holds']); cycles.append(cc); del cyc[e['g']]
        elif k == 'group_respawn':
            cyc.pop(e['g'], None)
        elif k == 'death':
            if e.get('by') is not None and e.get('gemsTo'):
                gain[team[e['by']]][e['r']] += e['gemsTo']; killgems[team[e['by']]] += e['gemsTo']
        elif k == 'tribute_start':
            trib.append(dict(r=e['r'], t=team[e['a']], a=ctype[e['a']], aid=e['a'], gems=e['gems'], dur=e['dur'], at=e['at'], altar=e['altar'], s=e['s']))
        elif k == 'tribute_end':
            for x in reversed(trib):
                if x['aid'] == e['a'] and 'end' not in x and 'cancel' not in x:
                    x['end'] = e['r']; x['gems_end'] = e['gems']; break
        elif k == 'tribute_cancel':
            for x in reversed(trib):
                if x['aid'] == e['a'] and 'end' not in x and 'cancel' not in x:
                    x['cancel'] = e['cause']; x['cancel_r'] = e['r']; break
            tcancel.append(dict(r=e['r'], t=team[e['a']], cause=e['cause'], gems=e['gems']))
        elif k == 'lock_place':
            locks.append(dict(r=e['r'], t=team[e['a']], to=e['to'], s=e['s'], a=ctype[e['a']]))
        elif k == 'tribute_blocked':
            tblocked.append(dict(r=e['r'], t=team[e['a']], gems=e['gems']))
        elif k == 'teleport_start':
            tele.append(dict(r=e['r'], t=team[e['a']], f=e.get('f'), to=e['to']))
        elif k == 'shop' and e.get('cons'):
            for nm, dlt in e['cons'].items():
                cons.append(dict(r=e['r'], t=team[e['a']], name=nm, n=dlt))
        elif k == 'recall_start':
            rstart.append(dict(r=e['r'], t=team[e['a']], aid=e['a'], gems=e['gems'], at=e['at'], s=e['s']))
        elif k == 'recall_cancel':
            rcancel.append(dict(r=e['r'], t=team[e['a']], aid=e['a'], cause=e['cause'], left=e['left'], gems=e['gems'], s=e['s']))
        elif k == 'recall_end':
            rend.append(dict(r=e['r'], t=team[e['a']], aid=e['a'], gems=e['gems'], f=e['f']))
        if e.get('a') is not None and e['t'] >= 0 and k not in ('recall_start',):
            last_actor_s[(e['r'], e['a'])] = e['s']
    # was the recall_start the last action of that turn
    for x in rstart:
        x['last'] = last_actor_s.get((x['r'], x['aid']), -1) < x['s']
    # ---- curves
    cum = [[0] * (len(CK)), [0] * (len(CK))]
    for t in (0, 1):
        for i, c in enumerate(CK):
            cum[t][i] = sum(v for rr, v in gain[t].items() if rr <= c) if c <= N else None
    gold = [[None] * len(CK), [None] * len(CK)]
    trib_gems = [[None] * len(CK), [None] * len(CK)]
    for i, c in enumerate(CK):
        if c <= N:
            for t in (0, 1):
                gold[t][i] = sum(x['earned'][c - 1] for x in ch if x['team'] == t)
                trib_gems[t][i] = R['gems'][t][c - 1]
    # ---- per-round spatial: territory and grouping
    terr = [[0, 0, 0, 0], [0, 0, 0, 0]]  # rounds<=200: enemy-half champion-rounds, total; >200 same
    spread = [[[], []], [[], []]]  # per team, [early(<=300), late] list of mean pairwise dist
    near_enemy_spawn = [[0, 0], [0, 0]]  # champion-rounds within 6 walking of enemy spawn, total (exclude own spawn)
    for ri in range(N):
        rr = R['round'][ri]
        for t in (0, 1):
            pts = []
            for c in ch:
                if c['team'] != t or not c['alive'][ri] or c['x'][ri] is None: continue
                p = (c['x'][ri], c['y'][ri])
                if D[t].get(p, 999) == 0: continue  # on own spawn
                pts.append(p)
                de, do = D[1 - t].get(p, 999), D[t].get(p, 999)
                b = 0 if rr <= 200 else 2
                terr[t][b + 1] += 1
                if de < do: terr[t][b] += 1
                near_enemy_spawn[t][1] += 1
                if de <= 6: near_enemy_spawn[t][0] += 1
            if len(pts) >= 2:
                ds = [cheb(pts[i], pts[j]) for i in range(len(pts)) for j in range(i + 1, len(pts))]
                spread[t][0 if rr <= 300 else 1].append(max(ds))
    def med(a):
        a = sorted(a); return a[len(a) // 2] if a else None
    def frac_le(a, v):
        return sum(1 for x in a if x <= v) / len(a) if a else None
    sp = [[dict(med=med(spread[t][k]), le6=frac_le(spread[t][k], 6), n=len(spread[t][k])) for k in (0, 1)] for t in (0, 1)]
    # cycles annotate
    for c in cycles:
        g = c['g']
        c['cls'] = gclass(groups[g]); c['gems'] = groups[g]['gems']
        c['rel'] = [rel(g, 0), rel(g, 1)]
        c['dist'] = gd[g]; c['rank'] = [rank[0][g], rank[1][g]]
    res = dict(dir=d, map=r['map'], opp=r['opp'], us=us, won=r['won'], rounds=N, kind=r.get('kindg'), source=r['source'],
               picks=m['draft']['picks'], ngroups=len(groups),
               cycles=cycles, cum=cum, gold=gold, trib_gems=trib_gems, killgems=killgems,
               terr=terr, spread=sp, nes=near_enemy_spawn,
               trib=trib, tcancel=tcancel, locks=locks, tblocked=tblocked, tele=tele, cons=cons,
               rstart_n=[sum(1 for x in rstart if x['t'] == t) for t in (0, 1)],
               rstart_last=[sum(1 for x in rstart if x['t'] == t and x['last']) for t in (0, 1)],
               rstart_gems0=[sum(1 for x in rstart if x['t'] == t and x['gems'] == 0) for t in (0, 1)],
               rcancel=[Counter((x['cause'], x['left']) for x in rcancel if x['t'] == t) for t in (0, 1)],
               rend_n=[sum(1 for x in rend if x['t'] == t) for t in (0, 1)],
               rend_gems=[[x['gems'] for x in rend if x['t'] == t] for t in (0, 1)],
               champ_turns=[sum(1 for c in ch if c['team'] == t for ri in range(N) if c['turn'][ri] in (1, 2, 3)) for t in (0, 1)],
               stats=[[c['stats'] | dict(name=c['name']) for c in m['champions'] if c['team'] == t] for t in (0, 1)])
    for kk in ('rcancel',):
        res[kk] = [{f'{a}|{b}': v for (a, b), v in x.items()} for x in res[kk]]
    with open(f'{OUT}/{d}.json', 'w') as f:
        json.dump(res, f)
    return d, None


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    gs = games()
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 40) as p:
        for d, err in p.imap_unordered(one, gs):
            if err: print(d, err)
    print('done', len(gs))
