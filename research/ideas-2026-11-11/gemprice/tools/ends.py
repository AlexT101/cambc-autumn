"""How losses end: at the round the enemy wins, our score, our carried bags, theirs; the race at earlier marks.
usage: python3 ends.py EXTDIR [MAPSUBSTR]"""
import gzip, json, os, sys, collections
sys.path.insert(0, os.path.dirname(__file__))
from mech import games
ext = sys.argv[1]; sub = sys.argv[2] if len(sys.argv) > 2 else ''
rows = []
for g, us, body in games(ext):
    if sub not in g['map']: continue
    d = ext + '/' + g['dir']
    meta = json.load(open(d + '/meta.json')); R = json.load(gzip.open(d + '/rounds.json.gz'))
    sc = R['gems']; rd = R['round']; n = len(rd)
    bag = [[0] * n, [0] * n]; pb = [0] * n
    names = {c['id']: c['name'] for c in meta['champions']}
    for c in R['champions']:
        for i, x in enumerate(c['gems']): bag[c['team']][i] += x
        if c['team'] == us and names[c['id']] == 'Prism':
            for i, x in enumerate(c['gems']): pb[i] += x
    win = meta['result']['winner'] == us
    def at(r):
        i = min(range(n), key=lambda j: abs(rd[j] - r)); return i
    i600 = next((i for i in range(n) if sc[1 - us][i] >= 600), None)
    row = dict(body=body, win=win, rounds=rd[-1], us=sc[us][-1], them=sc[1 - us][-1], bag=bag[us][-1], pbag=pb[-1], tbag=bag[1 - us][-1],
               r600=rd[i600] if i600 is not None else None, us600=sc[us][i600] if i600 is not None else None,
               bag600=bag[us][i600] if i600 is not None else None, tbag600=bag[1-us][i600] if i600 is not None else None,
               maxbag=max(bag[us][-150:]) if n else 0)
    rows.append(row)
for body in ('Mt3q', 'Flp4'):
    for w in (False, True):
        rs = [r for r in rows if r['body'] == body and r['win'] == w]
        print(f'{body} {"wins" if w else "losses"} {len(rs)}')
        for r in rs[:30]:
            print('  ', r)
