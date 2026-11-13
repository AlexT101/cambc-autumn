import json, gzip, sys, os
from collections import Counter, deque
from concurrent.futures import ProcessPoolExecutor
# Share of each bot's alive champion-rounds spent in the enemy half (walk distance nearer the enemy spawn),
# by the number of enemy bodies dead. argv: extract root, the candidate's team-name substring.
ROOT, CAND = sys.argv[1], sys.argv[2]
def bfs(mp, s):
    W, H = mp['width'], mp['height']
    block = set(map(tuple, mp['walls'])) | set(map(tuple, mp['holes'])) | set(map(tuple, mp['altars']))
    D = [[10**9] * H for _ in range(W)]; q = deque()
    for x in range(s['minX'], s['maxX'] + 1):
        for y in range(s['minY'], s['maxY'] + 1): D[x][y] = 0; q.append((x, y))
    while q:
        x, y = q.popleft()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < W and 0 <= ny < H and (nx, ny) not in block and D[nx][ny] > D[x][y] + 1:
                    D[nx][ny] = D[x][y] + 1; q.append((nx, ny))
    return D
def game(d):
    try:
        meta = json.load(open(os.path.join(d, 'meta.json')))
        mp = json.load(open(os.path.join(d, meta['mapFile'])))
        R = json.load(gzip.open(os.path.join(d, 'rounds.json.gz')))
    except Exception as e:
        return None
    names = [t['name'] for t in meta['teams']]
    D = [bfs(mp, mp['spawn'][0]), bfs(mp, mp['spawn'][1])]
    n = len(R['round']); ch = R['champions']
    dead = [[0] * n, [0] * n]
    for c in ch:
        for i, a in enumerate(c['alive']):
            if not a: dead[c['team']][i] += 1
    res = Counter()
    for c in ch:
        t = c['team']; who = 'cand' if CAND in names[t] else 'ref'
        own, en = D[t], D[1 - t]
        for i in range(n):
            if not c['alive'][i]: continue
            x, y = c['x'][i], c['y'][i]
            if x is None or x < 0: continue
            k = min(dead[1 - t][i], 2)
            res[(who, k, 'rounds')] += 1
            if en[x][y] < own[x][y]: res[(who, k, 'enemy')] += 1
    return res
def main():
    dirs = [os.path.join(ROOT, x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, x)) and x != 'maps']
    tot = Counter(); ok = 0
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game, dirs, chunksize=4):
            if r: tot.update(r); ok += 1
    print('games', ok, 'of', len(dirs))
    for who in ('cand', 'ref'):
        for k, lab in ((0, '0 dead'), (1, '1 dead'), (2, '2+ dead')):
            r = tot[(who, k, 'rounds')]
            print(f"{who} enemy {lab}: champion-rounds {r}  in enemy half {100 * tot[(who, k, 'enemy')] / max(1, r):.2f}%")
        r = sum(tot[(who, k, 'rounds')] for k in (1, 2)); e = sum(tot[(who, k, 'enemy')] for k in (1, 2))
        print(f"{who} enemy 1+ dead: champion-rounds {r}  in enemy half {100 * e / max(1, r):.2f}%")
if __name__ == '__main__': main()
