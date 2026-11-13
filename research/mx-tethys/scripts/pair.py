"""Cassi & Issac: distance between the bodies over time and at pair deaths; which body was the primary victim;
killer type; enemies/allies near the primary victim. Mirror W/L."""
import gzip, json, sys
from collections import defaultdict, Counter
from pathlib import Path
root = Path(sys.argv[1]); bname = sys.argv[2]; mx = int(sys.argv[3]) if len(sys.argv) > 3 else 10**9
cheb = lambda a, b: max(abs(a[0]-b[0]), abs(a[1]-b[1]))
dist_hist = defaultdict(Counter); death = defaultdict(Counter); n = 0; deaths = Counter()
for dd in sorted(root.iterdir()):
    mf = dd / 'meta.json'
    if not mf.exists(): continue
    m = json.loads(mf.read_text())
    if bname not in (m.get('source') or ''): continue
    names = {x['id']: x['name'] for x in m['champions']}; team = {x['id']: x['team'] for x in m['champions']}
    if 'Cassi' not in names.values(): continue
    try:
        R = json.load(gzip.open(dd / 'rounds.json.gz')); ev = [json.loads(l) for l in gzip.open(dd / 'events.jsonl.gz', 'rt')]
    except Exception: continue
    n += 1
    if n > mx: break
    w = m['result']['winner']
    rix = {r: i for i, r in enumerate(R['round'])}
    C = {c['id']: c for c in R['champions']}
    pairs = {}
    for t in (0, 1):
        ids = [i for i in names if team[i] == t and names[i] in ('Cassi', 'Issac')]
        if len(ids) == 2: pairs[t] = sorted(ids, key=lambda i: names[i])  # Cassi, Issac
    for t, (ca, isx) in pairs.items():
        side = 'W' if t == w else 'L'
        for i in range(0, len(R['round']), 3):
            if C[ca]['alive'][i] and C[ca]['x'][i] is not None and C[isx]['x'][i] is not None:
                d = cheb((C[ca]['x'][i], C[ca]['y'][i]), (C[isx]['x'][i], C[isx]['y'][i]))
                dist_hist[side]['0-2' if d <= 2 else '3-5' if d <= 5 else '6-10' if d <= 10 else '11+'] += 1
    for e in ev:
        if e['k'] != 'death' or e.get('linked') is not None: continue
        v = e['v']
        if names.get(v) not in ('Cassi', 'Issac'): continue
        t = team[v]; side = 'W' if t == w else 'L'
        ca, isx = pairs[t]; other = isx if v == ca else ca
        i = rix.get(e['r'] - 1)
        if i is None or C[v]['x'][i] is None or C[other]['x'][i] is None: continue
        d = cheb((C[v]['x'][i], C[v]['y'][i]), (C[other]['x'][i], C[other]['y'][i]))
        deaths[side] += 1
        death[side]['victim ' + names[v]] += 1
        death[side]['apart ' + ('0-2' if d <= 2 else '3-5' if d <= 5 else '6-10' if d <= 10 else '11+')] += 1
        death[side]['killer ' + names.get(e.get('by'), 'camp')] += 1
        death[side]['phase ' + ('r<=300' if e['r'] <= 300 else 'r>300')] += 1
print('games with the pair', n)
for s in 'WL':
    tot = sum(dist_hist[s].values())
    print(s, 'pair distance share of alive rounds:', {k: f'{v/tot:.2f}' for k, v in sorted(dist_hist[s].items())})
    print(s, 'pair deaths/game', f'{deaths[s]/n:.2f}', {k: f'{v/max(1,deaths[s]):.2f}' for k, v in sorted(death[s].items())})
