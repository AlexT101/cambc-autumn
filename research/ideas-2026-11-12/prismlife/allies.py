"""What allies near a retreating Prism were doing (D lines), fatal retreats against the rest: python3 allies.py EXTROOT/TAG"""
import collections, gzip, json, os, sys, zipfile
from multiprocessing import Pool
ROOT = '/home/ubuntu/cambc-autumn'


def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def one(d):
    try:
        meta = json.load(open(os.path.join(d, 'meta.json')))
        R = json.load(gzip.open(os.path.join(d, 'rounds.json.gz')))
        ev = [json.loads(l) for l in gzip.open(os.path.join(d, 'events.jsonl.gz'), 'rt')]
        names = [t['name'] for t in meta['teams']]; us = 0 if not names[0].startswith('rt-') else 1
        out = zipfile.ZipFile(os.path.join(ROOT, meta['source'])).read(f"team-{'ab'[us]}.stdout").decode('utf-8', 'replace')
    except Exception: return None
    team = {c['id']: c['team'] for c in meta['champions']}; typ = {c['id']: c['name'] for c in meta['champions']}
    ch = {c['id']: c for c in R['champions']}; rounds = R['round']; idx = {q: i for i, q in enumerate(rounds)}
    pr = [c for c in team if typ[c] == 'Prism' and team[c] == us]
    if not pr: return None
    p = pr[0]; P = ch[p]; D = collections.defaultdict(dict)
    for line in out.replace('\x00', '').splitlines():
        v = line.split()
        if len(v) >= 4 and v[0] == 'D':
            try: D[int(v[1])][int(v[2])] = v[3]
            except ValueError: pass
    mates = [c for c in ch if team[c] == us and c != p]; foes = [c for c in ch if team[c] != us]
    deaths = sorted(x['r'] for x in ev if x['k'] == 'death' and x['v'] == p and x.get('by') is not None)
    rs = sorted(q for q in D if D[q].get(p) == 'R')
    out = []; i = 0
    while i < len(rs):
        j = i
        while j + 1 < len(rs) and rs[j + 1] - rs[j] <= 2: j += 1
        r0, r1 = rs[i], rs[j]; i = j + 1
        if r1 - r0 + 1 < 4: continue
        died = any(r0 <= q <= r1 + 3 for q in deaths)
        c = collections.Counter(); nn = 0; ne = 0; rr = 0
        for q in range(r0, r1 + 1):
            st = idx.get(q - 1)
            if st is None or not P['alive'][st] or P['x'][st] is None: continue
            me = (P['x'][st], P['y'][st]); rr += 1
            ne += sum(1 for e in foes if ch[e]['alive'][st] and ch[e]['x'][st] is not None and cheb(me, (ch[e]['x'][st], ch[e]['y'][st])) <= 6)
            for m in mates:
                if ch[m]['alive'][st] and ch[m]['x'][st] is not None and cheb(me, (ch[m]['x'][st], ch[m]['y'][st])) <= 6:
                    c[D[q].get(m, '.')] += 1; nn += 1
        out.append((died, dict(c), nn / max(1, rr), ne / max(1, rr), r1 - r0 + 1))
    return out


if __name__ == '__main__':
    root = sys.argv[1]
    dirs = [os.path.join(root, x) for x in os.listdir(root) if os.path.isfile(os.path.join(root, x, 'meta.json'))]
    with Pool(24) as pool: R = [r for g in pool.map(one, dirs, chunksize=8) if g for r in g]
    for name, sel in (('fatal', True), ('survived', False)):
        S = [r for r in R if r[0] == sel]
        c = collections.Counter()
        for r in S: c.update(r[1])
        tot = sum(c.values())
        print(f'{name}: {len(S)} retreats of 4+ rounds; allies within 6 a round {sum(r[2] for r in S) / len(S):.2f}, enemies within 6 {sum(r[3] for r in S) / len(S):.2f}; none near in {100 * sum(1 for r in S if r[2] < 0.25) / len(S):.0f}%')
        print('   ally turns near it by decision:', ', '.join(f'{a} {100 * b / tot:.0f}%' for a, b in c.most_common(10)))
