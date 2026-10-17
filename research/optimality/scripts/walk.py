import json, os, collections
ROOT = r'C:\Users\alext\Github\cambc-autumn\replays\.analysis'
idxj = json.load(open(os.path.join(ROOT, 'index.json'), encoding='utf-8'))
maps = {}
for g in idxj['games']:
    if g['kind'] == 'ladder' and '20261016' <= g['source'].split('/')[2][:8]: maps[g['map']] = g['mapHash']
def bfs(m, src):
    W, H = m['width'], m['height']
    block = set(map(tuple, m['walls'])) | set(map(tuple, m['holes'])) | set(map(tuple, m['altars']))
    camp = {(c['x'], c['y']) for c in m['camps']}
    INF = 10**9; d = {}
    from collections import deque
    q = deque()
    for s in src: d[s] = 0; q.append(s)
    while q:
        x, y = q.popleft()
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                n = (x+dx, y+dy)
                if n == (x,y) or not (0 <= n[0] < W and 0 <= n[1] < H) or n in block or n in d: continue
                d[n] = d[(x,y)] + 1
                if n not in camp: q.append(n)
    return d
rows = []
for name, h in sorted(maps.items()):
    m = json.load(open(os.path.join(ROOT, 'maps', h + '.json')))
    sp = m['spawn'][0]
    src = [(x, y) for x in range(sp['minX'], sp['maxX']+1) for y in range(sp['minY'], sp['maxY']+1)]
    sp2 = m['spawn'][1]
    src2 = [(x, y) for x in range(sp2['minX'], sp2['maxX']+1) for y in range(sp2['minY'], sp2['maxY']+1)]
    d = bfs(m, src); d2 = bfs(m, src2)
    own = []
    for g in m['groups']:
        dd = min((d.get(tuple(t), 10**9) for t in g['tiles']), default=10**9)
        de = min((d2.get(tuple(t), 10**9) for t in g['tiles']), default=10**9)
        if dd <= de and g['gems'] + g['gold'] > 0: own.append((dd, g['gems'], g['gold'], '+'.join(sorted(set(g['types'])))))
    alt = [min(d.get((ax+dx, ay+dy), 10**9) for dx in (-1,0,1) for dy in (-1,0,1)) for ax, ay in m['altars']]
    gw = sum(o[0]*o[1] for o in own) / max(1, sum(o[1] for o in own))
    spawn_dist = min(d2.get(s, 10**9) for s in src)  # walk between spawns
    print(f"{name:14s} {m['width']}x{m['height']} spawns {spawn_dist:3d} own groups {len(own):2d} gem-weighted walk {gw:5.1f} nearest altar {min(alt):3d}  groups " + ' '.join(f"{o[0]}:{o[1]}g" for o in sorted(own)))
