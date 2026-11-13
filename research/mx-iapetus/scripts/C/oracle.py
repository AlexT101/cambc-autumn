# Oracle opportunity for live territory (ia-territory): from extracted mirror replays, how often a group a team's
# static side weight discounts below 0.5 is in fact never approached by an enemy (within 4 + its radius) before
# that team's nearest champion could walk there, clear it and capture it. Upper bound on what a perfect enemy
# predictor could free.
import json, gzip, sys, collections, numpy as np
from collections import deque
A = '/home/ubuntu/wt/mx-iapetus/replays/.an-mirror/'
LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else 300
idx = json.load(open(A + 'index.json'))['games']
dirs = sorted({r['dir'] for r in idx})[:LIMIT]
HOME_POW = 1.8913636
mapcache = {}
def bfs(mp, box):
    W, H = mp['width'], mp['height']
    block = set(map(tuple, mp['walls'])) | set(map(tuple, mp['holes'])) | set(map(tuple, mp['altars']))
    d = np.full((W, H), 10**6, dtype=np.int32); q = deque()
    for x in range(box['minX'], box['maxX'] + 1):
        for y in range(box['minY'], box['maxY'] + 1):
            d[x, y] = 0; q.append((x, y))
    while q:
        x, y = q.popleft()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < W and 0 <= ny < H and d[nx, ny] > d[x, y] + 1 and (nx, ny) not in block:
                    d[nx, ny] = d[x, y] + 1; q.append((nx, ny))
    return d
def mapinfo(path):
    if path in mapcache: return mapcache[path]
    mp = json.load(open(path))
    dA, dB = bfs(mp, mp['spawn'][0]), bfs(mp, mp['spawn'][1])
    camps = {c['id']: c for c in mp['camps']}
    G = []
    for g in mp['groups']:
        pts = [(camps[c]['x'], camps[c]['y']) for c in g['camps']]
        mx = sum(p[0] for p in pts) / len(pts); my = sum(p[1] for p in pts) / len(pts)
        cx, cy = min(pts, key=lambda p: (p[0] - mx) ** 2 + (p[1] - my) ** 2)
        rad = max(max(abs(p[0] - cx), abs(p[1] - cy)) for p in pts)
        hp = sum(camps[c]['hp'] for c in g['camps'])
        a, b = int(dA[cx, cy]), int(dB[cx, cy])
        mono = 'Monolith' in g['types']
        home = []
        for t in (0, 1):
            us, them = (a, b) if t == 0 else (b, a)
            share = min(1.0, 2 * them / (us + them)) if us + them > 0 and us < 10**6 and them < 10**6 else 1.0
            home.append(share ** HOME_POW)
        G.append(dict(id=g['id'], c=(cx, cy), rad=rad, steps=(a, b), hp=hp, gems=g['gems'], gold=g['gold'], home=home, mono=mono))
    mapcache[path] = G
    return G
def main():
    tot = collections.Counter(); gemsum = collections.Counter()
    for d in dirs:
        m = json.load(open(A + d + '/meta.json'))
        G = mapinfo(A + m['mapFile'].replace('../', ''))
        gid = {g['id']: i for i, g in enumerate(G)}
        R = json.load(gzip.open(A + d + '/rounds.json.gz'))
        N = len(R['round']); r0 = R['round'][0]
        ch = R['champions']
        X = np.array([[(-999 if v is None else v) for v in c['x']] for c in ch]); Y = np.array([[(-999 if v is None else v) for v in c['y']] for c in ch])
        AL = np.array([c['alive'] for c in ch], dtype=bool); TM = np.array([c['team'] for c in ch])
        ST = np.array([c['str'] for c in ch], dtype=float)
        # group state forward-filled: state, hp, respawn
        ng = len(G); state = np.zeros((ng, N), dtype=np.int8); ghp = np.zeros((ng, N)); grsp = np.zeros((ng, N))
        rows = collections.defaultdict(list)
        for row in R['groups']:
            rows[row[1]].append(row)
        for g, rs in rows.items():
            if g not in gid: continue
            i = gid[g]; last = None; k = 0
            rs.sort(key=lambda r: r[0])
            for j in range(N):
                rr = R['round'][j]
                while k < len(rs) and rs[k][0] <= rr: last = rs[k]; k += 1
                if last is not None: state[i, j] = last[2]; ghp[i, j] = last[7]; grsp[i, j] = last[5]
        for t in (0, 1):
            en = np.where(TM != t)[0]; us = np.where(TM == t)[0]
            # next round index at which an enemy is within 4 + rad of the group's centre
            nxt = np.full((ng, N + 1), 10**6, dtype=np.int64)
            for i, g in enumerate(G):
                cx, cy = g['c']
                near = np.zeros(N, dtype=bool)
                for e in en:
                    near |= AL[e] & (np.maximum(np.abs(X[e] - cx), np.abs(Y[e] - cy)) <= 4 + g['rad'])
                for j in range(N - 1, -1, -1):
                    nxt[i, j] = j if near[j] else nxt[i, j + 1]
            for j in range(0, N, 3):
                alive_us = [u for u in us if AL[u, j]]
                if not alive_us: continue
                tot['team_rounds'] += 1
                any_d = fr = hf = False; best = 0; bestm = 0
                for i, g in enumerate(G):
                    if g['mono'] or g['gems'] <= 0 or g['home'][t] >= 0.5: continue
                    s = state[i, j]
                    if s not in (1, 2, 3): continue
                    near = min(max(abs(X[u, j] - g['c'][0]), abs(Y[u, j] - g['c'][1])) for u in alive_us)
                    wait = grsp[i, j] if s == 3 else 0
                    if wait > near + 10: continue
                    any_d = True
                    strength = max(ST[u, j] for u in alive_us)
                    hp = g['hp'] if s == 3 else ghp[i, j]
                    finish = int(max(near, wait) + hp / max(strength, 30) + 6)
                    if nxt[i, j] > j + finish:
                        fr = True; best = max(best, g['gems'])
                tot['disc'] += any_d; tot['free'] += fr; gemsum['free'] += best
        tot['games'] += 1
    print(dict(tot)); t = tot['team_rounds']
    print('disc %.1f%%  oracle-free %.1f%% of team-rounds; mean best free gems %.1f' % (100 * tot['disc'] / t, 100 * tot['free'] / t, gemsum['free'] / max(1, tot['free'])))
if __name__ == '__main__':
    main()
