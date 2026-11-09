"""Render one episode: ocean's path (digits = turn), the model's zero-exposure walk (letters), pursuers' actual tiles."""
import json, gzip, sys
import numpy as np
sys.path.insert(0, __import__('os').path.dirname(__file__))
import retreat_audit as ra
ex = 'replays/retreat-analysis'
idx = {g['source']: g for g in json.load(open(f'{ex}/index.json'))['games']}
def show(r):
    g = idx[r['src']]; t = r['team']; c = r['champ']
    M = json.load(open(f"{ex}/maps/{g['mapHash']}.json"))
    R = json.load(gzip.open(f"{ex}/{g['dir']}/rounds.json.gz"))
    meta = json.load(open(f"{ex}/{g['dir']}/meta.json"))
    team_of = {x['id']: x['team'] for x in meta['champions']}; type_of = {x['id']: x['type'] for x in meta['champions']}
    ridx = {x: i for i, x in enumerate(R['round'])}; ch = {x['id']: x for x in R['champions']}
    W, H = M['width'], M['height']
    i0 = ridx[r['r0'] - 1]; p0 = (ch[c]['x'][i0], ch[c]['y'][i0])
    canvas = {}
    for p in M['walls']: canvas[tuple(p)] = '#'
    for p in M['holes']: canvas[tuple(p)] = 'o'
    for p in M['bushes']: canvas[tuple(p)] = '"'
    for p in M['altars']: canvas[tuple(p)] = 'A'
    for cmp in M['camps']: canvas[(cmp['x'], cmp['y'])] = 'c'
    s = M['spawn'][t]
    for x in range(s['minX'], s['maxX'] + 1):
        for y in range(s['minY'], s['maxY'] + 1): canvas[(x, y)] = 'S'
    pts = [p0]
    for k in range(r['K']):
        i = ridx.get(r['r0'] + k)
        if i is None or not ch[c]['alive'][i] or ch[c]['x'][i] is None or ch[c]['x'][i] < 0: break
        q = (ch[c]['x'][i], ch[c]['y'][i]); pts.append(q); canvas[q] = str((k + 1) % 10)
    canvas[p0] = '@'
    foe_tr = []
    for f in ch:
        if team_of[f] == t: continue
        tr = []
        for k in range(-1, r['K']):
            i = ridx.get(r['r0'] + k)
            if i is None or not ch[f]['alive'][i] or ch[f]['x'][i] is None or ch[f]['x'][i] < 0: continue
            q = (ch[f]['x'][i], ch[f]['y'][i]); tr.append(q)
        if tr and max(abs(tr[0][0] - p0[0]), abs(tr[0][1] - p0[1])) <= 10:
            foe_tr.append((ra.NAMES[type_of[f]], tr))
            for j, q in enumerate(tr): canvas.setdefault(q, 'e') if j else None
            canvas[tr[0]] = 'E'
    xs = [p[0] for p in pts] + [q[0] for _, tr in foe_tr for q in tr]; ys = [p[1] for p in pts] + [q[1] for _, tr in foe_tr for q in tr]
    x0, x1, y0, y1 = max(0, min(xs) - 5), min(W - 1, max(xs) + 5), max(0, min(ys) - 5), min(H - 1, max(ys) + 5)
    print(f"{r['src']} {r['type']} champ {c} r{r['r0']}-{r['r1']} died {r['died']} hp {r['hp']}/{r['maxhp']} home {r['home']}->{r['end_home']} K {r['K']} act {r['act']} opt_walk {r['opt_walk']} stunned {r['stunned']} taken {r['taken']:.0f} killer {r['killer']}")
    print('  pursuers', [(n, tr[:r['K'] + 1]) for n, tr in foe_tr])
    for y in range(y1, y0 - 1, -1):
        print('  ' + ''.join(canvas.get((x, y), '.') for x in range(x0, x1 + 1)))
rows = [json.loads(l) for l in open(sys.argv[1])]
sel = [r for r in rows if r['died'] and r['killer'] not in (None, 'camp') and r['stunned'] == 0 and r['opt_walk']['act'] == 0 and r['act'] > 0 and 3 <= r['K'] <= 8]
import random; random.seed(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
for r in random.sample(sel, 3): show(r); print()
