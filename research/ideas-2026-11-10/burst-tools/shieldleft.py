"""Our camp deaths right after a teammate's move made the victim the camp's nearest target (live archive)."""
import json, gzip, sys, os, collections
A = sys.argv[1]; tsv = sys.argv[2]
us = 'stellar best girl'
team_of, opp_of = {}, {}
for l in open(tsv):
    g, t, a, b, p = l.strip().split('|')
    team_of[g] = 0 if a == us else 1
    opp_of[g] = b if a == us else a
idx = json.load(open(f'{A}/index.json'))['games']
maps = {}
cnt = collections.Counter(); games = collections.Counter(); ex = []
for gm in idx:
    gid = os.path.basename(gm['source']).replace('.repl26a', '')[-36:]
    if gid not in team_of: continue
    opp = 'Fish' if 'Fish' in opp_of[gid] else 'Mite' if 'Mite' in opp_of[gid] else 'other'
    games[opp] += 1
    T = team_of[gid]
    h = gm['mapHash']
    if h not in maps: maps[h] = json.load(open(f'{A}/maps/{h}.json'))
    camps = maps[h]['camps']
    d = f"{A}/{gm['dir']}"
    r = json.load(gzip.open(f'{d}/rounds.json.gz'))
    R = r['round']; row = {x: i for i, x in enumerate(R)}
    ch = r['champions']
    for l in gzip.open(f'{d}/events.jsonl.gz'):
        e = json.loads(l)
        if e['k'] != 'death' or 'camp' not in e or 'linked' in e: continue
        v = e['v']; rr = e['r']
        V = next(c for c in ch if c['id'] == v)
        if V['team'] != T: continue
        cnt[(opp, 'campdeath')] += 1
        if rr <= 50: cnt[(opp, 'campdeath<=50')] += 1
        if rr - 1 not in row or rr - 2 not in row: continue
        i1, i0 = row[rr - 1], row[rr - 2]
        cm = camps[e['camp']]; mp = (cm['x'], cm['y'])
        dist = lambda x, y: max(abs(x - mp[0]), abs(y - mp[1]))
        vx, vy = V['x'][i1], V['y'][i1]
        if vx is None: continue
        dv = dist(vx, vy)
        for c in ch:
            if c['team'] != T or c['id'] == v: continue
            if c['x'][i0] is None or c['x'][i1] is None: continue
            s, f = dist(c['x'][i0], c['y'][i0]), dist(c['x'][i1], c['y'][i1])
            tf = c['turn'][i1] if c.get('turn') else None; tv = V['turn'][i1] if V.get('turn') else None
            first = tf is not None and tv is not None and tf < tv
            was = s < dv or (s == dv and first)
            now = f < dv or (f == dv and first)
            if was and not now and (c['x'][i0], c['y'][i0]) != (c['x'][i1], c['y'][i1]):
                cnt[(opp, 'shieldleft')] += 1
                if rr <= 50: cnt[(opp, 'shieldleft<=50')] += 1
                ex.append((gid, rr, v, c['id'], opp))
                break
for o in ('Mite', 'Fish', 'other'):
    n = games[o]
    if n: print(o, n, 'games', {k[1]: f"{cnt[k]} ({cnt[k]/n:.3f}/game)" for k in cnt if k[0] == o})
print(ex[:12])
