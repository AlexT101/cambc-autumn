"""Relaxed upper bounds for feas.py: tiles reachable in K king steps (ignoring occupancy), live monsters of any wake
state, with or without the nearest-champion test. HP needed = HP at end of D-1. py relax.py EXT ROWS.json B"""
import json, os, sys, collections
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/mitefit')
from mstats import load
STR = {'Wolf': 20, 'Elk': 60, 'Golem': 120, 'Monolith': 200}
RNG = {'Wolf': 3, 'Elk': 4, 'Golem': 4, 'Monolith': 5}
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))
ext, rf, B = sys.argv[1], sys.argv[2], int(sys.argv[3])
rows = json.load(open(rf)); idx = json.load(open(ext + '/index.json'))['games']
cnt = collections.Counter(); gem = collections.Counter(); N = 0; G = 0
for g in idx:
    mid = os.path.basename(g['source'])[:-8]
    if mid not in rows: continue
    fish = 1 if rows[mid]['side'] == 'a' else 0
    try: meta, R, ev, mp = load(ext, g['dir'])
    except Exception: continue
    P = lambda k: eval(mp[k]) if isinstance(mp[k], str) else mp[k]
    camps, groups = P('camps'), P('groups')
    team = {c['id']: c['team'] for c in meta['champions']}
    ch = R['champions']; n = len(R['round'])
    evr = collections.defaultdict(list)
    for e in ev: evr[e['r']].append(e)
    dead = set(); awake_g = set(); deadat = {}; awakeat = {}
    for r in range(1, n + 1):
        for e in evr[r]:
            if e['k'] == 'camp_death': dead.add(e['camp'])
            elif e['k'] == 'group_respawn':
                for c in groups[e['g']]['camps']: dead.discard(c)
                awake_g.discard(e['g'])
            elif e['k'] in ('group_wake', 'camp_attack'): awake_g.add(e['g'])
            elif e['k'] == 'group_sleep': awake_g.discard(e['g'])
        deadat[r] = set(dead); awakeat[r] = set(awake_g)
    for e in ev:
        if e['k'] != 'death' or 'linked' in e: continue
        v = e['v']; D = e['r']
        if team[v] == fish or team.get(e.get('by')) != fish or 'camp' in e or e['gems'] < B or D < 5: continue
        N += 1; G += e['gems']
        hp = ch[v]['hp'][D - 2]; i1 = D - 2
        others = [(ch[u]['x'][i1], ch[u]['y'][i1]) for u in range(len(ch)) if u != v and ch[u]['alive'][i1] and ch[u]['x'][i1] is not None]
        for K in (0, 1, 2):
            p0 = (ch[v]['x'][D - 2 - K], ch[v]['y'][D - 2 - K])   # tile K turns before the end of D-1
            if None in p0: continue
            for near in (True, False):
                for aw in (True, False):
                    best = 0
                    for dx in range(-K, K + 1):
                        for dy in range(-K, K + 1):
                            q = (p0[0] + dx, p0[1] + dy); s = 0
                            for c in camps:
                                if c['type'] not in STR or c['id'] in deadat[D - 1]: continue
                                cp = (c['x'], c['y']); d = cheb(cp, q)
                                if d > RNG[c['type']]: continue
                                if aw and c['group'] not in awakeat[D - 1]: continue
                                if near and any(cheb(cp, o) <= d for o in others): continue
                                s += STR[c['type']]
                            best = max(best, s)
                    if best >= hp:
                        cnt[(K, near, aw)] += 1; gem[(K, near, aw)] += e['gems']
print(f'deaths to Fish champions, bag >= {B}: {N}, gems {G}')
print('steps  nearest-test  awake-only   feasible   gems')
for K in (0, 1, 2):
    for near in (True, False):
        for aw in (True, False):
            k = (K, near, aw); print(f'{K:5d}  {str(near):12s}  {str(aw):10s}  {cnt[k]:4d} ({cnt[k]/N:.1%})  {gem[k]}')
