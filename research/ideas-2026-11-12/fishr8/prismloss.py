"""Our Prism's gem losses in Fish games, per game with our Prism: gems lost by killer, our win rate by loss to
Vesper, and the round and bag of each Vesper kill. py prismloss.py EXT ROWS.json"""
import json, os, sys, collections, statistics as st
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/mitefit')
from mstats import load
ext, rf = sys.argv[1:3]; rows = json.load(open(rf)); idx = json.load(open(ext + '/index.json'))['games']
games = []; kills = []
for g in idx:
    mid = os.path.basename(g['source'])[:-8]
    if mid not in rows: continue
    fish = 1 if rows[mid]['side'] == 'a' else 0
    try: meta, R, ev, mp = load(ext, g['dir'])
    except Exception: continue
    typ = {c['id']: c['name'] for c in meta['champions']}; team = {c['id']: c['team'] for c in meta['champions']}
    if not any(typ[i] == 'Prism' and team[i] != fish for i in typ): continue
    win = meta['result'].get('winner') != fish; lost = collections.Counter()
    for e in ev:
        if e['k'] == 'death' and team[e['v']] != fish and typ[e['v']] == 'Prism':
            k = typ.get(e.get('by'), 'other') if team.get(e.get('by')) == fish else 'other'
            lost[k] += e.get('gems', 0)
            if k == 'Vesper Vale': kills.append((e.get('r', e.get('round', 0)), e.get('gems', 0)))
    games.append((win, lost['Vesper Vale'], sum(lost.values())))
n = len(games); print(f'{n} games with our Prism; win {sum(g[0] for g in games)/n:.3f}; Prism gems lost/game {sum(g[2] for g in games)/n:.0f}, to Vesper {sum(g[1] for g in games)/n:.0f}')
for lo, hi in ((0, 1), (1, 40), (40, 100), (100, 10**6)):
    s = [g for g in games if lo <= g[1] < hi]
    if s: print(f'  lost to Vesper {lo}-{hi}: {len(s)} games, our win {sum(g[0] for g in s)/len(s):.3f}')
if kills:
    print(f'  Vesper kills of our Prism: {len(kills)}, bag median {st.median(k[1] for k in kills)}, bag>=40 {sum(k[1]>=40 for k in kills)}, round median {st.median(k[0] for k in kills)}')
