"""The state when each of the Prism's retreats began, from pl-trace's PLS/PLE lines: python3 rstart.py EXTROOT/TAG"""
import collections, gzip, json, os, sys, zipfile
from multiprocessing import Pool
import trace as T
ROOT = '/home/ubuntu/cambc-autumn'


def one(d):
    try:
        meta = json.load(open(os.path.join(d, 'meta.json')))
        ev = [json.loads(l) for l in gzip.open(os.path.join(d, 'events.jsonl.gz'), 'rt')]
        names = [t['name'] for t in meta['teams']]; us = 0 if not names[0].startswith('rt-') else 1
        out = zipfile.ZipFile(os.path.join(ROOT, meta['source'])).read(f"team-{'ab'[us]}.stdout").decode('utf-8', 'replace')
    except Exception: return None
    team = {c['id']: c['team'] for c in meta['champions']}; typ = {c['id']: c['name'] for c in meta['champions']}
    pr = [c for c in team if typ[c] == 'Prism' and team[c] == us]
    if not pr: return None
    p = pr[0]; S = {}; E = {}; D = {}
    for line in out.replace('\x00', '').splitlines():
        try: T.parse(line.strip(), p, S, E, D)
        except (ValueError, IndexError): pass
    deaths = sorted(x['r'] for x in ev if x['k'] == 'death' and x['v'] == p and x.get('by') is not None)
    rs = sorted(q for q in E if E[q]['dec'] == 'R' and q in S)
    runs = []; i = 0
    while i < len(rs):
        j = i
        while j + 1 < len(rs) and rs[j + 1] - rs[j] <= 2: j += 1
        r0, r1 = rs[i], rs[j]; i = j + 1
        prev = max((q for q in E if q < r0 and q >= r0 - 2), default=None)
        runs.append(dict(dir=os.path.basename(d), r0=r0, r1=r1, n=r1 - r0 + 1, died=any(r0 <= q <= r1 + 3 for q in deaths), sw=S[r0]['worst'] / max(1, S[r0]['hp']), ew=E[r0]['worst'] / max(1, E[r0]['hp']),
                         pdec=E[prev]['dec'] if prev else '.', pew=E[prev]['worst'] / max(1, E[prev]['hp']) if prev else -1, stun=S[r0]['stunned'],
                         maxsw=max(S[q]['worst'] / max(1, S[q]['hp']) for q in rs if r0 <= q <= r1)))
    return runs


if __name__ == '__main__':
    root = sys.argv[1]
    dirs = [os.path.join(root, x) for x in os.listdir(root) if os.path.isfile(os.path.join(root, x, 'meta.json'))]
    with Pool(24) as pool: R = [r for g in pool.map(one, dirs, chunksize=8) if g for r in g]
    nd = sum(r['died'] for r in R)
    print(f'{len(R)} retreats, {nd} end in death')
    b = lambda x: '0' if x < 0.001 else '<0.25' if x < 0.25 else '<0.5' if x < 0.5 else '<0.75' if x < 0.75 else '<1' if x < 1 else '>=1'
    order = ['0', '<0.25', '<0.5', '<0.75', '<1', '>=1']

    def tab(name, key, order, S=R):
        g = collections.defaultdict(list)
        for r in S: g[key(r)].append(r)
        print('\n' + name)
        for k in order:
            s = g.get(k)
            if not s: continue
            dd = sum(r['died'] for r in s)
            print(f'  {str(k):24s} {len(s):6d} ({100 * len(s) / len(S):5.1f}%)  die {100 * dd / len(s):5.1f}% = {dd:4d} ({100 * dd / max(1, nd):4.1f}%)  mean rounds {sum(r["n"] for r in s) / len(s):4.1f}')
    tab("Worst / health on its tile when the retreat's first turn began", lambda r: b(r['sw']), order)
    tab("Worst / health where the retreat's first turn ended", lambda r: b(r['ew']), order)
    tab('The turn before: decision', lambda r: r['pdec'], sorted({r['pdec'] for r in R}))
    tab('The turn before ended at worst / health', lambda r: b(r['pew']) if r['pew'] >= 0 else None, order)
    tab('The most worst / health at any turn start in the retreat', lambda r: b(r['maxsw']), order)
    tab('First turn began at 0 (no enemy reaches): the most later', lambda r: b(r['maxsw']) if r['sw'] < 0.001 else None, order)
    import random
    random.seed(5)
    L = [r for r in R if r['died'] and r['n'] >= 8 and r['sw'] < 0.001]
    for r in random.sample(L, min(6, len(L))): print(r['dir'], r['r0'], r['r1'], r['n'])
