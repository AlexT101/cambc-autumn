# Mite games: for each round and each of our champions at <= 35% hp with a Mite champion within 5 that one of our
# champions saw this round, did that Mite champion's priority carry the kill-chance offset (>= 6000, < 18000)? Rate
# of our champion dying within 3 rounds, by flag. Also the +2000 retreat flag (2000 <= p < 6000 contact band) and
# whether that Mite champion's distance to its own spawn falls in the next 3 rounds.
import json, gzip, os, collections
import numpy as np
ana = os.path.expanduser('~/tmp-offload/bigl/ana'); games = json.load(open(os.path.expanduser('~/tmp-offload/bigl/games.json')))
idx = json.load(open(ana + '/index.json'))['games']; done = set()
kill = collections.Counter(); ret = collections.Counter(); ng = 0
for g in idx:
    m = os.path.basename(g['source']).split('.')[0]; gm = games.get(m)
    if not gm or 'Mite' not in gm['opp_name'] or g['dir'] in done: continue
    done.add(g['dir']); ng += 1
    d = ana + '/' + g['dir']; R = json.load(gzip.open(d + '/rounds.json.gz'))
    mp = json.load(open(ana + '/maps/' + os.path.basename(json.load(open(d + '/meta.json'))['mapFile'])))
    us = 0 if gm['side'] == 'a' else 1
    C = R['champions']; mine = [c for c in C if c['team'] == us]; theirs = [c for c in C if c['team'] != us]
    sp = mp['spawn'][1 - us]
    def spd(x, y): return max(max(sp['minX'] - x, 0, x - sp['maxX']), max(sp['minY'] - y, 0, y - sp['maxY']))
    n = len(R['round'])
    seen_by_us = [set() for _ in range(n)]
    for c in mine:
        for i in range(n):
            for e in c['sees'][i] or []: seen_by_us[i].add(e)
    for i in range(n - 4):
        for e in theirs:
            if e['id'] not in seen_by_us[i] or not e['alive'][i] or e['x'][i] is None: continue
            p = e['prio'][i]
            # kill-chance flag against one of our low champions
            for c in mine:
                if not c['alive'][i] or c['x'][i] is None or c['hp'][i] > 0.35 * c['maxHp'][i]: continue
                dd = max(abs(c['x'][i] - e['x'][i]), abs(c['y'][i] - e['y'][i]))
                if dd > 5: continue
                flag = 6000 <= p < 18000
                died = any(not c['alive'][j] for j in range(i + 1, i + 4))
                kill[(flag, died)] += 1
            # retreat flag: 2000-offset contact codes
            if 2000 <= p < 6000 or 7000 <= p < 8000:
                a, b = spd(e['x'][i], e['y'][i]), (spd(e['x'][i + 3], e['y'][i + 3]) if e['alive'][i + 3] and e['x'][i + 3] is not None else None)
                if b is not None: ret[('flag', b < a)] += 1
            elif 0 < p < 200:
                a, b = spd(e['x'][i], e['y'][i]), (spd(e['x'][i + 3], e['y'][i + 3]) if e['alive'][i + 3] and e['x'][i + 3] is not None else None)
                if b is not None: ret[('contact', b < a)] += 1
print('Mite games', ng)
for f in (True, False):
    t = kill[(f, True)] + kill[(f, False)]
    print(f'kill flag {f}: situations {t}, our low champion dies within 3 rounds {100*kill[(f,True)]/max(t,1):.1f}%')
for f in ('flag', 'contact'):
    t = ret[(f, True)] + ret[(f, False)]
    print(f'{f}: {t} sightings, moves toward own spawn over 3 rounds {100*ret[(f,True)]/max(t,1):.1f}%')
