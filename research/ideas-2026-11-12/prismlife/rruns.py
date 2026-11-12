"""The Prism's retreats (runs of R decisions, debug builds' D lines) and how they end: python3 rruns.py EXTROOT/TAG"""
import collections, gzip, json, os, sys, zipfile
from multiprocessing import Pool
ROOT = '/home/ubuntu/cambc-autumn'


def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def one(d):
    try:
        meta = json.load(open(os.path.join(d, 'meta.json')))
        R = json.load(gzip.open(os.path.join(d, 'rounds.json.gz')))
        ev = [json.loads(l) for l in gzip.open(os.path.join(d, 'events.jsonl.gz'), 'rt')]
        mp = json.load(open(os.path.join(d, meta['mapFile'])))
        names = [t['name'] for t in meta['teams']]; us = 0 if not names[0].startswith('rt-') else 1
        out = zipfile.ZipFile(os.path.join(ROOT, meta['source'])).read(f"team-{'ab'[us]}.stdout").decode('utf-8', 'replace')
    except Exception as e:
        return None
    team = {c['id']: c['team'] for c in meta['champions']}; typ = {c['id']: c['name'] for c in meta['champions']}
    ch = {c['id']: c for c in R['champions']}
    pr = [c for c in team if typ[c] == 'Prism' and team[c] == us]
    if not pr: return []
    p = pr[0]; P = ch[p]; D = {}
    for line in out.splitlines():
        v = line.split()
        if len(v) >= 4 and v[0] == 'D' and v[2] == str(p): D[int(v[1])] = v[3]
    rounds = R['round']; idx = {q: i for i, q in enumerate(rounds)}
    sp = mp['spawn'][us]
    foes = [c for c in ch if team[c] != us]; mates = [c for c in ch if team[c] == us and c != p]
    deaths = {x['r'] for x in ev if x['k'] == 'death' and x['v'] == p and x.get('by') is not None}
    cdeaths = {x['r'] for x in ev if x['k'] == 'death' and x['v'] == p and x.get('by') is None}
    taken = collections.Counter(); dealt = collections.Counter()
    for x in ev:
        if x['k'] in ('attack', 'cast'):
            for v, a in x.get('dmg') or []:
                if v == p: taken[x['r']] += a
                if x.get('a') == p: dealt[x['r']] += a
    rs = sorted(q for q in D if D[q] == 'R')
    runs = []; i = 0
    while i < len(rs):
        j = i
        while j + 1 < len(rs) and rs[j + 1] - rs[j] <= 2: j += 1
        r0, r1 = rs[i], rs[j]; i = j + 1
        st = idx.get(r0 - 1)
        if st is None or not P['alive'][st] or P['x'][st] is None: continue
        me = (P['x'][st], P['y'][st])
        fo = [(ch[c]['x'][st], ch[c]['y'][st]) for c in foes if ch[c]['alive'][st] and ch[c]['x'][st] is not None]
        ne = sum(1 for q in fo if cheb(me, q) <= 8)
        na = sum(1 for c in mates if ch[c]['alive'][st] and ch[c]['x'][st] is not None and cheb(me, (ch[c]['x'][st], ch[c]['y'][st])) <= 6)
        ad = sorted(cheb(me, (ch[c]['x'][st], ch[c]['y'][st])) for c in mates if ch[c]['alive'][st] and ch[c]['x'][st] is not None)
        died = any(q in deaths for q in range(r0, r1 + 4)); cdied = any(q in cdeaths for q in range(r0, r1 + 4))
        en = idx.get(min(r1, rounds[-1]))
        home = max(sp['minX'] - me[0], 0, me[0] - sp['maxX'], sp['minY'] - me[1], me[1] - sp['maxY'])
        endhome = None
        if en is not None and P['alive'][en] and P['x'][en] is not None:
            e2 = (P['x'][en], P['y'][en]); endhome = max(sp['minX'] - e2[0], 0, e2[0] - sp['maxX'], sp['minY'] - e2[1], e2[1] - sp['maxY'])
        runs.append(dict(r0=r0, n=r1 - r0 + 1, hp=P['hp'][st] / max(1, P['maxHp'][st]), ne=ne, na=na, died=died, cdied=cdied, home=home, endhome=endhome,
                         taken=sum(taken[q] for q in range(r0, r1 + 4)) / max(1, P['maxHp'][st]), dealt=sum(dealt[q] for q in range(r0, r1 + 1)), gems=P['gems'][st], ally1=ad[0] if ad else 99, ally2=ad[1] if len(ad) > 1 else 99,
                         dir=os.path.basename(d)))
    return runs


