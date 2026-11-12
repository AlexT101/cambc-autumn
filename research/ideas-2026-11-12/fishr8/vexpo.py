"""Fish's Vesper's exposure before her Greed (rounds 50-450): rounds she is within 6 of one of ours, the local numbers
(ours within 6 of her vs her mates within 4 of her), her health share, how often we hit her, and her deaths then.
    py vexpo.py EXT ROWS.json"""
import json, os, sys, collections
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/mitefit')
from mstats import load
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))
ext, rf = sys.argv[1:3]; rows = json.load(open(rf)); idx = json.load(open(ext + '/index.json'))['games']
C = collections.Counter(); N = 0; bal = collections.Counter(); hitbal = collections.Counter()
for g in idx:
    mid = os.path.basename(g['source'])[:-8]
    if mid not in rows: continue
    fish = 1 if rows[mid]['side'] == 'a' else 0
    try: meta, R, ev, mp = load(ext, g['dir'])
    except Exception: continue
    typ = {c['id']: c['name'] for c in meta['champions']}; ch = R['champions']; n = len(R['round'])
    V = [c for c in ch if c['team'] == fish and typ[c['id']] == 'Vesper Vale']
    if not V: continue
    v = V[0]; N += 1
    hit = collections.Counter()
    for e in ev:
        if e['k'] in ('attack', 'cast') and e.get('a') in typ and ch[[c['id'] for c in ch].index(e['a'])]['team'] != fish:
            if any(x[0] == v['id'] and x[1] > 0 for x in e.get('dmg', [])): hit[e['r']] += 1
        if e['k'] == 'death' and e['v'] == v['id'] and 50 <= e['r'] <= 450: C['vdeaths'] += 1
    for i in range(49, min(n, 450)):
        if not v['alive'][i] or v['x'][i] is None: continue
        p = (v['x'][i], v['y'][i])
        ours = sum(1 for c in ch if c['team'] != fish and c['alive'][i] and c['x'][i] is not None and cheb(p, (c['x'][i], c['y'][i])) <= 6)
        if not ours: continue
        mates = sum(1 for c in ch if c['team'] == fish and c is not v and c['alive'][i] and c['x'][i] is not None and cheb(p, (c['x'][i], c['y'][i])) <= 4)
        C['rounds'] += 1; k = max(-3, min(3, ours - (mates + 1))); bal[k] += 1; hitbal[k] += hit[i + 1] > 0
        C['hit'] += hit[i + 1] > 0
print(f'{N} games with Fish Vesper: rounds 50-450 within 6 of ours {C["rounds"] / N:.1f} a game, hit by us in {C["hit"] / max(1, C["rounds"]):.2f} of them; her deaths r50-450 {C["vdeaths"] / N:.2f} a game')
print('  numbers (ours within 6 - Fish within 4 of her incl. her): ' + ', '.join(f'{k:+d}: {bal[k] / N:.1f} r/g, hit {hitbal[k] / max(1, bal[k]):.2f}' for k in sorted(bal)))
