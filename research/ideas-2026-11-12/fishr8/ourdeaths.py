"""Our deaths in live Fish games: per game, deaths and gems lost by our champion type and by Fish's killer type, and
the round. py ourdeaths.py EXT ROWS.json"""
import json, os, sys, collections
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/mitefit')
from mstats import load
ext, rf = sys.argv[1:3]; rows = json.load(open(rf)); idx = json.load(open(ext + '/index.json'))['games']
D = collections.Counter(); G = collections.Counter(); K = collections.Counter(); KG = collections.Counter(); N = 0; W = collections.Counter()
for g in idx:
    mid = os.path.basename(g['source'])[:-8]
    if mid not in rows: continue
    fish = 1 if rows[mid]['side'] == 'a' else 0
    try: meta, R, ev, mp = load(ext, g['dir'])
    except Exception: continue
    N += 1; typ = {c['id']: c['name'] for c in meta['champions']}; team = {c['id']: c['team'] for c in meta['champions']}
    fw = meta['result'].get('winner') == fish
    for e in ev:
        if e['k'] == 'death' and team[e['v']] != fish:
            t = typ[e['v']]; D[t] += 1; G[t] += e.get('gems', 0); k = typ.get(e.get('by'), 'camp/other') if team.get(e.get('by')) == fish else 'camp/other'
            K[k] += 1; KG[k] += e.get('gems', 0); W[('fishwin' if fw else 'ourwin', 'gems')] += e.get('gems', 0)
            if t == 'Prism': W[('prism', k)] += e.get('gems', 0)
print(f'{N} games; our deaths / gems lost a game by our type:', {t: (round(D[t] / N, 2), round(G[t] / N)) for t in sorted(D, key=lambda x: -G[x])})
print('  by Fish killer:', {t: (round(K[t] / N, 2), round(KG[t] / N)) for t in sorted(K, key=lambda x: -KG[x])})
print('  Prism gems lost by killer a game:', {k[1]: round(v / N) for k, v in W.items() if k[0] == 'prism'})
