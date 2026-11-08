# Context of every champion-kill death in the decoded scrims: victim side, bag, hp, channel, local numbers,
# isolation, distance from own spawn, round; pickled for tables. usage: deaths.py OUT.pkl
import json, gzip, os, sys, pickle, collections
import numpy as np
ana = os.path.expanduser('~/tmp-offload/bigl/ana'); games = json.load(open(os.path.expanduser('~/tmp-offload/bigl/games.json')))
idx = json.load(open(ana + '/index.json'))['games']
rows = []; done = set()
for g in idx:
    m = os.path.basename(g['source']).split('.')[0]; gm = games.get(m)
    if not gm or g['dir'] in done: continue
    done.add(g['dir'])
    d = ana + '/' + g['dir']
    meta = json.load(open(d + '/meta.json')); R = json.load(gzip.open(d + '/rounds.json.gz'))
    mp = json.load(open(ana + '/maps/' + os.path.basename(meta['mapFile'])))
    ev = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz', 'rt')]
    us = 0 if gm['side'] == 'a' else 1
    C = {c['id']: c for c in R['champions']}
    typ = {c['id']: c['name'] for c in meta['champions']}
    sp = mp['spawn']
    def spd(t, x, y):
        s = sp[t]; return max(max(s['minX'] - x, 0, x - s['maxX']), max(s['minY'] - y, 0, y - s['maxY']))
    n = len(R['round'])
    for e in ev:
        if e['k'] != 'death': continue
        v = e['v']; r = e['r']; i = max(0, r - 2)  # state at end of round r-1
        c = C[v]; t = c['team']
        if c['x'][i] is None: continue
        x, y = c['x'][i], c['y'][i]
        en = al = 0; en_hp = al_hp = 0.0; near_ally = 99
        for o in R['champions']:
            if o['id'] == v or not o['alive'][i] or o['x'][i] is None: continue
            dd = max(abs(o['x'][i] - x), abs(o['y'][i] - y))
            if o['team'] == t:
                near_ally = min(near_ally, dd)
                if dd <= 5: al += 1; al_hp += o['hp'][i]
            elif dd <= 5: en += 1; en_hp += o['hp'][i]
        # first round the victim was seen by any enemy in the 10 rounds before
        seen = [k for k in range(max(0, i - 10), i + 1) if c['seenBy'][k]]
        rows.append(dict(dir=g['dir'], match=m, opp=gm['opp_name'], win=gm['result'] == 'win', ours=t == us, r=r,
                         victim=typ[v], killer=typ.get(e.get('by')) if e.get('by') is not None else 'camp',
                         bag=e.get('gems', 0), hp=c['hp'][i] / c['maxHp'][i], chan=c['chan'][i], en=en, al=al,
                         en_hp=en_hp, al_hp=al_hp, near_ally=near_ally, spawn_d=spd(t, x, y),
                         enemy_spawn_d=spd(1 - t, x, y), seen_before=(i - seen[0]) if seen else -1,
                         linked=bool(e.get('linked')), map=gm['map'], copies=g.get('copies', 1)))
pickle.dump(rows, open(sys.argv[1], 'wb')); print(len(rows))
