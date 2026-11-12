"""Is the enemy between a retreating Prism and its spawn? python3 homeward.py EXTROOT/TAG   (debug builds: D lines)
A retreat is a run of R decisions (gaps <= 2). At its start: the Prism's walking distance home (a flood over the map's
open tiles, walls, holes, altars and camp tiles blocked) and that of each enemy within 8. Homeward: an enemy within 8
whose walk home is shorter than ours (it stands nearer our spawn along the walk)."""
import collections, gzip, json, os, sys, zipfile
from collections import deque
from multiprocessing import Pool
ROOT = '/home/ubuntu/cambc-autumn'


def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def flood(mp, us):
    W, H = mp['width'], mp['height']
    blocked = {tuple(t) for t in mp['walls']} | {tuple(t) for t in mp['holes']} | {tuple(t) for t in mp['altars']} | {(c['x'], c['y']) for c in mp['camps']}
    sp = mp['spawn'][us]; dist = {}
    q = deque()
    for x in range(sp['minX'], sp['maxX'] + 1):
        for y in range(sp['minY'], sp['maxY'] + 1): dist[(x, y)] = 0; q.append((x, y))
    while q:
        x, y = q.popleft()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                n = (x + dx, y + dy)
                if n in dist or n in blocked or not (0 <= n[0] < W and 0 <= n[1] < H): continue
                dist[n] = dist[(x, y)] + 1; q.append(n)
    return dist


def one(d):
    try:
        meta = json.load(open(os.path.join(d, 'meta.json'))); R = json.load(gzip.open(os.path.join(d, 'rounds.json.gz')))
        ev = [json.loads(l) for l in gzip.open(os.path.join(d, 'events.jsonl.gz'), 'rt')]
        mp = json.load(open(os.path.join(d, meta['mapFile'])))
        names = [t['name'] for t in meta['teams']]; us = 0 if not names[0].startswith('rt-') else 1
        out = zipfile.ZipFile(os.path.join(ROOT, meta['source'])).read(f"team-{'ab'[us]}.stdout").decode('utf-8', 'replace')
    except Exception: return None
    team = {c['id']: c['team'] for c in meta['champions']}; typ = {c['id']: c['name'] for c in meta['champions']}
    ch = {c['id']: c for c in R['champions']}; rounds = R['round']; idx = {q: i for i, q in enumerate(rounds)}
    pr = [c for c in team if typ[c] == 'Prism' and team[c] == us]
    if not pr: return None
    p = pr[0]; P = ch[p]; D = {}
    for line in out.replace('\x00', '').splitlines():
        v = line.split()
        if len(v) >= 4 and v[0] == 'D' and v[2] == str(p): D[int(v[1])] = v[3]
    home = flood(mp, us)
    foes = [c for c in ch if team[c] != us]
    deaths = sorted(x['r'] for x in ev if x['k'] == 'death' and x['v'] == p and x.get('by') is not None)
    rs = sorted(q for q in D if D[q] == 'R'); res = []; i = 0
    while i < len(rs):
        j = i
        while j + 1 < len(rs) and rs[j + 1] - rs[j] <= 2: j += 1
        r0, r1 = rs[i], rs[j]; i = j + 1
        st = idx.get(r0 - 1); en = idx.get(r1)
        if st is None or not P['alive'][st] or P['x'][st] is None: continue
        me = (P['x'][st], P['y'][st]); hp = home.get(me)
        if hp is None: continue
        near = [(ch[e]['x'][st], ch[e]['y'][st]) for e in foes if ch[e]['alive'][st] and ch[e]['x'][st] is not None and cheb(me, (ch[e]['x'][st], ch[e]['y'][st])) <= 8]
        if not near: continue
        hw = sum(1 for q in near if home.get(q, 999) < hp)
        end = (P['x'][en], P['y'][en]) if en is not None and P['alive'][en] and P['x'][en] is not None else None
        prog = hp - home.get(end, hp) if end else None
        res.append(dict(n=r1 - r0 + 1, died=any(r0 <= q <= r1 + 3 for q in deaths), home=hp, hw=hw, ne=len(near), prog=prog))
    return res


if __name__ == '__main__':
    root = sys.argv[1]
    dirs = [os.path.join(root, x) for x in os.listdir(root) if os.path.isfile(os.path.join(root, x, 'meta.json'))]
    with Pool(24) as pool: R = [r for g in pool.map(one, dirs, chunksize=4) if g for r in g]
    nd = sum(r['died'] for r in R)
    print(f'{len(R)} retreats with an enemy within 8, {nd} end in death')

    def tab(name, key, order, S=R):
        g = collections.defaultdict(list)
        for r in S: g[key(r)].append(r)
        print('\n' + name)
        for k in order:
            s = g.get(k)
            if not s: continue
            dd = sum(r['died'] for r in s); pr = [r['prog'] / r['n'] for r in s if r['prog'] is not None]
            print(f'  {str(k):30s} {len(s):6d} ({100 * len(s) / len(S):5.1f}%)  die {100 * dd / len(s):5.1f}% = {dd:4d} ({100 * dd / max(1, nd):4.1f}%)  mean rounds {sum(r["n"] for r in s) / len(s):4.1f}  steps nearer home a round {sum(pr) / max(1, len(pr)):.2f}')
    tab('Enemies within 8 standing nearer our spawn (by the walk) than the Prism', lambda r: 'none' if r['hw'] == 0 else 'some' if r['hw'] < r['ne'] else 'all', ['none', 'some', 'all'])
    tab('The same, retreats of 4+ rounds', lambda r: ('none' if r['hw'] == 0 else 'some' if r['hw'] < r['ne'] else 'all') if r['n'] >= 4 else None, ['none', 'some', 'all'])
    tab('Walk home at the start', lambda r: '<10' if r['home'] < 10 else '<20' if r['home'] < 20 else '<40' if r['home'] < 40 else '<60' if r['home'] < 60 else '60+', ['<10', '<20', '<40', '<60', '60+'])
    tab('Walk home x enemy homeward', lambda r: ('<20' if r['home'] < 20 else '<40' if r['home'] < 40 else '40+', 'homeward' if r['hw'] else 'behind'), [(a, b) for a in ('<20', '<40', '40+') for b in ('behind', 'homeward')])
    L = [r for r in R if r['n'] >= 4 and r['prog'] is not None]
    tab('Retreats of 4+ rounds by steps nearer home a round', lambda r: '<=0' if r['prog'] <= 0 else '<0.5' if r['prog'] / r['n'] < 0.5 else '<0.8' if r['prog'] / r['n'] < 0.8 else '0.8+', ['<=0', '<0.5', '<0.8', '0.8+'], L)
