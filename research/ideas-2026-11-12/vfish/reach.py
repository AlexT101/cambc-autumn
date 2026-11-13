"""Completed big Prism tributes: could a body of ours have walked there in time? (static walk: walls, holes, altars, enemy spawn)"""
import json, gzip, os, sys, collections, statistics as st
from collections import deque
ext = sys.argv[1]; idx = json.load(open(ext + '/index.json'))['games']
C = collections.Counter()
for g in idx:
    mid = os.path.basename(g['source'])[:-8]; cand = 0 if mid.endswith('-12') else 1
    p = f"{ext}/{g['dir']}"; meta = json.load(open(p + '/meta.json'))
    typ = {c['id']: c['name'] for c in meta['champions']}
    if not any(c['team'] != cand and c['name'] == 'Prism' for c in meta['champions']): continue
    ev = [json.loads(l) for l in gzip.open(p + '/events.jsonl.gz', 'rt')]
    pid = [c['id'] for c in meta['champions'] if c['team'] != cand and c['name'] == 'Prism'][0]
    done = []; s = None
    for e in ev:
        if e['k'] == 'tribute_start' and e['a'] == pid: s = e
        elif e['k'] in ('tribute_end', 'tribute_cancel') and e['a'] == pid and s:
            if s['gems'] >= 100 and e['k'] == 'tribute_end': done.append((s, e))
            s = None
    if not done: continue
    R = json.load(gzip.open(p + '/rounds.json.gz')); m = json.load(open(f"{ext}/maps/{g['mapHash']}.json"))
    W, H = m['width'], m['height']; blocked = set(map(tuple, m['walls'])) | set(map(tuple, m['holes'])) | set(map(tuple, m['altars']))
    es = m['spawn'][1 - cand]
    for x in range(es['minX'], es['maxX'] + 1):
        for y in range(es['minY'], es['maxY'] + 1): blocked.add((x, y))
    ch = R['champions']; n = len(R['round']); P = [c for c in ch if c['id'] == pid][0]; oid = {c['id'] for c in ch if c['team'] == cand}
    for s, e in done:
        ax, ay = s['altar']; dist = {}; q = deque()
        for dx in (-2, -1, 0, 1, 2):
            for dy in (-2, -1, 0, 1, 2):
                t = (ax + dx, ay + dy)
                if 0 <= t[0] < W and 0 <= t[1] < H and t not in blocked: dist[t] = 0; q.append(t)
        while q:
            x, y = q.popleft()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    t = (x + dx, y + dy)
                    if (dx or dy) and 0 <= t[0] < W and 0 <= t[1] < H and t not in blocked and t not in dist: dist[t] = dist[(x, y)] + 1; q.append(t)
        i0 = s['r'] - 1; L = e['r'] - s['r']
        seen = any(any(x in oid for x in P['seenBy'][i]) for i in range(i0, min(e['r'], n)))
        win = R['gems'][1 - cand][i0] + s['gems'] >= 1000
        best = 999; bestl = 999
        for c in ch:
            if c['team'] != cand or not c['alive'][i0] or c['x'][i0] is None: continue
            d = dist.get((c['x'][i0], c['y'][i0]), 999)
            if typ[c['id']] != 'Vesper Vale' or win:
                best = min(best, d)
                if c['cons'][i0][2] > 0: bestl = min(bestl, d)
        k = ('win ' if win else 'hoard ') + ('seen ' if seen else 'unseen ')
        C[k + ('a lock holder within its walk' if bestl <= L - 2 else 'a body (no lock) within its walk' if best <= L - 2 else 'nobody alive' if best == 999 else 'out of walking reach')] += 1
for k, v in sorted(C.items()): print(f'  {v:4d} {k}')