if __name__ == '__main__':
    root = sys.argv[1]
    dirs = [os.path.join(root, x) for x in os.listdir(root) if os.path.isfile(os.path.join(root, x, 'meta.json'))]
    with Pool(24) as pool: R = [r for g in pool.map(one, dirs, chunksize=8) if g for r in g]
    E = [r for r in R if r['ne'] > 0]
    nd = sum(r['died'] for r in R)
    print(f'{len(R)} retreats, {len(E)} with an enemy within 8 at the start; ending in death to champions {nd}, to camps {sum(r["cdied"] for r in R)}')

    def tab(name, key, order, S=E):
        g = collections.defaultdict(list)
        for r in S: g[key(r)].append(r)
        print('\n' + name)
        for k in order:
            s = g.get(k)
            if not s: continue
            dd = sum(r['died'] for r in s); hm = sum(1 for r in s if r['endhome'] == 0 and not r['died'])
            print(f'  {str(k):22s} {len(s):5d} ({100 * len(s) / len(S):4.1f}%)  die {100 * dd / len(s):5.1f}% = {dd:4d} ({100 * dd / max(1, nd):4.1f}% of retreat deaths)  reach spawn {100 * hm / len(s):4.1f}%  mean rounds {sum(r["n"] for r in s) / len(s):5.1f}  health taken {sum(r["taken"] for r in s) / len(s):.2f}')
    b = lambda x, cuts: next((f'<{c}' for c in cuts if x < c), f'>={cuts[-1]}')
    tab('Health when the retreat began', lambda r: b(r['hp'], [0.32, 0.5, 0.7, 0.9]), ['<0.32', '<0.5', '<0.7', '<0.9', '>=0.9'])
    tab('Steps from our spawn', lambda r: b(r['home'], [8, 16, 24, 32]), ['<8', '<16', '<24', '<32', '>=32'])
    tab('Allies within 6', lambda r: min(r['na'], 3), [0, 1, 2, 3])
    tab('Enemies within 8', lambda r: min(r['ne'], 4), [1, 2, 3, 4])
    tab('Length in rounds', lambda r: b(r['n'], [2, 4, 8, 16]), ['<2', '<4', '<8', '<16', '>=16'])
    tab('Healthy (70%+) retreats by allies', lambda r: min(r['na'], 3), [0, 1, 2, 3], [r for r in E if r['hp'] >= 0.7])
    tab('Healthy (70%+) retreats by steps from spawn', lambda r: b(r['home'], [8, 16, 24, 32]), ['<8', '<16', '<24', '<32', '>=32'], [r for r in E if r['hp'] >= 0.7])
    tab('Nearest ally (Chebyshev) at the start', lambda r: b(r['ally1'], [4, 7, 11, 17, 25]), ['<4', '<7', '<11', '<17', '<25', '>=25'])
    tab('Second nearest ally at the start', lambda r: b(r['ally2'], [4, 7, 11, 17, 25]), ['<4', '<7', '<11', '<17', '<25', '>=25'])
    L = [r for r in E if r['n'] >= 4]
    tab('Retreats of 4+ rounds: nearest ally', lambda r: b(r['ally1'], [4, 7, 11, 17, 25]), ['<4', '<7', '<11', '<17', '<25', '>=25'], L)
    tab('Retreats of 4+ rounds: nearest ally nearer than home?', lambda r: ('ally nearer' if r['ally1'] < r['home'] else 'home nearer', b(r['ally1'], [7, 17])), [(a, c) for a in ('ally nearer', 'home nearer') for c in ('<7', '<17', '>=17')], L)
    tab('Bag at the start', lambda r: b(r['gems'], [20, 100, 300]), ['<20', '<100', '<300', '>=300'])
