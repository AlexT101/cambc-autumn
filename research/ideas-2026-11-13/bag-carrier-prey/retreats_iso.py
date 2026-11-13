#!/usr/bin/env python3
"""The opp unit-turns (non-Vesper 50+ carrier seen, Fish's Vesper >8 from it, 2+ of ours within 6) by branch: our
health, our bag, the carrier's health, Fish within 8 of the carrier (not Vesper, not its twin), ours within 6.
    python3 retreats.py BATCH_DIR EXT_DIR"""
import collections, gzip, json, os, sys, zipfile, statistics as st
batch, ext = sys.argv[1], sys.argv[2]
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))
idx = json.load(open(os.path.join(ext, 'index.json')))['games']
bysrc = {os.path.basename(g['source']): g['dir'] for g in idx}
rowsby = collections.defaultdict(list)
for f in sorted(os.listdir(batch)):
    if not f.endswith('.repl26a') or f not in bysrc: continue
    us = 0 if f[:-8].endswith('-12') else 1
    lines = [l.split() for l in zipfile.ZipFile(os.path.join(batch, f)).read('team-%s.stdout' % 'ab'[us]).decode(errors='replace').splitlines() if l.startswith('BCP ')]
    d = os.path.join(ext, bysrc[f]); m = json.load(open(d + '/meta.json'))
    names = {c['id']: c['name'] for c in m['champions']}
    R = json.load(gzip.open(d + '/rounds.json.gz', 'rt')); C = {c['id']: c for c in R['champions']}; ri = {r: k for k, r in enumerate(R['round'])}
    ours = [c for c in C.values() if c['team'] == us]; fish = [c for c in C.values() if c['team'] != us]
    fv = [c for c in fish if names[c['id']] == 'Vesper Vale']
    for L in lines:
        r, me, br, h, gems, dist, why = int(L[1]), int(L[2]), L[3], int(L[4]), int(L[5]), int(L[6]), L[7]
        chp, ohp, og = float(L[8]), float(L[9]), int(L[10])
        k = ri.get(r)
        if k is None or h not in C or names[h] == 'Vesper Vale' or C[h]['x'][k] is None: continue
        pos = (C[h]['x'][k], C[h]['y'][k])
        vd = min([cheb((v['x'][k], v['y'][k]), pos) for v in fv if v['alive'][k] and v['x'][k] is not None] or [99])
        twin = {'Cassi': 'Issac', 'Issac': 'Cassi'}.get(names[h])
        no = sum(1 for o in ours if o['alive'][k] and o['x'][k] is not None and cheb((o['x'][k], o['y'][k]), pos) <= 6)
        fo = sum(1 for g in fish if g['id'] != h and g['alive'][k] and g['x'][k] is not None and names[g['id']] not in ('Vesper Vale', twin) and cheb((g['x'][k], g['y'][k]), pos) <= 8)
        if vd > 8 and no >= 2 and (fo == 0 or os.environ.get('ALLFO')): rowsby[br + ':' + why].append((ohp, og, chp, fo, no, dist, names[me] if me in names else '?', names[h]))
for br, rows in sorted(rowsby.items(), key=lambda kv: -len(kv[1]))[:12]:
    n = len(rows)
    print(f"{br}: {n}  our hp<0.45 {sum(r[0]<0.45 for r in rows)/n:.0%}  our bag>=16 {sum(r[1]>=16 for r in rows)/n:.0%}  carrier hp<0.5 {sum(r[2]<0.5 for r in rows)/n:.0%}"
          f"  Fish within 8: {dict(sorted(collections.Counter(min(r[3],3) for r in rows).items()))}  ours within 6: {dict(sorted(collections.Counter(min(r[4],4) for r in rows).items()))}  dist med {st.median(r[5] for r in rows)}")
    print('     our champs', dict(collections.Counter(r[6] for r in rows).most_common(6)), ' carriers', dict(collections.Counter(r[7] for r in rows).most_common(5)))
