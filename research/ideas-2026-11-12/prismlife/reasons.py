"""Why the Prism's retreats began, and how each kind ends (variants/pl-trace with the reason field).

    python3 reasons.py EXTROOT/TAG

PLE lines end with want_home's last reason (0 none, 1 below the recall line, 2 a pack's zone, 3 camps, 4 fled camps, 5
Willow, 6 the stand is lost) and the health share in percent. A retreat is a run of R turn ends (gaps of at most 2
rounds); its reason is the first turn's. Printed: retreats and deaths by reason and health, and the reasons on the
turns before each death.
"""
import collections, gzip, json, os, sys, zipfile
from multiprocessing import Pool
ROOT = '/home/ubuntu/cambc-autumn'
NAMES = {0: 'none', 1: 'recall line', 2: 'pack zone', 3: 'camps', 4: 'fled camps', 5: 'willow', 6: 'stand lost'}


def one(d):
    try:
        meta = json.load(open(os.path.join(d, 'meta.json')))
        ev = [json.loads(l) for l in gzip.open(os.path.join(d, 'events.jsonl.gz'), 'rt')]
        names = [t['name'] for t in meta['teams']]; us = 0 if not names[0].startswith('rt-') else 1
        out = zipfile.ZipFile(os.path.join(ROOT, meta['source'])).read(f"team-{'ab'[us]}.stdout").decode('utf-8', 'replace')
    except Exception as e:
        return None
    team = {c['id']: c['team'] for c in meta['champions']}; typ = {c['id']: c['name'] for c in meta['champions']}
    pr = [c for c in team if typ[c] == 'Prism' and team[c] == us]
    if not pr: return None
    p = pr[0]; E = {}
    for line in out.replace('\x00', '').splitlines():
        v = line.split()
        if len(v) >= 13 and v[0] == 'PLE':
            try:
                if len(v) == 13: v.insert(8, '?')
                if int(v[2]) == p: E[int(v[1])] = (v[8], int(v[12]), int(v[13]), int(v[6]) / max(1, int(v[5])))
            except ValueError: pass
    deaths = sorted(x['r'] for x in ev if x['k'] == 'death' and x['v'] == p and x.get('by') is not None)
    rs = sorted(q for q in E if E[q][0] == 'R')
    runs = []; i = 0
    while i < len(rs):
        j = i
        while j + 1 < len(rs) and rs[j + 1] - rs[j] <= 2: j += 1
        r0, r1 = rs[i], rs[j]; i = j + 1
        died = any(r0 <= q <= r1 + 3 for q in deaths)
        rc = collections.Counter(E[q][1] for q in rs if r0 <= q <= r1)
        runs.append(dict(reason=E[r0][1], hp=E[r0][2], n=r1 - r0 + 1, died=died, mix=dict(rc), last=E[r1][1], lasthp=E[r1][2]))
    pre = []
    for r in deaths:
        qs = [q for q in sorted(E) if r - 10 <= q <= r][-4:][::-1]
        pre.append([(E[q][0], E[q][1], E[q][2]) for q in qs])
    return dict(runs=runs, pre=pre)


if __name__ == '__main__':
    root = sys.argv[1]
    dirs = [os.path.join(root, x) for x in os.listdir(root) if os.path.isfile(os.path.join(root, x, 'meta.json'))]
    with Pool(24) as pool: G = [g for g in pool.map(one, dirs, chunksize=8) if g]
    R = [r for g in G for r in g['runs']]; nd = sum(r['died'] for r in R)
    print(f'{len(G)} Prism games, {len(R)} retreats ({len(R) / len(G):.1f} a game), {nd} end in death')

    def tab(name, key, order, S=R):
        g = collections.defaultdict(list)
        for r in S: g[key(r)].append(r)
        print('\n' + name)
        for k in order:
            s = g.get(k)
            if not s: continue
            dd = sum(r['died'] for r in s)
            print(f'  {str(k):34s} {len(s):6d} ({100 * len(s) / len(S):5.1f}%)  die {100 * dd / len(s):5.1f}% = {dd:4d} ({100 * dd / max(1, nd):4.1f}% of retreat deaths)  mean rounds {sum(r["n"] for r in s) / len(s):4.1f}')
    tab('By the reason of its first turn', lambda r: NAMES[r['reason']], list(NAMES.values()))
    hb = lambda h: '<32%' if h < 32 else '<50%' if h < 50 else '<70%' if h < 70 else '<90%' if h < 90 else '90%+'
    tab('Reason x health at the start', lambda r: (NAMES[r['reason']], hb(r['hp'])), [(a, b) for a in NAMES.values() for b in ('<32%', '<50%', '<70%', '<90%', '90%+')])
    tab('Stand lost: by length', lambda r: ('1' if r['n'] == 1 else '2-3' if r['n'] < 4 else '4-7' if r['n'] < 8 else '8+') if r['reason'] == 6 else None, ['1', '2-3', '4-7', '8+'])
    tab('Pack zone: by length', lambda r: ('1' if r['n'] == 1 else '2-3' if r['n'] < 4 else '4-7' if r['n'] < 8 else '8+') if r['reason'] == 2 else None, ['1', '2-3', '4-7', '8+'])
    P = [p for g in G for p in g['pre']]
    for k in range(4):
        c = collections.Counter((p[k][0], NAMES[p[k][1]]) if len(p) > k else ('no turn', '') for p in P)
        print(f'T{k} before a death (decision, reason):', ', '.join(f'{a}/{b} {100 * v / len(P):.0f}%' for (a, b), v in c.most_common(7)))
