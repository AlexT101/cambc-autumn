"""Hoard deaths (our champion, bag >= B, killed by a Fish champion) in live r8 games: could the victim's last turn
before the camp phase of the death round have ended where awake camps finish it first?
For each, from the victim's tile at the end of round D-2, over it and its 8 walkable neighbours, sum the Strength of
live monsters whose range covers the tile and for which the victim would be the strictly nearest champion (others at
their end-of-(D-1) tiles). awake = group awake at end of D-1; wakeable = asleep but the victim could hit it from its
start tile without moving (range 3 basic or 4 cast; then it cannot walk: ranged/exclusive).
HP needed = HP at end of D-1 (which already includes later hits in D-1). Jungle emblem: x0.7.
py feas.py EXT ROWS.json [B]"""
import json, gzip, os, sys, collections
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/mitefit')
from mstats import load
STR = {'Wolf': 20, 'Elk': 60, 'Golem': 120, 'Monolith': 200}
RNG = {'Wolf': 3, 'Elk': 4, 'Golem': 4, 'Monolith': 5}
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))
ext, rf = sys.argv[1:3]; B = int(sys.argv[3]) if len(sys.argv) > 3 else 100
rows = json.load(open(rf)); idx = json.load(open(ext + '/index.json'))['games']
res = []
for g in idx:
    mid = os.path.basename(g['source'])[:-8]
    if mid not in rows: continue
    fish = 1 if rows[mid]['side'] == 'a' else 0
    try: meta, R, ev, mp = load(ext, g['dir'])
    except Exception: continue
    P = lambda k: eval(mp[k]) if isinstance(mp[k], str) else mp[k]
    camps, groups = P('camps'), P('groups')
    W, H = int(mp['width']), int(mp['height'])
    block = set(map(tuple, P('walls'))) | set(map(tuple, P('holes'))) | set(map(tuple, P('altars'))) | {(c['x'], c['y']) for c in camps}
    typ = {c['id']: c['name'] for c in meta['champions']}; team = {c['id']: c['team'] for c in meta['champions']}
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
    win = meta['result'].get('winner') != fish
    for e in ev:
        if e['k'] != 'death' or 'linked' in e: continue
        v = e['v']; D = e['r']
        if team[v] == fish or team.get(e.get('by')) != fish or 'camp' in e or e['gems'] < B or D < 4: continue
        i1, i2 = D - 2, D - 3      # end of D-1, end of D-2
        p0 = (ch[v]['x'][i2], ch[v]['y'][i2])
        if None in p0: continue
        hp = ch[v]['hp'][i1]
        items = ch[v]['items'][i1] if ch[v]['items'][i1] else []
        jung = any('Jungle' in str(it) for it in items)
        others = [(ch[u]['x'][i1], ch[u]['y'][i1]) for u in range(len(ch)) if u != v and ch[u]['alive'][i1] and ch[u]['x'][i1] is not None]
        best = (0, None, None)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                q = (p0[0] + dx, p0[1] + dy)
                if not (0 <= q[0] < W and 0 <= q[1] < H) or (q != p0 and (q in block or q in others)): continue
                for mode in ('awake', 'wake'):
                    if mode == 'wake' and q != p0: continue
                    s = 0
                    for c in camps:
                        if c['type'] not in STR or c['id'] in deadat[D - 1]: continue
                        cp = (c['x'], c['y']); d = cheb(cp, q)
                        if d > RNG[c['type']] or any(cheb(cp, o) <= d for o in others): continue
                        aw = c['group'] in awakeat[D - 1]
                        if mode == 'awake' and not aw: continue
                        if mode == 'wake' and not aw:
                            # needs a hittable asleep member of the same group within 4 of p0
                            if not any(cc['group'] == c['group'] and cc['id'] not in deadat[D - 1] and cheb((cc['x'], cc['y']), p0) <= 4 for cc in camps): continue
                        s += STR[c['type']] * (0.7 if jung else 1)
                    if s > best[0]: best = (s, mode, q)
        res.append(dict(game=g['dir'], D=D, v=typ[v], gems=e['gems'], hp=hp, best=best[0], mode=best[1], jung=jung, win=win,
                        moved=best[2] != p0 if best[2] else None, by=typ[e['by']]))
json.dump(res, open(os.path.expanduser(f'~/tmp-offload/camp-death-gem-denial/feas{B}.json'), 'w'))
n = len(res); f = [x for x in res if x['best'] >= x['hp'] and x['best'] > 0]
print(f'deaths bag>={B}: {n}, gems {sum(x["gems"] for x in res)}; jungle {sum(x["jung"] for x in res)}')
print(f'feasible (camp strength >= HP, victim nearest): {len(f)} ({len(f)/max(n,1):.0%}), gems {sum(x["gems"] for x in f)}; awake {sum(x["mode"]=="awake" for x in f)}, wake {sum(x["mode"]=="wake" for x in f)}')
for x in f: print('  ', x)
near = [x for x in res if x['best'] > 0]
print(f'any reachable camp strength > 0: {len(near)}; strength vs hp:', sorted((round(x['best']), round(x['hp'])) for x in near))
