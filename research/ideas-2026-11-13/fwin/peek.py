"""One of our games on a map: groups, our positions and deaths.   py peek.py MAP FISH VERSION [rounds...]"""
import json, os, sys, collections
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/mitefit')
from mstats import load
ext = os.path.expanduser(os.environ.get('EXT', '~/tmp-offload/fwin/ours/ext')); rows = json.load(open(os.path.expanduser(os.environ.get('ROWS', '~/tmp-offload/fwin/ours/frows.json'))))
idx = json.load(open(ext + '/index.json'))['games']
mapn, fish, ver = sys.argv[1], int(sys.argv[2]), sys.argv[3]
RR = [int(x) for x in sys.argv[4:]] or [20, 50, 100, 150, 200, 300, 400]
for g in idx:
    m = os.path.basename(g['source'])[:-8]; r = rows.get(m)
    if not r or r['map'] != mapn or r['fish'] != fish or str(r.get('version', r.get('opp'))) != ver: continue
    meta, R, ev, mp = load(ext, g['dir']); typ = {c['id']: c['name'] for c in meta['champions']}; team = {c['id']: c['team'] for c in meta['champions']}
    print(mapn, mp['width'], mp['height'], 'spawn', mp['spawn'], 'altars', mp['altars'], 'fish team', fish)
    for gr in mp['groups']: print('   g', gr['id'], ','.join(sorted(set(gr['types']))), len(gr['types']), 'gold', gr['gold'], 'gems', gr['gems'], 'side', gr.get('side'), gr['tiles'][0])
    for rr in RR:
        i = rr - 1
        print(rr, 'ours', [(typ[c['id']][:4], c['x'][i], c['y'][i], int(c['earned'][i]), c['gems'][i]) for c in R['champions'] if c['team'] != fish])
        print('   fish', [(typ[c['id']][:4], c['x'][i], c['y'][i], int(c['earned'][i]), c['gems'][i]) for c in R['champions'] if c['team'] == fish])
    caps = collections.Counter((('F' if e['team'] == fish else 'U'), e['g']) for e in ev if e['k'] == 'capture' and e['r'] <= max(RR))
    print('captures to r', max(RR), dict(caps))
    print('deaths:', [(e['r'], typ[e['v']][:4], 'F' if team[e['v']] == fish else 'U', typ.get(e.get('by'), 'camp')[:4]) for e in ev if e['k'] == 'death' and e['r'] <= max(RR)])
    break
