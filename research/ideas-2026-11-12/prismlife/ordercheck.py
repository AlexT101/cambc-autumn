"""Which priority snapshot gives the team's turn order in the fuel file? In pl-capnp games every instance but the Prism
is charged 100k a turn, so the Prism's entries are the only ones under ~100k: python3 ordercheck.py EXTROOT/capnp"""
import gzip, json, os, struct, sys, zipfile
ROOT = '/home/ubuntu/cambc-autumn'
root = sys.argv[1]
tot = {k: [0, 0] for k in ('prev', 'same', 'prev2', 'id')}
for x in sorted(os.listdir(root))[:60]:
    d = os.path.join(root, x)
    if not os.path.isfile(os.path.join(d, 'meta.json')): continue
    meta = json.load(open(os.path.join(d, 'meta.json'))); R = json.load(gzip.open(os.path.join(d, 'rounds.json.gz')))
    names = [t['name'] for t in meta['teams']]; us = 0 if not names[0].startswith('rt-') else 1
    z = zipfile.ZipFile(os.path.join(ROOT, meta['source'])).read(f"team-{'ab'[us]}.fuel")
    fuel = [struct.unpack_from('<Q', z, i)[0] for i in range(77, len(z) - 7, 8)]
    team = {c['id']: c['team'] for c in meta['champions']}; typ = {c['id']: c['name'] for c in meta['champions']}
    ch = {c['id']: c for c in R['champions']}; rounds = R['round']; idx = {r: i for i, r in enumerate(rounds)}
    ours = sorted(c for c in ch if team[c] == us); pr = [c for c in ours if typ[c] == 'Prism']
    if not pr: continue
    p = pr[0]; n = len(ours); nr = meta['result']['rounds']; draft = len(fuel) - n * nr
    if draft < 0 or draft > 8: continue
    for r in range(5, nr):
        i = idx.get(r)
        if i is None: continue
        chunk = fuel[draft + (r - 1) * n: draft + r * n]
        if len(chunk) < n: break
        low = [k for k, f in enumerate(chunk) if f < 100000]
        if len(low) != 1: continue
        for name, j in (('prev', idx.get(r - 1)), ('same', i), ('prev2', idx.get(r - 2))):
            if j is None: continue
            order = sorted(ours, key=lambda c: (-ch[c]['prio'][j], c))
            tot[name][0] += order.index(p) == low[0]; tot[name][1] += 1
        tot['id'][0] += ours.index(p) == low[0]; tot['id'][1] += 1
for k, (a, b) in tot.items(): print(f'{k:6s} the Prism is the one entry under 100k in {100 * a / max(1, b):.1f}% of {b} rounds')
