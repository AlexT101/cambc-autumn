"""Where our Prism spends its rounds and where it dies: python3 zones.py EXTROOT/TAG
Zone: its Chebyshev distance to our spawn over the sum of its distances to both spawns (0 our spawn, 1 theirs).
Per zone: the share of its living rounds off spawn, deaths to champions, the hazard per 1000 rounds, and the same split
by allies within 6 (0, 1, 2+) and by its bag."""
import collections, gzip, json, os, sys
from multiprocessing import Pool


def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def box(sp, p): return max(sp['minX'] - p[0], 0, p[0] - sp['maxX'], sp['minY'] - p[1], p[1] - sp['maxY'])


def one(d):
    try:
        meta = json.load(open(os.path.join(d, 'meta.json'))); R = json.load(gzip.open(os.path.join(d, 'rounds.json.gz')))
        ev = [json.loads(l) for l in gzip.open(os.path.join(d, 'events.jsonl.gz'), 'rt')]
        mp = json.load(open(os.path.join(d, meta['mapFile'])))
    except Exception: return None
    names = [t['name'] for t in meta['teams']]; us = 0 if not names[0].startswith('rt-') else 1
    team = {c['id']: c['team'] for c in meta['champions']}; typ = {c['id']: c['name'] for c in meta['champions']}
    ch = {c['id']: c for c in R['champions']}; rounds = R['round']; idx = {q: i for i, q in enumerate(rounds)}
    pr = [c for c in ch if typ[c] == 'Prism' and team[c] == us]
    if not pr: return None
    p = pr[0]; P = ch[p]; mates = [c for c in ch if team[c] == us and c != p]
    deaths = {x['r'] for x in ev if x['k'] == 'death' and x['v'] == p and x.get('by') is not None}
    rows = []
    for i, r in enumerate(rounds[:-1]):
        if not P['alive'][i] or P['x'][i] is None: continue
        me = (P['x'][i], P['y'][i]); a = box(mp['spawn'][us], me); b = box(mp['spawn'][1 - us], me)
        if a == 0: continue
        z = a / max(1, a + b)
        na = sum(1 for c in mates if ch[c]['alive'][i] and ch[c]['x'][i] is not None and cheb(me, (ch[c]['x'][i], ch[c]['y'][i])) <= 6)
        rows.append((min(4, int(z * 5)), min(na, 2), P['gems'][i], (r + 1) in deaths, r))
    return rows


if __name__ == '__main__':
    root = sys.argv[1]
    dirs = [os.path.join(root, x) for x in os.listdir(root) if os.path.isfile(os.path.join(root, x, 'meta.json'))]
    with Pool(24) as pool: R = [r for g in pool.map(one, dirs, chunksize=8) if g for r in g]
    nd = sum(r[3] for r in R)
    print(f'{len(R)} Prism rounds off spawn, {nd} deaths to champions ({1000 * nd / len(R):.2f} per 1000 rounds)')

    def tab(name, key, order):
        g = collections.defaultdict(list)
        for r in R: g[key(r)].append(r)
        print('\n' + name)
        for k in order:
            s = g.get(k)
            if not s: continue
            dd = sum(r[3] for r in s)
            print(f'  {str(k):26s} {100 * len(s) / len(R):5.1f}% of rounds  {dd:4d} deaths ({100 * dd / nd:4.1f}%)  {1000 * dd / len(s):5.2f} per 1000 rounds')
    zn = ['0-0.2 (home)', '0.2-0.4', '0.4-0.6 (middle)', '0.6-0.8', '0.8-1 (theirs)']
    tab('Zone', lambda r: zn[r[0]], zn)
    tab('Allies within 6', lambda r: r[1], [0, 1, 2])
    tab('Zone x allies within 6', lambda r: (zn[r[0]], r[1]), [(z, a) for z in zn for a in (0, 1, 2)])
    tab('Bag', lambda r: '<20' if r[2] < 20 else '<100' if r[2] < 100 else '<300' if r[2] < 300 else '300+', ['<20', '<100', '<300', '300+'])
    tab('Round', lambda r: '<150' if r[4] < 150 else '<300' if r[4] < 300 else '<600' if r[4] < 600 else '600+', ['<150', '<300', '<600', '600+'])
    tab('Round x allies', lambda r: ('<300' if r[4] < 300 else '<600' if r[4] < 600 else '600+', r[1]), [(a, b) for a in ('<300', '<600', '600+') for b in (0, 1, 2)])
