"""Where Fish captures to round R (default 300): groups on its own half, ours, or the middle (the map's group side),
captures and base gold a game, with Vesper's part. py where.py EXT ROWS.json [R]"""
import json, os, sys, collections
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/mitefit')
from mstats import load
ext, rf = sys.argv[1:3]; R = int(sys.argv[3]) if len(sys.argv) > 3 else 300
rows = json.load(open(rf)); idx = json.load(open(ext + '/index.json'))['games']
N = 0; C = collections.Counter(); G = collections.Counter(); V = collections.Counter(); sides = collections.Counter()
for g in idx:
    mid = os.path.basename(g['source'])[:-8]
    if mid not in rows: continue
    fish = 1 if rows[mid]['side'] == 'a' else 0
    try: meta, Rr, ev, mp = load(ext, g['dir'])
    except Exception: continue
    N += 1; typ = {c['id']: c['name'] for c in meta['champions']}
    for e in ev:
        if e['k'] != 'capture' or e['r'] > R or e['team'] != fish: continue
        gr = mp['groups'][e['g']]; s = gr.get('side'); sides[s] += 1
        where = 'own' if s == fish else 'ours' if s == 1 - fish else 'mid'
        C[where] += 1; G[where] += gr['gold']
        if any(typ.get(sh[0]) == 'Vesper Vale' for sh in e['shares']): V[where] += 1
print(f'{N} games, Fish captures to r{R} a game (base gold a game; with Vesper on it):', {w: (round(C[w] / N, 2), round(G[w] / N), round(V[w] / N, 2)) for w in ('own', 'mid', 'ours')}, dict(sides))
