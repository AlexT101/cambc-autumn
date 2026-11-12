"""ASCII of a map window: python3 amap.py EXTROOT/TAG/DIR X0 X1 Y0 Y1 [x,y:char ...]   (# wall, o hole, " bush, A altar, camp initials, S our spawn, s theirs)"""
import json, os, sys
d = sys.argv[1]; x0, x1, y0, y1 = map(int, sys.argv[2:6])
meta = json.load(open(os.path.join(d, 'meta.json'))); mp = json.load(open(os.path.join(d, meta['mapFile'])))
names = [t['name'] for t in meta['teams']]; us = 0 if not names[0].startswith('rt-') else 1
g = {}
for t in mp['walls']: g[tuple(t)] = '#'
for t in mp['holes']: g[tuple(t)] = 'o'
for t in mp['bushes']: g[tuple(t)] = '"'
for t in mp['altars']: g[tuple(t)] = 'A'
for c in mp['camps']: g[(c['x'], c['y'])] = {'Wolf': 'w', 'Elk': 'e', 'Golem': 'O', 'Monolith': 'M', 'Gem cluster': 'g', 'Gold cluster': '$'}[c['type']]
for k, sp in enumerate(mp['spawn']):
    for x in range(sp['minX'], sp['maxX'] + 1):
        for y in range(sp['minY'], sp['maxY'] + 1): g[(x, y)] = 'S' if k == us else 's'
for a in sys.argv[6:]:
    xy, c = a.split(':'); x, y = map(int, xy.split(',')); g[(x, y)] = c
print('    ' + ''.join(str(x % 10) for x in range(x0, x1 + 1)))
for y in range(y1, y0 - 1, -1):
    print(f'{y:3d} ' + ''.join(g.get((x, y), '.') for x in range(x0, x1 + 1)))
